
from playwright.async_api import Playwright, async_playwright, expect
from jurisdiccion import Jurisdiccion

class Neuquen(Jurisdiccion):
    @classmethod
    async def create(cls, playwright: Playwright, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta):
        self = await super().create(playwright, "Neuquén", "NEU", cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta)
        return self
    
    async def AFIP_login(self, URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml"):
        return await super().AFIP_login(URL_AFIP_LOGIN)
    
    async def consultar_notificaciones(self):
        # return await super().consultar_notificaciones()
        print("Procesando Neuquen")
        
    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()

async def main():
    async with async_playwright() as playwright:
        client = "EDGE ARGENTINA S.R.L"
        fecha_desde = "01052024"
        fecha_hasta = "30052024"
        cuit_Neuquen = "20386165476"
        clave_fiscal_Neuquen = "Gabriel1994"
        neuquen = await Neuquen.create(playwright, client, cuit_Neuquen, clave_fiscal_Neuquen, fecha_desde, fecha_hasta)
        # await neuquen.AFIP_login()
        await neuquen.procesar_jurisdiccion()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
