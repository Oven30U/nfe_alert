import sys
import os
import asyncio
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Agregar el directorio que contiene el módulo 'jurisdicciones' al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jurisdicciones import (
    Catamarca,
    SantiagoDelEstero,
    Cordoba,
    Arba,
    Salta,
    Chaco,
    Sicnea,
    Agip,
    RioNegro,
)


async def catamarca_test():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_CATAMARCA_CLIENT")
        cuit_Catamarca = os.getenv("TEST_CATAMARCA_CUIT")
        clave_fiscal_Catamarca = os.getenv("TEST_CATAMARCA_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_CATAMARCA_CUIT_CLIENTE_INPUT")

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
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        cuit_SantiagoDelEstero = os.getenv("TEST_SANTIAGO_DEL_ESTERO_CUIT")
        clave_fiscal_SantiagoDelEstero = os.getenv("TEST_SANTIAGO_DEL_ESTERO_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_SANTIAGO_DEL_ESTERO_CUIT_CLIENTE_INPUT")
        client = os.getenv("TEST_SANTIAGO_DEL_ESTERO_CLIENT")

        santiago_del_estero = await SantiagoDelEstero.create(
            playwright,
            client,
            cuit_SantiagoDelEstero,
            clave_fiscal_SantiagoDelEstero,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
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
            headless=False,
        )
        await cordoba.procesar_jurisdiccion()


async def arba_test():
    async with async_playwright() as playwright:
        fecha_desde = "01072024"
        fecha_hasta = "30072024"

        # cuit_Arba = "30712132554"
        # clave_fiscal_Arba = "Facebook1819"
        # cuit_cliente_input = "30712132554"
        # client = "FACEBOOK ARGENTINA S.R.L"

        client = "EDGE ARGENTINA S.R.L"
        cuit_Arba = "30714604356"
        clave_fiscal_Arba = "Edge2018"
        cuit_cliente_input = "30714604356"

        # client = "ABBOTT LABORATORIES ARG. S.A"
        # cuit_Arba = "30500846301"
        # clave_fiscal_Arba = "Abbott2018"
        # cuit_cliente_input = "30500846301"

        arba = await Arba.create(
            playwright,
            client,
            cuit_Arba,
            clave_fiscal_Arba,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await arba.procesar_jurisdiccion()


async def salta_test():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")
        client = os.getenv("TEST_SALTA_CLIENT")
        cuit_Salta = os.getenv("TEST_SALTA_CUIT")
        clave_fiscal_Salta = os.getenv("TEST_SALTA_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_SALTA_CUIT_CLIENTE_INPUT")

        salta = await Salta.create(
            playwright,
            client,
            cuit_Salta,
            clave_fiscal_Salta,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await salta.procesar_jurisdiccion()


async def sicnea_test():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")
        client = os.getenv("TEST_SICNEA_CLIENT")
        cuit_Sicnea = os.getenv("TEST_SICNEA_CUIT")
        clave_fiscal_Sicnea = os.getenv("TEST_SICNEA_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_SICNEA_CUIT_CLIENTE_INPUT")

        sicnea = await sicnea.create(
            playwright,
            client,
            cuit_Sicnea,
            clave_fiscal_Sicnea,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await sicnea.procesar_jurisdiccion()


async def chaco_test():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_CHACO_CLIENT")
        cuit_Chaco = os.getenv("TEST_CHACO_CUIT")
        clave_fiscal_Chaco = os.getenv("TEST_CHACO_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_CHACO_CUIT_CLIENTE_INPUT")

        chaco = await Chaco.create(
            playwright,
            client,
            cuit_chaco,
            clave_fiscal_chaco,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await chaco.procesar_jurisdiccion()


async def agip_test():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_AGIP_CLIENT")
        cuit_agip = os.getenv("TEST_AGIP_CUIT")
        clave_fiscal_agip = os.getenv("TEST_AGIP_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_AGIP_CUIT_CLIENTE_INPUT")

        agip = await Agip.create(
            playwright,
            client,
            cuit_agip,
            clave_fiscal_agip,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await agip.procesar_jurisdiccion()  # https://claveciudad.agip.gob.ar/


async def rio_negro_test():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_RIO_NEGRO_CLIENT")
        cuit_rio_negro = os.getenv("TEST_RIO_NEGRO_CUIT")
        clave_fiscal_rio_negro = os.getenv("TEST_RIO_NEGRO_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_RIO_NEGRO_CUIT_CLIENTE_INPUT")

        rio_negro = await RioNegro.create(
            playwright,
            client,
            cuit_rio_negro,
            clave_fiscal_rio_negro,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await rio_negro.procesar_jurisdiccion()


if __name__ == "__main__":
    # asyncio.run(catamarca_test())
    asyncio.run(santiago_test())
    # asyncio.run(cordoba_test())
    # asyncio.run(arba_test())
    # asyncio.run(salta_test())
    # asyncio.run(chaco_test())
    # asyncio.run(sicnea_test())
    # asyncio.run(agip_test())
    # asyncio.run(rio_negro_test())
