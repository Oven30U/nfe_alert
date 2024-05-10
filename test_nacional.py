import pytest
from playwright.async_api import async_playwright
from nacional import Nacional

@pytest.mark.asyncio
async def test_nacional():
    async with async_playwright() as playwright:
        client = "EDGE ARGENTINA S.R.L"
        fecha_desde = "01/05/2024"
        fecha_hasta = "30/05/2024"
        cuit_Nacional = "20386165476"
        clave_fiscal_Nacional = "Gabriel1994"
        cuit_cliente_input="30714604356"
        nacional = await Nacional.create(playwright, client, cuit_Nacional, clave_fiscal_Nacional, fecha_desde, fecha_hasta, cuit_cliente_input)
        await nacional.procesar_jurisdiccion()

        assert nacional.new_page is not None
        assert nacional.hay_notificacion is not None
        assert nacional.hay_screenshot is not None
        assert nacional.error is None
        assert nacional.nombre is not None