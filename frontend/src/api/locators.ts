type SourceLocator = {
  page?: number | null
  section?: string | null
  sheet?: string | null
  table?: string | null
  row_start?: number | null
  column_start?: number | null
}

export function sourceLocationLabel(locator: SourceLocator, lowerCase = false): string {
  let label: string
  if (locator.row_start != null) {
    label = `Таблица ${locator.sheet || locator.table || ""}, строка ${locator.row_start}, столбец ${locator.column_start}`
  } else if (locator.page != null) {
    label = `Страница ${locator.page}`
  } else if (locator.section) {
    label = locator.section.replace(/^Lines /, "Строки ").replace(/^Line /, "Строка ")
    if (label === locator.section) label = `Раздел ${label}`
  } else {
    label = "Место в источнике не указано"
  }
  return lowerCase ? label.charAt(0).toLowerCase() + label.slice(1) : label
}
