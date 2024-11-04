import asyncio
from playwright.async_api import async_playwright
from jurisdicciones import Catamarca, SantiagoDelEstero, Cordoba

async def catamarca_test():
    async with async_playwright() as playwright:
        fecha_desde = "01082024"
        fecha_hasta = "30082024"

        cuit_Catamarca = "20408964823"
        clave_fiscal_Catamarca = "Elcolo_1998&"
        cuit_cliente_input = "30714604356"
        client = "EDGE ARGENTINA S.R.L"

        catamarca = await Catamarca.create(
            playwright,
            client,
            cuit_Catamarca,
            clave_fiscal_Catamarca,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await catamarca.procesar_jurisdiccion()


async def santiago_test():
    async with async_playwright() as playwright:
        fecha_desde = "01082024"
        fecha_hasta = "30082024"

        cuit_SantiagoDelEstero = "30714604356"
        clave_fiscal_SantiagoDelEstero = "Edge2023"
        cuit_cliente_input = "30714604356"
        client = "EDGE ARGENTINA S.R.L"

        santiago_del_estero = await SantiagoDelEstero.create(
            playwright,
            client,
            cuit_SantiagoDelEstero,
            clave_fiscal_SantiagoDelEstero,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False
        )
        await santiago_del_estero.procesar_jurisdiccion()


async def cordoba_test():
    async with async_playwright() as playwright:
        fecha_desde = "01052024"
        fecha_hasta = "30052024"

        client = "EDGE ARGENTINA S.R.L"
        cuit_Cordoba = "20386165476"
        clave_fiscal_Cordoba = "1994Gabriel"
        cuit_cliente_input = "30714604356"

        # client = "MAGNETI MARELLI CONJ.DE ESCAPE S.A"
        # cuit_Cordoba = "23381628124"
        # clave_fiscal_Cordoba = "Achavesgaspar24"
        # cuit_cliente_input = "30707570144"

        cordoba = await Cordoba.create(
            playwright,
            client,
            cuit_Cordoba,
            clave_fiscal_Cordoba,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False
        )
        await cordoba.procesar_jurisdiccion()

# asyncio.run(catamarca_test())
# asyncio.run(santiago_test())
asyncio.run(cordoba_test())
