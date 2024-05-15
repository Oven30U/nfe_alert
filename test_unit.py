import pytest
from playwright.async_api import async_playwright


class BaseTest:
    @pytest.mark.asyncio
    async def run_test(
        self,
        Jurisdiccion,
        client,
        cuit,
        clave_fiscal,
        fecha_desde,
        fecha_hasta,
        cuit_cliente_input,
    ):
        async with async_playwright() as playwright:
            jurisdiccion = await Jurisdiccion.create(
                playwright,
                client,
                cuit,
                clave_fiscal,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
            )
            await jurisdiccion.procesar_jurisdiccion()

            assert jurisdiccion.page is not None
            assert jurisdiccion.hay_notificacion is not None
            assert jurisdiccion.hay_screenshot is not None
            if jurisdiccion.hay_notificacion not in ["Hay notificaciones", "No hay notificaciones"] or jurisdiccion.hay_screenshot not in ["Se realizó screenshot", "No se realizó screenshot"]:
                assert jurisdiccion.error is None
            assert jurisdiccion.nombre is not None


class TestNacional(BaseTest):
    @pytest.mark.asyncio
    async def test_nacional(self):
        from nacional import Nacional

        await self.run_test(
            Nacional,
            "EDGE ARGENTINA S.R.L",
            "20386165476",
            "Gabriel1994",
            "01/05/2024",
            "30/05/2024",
            "30714604356",
        )


class TestArba(BaseTest):
    @pytest.mark.asyncio
    async def test_arba(self):
        from arba import Arba

        await self.run_test(
            Arba,
            "EDGE ARGENTINA S.R.L",
            "30714604356",
            "Edge2018",
            "01052024",
            "30052024",
            "30714604356",
        )


class TestAgip(BaseTest):
    @pytest.mark.asyncio
    async def test_agip(self):
        from agip import Agip

        await self.run_test(
            Agip,
            "FACEBOOK ARGENTINA S.R.L",
            "20236063586",
            "Bart41051",
            "01052024",
            "30052024",
            "30712132554",
        )


class TestMendoza(BaseTest):
    @pytest.mark.asyncio
    async def test_mendoza(self):
        from mendoza import Mendoza

        await self.run_test(
            Mendoza,
            "EDGE ARGENTINA S.R.L",
            "30714604356",
            "Edge2023",
            "01052024",
            "30052024",
            "30714604356",
        )


class TestCordoba(BaseTest):
    @pytest.mark.asyncio
    async def test_cordoba(self):
        from cordoba import Cordoba

        await self.run_test(
            Cordoba,
            "EDGE ARGENTINA S.R.L",
            "20386165476",
            "Gabriel1994",
            "01052024",
            "30052024",
            "30714604356",
        )


class TestRioNegro(BaseTest):
    @pytest.mark.asyncio
    async def test_rio_negro(self):
        from rio_negro import RioNegro

        await self.run_test(
            RioNegro,
            "EDGE ARGENTINA S.R.L",
            "20386165476",
            "Gabriel1994",
            "01052024",
            "30052024",
            "30714604356",
        )
