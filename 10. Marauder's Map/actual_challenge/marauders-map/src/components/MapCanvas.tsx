import { useEffect, useImperativeHandle, useRef, type Ref, type RefObject } from 'react'
import mapUrl from '../assets/marauders-map.png'
import { MAP_HEIGHT, MAP_WIDTH, type Route } from '../data/routes'
import { FootprintDefs, FootprintPool } from './Footprint'

export interface MapViewApi {
  /** Return to the starting view (fit on desktop, height-filling on phones). */
  resetView: () => void
}

interface MapCanvasProps {
  routes: readonly Route[]
  /** Receives the <g> that holds every walker; the animation hook drives it. */
  footprintsRef: RefObject<SVGGElement | null>
  viewRef?: Ref<MapViewApi>
  /** Draw the calibrated routes over the map. */
  debug?: boolean
  /** Fires when the map is zoomed in past its starting view, and back. */
  onZoomedChange?: (zoomed: boolean) => void
}

interface View {
  scale: number
  x: number
  y: number
  fit: number
  initial: number
  max: number
  touched: boolean
}

const DESKTOP_MARGIN = 0.975
const MAX_ZOOM_FACTOR = 6

/**
 * The parchment, the footprint overlay and the title all live in one "stage"
 * that is exactly as large as the map image (1680 x 936). Zooming and
 * panning only change that stage's transform, so the image, labels and every
 * footprint are scaled together and cannot drift out of alignment.
 */
