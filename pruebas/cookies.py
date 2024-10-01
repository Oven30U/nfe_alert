import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

class LoginError(Exception):
    pass

class AFIPAutomation:
    def __init__(self, page, cuit, clave_fiscal):
        self.page = page
        self._cuit = cuit
        self._clave_fiscal = clave_fiscal

    async def AFIP_login(self, URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml"):
        await self.page.goto(URL_AFIP_LOGIN)
        await self.page.get_by_role("spinbutton").click()
        await self.page.get_by_role("spinbutton").fill(self._cuit)
        await self.page.get_by_role("button", name="Siguiente").click()
        incorrect_login = await self.page.query_selector(":has-text('Número de CUIL/CUIT incorrecto')")
        if incorrect_login:
            raise LoginError("Login CUIT incorrecto")
        await self.page.get_by_label("TU CLAVE").click()
        await self.page.get_by_label("TU CLAVE").fill(self._clave_fiscal)
        await self.page.get_by_role("button", name="Ingresar").click()
        await self.page.wait_for_load_state("networkidle")
        if URL_AFIP_LOGIN == "https://auth.afip.gob.ar/contribuyente_/login.xhtml":
            incorrect_login = await self.page.query_selector(":has-text('Clave o usuario incorrecto')")
            if incorrect_login:
                raise LoginError("Login pass incorrecto")

async def save_cookies(context, path):
    cookies = await context.cookies()
    future_date = (datetime.now() + timedelta(days=365*10)).timestamp()
    for cookie in cookies:
        cookie['expires'] = future_date
    with open(path, 'w') as file:
        json.dump(cookies, file)

async def load_cookies(context, path):
    with open(path, 'r') as file:
        cookies = json.load(file)
    await context.add_cookies(cookies)

async def login_and_save_cookies(context, cuit, clave_fiscal, path):
    page = await context.new_page()
    automation = AFIPAutomation(page, cuit, clave_fiscal)
    await automation.AFIP_login()
    await save_cookies(context, path)
    await page.close()

async def check_login_status(page):
    return await page.locator('input#buscadorInput').count() > 0

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        cuit = '20386165476'
        cliente = 'EDGE'
        cookies_file = f'cookies/{cliente}/cookies_Nacional_{cuit}.json'

        try:
            await load_cookies(context, path=cookies_file)
        except FileNotFoundError:
            pass
            # await login_and_save_cookies(context, cuit=cuit, clave_fiscal='1994Gabriel', path=cookies_file)

        page = await context.new_page()
        await page.goto('https://portalcf.cloud.afip.gob.ar/portal/app/')

        if not await check_login_status(page):
            automation = AFIPAutomation(page, cuit=cuit, clave_fiscal='1994Gabriel')
            await automation.AFIP_login()
            await save_cookies(context, path=cookies_file)
            await page.goto('https://portalcf.cloud.afip.gob.ar/portal/app/')

        # Perform your actions here

        await browser.close()

# Run the main function
import asyncio

asyncio.run(main())