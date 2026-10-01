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
    const initialMaterials = await userContext.request.get("/api/v1/materials")
    expect(await initialMaterials.json(), "live check needs an empty approved corpus").toEqual([])
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
    await expect(userPage.getByRole("heading", { name: "Подтверждено источником" })).toBeVisible({ timeout: 60_000 })
    await userPage.getByRole("button", { name: unsupportedChatTitle, exact: true }).click()
    await expect(userPage.getByText(/There is no approved source evidence/)).toBeVisible()
    await userPage.getByRole("button", { name: "Удалить чат" }).click()
    await userPage.getByRole("button", { name: "Подтвердить удаление" }).click()
    await expect(userPage.getByRole("button", { name: unsupportedChatTitle, exact: true })).toHaveCount(0)
    await userPage.getByRole("button", { name: "Новый чат" }).click()
    await expect(userPage.getByRole("heading", { name: "Подтверждено источником" })).toHaveCount(0)
    await userPage.getByRole("button", { name: approvedBrief, exact: true }).click()
    await expect(userPage.getByRole("heading", { name: "Подтверждено источником" })).toBeVisible()
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
      await expect(userPage.getByRole("heading", { name: "Подтверждено источником" })).toHaveCount(2)
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
    await expect(userPage.getByRole("heading", { name: "Подтверждено источником" })).toHaveCount(process.env.LIVE_E2E_RESET_VECTOR === "true" ? 2 : 1)
    await expect(userPage.getByRole("button", { name: /Источник · таблица CSV, строка 2/ }).first()).toBeDisabled()
    await expect(userPage.getByText("Источник отозван или недоступен")).toHaveCount(process.env.LIVE_E2E_RESET_VECTOR === "true" ? 2 : 1)
    await userPage.getByRole("button", { name: "Материалы" }).click()
    await expect(userPage.getByText(title)).toHaveCount(0)

    const brokenTitle = `Synthetic broken PDF ${marker}`
    await upload.getByLabel("Оригинальный файл").setInputFiles({
      name: "broken.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4\n%%EOF"),
    })
    await upload.getByLabel("Ссылка на источник").fill(`https://example.invalid/${marker}/broken`)
    await upload.getByLabel("Название").fill(brokenTitle)
    await upload.getByLabel("Примечание о правах").fill("Self-authored malformed fixture")
    const brokenIntakeResponse = adminPage.waitForResponse((response) => response.url().endsWith("/api/v1/admin/sources") && response.request().method() === "POST")
    await upload.getByRole("button", { name: "Загрузить на проверку" }).click()
    const brokenIntake = (await (await brokenIntakeResponse).json()) as { revision_id: string }
    await expect.poll(async () => {
      const response = await adminContext.request.get(`/api/v1/admin/revisions/${brokenIntake.revision_id}`)
      return ((await response.json()) as { status: string }).status
    }, { timeout: 120_000 }).toBe("failed")
    await adminPage.reload()
    await adminPage.getByRole("button", { name: "Админка" }).click()
    const failedSearch = adminPage.getByRole("form", { name: "Поиск в инвентаре" })
    await failedSearch.getByRole("textbox", { name: "Источник или название" }).fill(brokenTitle)
    await failedSearch.getByRole("button", { name: "Найти" }).click()
    await adminPage.getByRole("button", { name: new RegExp(brokenTitle) }).click()
    await expect(adminPage.getByText("source_extraction_failed")).toBeVisible()
    await expect(adminPage.getByRole("form", { name: "Одобрение ревизии" })).toHaveCount(0)
    expect((await userContext.request.get(`/api/v1/materials/${brokenIntake.revision_id}`)).status()).toBe(404)
    const retryResponse = adminPage.waitForResponse((response) => response.url().endsWith(`/api/v1/admin/revisions/${brokenIntake.revision_id}/retry`))
    await adminPage.getByRole("button", { name: "Повторить обработку" }).click()
    expect(((await (await retryResponse).json()) as { status: string }).status).toBe("candidate")
    await expect.poll(async () => {
      const response = await adminContext.request.get(`/api/v1/admin/revisions/${brokenIntake.revision_id}`)
      return ((await response.json()) as { status: string }).status
    }, { timeout: 120_000 }).toBe("failed")
    expect((await userContext.request.get(`/api/v1/materials/${brokenIntake.revision_id}`)).status()).toBe(404)

    const workbookTitle = `Synthetic workbook ${marker}`
    const workbook = await readFile(new URL("./fixtures/self-authored.xlsx", import.meta.url))
    await upload.getByLabel("Оригинальный файл").setInputFiles({
      name: "self-authored.xlsx",
      mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      buffer: workbook,
    })
    await upload.getByLabel("Ссылка на источник").fill(`https://example.invalid/${marker}/workbook`)
    await upload.getByLabel("Название").fill(workbookTitle)
    await upload.getByLabel("Примечание о правах").fill("Self-authored workbook for technical test")
    const workbookIntakeResponse = adminPage.waitForResponse((response) => response.url().endsWith("/api/v1/admin/sources") && response.request().method() === "POST")
    await upload.getByRole("button", { name: "Загрузить на проверку" }).click()
    const workbookIntake = (await (await workbookIntakeResponse).json()) as { revision_id: string }
    await expect.poll(async () => {
      const response = await adminContext.request.get(`/api/v1/admin/revisions/${workbookIntake.revision_id}`)
      return ((await response.json()) as { status: string }).status
    }, { timeout: 120_000 }).toBe("review_pending")
    await adminPage.reload()
    await adminPage.getByRole("button", { name: "Админка" }).click()
    const workbookSearch = adminPage.getByRole("form", { name: "Поиск в инвентаре" })
    await workbookSearch.getByRole("textbox", { name: "Источник или название" }).fill(workbookTitle)
    await workbookSearch.getByRole("button", { name: "Найти" }).click()
    await adminPage.getByRole("button", { name: new RegExp(workbookTitle) }).click()
    await expect(adminPage.getByText("Item: Example A; Count: 7", { exact: true })).toBeVisible()
    const workbookReview = adminPage.getByRole("form", { name: "Одобрение ревизии" })
    await workbookReview.getByLabel("Основание и ограничения").fill("Self-authored workbook for isolated live test")
    await workbookReview.getByLabel("HTTPS-ссылка на доказательство прав").fill(`https://example.invalid/${marker}/workbook/rights`)
    await workbookReview.getByLabel(/Показ текстовых фрагментов/).check()
    await workbookReview.getByLabel(/Чувствительность материала/).check()
    await workbookReview.getByLabel(/Показ оригинального файла/).check()
    await workbookReview.getByRole("button", { name: "Одобрить эту ревизию" }).click()
    await expect(adminPage.getByRole("form", { name: "Отзыв ревизии" })).toBeVisible()
    approvedRevisionId = workbookIntake.revision_id
    const workbookDetail = await adminContext.request.get(`/api/v1/admin/revisions/${approvedRevisionId}`)
    const workbookSegments = ((await workbookDetail.json()) as {
      segments: { segment_id: string; locator: { sheet: string; row_start: number; column_start: number } }[]
    }).segments
    expect(workbookSegments.map((segment) => [segment.locator.sheet, segment.locator.row_start, segment.locator.column_start])).toEqual([
      ["North", 2, 3], ["North", 3, 2], ["South", 2, 2],
    ])
    await expect.poll(async () => {
      const response = await fetch(`${vectorURL}/collections/culture_text_e5_small_v1/points`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ ids: [workbookSegments[1].segment_id], with_payload: true, with_vector: false }),
      })
      if (!response.ok) return null
      const data = (await response.json()) as { result: { payload: { revision_id: string } }[] }
      return data.result[0]?.payload.revision_id ?? null
    }, { timeout: 180_000 }).toBe(approvedRevisionId)

    const workbookFilter = userPage.getByRole("form", { name: "Поиск материалов" })
    await workbookFilter.getByRole("combobox", { name: "Тип документа" }).selectOption("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    await workbookFilter.getByRole("button", { name: "Найти" }).click()
    await userPage.getByRole("button", { name: new RegExp(workbookTitle) }).click()
    await expect(userPage.getByRole("heading", { name: "Таблица North, строка 3, столбец 2" })).toBeVisible()
    await expect(userPage.getByText("Item: Example A; Count: 7")).toBeVisible()
    const workbookDownloadPromise = userPage.waitForEvent("download")
    await userPage.getByRole("link", { name: "Скачать исходную книгу XLSX" }).click()
    const workbookDownload = await workbookDownloadPromise
    expect(await readFile(await workbookDownload.path())).toEqual(workbook)

    await userPage.getByRole("button", { name: "Вернуться к чату" }).first().click()
    await userPage.getByRole("button", { name: "Новый чат" }).click()
    const workbookBrief = "Item: Example A; Count: 7"
    await userPage.getByRole("textbox", { name: "Ваш творческий бриф" }).fill(workbookBrief)
    const workbookAnswerResponse = userPage.waitForResponse((response) => response.url().includes("/api/v1/chats/") && response.url().endsWith("/messages") && response.request().method() === "POST")
    await userPage.getByRole("button", { name: "Отправить" }).click()
    const workbookAnswer = (await (await workbookAnswerResponse).json()) as {
      evidence_status: string; citations: { revision_id: string; segment_id: string; sheet: string; row_start: number; column_start: number }[]
    }
    expect(workbookAnswer.evidence_status).toBe("grounded")
    expect(workbookAnswer.citations).toHaveLength(1)
    expect(workbookAnswer.citations[0].revision_id).toBe(approvedRevisionId)
    expect(workbookSegments).toContainEqual(expect.objectContaining({
      segment_id: workbookAnswer.citations[0].segment_id,
      locator: expect.objectContaining({
        sheet: workbookAnswer.citations[0].sheet,
        row_start: workbookAnswer.citations[0].row_start,
        column_start: workbookAnswer.citations[0].column_start,
      }),
    }))
    await expect(userPage.getByRole("heading", { name: "Подтверждено источником" })).toBeVisible()
    await userPage.getByRole("button", { name: new RegExp(`Источник · таблица ${workbookAnswer.citations[0].sheet}, строка ${workbookAnswer.citations[0].row_start}`) }).click()
    await expect(userPage.locator(`#segment-${workbookAnswer.citations[0].segment_id}`)).toBeFocused()
    const workbookRevoke = adminPage.getByRole("form", { name: "Отзыв ревизии" })
    await workbookRevoke.getByLabel("Причина отзыва").fill("Synthetic workbook test completed")
    await workbookRevoke.getByRole("button", { name: "Отозвать эту ревизию" }).click()
    await expect.poll(async () => {
      const response = await adminContext.request.get(`/api/v1/admin/revisions/${workbookIntake.revision_id}`)
      return ((await response.json()) as { decision: string }).decision
    }).toBe("revoke")
    approvedRevisionId = null
    await userPage.reload()
    await userPage.getByRole("button", { name: workbookBrief, exact: true }).click()
    await expect(userPage.getByRole("button", { name: /Источник · таблица North, строка/ })).toBeDisabled()

    const proseTitle = `Synthetic two-page PDF ${marker}`
    const prose = await readFile(new URL("./fixtures/self-authored-pages.pdf", import.meta.url))
    await upload.getByLabel("Оригинальный файл").setInputFiles({
      name: "self-authored-pages.pdf", mimeType: "application/pdf", buffer: prose,
    })
    await upload.getByLabel("Ссылка на источник").fill(`https://example.invalid/${marker}/prose`)
    await upload.getByLabel("Название").fill(proseTitle)
    await upload.getByLabel("Примечание о правах").fill("Self-authored PDF for technical test")
    const proseIntakeResponse = adminPage.waitForResponse((response) => response.url().endsWith("/api/v1/admin/sources") && response.request().method() === "POST")
    await upload.getByRole("button", { name: "Загрузить на проверку" }).click()
    const proseIntake = (await (await proseIntakeResponse).json()) as { revision_id: string }
    expect((await userContext.request.get(`/api/v1/materials/${proseIntake.revision_id}`)).status()).toBe(404)
    await expect.poll(async () => {
      const response = await adminContext.request.get(`/api/v1/admin/revisions/${proseIntake.revision_id}`)
      return ((await response.json()) as { status: string }).status
    }, { timeout: 120_000 }).toBe("review_pending")
    await adminPage.reload()
    await adminPage.getByRole("button", { name: "Админка" }).click()
    const proseSearch = adminPage.getByRole("form", { name: "Поиск в инвентаре" })
    await proseSearch.getByRole("textbox", { name: "Источник или название" }).fill(proseTitle)
    await proseSearch.getByRole("button", { name: "Найти" }).click()
    await adminPage.getByRole("button", { name: new RegExp(proseTitle) }).click()
    await expect(adminPage.getByText("Synthetic first page blue kites", { exact: true })).toBeVisible()
    await expect(adminPage.getByText("Synthetic second page copper discs seven", { exact: true })).toBeVisible()
    const proseReviewOriginal = await adminContext.request.get(`/api/v1/admin/revisions/${proseIntake.revision_id}/original`)
    expect(proseReviewOriginal.status()).toBe(200)
    expect(await proseReviewOriginal.body()).toEqual(prose)
    const proseReview = adminPage.getByRole("form", { name: "Одобрение ревизии" })
    await proseReview.getByLabel("Основание и ограничения").fill("Self-authored two-page PDF for isolated live test")
    await proseReview.getByLabel("HTTPS-ссылка на доказательство прав").fill(`https://example.invalid/${marker}/prose/rights`)
    await proseReview.getByLabel(/Показ текстовых фрагментов/).check()
    await proseReview.getByLabel(/Чувствительность материала/).check()
    await proseReview.getByLabel(/Показ оригинального файла/).check()
    await proseReview.getByRole("button", { name: "Одобрить эту ревизию" }).click()
    await expect(adminPage.getByRole("form", { name: "Отзыв ревизии" })).toBeVisible()
    approvedRevisionId = proseIntake.revision_id
    const proseDetail = await adminContext.request.get(`/api/v1/admin/revisions/${approvedRevisionId}`)
    const proseSegments = ((await proseDetail.json()) as {
      segments: { segment_id: string; locator: { page: number }; text: string }[]
    }).segments
    expect(proseSegments.map((segment) => [segment.locator.page, segment.text])).toEqual([
      [1, "Synthetic first page blue kites"],
      [2, "Synthetic second page copper discs seven"],
    ])
    await expect.poll(async () => {
      const response = await fetch(`${vectorURL}/collections/culture_text_e5_small_v1/points`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ ids: [proseSegments[1].segment_id], with_payload: true, with_vector: false }),
      })
      if (!response.ok) return null
      const data = (await response.json()) as { result: { payload: { revision_id: string } }[] }
      return data.result[0]?.payload.revision_id ?? null
    }, { timeout: 180_000 }).toBe(approvedRevisionId)
    const proseBrief = "Synthetic second page copper discs seven"
    await userPage.getByRole("button", { name: "Новый чат" }).click()
    await userPage.getByRole("textbox", { name: "Ваш творческий бриф" }).fill(proseBrief)
    const proseAnswerResponse = userPage.waitForResponse((response) => response.url().includes("/api/v1/chats/") && response.url().endsWith("/messages") && response.request().method() === "POST")
    await userPage.getByRole("button", { name: "Отправить" }).click()
    const proseAnswer = (await (await proseAnswerResponse).json()) as {
      evidence_status: string; citations: { revision_id: string; segment_id: string; page: number }[]
    }
    expect(proseAnswer.evidence_status).toBe("grounded")
    expect(proseAnswer.citations).toEqual([expect.objectContaining({
      revision_id: approvedRevisionId, segment_id: proseSegments[1].segment_id, page: 2,
    })])
    await userPage.getByRole("button", { name: "Источник · страница 2" }).click()
    await expect(userPage.locator(`#segment-${proseSegments[1].segment_id}`)).toBeFocused()
    await expect(userPage.getByRole("heading", { name: "Страница 2" })).toBeVisible()
    await expect(userPage.getByRole("link", { name: "Открыть страницу 2 в источнике" })).toHaveAttribute(
      "href", `/api/v1/materials/${approvedRevisionId}/original#page=2`,
    )
    const proseUserOriginal = await userContext.request.get(`/api/v1/materials/${approvedRevisionId}/original`)
    expect(proseUserOriginal.status()).toBe(200)
    expect(await proseUserOriginal.body()).toEqual(prose)
    const proseRevoke = adminPage.getByRole("form", { name: "Отзыв ревизии" })
    await proseRevoke.getByLabel("Причина отзыва").fill("Synthetic PDF test completed")
    await proseRevoke.getByRole("button", { name: "Отозвать эту ревизию" }).click()
    await expect.poll(async () => {
      const response = await adminContext.request.get(`/api/v1/admin/revisions/${proseIntake.revision_id}`)
      return ((await response.json()) as { decision: string }).decision
    }).toBe("revoke")
    approvedRevisionId = null
    expect((await userContext.request.get(`/api/v1/materials/${proseIntake.revision_id}/original`)).status()).toBe(404)
    await userPage.reload()
    await userPage.getByRole("button", { name: proseBrief, exact: true }).click()
    await expect(userPage.getByRole("button", { name: "Источник · страница 2" })).toBeDisabled()

    const textTitle = `Synthetic reviewed TXT ${marker}`
    const textOriginal = Buffer.from(`Synthetic first line\r\n${marker} has seven.\r\n\r\nUnrelated appendix.\r\n`, "utf8")
    await upload.getByLabel("Оригинальный файл").setInputFiles({
      name: "reviewed.txt", mimeType: "text/plain", buffer: textOriginal,
    })
    await upload.getByLabel("Ссылка на источник").fill(`https://example.invalid/${marker}/text`)
    await upload.getByLabel("Название").fill(textTitle)
    await upload.getByLabel("Примечание о правах").fill("Self-authored TXT for isolated review test")
    const textIntakeResponse = adminPage.waitForResponse((response) => response.url().endsWith("/api/v1/admin/sources") && response.request().method() === "POST")
    await upload.getByRole("button", { name: "Загрузить на проверку" }).click()
    const textIntake = (await (await textIntakeResponse).json()) as { revision_id: string }
    expect((await userContext.request.get(`/api/v1/materials/${textIntake.revision_id}`)).status()).toBe(404)
    await expect.poll(async () => {
      const response = await adminContext.request.get(`/api/v1/admin/revisions/${textIntake.revision_id}`)
      return ((await response.json()) as { status: string }).status
    }, { timeout: 120_000 }).toBe("review_pending")
    await adminPage.reload()
    await adminPage.getByRole("button", { name: "Админка" }).click()
    const textSearch = adminPage.getByRole("form", { name: "Поиск в инвентаре" })
    await textSearch.getByRole("textbox", { name: "Источник или название" }).fill(textTitle)
    await textSearch.getByRole("button", { name: "Найти" }).click()
    await adminPage.getByRole("button", { name: new RegExp(textTitle) }).click()
    const textSegments = ((await (await adminContext.request.get(`/api/v1/admin/revisions/${textIntake.revision_id}`)).json()) as {
      segments: { segment_id: string; included: boolean; locator: { section: string } }[]
    }).segments
    expect(textSegments.map((segment) => segment.locator.section)).toEqual(["Lines 1–2", "Line 4"])
    const segmentReview = adminPage.getByRole("form", { name: "Проверка фрагментов" })
    await segmentReview.getByRole("checkbox", { name: /Исключить: Строка 4/ }).check()
    await segmentReview.getByRole("textbox", { name: "Причина изменения" }).fill("Unrelated synthetic appendix excluded")
    await segmentReview.getByRole("button", { name: "Сохранить исключения" }).click()
    await expect(adminPage.getByText("Оригинал содержит исключённые фрагменты и недоступен пользователю.")).toBeVisible()
    await expect(adminPage.getByRole("form", { name: "Одобрение ревизии" }).getByLabel(/Показ оригинального файла/)).toBeDisabled()
    const textReview = adminPage.getByRole("form", { name: "Одобрение ревизии" })
    await textReview.getByLabel("Основание и ограничения").fill("Self-authored TXT with excluded appendix")
    await textReview.getByLabel("HTTPS-ссылка на доказательство прав").fill(`https://example.invalid/${marker}/text/rights`)
    await textReview.getByLabel(/Показ текстовых фрагментов/).check()
    await textReview.getByLabel(/Чувствительность материала/).check()
    await textReview.getByRole("button", { name: "Одобрить эту ревизию" }).click()
    await expect(adminPage.getByRole("form", { name: "Отзыв ревизии" })).toBeVisible()
    approvedRevisionId = textIntake.revision_id
    await expect.poll(async () => {
      const response = await fetch(`${vectorURL}/collections/culture_text_e5_small_v1/points`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ ids: textSegments.map((segment) => segment.segment_id), with_payload: true, with_vector: false }),
      })
      if (!response.ok) return null
      const data = (await response.json()) as { result: { id: string }[] }
      return data.result.map((point) => point.id)
    }, { timeout: 180_000 }).toEqual([textSegments[0].segment_id])
    expect((await userContext.request.get(`/api/v1/materials/${approvedRevisionId}/original`)).status()).toBe(404)
    const textUserDetail = await userContext.request.get(`/api/v1/materials/${approvedRevisionId}`)
    expect(((await textUserDetail.json()) as { segments: { segment_id: string }[] }).segments.map((segment) => segment.segment_id)).toEqual([textSegments[0].segment_id])
    await userPage.getByRole("button", { name: "Новый чат" }).click()
    await userPage.getByRole("textbox", { name: "Ваш творческий бриф" }).fill(marker)
    await userPage.getByRole("button", { name: "Отправить" }).click()
    await expect(userPage.getByRole("button", { name: "Источник · строки 1–2" })).toBeVisible({ timeout: 60_000 })
    await userPage.getByRole("button", { name: "Источник · строки 1–2" }).click()
    await expect(userPage.locator(`#segment-${textSegments[0].segment_id}`)).toBeFocused()
    const textRevoke = adminPage.getByRole("form", { name: "Отзыв ревизии" })
    await textRevoke.getByLabel("Причина отзыва").fill("Synthetic TXT review test completed")
    await textRevoke.getByRole("button", { name: "Отозвать эту ревизию" }).click()
    await expect.poll(async () => {
      const response = await adminContext.request.get(`/api/v1/admin/revisions/${textIntake.revision_id}`)
      return ((await response.json()) as { decision: string }).decision
    }).toBe("revoke")
    approvedRevisionId = null
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
