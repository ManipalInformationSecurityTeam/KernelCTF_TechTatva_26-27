interface MapControlsProps {
  paused: boolean
  onTogglePause: () => void
  onReset: () => void
  /** Offered only once the map has been zoomed in. */
  showRecenter: boolean
  onRecenter: () => void
}

const icon = {
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
}

export function MapControls({
  paused,
  onTogglePause,
  onReset,
  showRecenter,
  onRecenter,
}: MapControlsProps) {
  return (
    <div className="controls" role="group" aria-label="Footstep controls">
      <button
        type="button"
        className="ink-button"
        onClick={onTogglePause}
        aria-pressed={paused}
        title={paused ? 'Let the footsteps walk again (Space)' : 'Hold the footsteps still (Space)'}
      >
        {paused ? (
          <svg {...icon}>
            <path d="M8 5.5v13l11-6.5z" />
          </svg>
        ) : (
          <svg {...icon}>
            <path d="M8.5 5.5v13M15.5 5.5v13" />
          </svg>
        )}
        <span>{paused ? 'Resume' : 'Pause'}</span>
      </button>

      <button
        type="button"
        className="ink-button"
        onClick={onReset}
        title="Begin the footsteps again from the start"
      >
        <svg {...icon}>
          <path d="M4.5 12a7.5 7.5 0 1 0 2.4-5.5" />
          <path d="M4 4.5v4.2h4.2" />
        </svg>
        <span>Reset</span>
      </button>

      {showRecenter && (
        <button
          type="button"
          className="ink-button ink-button--quiet"
          onClick={onRecenter}
          title="Return to the whole map (or double-click the map)"
        >
          <svg {...icon}>
            <path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" />
          </svg>
          <span>Whole map</span>
        </button>
      )}
    </div>
  )
}
