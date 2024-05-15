import pytest
from playwright.async_api import async_playwright
from neuquen import Neuquen

@pytest.mark.asyncio
async def test_neuquen():
    async with async_playwright() as playwright:
        client = "EDGE ARGENTINA S.R.L"
        fecha_desde = "01052024"
        fecha_hasta = "30052024"
        cuit_Neuquen = "20386165476"
        clave_fiscal_Neuquen = "Gabriel1994"
        cuit_cliente_input="30714604356"
        neuquen = await Neuquen.create(playwright, client, cuit_Neuquen, clave_fiscal_Neuquen, fecha_desde, fecha_hasta)
        await neuquen.procesar_jurisdiccion()

        assert neuquen.page is not None
        assert neuquen.hay_notificacion is not None
        assert neuquen.hay_screenshot is not None
        assert neuquen.error is None
        assert neuquen.nombre is not None