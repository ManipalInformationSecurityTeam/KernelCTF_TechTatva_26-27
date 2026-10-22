/**
 * Footprint artwork and the pool of <use> elements that the animation hook
 * recycles. The shapes are drawn pointing "up" (towards -y) around the origin,
 * roughly 15 map pixels long, so the hook only has to translate and rotate.
 */

export const LEFT_FOOT_ID = 'fp-left'
export const RIGHT_FOOT_ID = 'fp-right'

/** Footprints per walker. Must cover (fade time / step time) with spare. */
export const POOL_SIZE = 28

const SOLE =
  'M-3,-6.5 C-3.2,-8.6 -0.6,-9.4 1.2,-8.7 C3,-8 3.2,-5.8 2.6,-4 ' +
  'C2.2,-2.6 2,-1.2 1.2,-0.2 C0.2,0.8 -2.4,0.4 -3,-1.4 C-3.4,-3 -2.9,-4.9 -3,-6.5 Z'
const HEEL =
  'M-1.9,2.6 C-2.1,1.8 -1.2,1.4 0.2,1.4 C1.5,1.4 2.2,2 2.1,2.9 ' +
  'C2,4.6 1.1,5.7 -0.1,5.7 C-1.3,5.7 -1.9,4.3 -1.9,2.6 Z'
const TREAD = 'M-2.3,-6.2 L1.7,-6.8 M-2.5,-4.2 L2,-4.7 M-2.4,-2.2 L1.7,-2.5'

function Shoe() {
  return (
    <>
      <path d={SOLE} />
      <path d={HEEL} />
      <path d={TREAD} className="fp-tread" />
    </>
  )
}

/** Left and right shoe impressions. Rendered once inside the overlay SVG. */
export function FootprintDefs() {
  return (
    <defs>
      <g id={LEFT_FOOT_ID} className="fp-ink">
        <g transform="translate(0 -1.8) rotate(-5)">
          <Shoe />
        </g>
      </g>
      <g id={RIGHT_FOOT_ID} className="fp-ink">
        <g transform="translate(0 -1.8) scale(-1 1) rotate(-5)">
          <Shoe />
        </g>
      </g>
    </defs>
  )
}

interface FootprintPoolProps {
  routeId: string
  d: string
  showRoute?: boolean
}

/**
 * Everything one walker needs: its (invisible) route path for measuring, and
 * a fixed set of footprint elements. React renders this once; after that the
 * animation hook mutates the elements directly, so no frame ever re-renders.
 */
export function FootprintPool({ routeId, d, showRoute = false }: FootprintPoolProps) {
  return (
    <g data-route={routeId}>
      <path
        data-route-path
        d={d}
        fill="none"
        className={showRoute ? 'route-debug' : undefined}
        stroke={showRoute ? undefined : 'none'}
      />
      {Array.from({ length: POOL_SIZE }, (_, i) => (
        <use key={i} data-footprint href={`#${LEFT_FOOT_ID}`} opacity="0" />
      ))}
    </g>
  )
}
