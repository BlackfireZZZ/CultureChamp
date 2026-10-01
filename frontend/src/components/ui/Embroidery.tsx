type Thread = "main" | "strong" | "muted"
type Stitch = { column: number; row: number; thread: Thread }

function stitchField(variant: "panel" | "band"): Stitch[] {
  const marks = new Map<string, Stitch>()
  const add = (column: number, row: number, thread: Thread) => {
    marks.set(`${column}:${row}`, { column, row, thread })
  }
  const diamond = (column: number, row: number, radius: number, thread: Thread) => {
    for (let offset = -radius; offset <= radius; offset += 1) {
      const reach = radius - Math.abs(offset)
      add(column - reach, row + offset, thread)
      add(column + reach, row + offset, thread)
    }
  }

  if (variant === "band") {
    for (let column = 0; column < 36; column += 2) {
      add(column, 0, "muted")
      add(column, 6, "muted")
    }
    for (const center of [6, 18, 30]) {
      diamond(center, 3, 2, "main")
      add(center, 3, "strong")
      add(center - 3, 4, "strong")
      add(center - 4, 3, "main")
      add(center + 3, 4, "strong")
      add(center + 4, 3, "main")
      add(center - 2, 5, "main")
      add(center + 2, 5, "main")
      add(center, 1, "strong")
    }
    for (const column of [0, 12, 24, 35]) diamond(column, 3, 1, "strong")
  } else {
    for (let row = 0; row < 42; row += 1) {
      add(0, row, row % 2 === 0 ? "main" : "strong")
      add(18, row, row % 2 === 0 ? "main" : "strong")
      if (row % 3 === 0) {
        add(2, row, "muted")
        add(16, row, "muted")
      }
    }
    for (let row = 2; row < 41; row += 1) add(9, row, "main")
    for (const center of [7, 21, 35]) {
      diamond(9, center, 4, "strong")
      diamond(9, center, 2, "main")
      add(9, center, "strong")
      for (const side of [-1, 1]) {
        add(9 + side * 5, center, "main")
        add(9 + side * 6, center - 1, "strong")
        add(9 + side * 6, center + 1, "strong")
      }
    }
    for (const row of [14, 28]) {
      for (let step = 1; step <= 5; step += 1) {
        add(9 - step, row - Math.ceil(step / 2), "main")
        add(9 + step, row + Math.ceil(step / 2), "main")
      }
      for (const side of [-1, 1]) {
        add(9 + side * 5, row - 4, "strong")
        add(9 + side * 6, row - 3, "strong")
        add(9 + side * 5, row + 4, "strong")
        add(9 + side * 6, row + 3, "strong")
      }
    }
    for (let column = 2; column <= 16; column += 2) {
      add(column, 0, "muted")
      add(column, 41, "muted")
    }
  }
  return [...marks.values()]
}

const bandStitches = stitchField("band")
const panelStitches = stitchField("panel")

export function Embroidery({ variant }: { variant: "panel" | "band" }) {
  const panel = variant === "panel"
  const stitches = panel ? panelStitches : bandStitches
  return <svg className={`embroidery embroidery-${variant}`} viewBox={panel ? "0 0 190 420" : "0 0 360 70"} aria-hidden="true" focusable="false">
    {stitches.map(({ column, row, thread }) => {
      const x = column * 10 + 5
      const y = row * 10 + 5
      return <path key={`${column}:${row}`} className={`thread-${thread}`} d={`M${x - 3.5} ${y - 3.5}l7 7m0-7l-7 7`} />
    })}
  </svg>
}
