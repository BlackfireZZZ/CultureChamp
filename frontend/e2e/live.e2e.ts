import { readFile } from "node:fs/promises"

import { expect, test } from "@playwright/test"

const baseURL = process.env.LIVE_E2E_BASE_URL
const vectorURL = process.env.LIVE_E2E_VECTOR_URL
const adminName = process.env.LIVE_E2E_ADMIN_USER
const adminPassword = process.env.LIVE_E2E_ADMIN_PASSWORD

async function expectNoHorizontalOverflow(page: import("@playwright/test").Page) {
  for (const width of [360, 768, 1280, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    const layout = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      rightmost: [...document.querySelectorAll("body *")]
        .filter((element) => element.getBoundingClientRect().right > window.innerWidth + 1)
        .slice(0, 5)
        .map((element) => `${element.tagName}.${element.className}: ${element.textContent?.slice(0, 50)}`),
    }))
    expect(layout.scrollWidth, layout.rightmost.join(" | ")).toBeLessThanOrEqual(width)
  }
}

test.skip(!baseURL || !vectorURL || !adminName || !adminPassword, "requires an isolated live stack and pilot admin")
test.setTimeout(360_000)

test("live synthetic source flows from admin review to cited chat and revocation", async ({ browser }) => {
  const marker = `live${Date.now()}`
  const title = `Synthetic live table ${marker}`
  const description = `Self-authored catalogue summary ${marker}`
  const reviewedDescription = `Reviewed self-authored catalogue summary ${marker}`
  const region = `Synthetic region ${marker}`
  const cell = `item: ${marker}; count: seven`
  const approvedBrief = `${cell} — summarize the source`
  const csv = Buffer.from(`item,count\r\n${marker},seven\r\n`, "utf8")
  const userName = `user_${marker}`
  const userPassword = "self-authored-live-test-password"
  let approvedRevisionId: string | null = null
  let adminCsrfToken: string | null = null

  const adminContext = await browser.newContext({ baseURL })
  const adminPage = await adminContext.newPage()
  const userContext = await browser.newContext({ baseURL, acceptDownloads: true })
  const userPage = await userContext.newPage()
  try {
    await adminPage.goto("/")
    await adminPage.getByRole("textbox", { name: "Имя пользователя" }).fill(adminName!)
    await adminPage.getByLabel("Пароль").fill(adminPassword!)
    const loginResponse = adminPage.waitForResponse((response) => response.url().endsWith("/api/v1/auth/login"))
    await adminPage.getByRole("button", { name: "Войти" }).click()
    const csrfToken = ((await (await loginResponse).json()) as { csrf_token: string }).csrf_token
    adminCsrfToken = csrfToken
    await expect(adminPage.getByRole("button", { name: "Админка" })).toBeVisible()

    const created = await adminContext.request.post("/api/v1/admin/accounts", {
      headers: { origin: baseURL!, "x-csrf-token": csrfToken },
      data: { username: userName, password: userPassword, role: "user" },
    })
    expect(created.status()).toBe(201)
    await adminPage.getByRole("button", { name: "Админка" }).click()
    const upload = adminPage.getByRole("form", { name: "Загрузка кандидата" })
    await upload.getByLabel("Оригинальный файл").setInputFiles({ name: "synthetic.csv", mimeType: "text/csv", buffer: csv })
    await upload.getByLabel("Ссылка на источник").fill(`https://example.invalid/${marker}`)
    await upload.getByLabel("Название").fill(title)
    await upload.getByLabel("Краткое описание").fill(description)
    await upload.getByLabel("Автор или организация").fill("Self-authored test")
    await upload.getByLabel("Примечание о правах").fill("Self-authored synthetic fixture")
    await upload.getByLabel("Метки, по одной в строке").fill(`region:${region}\ntopic:Synthetic testing`)
    const intakeResponse = adminPage.waitForResponse((response) => response.url().endsWith("/api/v1/admin/sources") && response.request().method() === "POST")
    await upload.getByRole("button", { name: "Загрузить на проверку" }).click()
    const intake = (await (await intakeResponse).json()) as { revision_id: string }

    await userPage.goto("/")
    await userPage.getByRole("textbox", { name: "Имя пользователя" }).fill(userName)
    await userPage.getByLabel("Пароль").fill(userPassword)
    await userPage.getByRole("button", { name: "Войти" }).click()
    await expect(userPage.getByRole("button", { name: "Материалы" })).toBeVisible()
    await userPage.getByRole("button", { name: "Материалы" }).click()
    await expect(userPage.getByText(title)).toHaveCount(0)
    await userPage.getByRole("button", { name: "Вернуться к чату" }).first().click()
    const requestIds: string[] = []
    await userPage.route("**/api/v1/chats/*/messages", async (route) => {
      const payload = route.request().postDataJSON() as { request_id: string }
      requestIds.push(payload.request_id)
      if (requestIds.length === 1) await route.fulfill({ status: 503 })
      else await route.continue()
    })
    await userPage.getByRole("textbox", { name: "Ваш творческий бриф" }).fill(cell)
    await userPage.getByRole("button", { name: "Отправить" }).click()
    await expect(userPage.getByRole("alert")).toContainText("Текст сохранён")
    await expect(userPage.getByRole("textbox", { name: "Ваш творческий бриф" })).toHaveValue(cell)
    await userPage.getByRole("button", { name: "Отправить" }).click()
    await expect(userPage.getByText(/There is no approved source evidence/)).toBeVisible()
    expect(requestIds[1]).toBe(requestIds[0])
    const unsupportedChatTitle = cell

    await expect.poll(async () => {
      const response = await adminContext.request.get(`/api/v1/admin/revisions/${intake.revision_id}`)
      return ((await response.json()) as { status: string }).status
    }, { timeout: 120_000 }).toBe("review_pending")
    await adminPage.reload()
    await adminPage.getByRole("button", { name: "Админка" }).click()
    const inventorySearch = adminPage.getByRole("form", { name: "Поиск в инвентаре" })
    await inventorySearch.getByRole("textbox", { name: "Источник или название" }).fill(marker)
    await inventorySearch.getByRole("combobox", { name: "Формат" }).selectOption("text/csv")
    await inventorySearch.getByRole("combobox", { name: "Тип метки" }).selectOption("region")
    await inventorySearch.getByRole("textbox", { name: "Значение метки" }).fill(region)
    await inventorySearch.getByRole("button", { name: "Найти" }).click()
    await adminPage.getByRole("button", { name: new RegExp(title) }).click()
    await expectNoHorizontalOverflow(adminPage)
    const reviewOriginalPath = `/api/v1/admin/revisions/${intake.revision_id}/original`
    await expect(adminPage.getByRole("link", { name: "Открыть оригинал для проверки" })).toHaveAttribute("href", reviewOriginalPath)
    const reviewOriginal = await adminContext.request.get(reviewOriginalPath)
    expect(reviewOriginal.status()).toBe(200)
    expect(await reviewOriginal.body()).toEqual(csv)
    expect((await userContext.request.get(reviewOriginalPath)).status()).toBe(403)
    const metadataEdit = adminPage.getByRole("form", { name: "Правка метаданных" })
    await metadataEdit.getByRole("textbox", { name: "Краткое описание" }).fill(reviewedDescription)
    await metadataEdit.getByRole("textbox", { name: "Метки, по одной в строке" }).fill(`region:${region}\ntopic:Reviewed synthetic testing`)
    await metadataEdit.getByRole("textbox", { name: "Причина изменения" }).fill("Compared candidate metadata with the original synthetic table")
    await metadataEdit.getByRole("button", { name: "Сохранить описание и метки" }).click()
    await expect(adminPage.getByText(reviewedDescription).first()).toBeVisible()
    await adminPage.getByText("История метаданных").click()
    await expect(adminPage.getByText("Версия 1")).toBeVisible()
    const review = adminPage.getByRole("form", { name: "Одобрение ревизии" })
    await review.getByLabel("Основание и ограничения").fill("Self-authored synthetic CSV for a private live test")
    await review.getByLabel("HTTPS-ссылка на доказательство прав").fill(`https://example.invalid/${marker}/rights`)
    await review.getByLabel(/Показ текстовых фрагментов/).check()
    await review.getByLabel(/Чувствительность материала/).check()
    await review.getByLabel(/Показ оригинального файла/).check()
    await review.getByRole("button", { name: "Одобрить эту ревизию" }).click()
    await expect(adminPage.getByRole("form", { name: "Отзыв ревизии" })).toBeVisible()
    approvedRevisionId = intake.revision_id

    const detail = await adminContext.request.get(`/api/v1/admin/revisions/${intake.revision_id}`)
    const segmentId = ((await detail.json()) as { segments: { segment_id: string }[] }).segments[0].segment_id
    await expect.poll(async () => {
      const response = await fetch(`${vectorURL}/collections/culture_text_e5_small_v1/points`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ ids: [segmentId], with_payload: true, with_vector: false }),
      })
      if (!response.ok) return null
      const data = (await response.json()) as { result: { payload: { revision_id: string } }[] }
      return data.result[0]?.payload.revision_id ?? null
    }, { timeout: 180_000 }).toBe(intake.revision_id)

    await userPage.getByRole("button", { name: "Материалы" }).click()
    const filter = userPage.getByRole("form", { name: "Поиск материалов" })
    await filter.getByRole("textbox", { name: "Регион" }).fill(region)
    await filter.getByRole("button", { name: "Найти" }).click()
    await expect(userPage.getByRole("button", { name: new RegExp(title) })).toBeVisible()
    await expect(userPage.getByText(reviewedDescription)).toBeVisible()
    await filter.getByRole("textbox", { name: "Регион" }).fill("Unrelated region")
    await filter.getByRole("button", { name: "Найти" }).click()
    await expect(userPage.getByRole("heading", { name: "Материалов по запросу не найдено" })).toBeVisible()
    await userPage.getByRole("button", { name: "Вернуться к чату" }).first().click()

    await userPage.getByRole("button", { name: "Новый чат" }).click()
    await userPage.getByRole("textbox", { name: "Ваш творческий бриф" }).fill(approvedBrief)
    await userPage.getByRole("button", { name: "Отправить" }).click()
    await expect(userPage.getByText(/Source-supported:/)).toBeVisible({ timeout: 60_000 })
    await userPage.getByRole("button", { name: unsupportedChatTitle, exact: true }).click()
    await expect(userPage.getByText(/There is no approved source evidence/)).toBeVisible()
    await userPage.getByRole("button", { name: "Удалить чат" }).click()
    await expect(userPage.getByRole("button", { name: unsupportedChatTitle, exact: true })).toHaveCount(0)
    await userPage.getByRole("button", { name: "Новый чат" }).click()
    await expect(userPage.getByText(/Source-supported:/)).toHaveCount(0)
    await userPage.getByRole("button", { name: approvedBrief, exact: true }).click()
    await expect(userPage.getByText(/Source-supported:/)).toBeVisible()
    await expectNoHorizontalOverflow(userPage)
    await userPage.getByRole("button", { name: /Источник · таблица CSV, строка 2/ }).click()
    await expect(userPage.locator(`#segment-${segmentId}`)).toBeFocused()
    await expect(userPage.getByRole("heading", { name: title })).toBeVisible()
    await expectNoHorizontalOverflow(userPage)
    const downloadPromise = userPage.waitForEvent("download")
    await userPage.getByRole("link", { name: "Скачать исходную таблицу CSV" }).click()
    const download = await downloadPromise
    expect(await readFile(await download.path())).toEqual(csv)

    if (process.env.LIVE_E2E_RESET_VECTOR === "true") {
      expect(["127.0.0.1", "localhost"]).toContain(new URL(vectorURL!).hostname)
      const collection = "culture_text_e5_small_v1"
      const dropped = await fetch(`${vectorURL}/collections/${collection}`, { method: "DELETE" })
      expect(dropped.ok).toBe(true)
      await expect.poll(async () => {
        const response = await fetch(`${vectorURL}/collections/${collection}/points`, {
          method: "POST", headers: { "content-type": "application/json" },
          body: JSON.stringify({ ids: [segmentId], with_payload: true, with_vector: false }),
        })
        if (!response.ok) return null
        const data = (await response.json()) as { result: { payload: { revision_id: string } }[] }
        return data.result[0]?.payload.revision_id ?? null
      }, { timeout: 180_000 }).toBe(intake.revision_id)
      await userPage.getByRole("button", { name: "Вернуться к чату" }).first().click()
      await userPage.getByRole("textbox", { name: "Ваш творческий бриф" }).fill(cell)
      await userPage.getByRole("button", { name: "Отправить" }).click()
      await expect(userPage.getByText(/Source-supported:/)).toHaveCount(2)
    }

    const revoke = adminPage.getByRole("form", { name: "Отзыв ревизии" })
    await revoke.getByLabel("Причина отзыва").fill("Self-authored live test completed")
    await revoke.getByRole("button", { name: "Отозвать эту ревизию" }).click()
    await expect.poll(async () => {
      const response = await adminContext.request.get(`/api/v1/admin/revisions/${intake.revision_id}`)
      return ((await response.json()) as { decision: string }).decision
    }).toBe("revoke")
    expect(await (await adminContext.request.get(reviewOriginalPath)).body()).toEqual(csv)
    approvedRevisionId = null
    await userPage.reload()
    await userPage.getByRole("button", { name: approvedBrief, exact: true }).click()
    await expect(userPage.getByText(/Source-supported:/)).toHaveCount(process.env.LIVE_E2E_RESET_VECTOR === "true" ? 2 : 1)
    await expect(userPage.getByRole("button", { name: /Источник · таблица CSV, строка 2/ }).first()).toBeDisabled()
    await expect(userPage.getByText("Источник отозван или недоступен")).toHaveCount(process.env.LIVE_E2E_RESET_VECTOR === "true" ? 2 : 1)
    await userPage.getByRole("button", { name: "Материалы" }).click()
    await expect(userPage.getByText(title)).toHaveCount(0)
  } finally {
    if (approvedRevisionId && adminCsrfToken) {
      await adminContext.request.post(`/api/v1/admin/revisions/${approvedRevisionId}/revoke`, {
        headers: { origin: baseURL!, "x-csrf-token": adminCsrfToken },
        data: { reason: "Live synthetic test cleanup after failure" },
      }).catch(() => undefined)
    }
    await userContext.close()
    await adminContext.close()
  }
})
