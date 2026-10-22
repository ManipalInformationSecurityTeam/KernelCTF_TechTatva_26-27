export type Point = readonly [number, number]

/**
 * Turns a list of control points into a smooth SVG path using a
 * Catmull-Rom spline converted to cubic Béziers. The curve passes
 * through every control point, so a route stays exactly where it was
 * calibrated, while corners are rounded the way a walker would cut them.
 */
export function smoothPath(points: readonly Point[], tension = 0.5): string {
  if (points.length < 2) return ''
  const f = (n: number) => n.toFixed(1)
  let d = `M${f(points[0][0])},${f(points[0][1])}`
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] ?? points[i]
    const p1 = points[i]
    const p2 = points[i + 1]
    const p3 = points[i + 2] ?? p2
    const k = tension / 3
    const c1x = p1[0] + (p2[0] - p0[0]) * k
    const c1y = p1[1] + (p2[1] - p0[1]) * k
    const c2x = p2[0] - (p3[0] - p1[0]) * k
    const c2y = p2[1] - (p3[1] - p1[1]) * k
    d += ` C${f(c1x)},${f(c1y)} ${f(c2x)},${f(c2y)} ${f(p2[0])},${f(p2[1])}`
  }
  return d
}
