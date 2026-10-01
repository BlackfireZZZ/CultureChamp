export function answerParts(text: string): { title: string; body: string; imagePrompt?: boolean }[] | null {
  const match = /^Source-supported: ([\s\S]+?)\n\nInterpretation: ([\s\S]+?)\n\n(New creative proposal|Image prompt): ([\s\S]+)$/.exec(text)
  if (!match) return null
  return [
    { title: "Подтверждено источником", body: match[1] },
    { title: "Интерпретация", body: match[2] },
    { title: match[3] === "Image prompt" ? "Промпт для изображения" : "Новая творческая идея", body: match[4], imagePrompt: match[3] === "Image prompt" },
  ]
}
