import asyncio
from playwright.async_api import (
    Page,
    Frame,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)


async def humanoid_click(page: Page, frame: Frame, selector: str, retries: int = 2):
    try:
        # Esperar que el selector esté visible en el frame
        await frame.wait_for_selector(selector, state="visible", timeout=10000)

        # Obtener la posición del elemento en el frame
        element = frame.locator(selector)
        box = await element.bounding_box()
        if not box:
            raise ValueError(f"No se pudo obtener la posición del elemento: {selector}")
        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2

        # Ajustar las coordenadas del elemento al contexto de la página principal
        frame_box = await frame.evaluate("document.body.getBoundingClientRect()")
        x += frame_box["x"]
        y += frame_box["y"]

        # Mover mouse desde una posición superior izquierda simulando desplazamiento humano
        await page.mouse.move(x - 110, y - 110)
        await asyncio.sleep(0.2)
        await page.mouse.move(x, y, steps=20)
        await asyncio.sleep(0.4)

        # Hover y clic
        await page.mouse.click(
            x, y, delay=80
        )  # Delay para simular tiempo de reacción de clic
        await asyncio.sleep(0.4)

    except (PlaywrightTimeoutError, ValueError) as e:
        if retries > 0:
            print(
                f"Fallo al hacer clic en {selector}, reintentando... ({retries} restantes)"
            )
            await asyncio.sleep(1)  # Espera antes de reintentar
            await humanoid_click(page, frame, selector, retries - 1)
        else:
            raise RuntimeError(f"Error al intentar hacer clic en {selector}") from e


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://www.dgrsalta.gov.ar/rentassalta/login.jsp")

        # Buscar el iframe que contiene el reCAPTCHA
        frame = next((f for f in page.frames if "recaptcha" in f.url), None)
        if not frame:
            print("No se encontró el iframe de reCAPTCHA.")
            await browser.close()
            return

        try:
            await humanoid_click(page, frame, ".recaptcha-checkbox-border")
            print("Clic en reCAPTCHA realizado con éxito.")
        except RuntimeError as e:
            print(f"Hubo un error al intentar hacer clic en reCAPTCHA: {e}")

        await browser.close()


asyncio.run(main())
