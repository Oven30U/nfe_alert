import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import asyncio
from playwright.async_api import async_playwright


def afip_login():
    # Cargar variables de entorno
    load_dotenv()
    cuit = os.getenv("TEST_NACIONAL_CUIT")
    clave_fiscal = os.getenv("TEST_NACIONAL_CLAVE_FISCAL")

    with requests.Session() as session:
        # Paso 1: Obtener la página de login inicial y extraer ViewState y otros campos ocultos
        login_url = "https://auth.afip.gob.ar/contribuyente_/login.xhtml"
        response = session.get(login_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Extraer todos los campos ocultos
        hidden_inputs = soup.find_all("input", {"type": "hidden"})
        form_data = {}
        for hidden in hidden_inputs:
            name = hidden.get("name")
            value = hidden.get("value", "")
            form_data[name] = value

        # Agregar los campos necesarios para el primer paso del formulario (ingresar CUIT/CUIL)
        form_data.update({
            "form:username": cuit,
            "form:btnSiguiente": "Siguiente",
        })

        # Enviar el primer formulario (CUIT/CUIL)
        response = session.post(login_url, data=form_data)
        response.raise_for_status()

        # Parsear la respuesta y extraer el nuevo ViewState y otros campos ocultos
        soup = BeautifulSoup(response.content, "html.parser")
        hidden_inputs = soup.find_all("input", {"type": "hidden"})
        form_data = {}
        for hidden in hidden_inputs:
            name = hidden.get("name")
            value = hidden.get("value", "")
            form_data[name] = value

        # Agregar los campos necesarios para el segundo paso del formulario (ingresar Clave Fiscal)
        form_data.update({
            "form:password": clave_fiscal,
            "form:btnIngresar": "Ingresar",
        })

        # Enviar el segundo formulario (Clave Fiscal)
        response = session.post(login_url, data=form_data)
        response.raise_for_status()

        # Parsear la respuesta después del login
        soup = BeautifulSoup(response.content, "html.parser")

        # Obtener el título de la página
        page_title = soup.title.string.strip() if soup.title else ""

        # # Verificar el título para determinar el estado del login
        # if page_title == "Portal de Clave Fiscal":
        #     print("Login exitoso.")
        # elif page_title == "Acceso con Clave Fiscal - ARCA":
        #     print("Login fallido.")
        #     return None
        # else:
        #     print(f"Título desconocido: {page_title}")
        #     # Opcional: guardar el HTML para inspección
        #     with open("afip_response.html", "w", encoding="utf-8") as f:
        #         f.write(response.text)
        #     return None

        # # Verificar si hay un mensaje de error en el formulario
        # error_element = soup.find("span", {"id": "F1:msg"})
        # if error_element:
        #     error_message = error_element.text.strip()
        #     if error_message:
        #         print(f"Error en el login: {error_message}")
        #         return None

        # # Verificar si el login fue exitoso buscando un elemento específico
        # success_element = soup.find("h1")
        # if success_element and "Portal del Contribuyente" in success_element.text:
        #     print("Login exitoso.")
        # else:
        #     print("No se pudo determinar el estado del login.")
        #     # Opcional: guardar el HTML para inspección
        #     with open("afip_response.html", "w", encoding="utf-8") as f:
        #         f.write(response.text)
        #     return None

        # Retornar las cookies de la sesión
        cookies = session.cookies.get_dict()
        return cookies


async def afip_playwright(cookies):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()

        # Añadir las cookies a la sesión de Playwright
        playwright_cookies = []
        for name, value in cookies.items():
            playwright_cookies.append({
                "name": name,
                "value": value,
                "domain": "auth.afip.gob.ar",
                "path": "/",
                "httpOnly": True,
                "secure": True,
            })

        await context.add_cookies(playwright_cookies)

        page = await context.new_page()

        # Navegar a la página que quieras después del login, por ejemplo el portal principal
        await page.goto("https://auth.afip.gob.ar/contribuyente_/login.xhtml")

        # Verificar si el login fue exitoso buscando un elemento específico
        if await page.query_selector("text=Bienvenido") or await page.query_selector("text=Último acceso"):
            print("Login exitoso en Playwright.")
        else:
            print("Login fallido en Playwright.")

        # Continuar con las acciones en la página
        # ...

        # Cerrar el navegador
        await browser.close()


if __name__ == "__main__":
    cookies = afip_login()
    if cookies:
        asyncio.run(afip_playwright(cookies))