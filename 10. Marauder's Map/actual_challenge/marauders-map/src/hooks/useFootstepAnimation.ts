import { useCallback, useEffect, useRef, type RefObject } from 'react'
import type { Route } from '../data/routes'
import { LEFT_FOOT_ID, RIGHT_FOOT_ID } from '../components/Footprint'

/** How the ink behaves once a print has been made. */
const INK_IN = 0.16 // seconds for a fresh print to sink into the paper
const INK_HOLD = 1.8 // seconds a print stays at full strength
const INK_FADE = 8.5 // seconds it then takes to vanish
const INK_MAX = 0.8 // never fully opaque, so the map's own ink shows through

const FOOT_SCALE = 0.84
const FOOT_OFFSET = 2.9 // sideways distance of each foot from the route centreline
const MAX_FRAME = 0.05 // clamp huge gaps (background tab) so walkers don't leap

interface Print {
  el: SVGUseElement
  born: number
  alive: boolean
  shown: number
}

interface Walker {
  route: Route
  path: SVGPathElement
  length: number
  prints: Print[]
  cursor: number
  phase: 'waiting' | 'walking' | 'resting'
  timer: number
  s: number
  nextStep: number
  foot: 0 | 1
  pauseIndex: number
  pauseLeft: number
}

interface Options {
  paused: boolean
  /** When true the walkers don't loop on their own; a static trail is drawn. */
  reducedMotion: boolean
}

/**
 * Drives every walker along its route. All per-frame work happens on the DOM
 * nodes directly, so React never re-renders while the footprints move.
 */
