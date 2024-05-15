import pytest
from playwright.async_api import async_playwright
from arba import Arba


@pytest.mark.asyncio
async def test_arba():
    async with async_playwright() as playwright:
        fecha_desde = "01052024"
        fecha_hasta = "30052024"
        # cuit_Arba = "30712132554"
        # clave_fiscal_Arba = "Facebook1819"
        # cuit_cliente_input = "30712132554"
        # client = "FACEBOOK ARGENTINA S.R.L"
        client = "EDGE ARGENTINA S.R.L"
        cuit_Arba = "30714604356"
        clave_fiscal_Arba = "Edge2018"
        cuit_cliente_input = "30714604356"
        arba = await Arba.create(
            playwright,
            client,
            cuit_Arba,
            clave_fiscal_Arba,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await arba.procesar_jurisdiccion()

        assert arba.page is not None
        assert arba.hay_notificacion is not None
        assert arba.hay_screenshot is not None
        assert arba.error is None
        assert arba.nombre is not None
