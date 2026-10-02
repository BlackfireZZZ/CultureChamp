type Thread = "outline" | "body" | "highlight"
type Point = readonly [number, number]

const pitch = 4
const stitches = new Map<string, { x: number; y: number; thread: Thread }>()

function inside(point: Point, polygon: readonly Point[]) {
  let contained = false
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i]
    const [xj, yj] = polygon[j]
    if ((yi > point[1]) !== (yj > point[1]) && point[0] < (xj - xi) * (point[1] - yi) / (yj - yi) + xi) contained = !contained
  }
  return contained
}

function fill(polygon: readonly Point[], thread: Thread) {
  const xs = polygon.map(([x]) => x)
  const ys = polygon.map(([, y]) => y)
  for (let y = Math.floor(Math.min(...ys) / pitch) * pitch; y <= Math.max(...ys); y += pitch) {
    for (let x = Math.floor(Math.min(...xs) / pitch) * pitch; x <= Math.max(...xs); x += pitch) {
      if (inside([x, y], polygon)) stitches.set(`${x}:${y}`, { x, y, thread })
    }
  }
}

// Drawn from a side-profile bear reference. All visible contours are stitches.
// The receding legs are darker, so all four paws remain legible in profile.
fill([[72, 95], [68, 111], [67, 143], [73, 150], [101, 150], [105, 143], [91, 139], [90, 103]], "outline")
fill([[140, 88], [137, 112], [141, 144], [147, 150], [177, 150], [180, 144], [164, 139], [162, 91]], "outline")
// A high shoulder hump, deep barrel and sloping rump carry the silhouette.
fill([[30, 82], [25, 69], [28, 54], [41, 43], [62, 34], [86, 30], [110, 33], [131, 28], [141, 20], [153, 16], [168, 19], [181, 28], [194, 43], [204, 52], [213, 70], [207, 88], [193, 105], [172, 113], [139, 114], [107, 111], [81, 106], [59, 112], [40, 103]], "body")
// Near legs are substantial and set at different angles, ending in flat paws.
fill([[42, 95], [61, 99], [68, 111], [62, 130], [63, 141], [72, 145], [74, 151], [43, 151], [37, 146], [36, 131], [39, 112]], "body")
fill([[169, 95], [190, 89], [202, 106], [201, 123], [208, 141], [219, 145], [221, 151], [183, 151], [177, 145], [173, 127], [169, 113]], "body")
// The head projects only a little beyond the neck: blunt muzzle, round ear.
fill([[181, 50], [198, 46], [216, 48], [228, 54], [239, 65], [244, 75], [254, 79], [258, 85], [254, 91], [241, 94], [226, 88], [209, 89], [193, 84], [182, 77]], "body")
fill([[204, 52], [204, 42], [209, 38], [216, 39], [221, 44], [219, 54]], "outline")
fill([[185, 51], [190, 45], [195, 46], [199, 51]], "outline")
fill([[50, 60], [65, 43], [85, 37], [103, 39], [119, 46], [118, 56], [94, 52], [68, 61]], "highlight")
fill([[140, 44], [151, 33], [165, 36], [174, 50], [158, 47]], "highlight")
fill([[207, 56], [222, 57], [232, 65], [235, 74], [221, 72], [208, 69]], "highlight")
fill([[236, 80], [248, 80], [256, 84], [252, 88], [240, 87]], "highlight")
fill([[250, 78], [258, 79], [261, 84], [257, 88], [251, 86]], "outline")
fill([[229, 64], [234, 64], [235, 68], [230, 69]], "outline")
// Short cross-stitch claws repeat at the edge of the four paws.
for (const [x, y] of [[97, 149], [101, 149], [173, 149], [177, 149], [70, 150], [74, 150], [214, 150], [218, 150]] as const) {
  fill([[x - 1, y - 2], [x + 2, y - 2], [x + 3, y + 2], [x - 1, y + 2]], "outline")
}

// Stitch-to-stitch color variation suggests fur without inventing a smooth fill.
for (const mark of stitches.values()) {
  if (mark.thread !== "body") continue
  const variation = Math.sin(mark.x * .39 + mark.y * .16) + Math.sin(mark.x * .12 - mark.y * .43)
  if (variation > 1.48 && mark.y < 105) mark.thread = "highlight"
  else if (variation < -1.55) mark.thread = "outline"
}

const paths: Record<Thread, string> = { outline: "", body: "", highlight: "" }
for (const { x, y, thread } of stitches.values()) {
  paths[thread] += `M${x - 1.45} ${y - 1.45}l2.9 2.9m0-2.9l-2.9 2.9`
}

export function BearOrnament() {
  return <svg className="bear-ornament" viewBox="0 0 280 160" aria-hidden="true" focusable="false">
    {(["outline", "body", "highlight"] as const).map((thread) => <path key={thread} className={`bear-thread-${thread}`} d={paths[thread]} />)}
  </svg>
}