export function useFootstepAnimation(
  containerRef: RefObject<SVGGElement | null>,
  routes: readonly Route[],
  { paused, reducedMotion }: Options,
) {
  const pausedRef = useRef(paused)
  const controlsRef = useRef<{ reset: () => void; wake: () => void } | null>(null)

  useEffect(() => {
    pausedRef.current = paused
    if (!paused) controlsRef.current?.wake()
  }, [paused])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const walkers: Walker[] = []
    for (const route of routes) {
      const group = container.querySelector<SVGGElement>(`[data-route="${route.id}"]`)
      const path = group?.querySelector<SVGPathElement>('[data-route-path]')
      if (!group || !path) continue
      const prints = Array.from(group.querySelectorAll<SVGUseElement>('[data-footprint]')).map(
        (el): Print => ({ el, born: 0, alive: false, shown: 0 }),
      )
      walkers.push({
        route,
        path,
        length: path.getTotalLength(),
        prints,
        cursor: 0,
        phase: 'waiting',
        timer: route.startDelay,
        s: 0,
        nextStep: 0,
        foot: 0,
        pauseIndex: 0,
        pauseLeft: 0,
      })
    }

    let now = 0
    let rate = pausedRef.current ? 0 : 1
    let raf = 0
    let last = 0
    let running = false

    const hide = (p: Print) => {
      p.alive = false
      p.shown = 0
      p.el.style.opacity = '0'
    }

    const place = (w: Walker, distance: number) => {
      const d = Math.min(Math.max(distance, 0), w.length)
      const a = w.path.getPointAtLength(Math.max(d - 3.5, 0))
      const b = w.path.getPointAtLength(Math.min(d + 3.5, w.length))
      const p = w.path.getPointAtLength(d)
      let tx = b.x - a.x
      let ty = b.y - a.y
      const mag = Math.hypot(tx, ty) || 1
      tx /= mag
      ty /= mag
      // Left foot sits to the walker's left (screen-space normal flips with side).
      const side = w.foot === 0 ? -1 : 1
      const x = p.x + -ty * side * FOOT_OFFSET
      const y = p.y + tx * side * FOOT_OFFSET
      const angle = (Math.atan2(ty, tx) * 180) / Math.PI + 90

      const print = w.prints[w.cursor]
      w.cursor = (w.cursor + 1) % w.prints.length
      print.el.setAttribute('href', `#${w.foot === 0 ? LEFT_FOOT_ID : RIGHT_FOOT_ID}`)
      print.el.setAttribute(
        'transform',
        `translate(${x.toFixed(2)} ${y.toFixed(2)}) rotate(${angle.toFixed(1)}) scale(${FOOT_SCALE})`,
      )
      print.born = now
      print.alive = true
      print.shown = -1
      w.foot = w.foot === 0 ? 1 : 0
    }

    const startWalk = (w: Walker) => {
      w.phase = 'walking'
      w.s = 0
      w.nextStep = 0
      w.pauseIndex = 0
      w.pauseLeft = 0
      w.foot = 0
    }

    const stepWalker = (w: Walker, dt: number) => {
      const { route } = w
      if (w.phase === 'waiting') {
        w.timer -= dt
        if (w.timer <= 0) startWalk(w)
        else return
      }
      if (w.phase === 'resting') {
        w.timer -= dt
        if (w.timer <= 0) startWalk(w)
        else return
      }

      if (w.pauseLeft > 0) {
        w.pauseLeft -= dt
        return
      }

      w.s = Math.min(w.s + route.speed * dt, w.length)
      const pause = route.pauses[w.pauseIndex]
      if (pause && w.s >= pause.at * w.length) {
        w.s = pause.at * w.length
        w.pauseLeft = pause.duration
        w.pauseIndex++
      }
      while (w.nextStep <= w.s) {
        place(w, w.nextStep)
        w.nextStep += route.stride
      }
      if (w.s >= w.length) {
        w.phase = 'resting'
        w.timer = route.restartDelay
      }
    }

    const fade = () => {
      for (const w of walkers) {
        for (const p of w.prints) {
          if (!p.alive) continue
          const age = now - p.born
          const strength =
            Math.min(1, age / INK_IN) *
            (age < INK_HOLD ? 1 : 1 - (age - INK_HOLD) / INK_FADE)
          if (age > INK_HOLD && strength <= 0.01) {
            hide(p)
            continue
          }
          const o = Math.round(strength * strength * INK_MAX * 100) / 100
          if (o !== p.shown) {
            p.shown = o
            p.el.style.opacity = String(o)
          }
        }
      }
    }

    const frame = (t: number) => {
      const dt = Math.min((t - last) / 1000, MAX_FRAME)
      last = t
      const target = pausedRef.current ? 0 : 1
      // Ease the walking rate so pausing and resuming glide rather than snap.
      rate += (target - rate) * Math.min(1, dt * 5)
      if (Math.abs(target - rate) < 0.004) rate = target

      const vdt = dt * rate
      if (vdt > 0) {
        now += vdt
        for (const w of walkers) stepWalker(w, vdt)
        fade()
      }

      if (rate === 0 && target === 0) {
        running = false
        return
      }
      raf = requestAnimationFrame(frame)
    }

    const wake = () => {
      if (running) return
      running = true
      last = performance.now()
      raf = requestAnimationFrame(frame)
    }

    /** A frozen snapshot of a trail behind each walker, for reduced motion. */
    const drawStaticTrail = () => {
      for (const w of walkers) {
        const count = Math.min(w.prints.length - 1, Math.floor((w.length * 0.62) / w.route.stride))
        w.foot = 0
        for (let i = 0; i < count; i++) {
          // Earlier prints were made longer ago, so they are fainter.
          now = -(INK_HOLD * 0.5 + (INK_FADE * 0.8 * (count - 1 - i)) / count)
          place(w, i * w.route.stride)
        }
      }
      now = 0
      fade()
    }

    const reset = () => {
      for (const w of walkers) {
        for (const p of w.prints) hide(p)
        w.cursor = 0
        w.phase = 'waiting'
        w.timer = w.route.startDelay
        w.s = 0
        w.nextStep = 0
        w.pauseIndex = 0
        w.pauseLeft = 0
        w.foot = 0
      }
      now = 0
    }

    controlsRef.current = {
      reset: () => {
        reset()
        wake()
      },
      wake,
    }

    if (reducedMotion && pausedRef.current) {
      drawStaticTrail()
    } else {
      wake()
    }

    return () => {
      cancelAnimationFrame(raf)
      running = false
      controlsRef.current = null
      for (const w of walkers) for (const p of w.prints) hide(p)
    }
  }, [containerRef, routes, reducedMotion])

  const reset = useCallback(() => controlsRef.current?.reset(), [])
  return { reset }
}
