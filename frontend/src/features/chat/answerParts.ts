export function answerParts(text: string): { title: string; body: string }[] | null {
  const match = /^Source-supported: ([\s\S]+?)\n\nInterpretation: ([\s\S]+?)\n\nNew creative proposal: ([\s\S]+)$/.exec(text)
  if (!match) return null
  return [
    { title: "Подтверждено источником", body: match[1] },
    { title: "Интерпретация", body: match[2] },
    { title: "Новая творческая идея", body: match[3] },
  ]
}