export function MapCanvas({
  routes,
  footprintsRef,
  viewRef,
  debug = false,
  onZoomedChange,
}: MapCanvasProps) {
  const viewportRef = useRef<HTMLDivElement>(null)
  const stageRef = useRef<HTMLDivElement>(null)
  const view = useRef<View>({ scale: 1, x: 0, y: 0, fit: 1, initial: 1, max: 6, touched: false })
  const zoomedRef = useRef(false)
  const onZoomedRef = useRef(onZoomedChange)
  const apiRef = useRef<MapViewApi | null>(null)

  useEffect(() => {
    onZoomedRef.current = onZoomedChange
  }, [onZoomedChange])

  useEffect(() => {
    const viewport = viewportRef.current
    const stage = stageRef.current
    if (!viewport || !stage) return
    const v = view.current

    const clamp = () => {
      const vw = viewport.clientWidth
      const vh = viewport.clientHeight
      const w = MAP_WIDTH * v.scale
      const h = MAP_HEIGHT * v.scale
      v.x = w <= vw ? (vw - w) / 2 : Math.min(0, Math.max(vw - w, v.x))
      v.y = h <= vh ? (vh - h) / 2 : Math.min(0, Math.max(vh - h, v.y))
    }

    const apply = () => {
      clamp()
      stage.style.transform = `translate3d(${v.x}px, ${v.y}px, 0) scale(${v.scale})`
      const zoomed = v.scale > v.initial * 1.04
      viewport.dataset.zoomed = zoomed ? 'true' : 'false'
      if (zoomed !== zoomedRef.current) {
        zoomedRef.current = zoomed
        onZoomedRef.current?.(zoomed)
      }
    }

    const computeBounds = () => {
      const vw = viewport.clientWidth
      const vh = viewport.clientHeight
      const contain = Math.min(vw / MAP_WIDTH, vh / MAP_HEIGHT)
      v.fit = contain * DESKTOP_MARGIN
      // On narrow screens, fill the height and let the person pan sideways
      // rather than shrinking every wall and label to illegibility.
      const narrow = vw < 760 || vw / vh < 1.05
      v.initial = narrow ? Math.max(v.fit, vh / MAP_HEIGHT) : v.fit
      v.max = Math.max(v.initial * MAX_ZOOM_FACTOR, 3)
    }

    const centerOn = (scale: number, mapX = MAP_WIDTH / 2, mapY = MAP_HEIGHT / 2) => {
      v.scale = scale
      v.x = viewport.clientWidth / 2 - mapX * scale
      v.y = viewport.clientHeight / 2 - mapY * scale
    }

    const resetView = () => {
      computeBounds()
      v.touched = false
      centerOn(v.initial)
      apply()
    }

    /** Zoom by `factor`, keeping the map point under (cx, cy) where it is. */
    const zoomAt = (factor: number, cx: number, cy: number) => {
      const next = Math.min(v.max, Math.max(v.fit, v.scale * factor))
      const k = next / v.scale
      v.x = cx - (cx - v.x) * k
      v.y = cy - (cy - v.y) * k
      v.scale = next
      v.touched = true
      apply()
    }

    resetView()

    const ro = new ResizeObserver(() => {
      computeBounds()
      if (!v.touched) {
        centerOn(v.initial)
      } else {
        v.scale = Math.min(v.max, Math.max(v.fit, v.scale))
      }
      apply()
    })
    ro.observe(viewport)

    // ---- pointer gestures: one finger pans, two fingers pinch ----------------
    const pointers = new Map<number, { x: number; y: number }>()
    let pinchDist = 0

    const local = (e: { clientX: number; clientY: number }) => {
      const r = viewport.getBoundingClientRect()
      return { x: e.clientX - r.left, y: e.clientY - r.top }
    }
    const pinchState = () => {
      const [a, b] = [...pointers.values()]
      return { dist: Math.hypot(a.x - b.x, a.y - b.y), cx: (a.x + b.x) / 2, cy: (a.y + b.y) / 2 }
    }

    const onDown = (e: PointerEvent) => {
      pointers.set(e.pointerId, local(e))
      viewport.setPointerCapture(e.pointerId)
      if (pointers.size === 2) pinchDist = pinchState().dist
      viewport.classList.add('is-dragging')
    }
    const onMove = (e: PointerEvent) => {
      const prev = pointers.get(e.pointerId)
      if (!prev) return
      const cur = local(e)
      pointers.set(e.pointerId, cur)
      if (pointers.size === 1) {
        v.x += cur.x - prev.x
        v.y += cur.y - prev.y
        v.touched = true
        apply()
      } else if (pointers.size === 2) {
        const { dist, cx, cy } = pinchState()
        if (pinchDist > 0) zoomAt(dist / pinchDist, cx, cy)
        pinchDist = dist
      }
    }
    const onUp = (e: PointerEvent) => {
      pointers.delete(e.pointerId)
      if (pointers.size < 2) pinchDist = 0
      if (pointers.size === 0) viewport.classList.remove('is-dragging')
    }
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      const { x, y } = local(e)
      // Trackpad pinch arrives as ctrl+wheel with small deltas.
      const speed = e.ctrlKey ? 0.012 : 0.0016
      zoomAt(Math.exp(-e.deltaY * speed), x, y)
    }
    const onDouble = (e: MouseEvent) => {
      const { x, y } = local(e)
      if (v.scale > v.initial * 1.3) resetView()
      else zoomAt((v.initial * 2.6) / v.scale, x, y)
    }

    viewport.addEventListener('pointerdown', onDown)
    viewport.addEventListener('pointermove', onMove)
    viewport.addEventListener('pointerup', onUp)
    viewport.addEventListener('pointercancel', onUp)
    viewport.addEventListener('wheel', onWheel, { passive: false })
    viewport.addEventListener('dblclick', onDouble)

    apiRef.current = { resetView }

    return () => {
      ro.disconnect()
      viewport.removeEventListener('pointerdown', onDown)
      viewport.removeEventListener('pointermove', onMove)
      viewport.removeEventListener('pointerup', onUp)
      viewport.removeEventListener('pointercancel', onUp)
      viewport.removeEventListener('wheel', onWheel)
      viewport.removeEventListener('dblclick', onDouble)
      apiRef.current = null
    }
  }, [])

  useImperativeHandle(viewRef, () => ({ resetView: () => apiRef.current?.resetView() }), [])

  return (
    <div ref={viewportRef} className="viewport" data-zoomed="false">
      <div ref={stageRef} className="stage" style={{ width: MAP_WIDTH, height: MAP_HEIGHT }}>
        <img
          className="map-image"
          src={mapUrl}
          width={MAP_WIDTH}
          height={MAP_HEIGHT}
          alt="Aged parchment map of a castle's corridors, towers and courtyards, with ink footprints on it"
          draggable={false}
        />

        <svg
          className="overlay"
          viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
          width={MAP_WIDTH}
          height={MAP_HEIGHT}
          aria-hidden="true"
          focusable="false"
        >
          <FootprintDefs />
          <g ref={footprintsRef}>
            {routes.map((r) => (
              <FootprintPool key={r.id} routeId={r.id} d={r.d} showRoute={debug} />
            ))}
          </g>
          {debug &&
            routes.flatMap((r) =>
              r.points.map(([x, y], i) => (
                <circle key={`${r.id}-${i}`} cx={x} cy={y} r={2.2} className="route-debug-point" />
              )),
            )}
        </svg>

        <div className="paper-edge" aria-hidden="true" />

        <header className="map-title">
          <h1>The Marauder&rsquo;s Map</h1>
          <p>I solemnly swear that I am up to no good.</p>
        </header>
      </div>
    </div>
  )
}
