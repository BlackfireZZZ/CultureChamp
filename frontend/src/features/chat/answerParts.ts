export function answerParts(text: string): { title: string; body: string; imagePrompt?: boolean }[] | null {
  const match = /^(?:Source-supported|Подтверждено источником): ([\s\S]+?)\n\n(?:Interpretation|Интерпретация): ([\s\S]+?)\n\n(New creative proposal|Image prompt|Новая творческая идея|Промпт для изображения): ([\s\S]+)$/.exec(text)
  if (!match) return null
  return [
    { title: "Подтверждено источником", body: match[1] },
    { title: "Интерпретация", body: match[2] },
    { title: match[3] === "Image prompt" || match[3] === "Промпт для изображения" ? "Промпт для изображения" : "Новая творческая идея", body: match[4], imagePrompt: match[3] === "Image prompt" || match[3] === "Промпт для изображения" },
  ]
}
