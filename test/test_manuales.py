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
    Nacional,
    EntreRios,
    SanLuis,
    Tucuman,
    LaPampa,
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
        clave_fiscal_SantiagoDelEstero = os.getenv(
            "TEST_SANTIAGO_DEL_ESTERO_CLAVE_FISCAL"
        )
        cuit_cliente_input = os.getenv("TEST_SANTIAGO_DEL_ESTERO_CUIT_CLIENTE_INPUT")
        client = os.getenv("TEST_SANTIAGO_DEL_ESTERO_CLIENT")
        client_folder = os.getenv("TEST_SANTIAGO_DEL_ESTERO_CLIENT_FOLDER")

        santiago_del_estero = await SantiagoDelEstero.create(
            playwright,
            client,
            client_folder,
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
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_CORDOBA_CLIENT")
        cuit_Cordoba = os.getenv("TEST_CORDOBA_CUIT")
        clave_fiscal_Cordoba = os.getenv("TEST_CORDOBA_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_CORDOBA_CUIT_CLIENTE_INPUT")

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
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_ARBA_CLIENT")
        client_folder = os.getenv("TEST_ARBA_CLIENT_FOLDER")
        cuit_Arba = os.getenv("TEST_ARBA_CUIT")
        clave_fiscal_Arba = os.getenv("TEST_ARBA_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_ARBA_CLIENTE_INPUT")

        arba = await Arba.create(
            playwright,
            client,
            client_folder,
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
        client_folder = os.getenv("TEST_SICNEA_CLIENT_FOLDER")
        cuit_sicnea = os.getenv("TEST_SICNEA_CUIT")
        clave_fiscal_sicnea = os.getenv("TEST_SICNEA_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_SICNEA_CUIT_CLIENTE_INPUT")

        sicnea = await Sicnea.create(
            playwright,
            client,
            client_folder,
            cuit_sicnea,
            clave_fiscal_sicnea,
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
        cuit_chaco = os.getenv("TEST_CHACO_CUIT")
        clave_fiscal_chaco = os.getenv("TEST_CHACO_CLAVE_FISCAL")
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
        client_folder = os.getenv("TEST_SICNEA_CLIENT_FOLDER")
        cuit_agip = os.getenv("TEST_AGIP_CUIT")
        clave_fiscal_agip = os.getenv("TEST_AGIP_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_AGIP_CUIT_CLIENTE_INPUT")

        agip = await Agip.create(
            playwright,
            client,
            client_folder,
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


async def nacional_test():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_NACIONAL_CLIENT")
        client_folder = os.getenv("TEST_NACIONAL_CLIENT_FOLDER")
        cuit_nacional = os.getenv("TEST_NACIONAL_CUIT")
        clave_fiscal_nacional = os.getenv("TEST_NACIONAL_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_NACIONAL_CUIT_CLIENTE_INPUT")

        nacional = await Nacional.create(
            playwright,
            client,
            client_folder,
            cuit_nacional,
            clave_fiscal_nacional,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await nacional.procesar_jurisdiccion()


async def entre_rios_test():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_ENTRERIOS_CLIENT")
        cuit_entre_rios = os.getenv("TEST_ENTRERIOS_CUIT")
        clave_fiscal_entre_rios = os.getenv("TEST_ENTRERIOS_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_ENTRERIOS_CUIT_CLIENTE_INPUT")

        entre_rios = await EntreRios.create(
            playwright,
            client,
            cuit_entre_rios,
            clave_fiscal_entre_rios,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await entre_rios.procesar_jurisdiccion()


async def san_luis_test():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_SANLUIS_CLIENT")
        cuit_san_luis = os.getenv("TEST_SANLUIS_CUIT")
        clave_fiscal_san_luis = os.getenv("TEST_SANLUIS_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_SANLUIS_CUIT_CLIENTE_INPUT")

        san_luis = await SanLuis.create(
            playwright,
            client,
            cuit_san_luis,
            clave_fiscal_san_luis,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await san_luis.procesar_jurisdiccion()


async def tucuman_test():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_TUCUMAN_CLIENT")
        cuit_tucuman = os.getenv("TEST_TUCUMAN_CUIT")
        clave_fiscal_tucuman = os.getenv("TEST_TUCUMAN_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_TUCUMAN_CUIT_CLIENTE_INPUT")

        tucuman = await Tucuman.create(
            playwright,
            client,
            cuit_tucuman,
            clave_fiscal_tucuman,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await tucuman.procesar_jurisdiccion()


async def la_pampa_test():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_LA_PAMPA_CLIENT")
        cuit_la_pampa = os.getenv("TEST_LA_PAMPA_CUIT")
        clave_fiscal_la_pampa = os.getenv("TEST_LA_PAMPA_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_LA_PAMPA_CUIT_CLIENTE_INPUT")

        la_pampa = await LaPampa.create(
            playwright,
            client,
            cuit_la_pampa,
            clave_fiscal_la_pampa,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await la_pampa.procesar_jurisdiccion()




def send_email_smtp_test():
    """
    Test manual para enviar el correo con contraseña del zip
    """
    from correo_cli import send_email_smtp
    from conectar_db import read_and_modify_html
    send_email_smtp(
    sender_email="robot-tax-ar@deloitte.com",
    receiver_emails=["lmarinaro@deloitte.com"],
    subject=f"Actualización de clave de seguridad para NFE Alert: Revisión de Domicilios Fiscales Electrónicos - Cliente test",
    html_file_path=None,
    zip_file_paths=None,
    html_content=read_and_modify_html("Cliente test", "12345678", 90, "lmarinaro"))


if __name__ == "__main__":
    # asyncio.run(catamarca_test())
    # asyncio.run(santiago_test())
    # asyncio.run(cordoba_test())
    # asyncio.run(arba_test())
    # asyncio.run(salta_test())
    # asyncio.run(chaco_test())
    # asyncio.run(sicnea_test())
    # asyncio.run(agip_test())
    # asyncio.run(rio_negro_test())
    asyncio.run(nacional_test())
    # asyncio.run(entre_rios_test())
    # asyncio.run(san_luis_test())
    # asyncio.run(tucuman_test())
    # asyncio.run(la_pampa_test())
    # send_email_smtp_test()
