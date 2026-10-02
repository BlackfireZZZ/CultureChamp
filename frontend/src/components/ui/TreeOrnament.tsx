type Thread = "bark" | "gold" | "light"
type Stitch = { x: number; y: number; thread: Thread }
type Point = readonly [number, number]
type Curve = readonly [Point, Point, Point, Point]

const pitch = 7
const marks = new Map<string, Stitch>()

function add(x: number, y: number, thread: Thread) {
  const column = Math.round(x / pitch)
  const row = Math.round(y / pitch)
  if (column < 0 || column > 88 || row < 0 || row > 127) return
  marks.set(`${column}:${row}`, { x: column * pitch, y: row * pitch, thread })
}

function pointOn(curve: Curve, t: number): Point {
  const u = 1 - t
  return [
    u ** 3 * curve[0][0] + 3 * u ** 2 * t * curve[1][0] + 3 * u * t ** 2 * curve[2][0] + t ** 3 * curve[3][0],
    u ** 3 * curve[0][1] + 3 * u ** 2 * t * curve[1][1] + 3 * u * t ** 2 * curve[2][1] + t ** 3 * curve[3][1],
  ]
}

function stem(curve: Curve, startWidth: number, endWidth = 0, thread: Thread = "bark") {
  for (let step = 0; step <= 190; step += 1) {
    const t = step / 190
    const [x, y] = pointOn(curve, t)
    const [nextX, nextY] = pointOn(curve, Math.min(t + .006, 1))
    const length = Math.hypot(nextX - x, nextY - y) || 1
    const normalX = -(nextY - y) / length
    const normalY = (nextX - x) / length
    const radius = (startWidth * (1 - t) + endWidth * t) / 2
    for (let offset = -radius; offset <= radius; offset += pitch * .82) {
      add(x + normalX * offset, y + normalY * offset, Math.abs(offset) < pitch ? thread : "gold")
    }
  }
}

function leaf(x: number, y: number, angle: number, length = 26) {
  const ux = Math.cos(angle)
  const uy = Math.sin(angle)
  const vx = -uy
  const vy = ux
  for (let along = 0; along <= length; along += pitch) {
    const width = Math.sin(Math.PI * along / length) * length * .28
    for (let across = -width; across <= width; across += pitch) {
      add(x + ux * along + vx * across, y + uy * along + vy * across, Math.abs(across) < pitch / 2 ? "light" : "gold")
    }
  }
}

function berry(x: number, y: number, radius = 9) {
  for (let dy = -radius; dy <= radius; dy += pitch) {
    for (let dx = -radius; dx <= radius; dx += pitch) {
      if (dx * dx + dy * dy <= radius * radius) add(x + dx, y + dy, dx + dy > 0 ? "gold" : "light")
    }
  }
}

function flower(x: number, y: number, size = 3) {
  for (let dy = -size; dy <= size; dy += 1) {
    for (let dx = -size; dx <= size; dx += 1) {
      if (Math.abs(dx) + Math.abs(dy) === size || (Math.abs(dx) === 1 && Math.abs(dy) === 1)) {
        add(x + dx * pitch, y + dy * pitch, (dx + dy) % 2 ? "light" : "gold")
      }
    }
  }
  add(x, y, "bark")
}

function bird(x: number, y: number, facing: 1 | -1) {
  const rows = [
    "      xx        ",
    "     xLLxx      ",
    "    xLLLLLxx    ",
    "   xLLLggLLLxxx ",
    "  xggggggggggx ",
    " xggggggggggx  ",
    "  xgggggggggx   ",
    "   xgggggggx    ",
    "    xgggggx     ",
    "      xxx       ",
  ]
  rows.forEach((row, rowIndex) => [...row].forEach((letter, column) => {
    if (letter === " ") return
    const dx = facing === 1 ? column : row.length - column
    add(x + dx * pitch, y + rowIndex * pitch, letter === "L" ? "light" : letter === "g" ? "gold" : "bark")
  }))
  add(x + (facing === 1 ? 10 : 5) * pitch, y + 2 * pitch, "bark")
  stem([[x + 6 * pitch, y + 9 * pitch], [x + 3 * pitch, y + 13 * pitch], [x + pitch, y + 12 * pitch], [x - pitch, y + 15 * pitch]], 0, 0, "gold")
}

const trunk: Curve = [[326, 880], [255, 682], [344, 416], [302, 78]]
stem(trunk, 66, 5)
// Split roots anchor the tree to the page rather than leaving a floating motif.
stem([[324, 857], [264, 853], [190, 888], [102, 884]], 24, 1)
stem([[331, 858], [372, 836], [425, 890], [531, 881]], 22, 1)
stem([[305, 867], [284, 842], [265, 880], [224, 889]], 14, 1)
stem([[349, 861], [390, 862], [391, 887], [432, 890]], 14, 1)

