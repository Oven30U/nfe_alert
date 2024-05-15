import pytest
from playwright.async_api import async_playwright
from mendoza import Mendoza


@pytest.mark.asyncio
async def test_mendoza():
    async with async_playwright() as playwright:
        fecha_desde = "01052024"
        fecha_hasta = "30052024"
        client = "EDGE ARGENTINA S.R.L"
        cuit_Mendoza = "30714604356"
        clave_fiscal_Mendoza = "Edge2023"
        cuit_cliente_input = "30714604356"
        mendoza = await Mendoza.create(
            playwright,
            client,
            cuit_Mendoza,
            clave_fiscal_Mendoza,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await mendoza.procesar_jurisdiccion()

        assert mendoza.page is not None
        assert mendoza.hay_notificacion is not None
        assert mendoza.hay_screenshot is not None
        assert mendoza.error is None
        assert mendoza.nombre is not None
