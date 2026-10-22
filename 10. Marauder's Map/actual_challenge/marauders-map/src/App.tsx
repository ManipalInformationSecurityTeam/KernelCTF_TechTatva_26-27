import { useCallback, useEffect, useRef, useState } from 'react'
import { MapCanvas, type MapViewApi } from './components/MapCanvas'
import { MapControls } from './components/MapControls'
import { OwlPanel } from './components/OwlPanel'
import { SearchBar } from './components/SearchBar'
import { ROUTES } from './data/routes'
import { useFootstepAnimation } from './hooks/useFootstepAnimation'

const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)'
const debug = new URLSearchParams(window.location.search).has('debug')

function useReducedMotion() {
  const [reduced, setReduced] = useState(() => window.matchMedia(REDUCED_MOTION_QUERY).matches)
  useEffect(() => {
    const query = window.matchMedia(REDUCED_MOTION_QUERY)
    const onChange = () => setReduced(query.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])
  return reduced
}

export default function App() {
  const reducedMotion = useReducedMotion()
  // Someone who asked for reduced motion starts with a still trail of prints
  // and can still choose to set the footsteps walking.
  const [paused, setPaused] = useState(reducedMotion)
  const [zoomed, setZoomed] = useState(false)
  const footprintsRef = useRef<SVGGElement>(null)
  const viewRef = useRef<MapViewApi>(null)

  const { reset } = useFootstepAnimation(footprintsRef, ROUTES, { paused, reducedMotion })

  useEffect(() => {
    if (reducedMotion) setPaused(true)
  }, [reducedMotion])

  const togglePause = useCallback(() => setPaused((p) => !p), [])
  const handleReset = useCallback(() => {
    setPaused(false)
    reset()
  }, [reset])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      if (target?.tagName === 'BUTTON' || e.metaKey || e.ctrlKey || e.altKey) return
      if (e.code === 'Space') {
        e.preventDefault()
        togglePause()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [togglePause])

  return (
    <main className="app" data-paused={paused}>
      <MapCanvas
        routes={ROUTES}
        footprintsRef={footprintsRef}
        viewRef={viewRef}
        debug={debug}
        onZoomedChange={setZoomed}
      />
      <MapControls
        paused={paused}
        onTogglePause={togglePause}
        onReset={handleReset}
        showRecenter={zoomed}
        onRecenter={() => viewRef.current?.resetView()}
      />
      <SearchBar />
      <OwlPanel />
    </main>
  )
}
