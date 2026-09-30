export type DemoChat = { id: string; title: string; messages: { role: "user" | "assistant"; text: string }[] }

const chats: DemoChat[] = [
  {
    id: "preview-1",
    title: "Музейная вводная панель",
    messages: [
      { role: "user", text: "Подготовить вводную панель о меняющихся практиках в Приморье." },
      { role: "assistant", text: "Демонстрационный ответ. Проверенные культурные утверждения и ссылки появятся только после одобрения источников и подключения серверного чата." },
    ],
  },
]

export function getDemoChats(): Promise<DemoChat[]> {
  return Promise.resolve(structuredClone(chats))
}

export function createDemoReply(brief: string): Promise<string> {
  if (!brief.trim()) return Promise.reject(new Error("Empty brief"))
  return new Promise((resolve) => window.setTimeout(
    () => resolve("Демонстрационный ответ. Серверная генерация и проверенные ссылки пока не подключены."),
    250,
  ))
}
