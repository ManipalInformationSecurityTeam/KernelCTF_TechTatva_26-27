import { smoothPath, type Point } from '../lib/spline'

/**
 * Route calibration data.
 *
 * Every coordinate is in the pixel space of the supplied map image
 * (1680 x 936). The SVG overlay uses the same viewBox, so a point here
 * is exactly the same spot on the parchment at any zoom level.
 *
 * Control points were placed on the footprint marks already inked on the
 * map (which sit in open corridors) and checked against zoomed crops of
 * the walls. Add `?debug` to the URL to draw them over the map.
 */
export const MAP_WIDTH = 1680
export const MAP_HEIGHT = 936

export interface RouteConfig {
  id: string
  /** Where the route runs, for humans editing this file. */
  label: string
  /** Control points, in map pixels. */
  points: readonly Point[]
  /** Walking speed in map pixels per second. */
  speed: number
  /** Distance between successive prints, in map pixels. */
  stride: number
  /** Seconds before this walker first appears. */
  startDelay: number
  /** Seconds the walker rests at the end before starting over. */
  restartDelay: number
  /** Short stops along the way: `at` is a fraction of the route length. */
  pauses: readonly { at: number; duration: number }[]
}

const routes: readonly RouteConfig[] = [
  {
    id: 'transfiguration-corridor',
    label: 'Door beside the Astronomy Tower, east along the Dark Arts corridor',
    points: [
      [560, 226], [594, 230], [620, 216], [634, 201], [647, 197],
      [668, 199], [690, 192], [713, 188], [740, 197],
    ],
    speed: 27,
    stride: 12,
    startDelay: 0.4,
    restartDelay: 3.2,
    pauses: [{ at: 0.42, duration: 1.4 }],
  },
  {
    id: 'north-tower-passage',
    label: 'Passage beneath the North Tower, down to the central spine',
    points: [
      [884, 160], [886, 183], [899, 199], [912, 208], [930, 224],
      [946, 233], [962, 233], [972, 252], [978, 270], [986, 286],
    ],
    speed: 31,
    stride: 12.5,
    startDelay: 2.6,
    restartDelay: 4.4,
    pauses: [{ at: 0.55, duration: 1.1 }],
  },
  {
    id: 'library-corridor',
    label: 'Along the top of the Library and down its eastern flank',
    points: [
      [502, 398], [540, 393], [568, 396], [588, 414], [595, 432],
      [597, 452], [596, 480], [598, 512], [594, 535], [604, 562], [615, 578],
    ],
    speed: 29,
    stride: 12,
    startDelay: 5.1,
    restartDelay: 2.8,
    pauses: [
      { at: 0.3, duration: 1.2 },
      { at: 0.72, duration: 1.8 },
    ],
  },
  {
    id: 'east-spine',
    label: 'Long corridor east of the courtyard, round to the Ravenclaw tower',
    points: [
      [1043, 436], [1034, 462], [1033, 480], [1032, 510], [1030, 545],
      [1022, 570], [1030, 580], [1045, 583], [1075, 584], [1104, 583],
      [1128, 589], [1142, 612], [1150, 634], [1160, 652], [1171, 674],
      [1187, 696], [1204, 710], [1220, 730], [1238, 756],
    ],
    speed: 34,
    stride: 13,
    startDelay: 1.3,
    restartDelay: 5.5,
    pauses: [
      { at: 0.28, duration: 1.6 },
      { at: 0.62, duration: 1.0 },
    ],
  },
  {
    id: 'hufflepuff-passage',
    label: 'Curving passage towards the Hufflepuff common room',
    points: [
      [1372, 384], [1385, 368], [1400, 354], [1424, 344],
      [1446, 336], [1468, 343], [1488, 351],
    ],
    speed: 24,
    stride: 11.5,
    startDelay: 3.8,
    restartDelay: 3.6,
    pauses: [{ at: 0.5, duration: 1.5 }],
  },
  {
    id: 'dungeon-corridor',
    label: 'Corridor above the Slytherin common room, towards the courtyard',
    points: [
      [303, 696], [325, 686], [345, 690], [364, 692], [395, 692],
      [424, 693], [450, 684], [471, 671],
    ],
    speed: 30,
    stride: 12,
    startDelay: 6.4,
    restartDelay: 4.1,
    pauses: [{ at: 0.38, duration: 1.3 }],
  },
  {
    id: 'west-corridor',
    label: 'Long west corridor, down towards the spiral stair',
    points: [[290, 390], [287, 430], [277, 470], [283, 490]],
    speed: 22,
    stride: 11.5,
    startDelay: 4.4,
    restartDelay: 3.9,
    pauses: [{ at: 0.6, duration: 1.2 }],
  },
]

export interface Route extends RouteConfig {
  /** SVG path data generated from `points`. */
  d: string
}

export const ROUTES: readonly Route[] = routes.map((r) => ({
  ...r,
  d: smoothPath(r.points),
}))
