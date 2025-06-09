import asyncio
import logging
from typing import NoReturn
from playwright.async_api import async_playwright, Page
import time


async def main() -> NoReturn:
    """
    Funcion principal para manejar el proceso de inicio de sesión en el portal ATM Mendoza.

    Verifica si ya está conectado antes de intentar iniciar sesión y se adapta a diferentes
    escenarios de inicio de sesión.
    """
    # Configure logging | reemplazar por logger estandard
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="es-AR",
            viewport={"width": 1280, "height": 800},
            timezone_id="America/Argentina/Buenos_Aires",
        )
        page = await context.new_page()

        time.sleep(1.5)

        await page.goto(
            "https://atm.mendoza.gov.ar/portalatm/misTramites/misTramitesLogin.jsp"
        )

        if await is_logged_in(page):
            logger.info("Sesión ya iniciada. Saltando proceso de inicio de sesión.")
        else:
            logger.info(
                "No se ha iniciado sesión. Iniciando proceso de inicio de sesión."
            )
            await perform_login(page)

        # Verificar estado final
        await page.screenshot(path="session_status.png")

        # Cerrar navegador
        await browser.close()


async def is_logged_in(page: Page) -> bool:
    """
    Verifica si el usuario ya ha iniciado sesión.

    Args:
        page: El objeto page de Playwright

    Returns:
        bool: True si el usuario ha iniciado sesión, False en caso contrario
    """
    try:
        logout_element = await page.wait_for_selector(
            "//a[contains(text(), 'Cerrar Sesión')]", timeout=3000
        )
        return logout_element is not None
    except Exception:
        return False


async def perform_login(page: Page) -> None:
    """
    Realiza el proceso de inicio de sesión en el portal ATM Mendoza con un enfoque flexible.

    Prueba diferentes métodos de inicio de sesión según sea necesario, primero con la evaluación de funciones JS,
    luego con un clic en el botón si es necesario.

    Args:
        page: El objeto page de Playwright
    """
    try:
        # Esperar al selector del formulario de login
        await page.wait_for_selector("#cuit")

        # Completar el formulario de login
        await page.fill("#cuit", "30712399623")
        await page.fill("#password", "AbbVie2025.")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_selector("#ingresar")

        # Esperar a que la función de login esté definida
        await page.wait_for_function("typeof window.entrar === 'function'")
        time.sleep(1.5)

        # Primer intento: Usar evaluate para invocar JavaScript function
        logging.info("Intentando iniciar sesión usando evaluación de función JS")
        await page.evaluate("entrar()")

        # Verificar si esto fue suficiente para iniciar sesión
        await page.wait_for_timeout(
            2000
        )  # Dar tiempo para que se complete el inicio de sesión
        if await is_logged_in(page):
            logging.info("Inicio de sesión exitoso con función JS")
            return

        # Segundo intento: Hacer clic en el botón de login
        logging.info(
            "La función JS no fue suficiente, haciendo clic en el botón de inicio de sesión"
        )
        await page.click("#ingresar")

        # Verificar si el login fue exitoso
        await page.wait_for_timeout(2000)
        if await is_logged_in(page):
            logging.info("Inicio de sesión exitoso después de hacer clic en el botón")
        else:
            logging.warning(
                "El inicio de sesión podría haber fallado - 'Cerrar Sesión' no encontrado"
            )

    except Exception as e:
        logging.error(f"El proceso de inicio de sesión falló: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