const branches: { curve: Curve; width: number; side: number }[] = [
  { curve: [[294, 698], [222, 645], [122, 707], [30, 627]], width: 21, side: -1 },
  { curve: [[297, 618], [364, 555], [466, 618], [598, 543]], width: 20, side: 1 },
  { curve: [[300, 540], [228, 470], [140, 526], [23, 432]], width: 19, side: -1 },
  { curve: [[312, 471], [384, 395], [474, 461], [603, 340]], width: 18, side: 1 },
  { curve: [[309, 385], [216, 343], [157, 342], [71, 247]], width: 17, side: -1 },
  { curve: [[308, 329], [385, 295], [467, 272], [570, 182]], width: 14, side: 1 },
  { curve: [[304, 262], [231, 218], [216, 164], [170, 90]], width: 12, side: -1 },
  { curve: [[304, 194], [362, 139], [409, 110], [443, 38]], width: 10, side: 1 },
  { curve: [[302, 576], [365, 515], [440, 538], [520, 474]], width: 9, side: 1 },
  { curve: [[302, 435], [240, 381], [178, 401], [115, 362]], width: 9, side: -1 },
  { curve: [[307, 275], [351, 230], [398, 217], [460, 160]], width: 8, side: 1 },
]

for (const { curve, width, side } of branches) {
  stem(curve, width)
  for (const t of [.33, .51, .68, .82]) {
    const [x, y] = pointOn(curve, t)
    const direction = side * (t > .6 ? 1 : -1)
    const tipX = x + direction * (27 + t * 16)
    const tipY = y - 46 - t * 12
    stem([[x, y], [x + direction * 7, y - 17], [tipX - direction * 8, tipY + 13], [tipX, tipY]], 4)
    leaf(tipX - direction * 8, tipY + 11, direction < 0 ? -2.55 : -.6, 23)
    flower(tipX, tipY - 9, 2)
  }
  const [endX, endY] = curve[3]
  flower(endX, endY, 3)
  leaf(endX - side * 18, endY + 15, side < 0 ? -2.6 : -.55, 31)
  leaf(endX - side * 34, endY + 25, side < 0 ? -.7 : -2.45, 26)
}

// Secondary sprays vary in reach and angle; the canopy is deliberately uneven.
for (const [anchor, tip, width] of [
  [[97, 606], [18, 559], 3], [[166, 656], [129, 701], 2],
  [[105, 430], [35, 392], 3], [[180, 468], [114, 435], 2],
  [[111, 261], [34, 220], 2], [[210, 163], [165, 124], 2],
  [[419, 578], [508, 555], 3], [[488, 562], [573, 486], 2],
  [[444, 430], [534, 392], 3], [[527, 345], [582, 291], 2],
  [[438, 250], [513, 216], 2], [[385, 127], [470, 97], 2],
] as const) {
  const [ax, ay] = anchor
  const [tx, ty] = tip
  stem([[ax, ay], [ax + (tx - ax) * .25, ay - 25], [tx - (tx - ax) * .15, ty + 10], [tx, ty]], width)
  leaf(tx - Math.sign(tx - ax) * 8, ty + 12, tx < ax ? -2.45 : -.7, 24)
  flower(tx, ty - 5, 2)
}

// Unequal clusters and birds echo the reference without mirroring the two sides.
for (const [x, y, angle, length] of [
  [102, 613, -1.25, 52], [158, 640, -2.15, 46], [223, 618, -.9, 41],
  [77, 448, -.9, 48], [143, 469, -2.2, 51], [195, 485, -1.1, 38],
  [122, 322, -1.15, 44], [188, 294, -2.35, 42],
  [358, 411, -1.1, 48], [410, 520, -2.2, 52], [452, 340, -.75, 44],
  [66, 593, -2.2, 34], [168, 579, -.5, 35], [101, 407, -1.45, 32],
  [158, 386, -2.7, 34], [467, 478, -.85, 34], [502, 397, -2.5, 37],
  [355, 222, -.5, 31], [408, 177, -2.6, 35],
] as const) leaf(x, y, angle, length)
stem([[109, 648], [100, 663], [90, 674], [91, 687]], 2)
stem([[399, 552], [396, 572], [425, 582], [423, 607]], 2)
for (const [x, y] of [[86, 684], [103, 690], [94, 705], [111, 710], [80, 711], [418, 603], [434, 614], [415, 627], [444, 633], [424, 644]] as const) berry(x, y, 12)
flower(103, 310, 4)
flower(472, 291, 4)
flower(210, 600, 3)
flower(537, 515, 3)
bird(123, 295, 1)
bird(440, 593, -1)

const threadPaths: Record<Thread, string> = { bark: "", gold: "", light: "" }
for (const { x, y, thread } of marks.values()) {
  threadPaths[thread] += `M${x - 2.6} ${y - 2.6}l5.2 5.2m0-5.2l-5.2 5.2`
}

export function TreeOrnament() {
  return <><svg className="tree-ornament" viewBox="0 0 620 900" aria-hidden="true" focusable="false">
    {(["bark", "gold", "light"] as const).map((thread) => <path key={thread} className={`tree-thread-${thread}`} d={threadPaths[thread]} />)}
  </svg><BearOrnament /></>
}
import { BearOrnament } from "./BearOrnament"
import "./ornaments.css"
