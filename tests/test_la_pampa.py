import asyncio
from playwright.async_api import Playwright, Page, async_playwright, expect


async def login(page: Page, company_name: str) -> None:
    await (
        page.locator('iframe[name="iframe1"]')
        .content_frame.get_by_role("textbox", name="C.U.I.T.:")
        .click()
    )
    await (
        page.locator('iframe[name="iframe1"]')
        .content_frame.get_by_role("textbox", name="C.U.I.T.:")
        .fill("27274984223")
    )
    await (
        page.locator('iframe[name="iframe1"]')
        .content_frame.locator("#pPassword")
        .click()
    )
    await (
        page.locator('iframe[name="iframe1"]')
        .content_frame.locator("#pPassword")
        .fill("Pampa23")
    )
    await (
        page.locator('iframe[name="iframe1"]')
        .content_frame.get_by_role("button", name="Enviar")
        .click()
    )
    await (
        page.locator('iframe[name="iframe1"]')
        .content_frame.get_by_role("row", name=company_name)
        .get_by_role("radio")
        .check()
    )
    await page.wait_for_timeout(3000)
    await (
        page.locator('iframe[name="iframe1"]')
        .content_frame.get_by_role("button", name="Confirmar")
        .click()
    )


async def run(playwright: Playwright) -> None:
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    await context.tracing.start(screenshots=True, snapshots=True)
    page = await context.new_page()
    try:
        await page.goto(
            "https://dgr.lapampa.gob.ar/ServiciosEnLinea/?programa=MenuCuenta"
        )
        company = "30-598129246 JANSSEN CILAG"
        attempts = 0
        max_attempts = 200
        while attempts < max_attempts:
            try:
                await login(page, company)
            except Exception:
                break
            await page.wait_for_load_state("domcontentloaded")
            try:
                await expect(page.locator("#loginbutton")).to_contain_text(
                    "Iniciar Sesión", timeout=5000
                )
            except:
                pass
            text = await page.locator("#loginbutton").inner_text()
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_load_state("networkidle")
            try:
                await (
                    page.locator("li.list-group-item")
                    .filter(has_text="Cerrar Sesión")
                    .wait_for(timeout=5000)
                )
                break
            except:
                pass
            await page.goto(
                "https://dgr.lapampa.gob.ar/ServiciosEnLinea/?programa=MenuCuenta"
            )
            attempts += 1
        # await login(page, company)
        await page.get_by_role("link", name="Gestionar").click()
        await page.get_by_role("link", name="Contribuyente").click()
        await (
            page.locator('iframe[name="iframe1"]')
            .content_frame.get_by_role("button", name="Domicilio Fiscal Electrónico")
            .click()
        )
        await (
            page.locator('iframe[name="iframe1"]')
            .content_frame.get_by_role("link", name="Consulta de Novedades / Trá")
            .click()
        )
        content = await page.locator('iframe[name="iframe1"]').content_frame.locator("tbody").inner_text()
        print("Contenido de la tabla:", content)

        # ---------------------
    finally:
        await context.tracing.stop(path="traces/trace_la_pampa.zip")
        await context.close()
        await browser.close()


async def main() -> None:
    async with async_playwright() as playwright:
        await run(playwright)


asyncio.run(main())
