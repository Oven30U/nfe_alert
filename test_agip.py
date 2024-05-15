import pytest
from playwright.async_api import async_playwright
from agip import Agip

@pytest.mark.asyncio
async def test_agip():
    async with async_playwright() as playwright:
        client = "FACEBOOK ARGENTINA S.R.L"
        fecha_desde = "01052024"
        fecha_hasta = "30052024"
        cuit_Agip = "20236063586"
        clave_fiscal_Agip = "Bart41051"
        cuit_cliente_input="30712132554"
        agip = await Agip.create(playwright, client, cuit_Agip, clave_fiscal_Agip, fecha_desde, fecha_hasta, cuit_cliente_input)
        await agip.procesar_jurisdiccion()

        assert agip.page is not None
        assert agip.hay_notificacion is not None
        assert agip.hay_screenshot is not None
        assert agip.error is None
        assert agip.nombre is not None