import pytest
from playwright.async_api import async_playwright


class BaseTest:
    """Test para el manejo coherente de todos los retornos"""

    @pytest.mark.asyncio
    async def run_base_test(
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
            if jurisdiccion.hay_notificacion not in [
                "Hay notificaciones",
                "No hay notificaciones",
            ] or jurisdiccion.hay_screenshot not in [
                "Se realizó screenshot",
                "No se realizó screenshot",
            ]:
                assert jurisdiccion.error is None
            assert jurisdiccion.nombre is not None
            if jurisdiccion.error is not None:
                assert (
                    jurisdiccion.hay_notificacion == "Error al buscar notificación"
                    and jurisdiccion.hay_screenshot == "Error al tomar screenshot"
                )


class ErrorTest:
    """Test para identificar retornos de error"""

    @pytest.mark.asyncio
    async def run_error_test(
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

            # Verifica que no haya errores
            assert jurisdiccion.error is None


class TestNacional(BaseTest, ErrorTest):
    def setup_method(self, method):
        from nacional import Nacional

        self.Jurisdiccion = Nacional
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "20386165476"
        self.clave_fiscal = "Gabriel1994"
        self.fecha_desde = "01/05/2024"
        self.fecha_hasta = "30/05/2024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.asyncio
    async def test_nacional(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,
        )

    @pytest.mark.asyncio
    async def test_nacional_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,
        )


class TestArba(BaseTest, ErrorTest):
    def setup_method(self, method):
        from arba import Arba

        self.Jurisdiccion = Arba
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "30714604356"
        self.clave_fiscal = "Edge2018"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.asyncio
    async def test_arba(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,
        )

    @pytest.mark.asyncio
    async def test_arba_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,
        )


class TestAgip(BaseTest, ErrorTest):
    def setup_method(self, method):
        from agip import Agip

        self.Jurisdiccion = Agip
        self.client = "FACEBOOK ARGENTINA S.R.L"
        self.cuit = "20236063586"
        self.clave_fiscal = "Bart41051"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30712132554"

    @pytest.mark.asyncio
    async def test_agip(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,
        )

    @pytest.mark.asyncio
    async def test_agip_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,
        )


class TestMendoza(BaseTest, ErrorTest):
    def setup_method(self, method):
        from mendoza import Mendoza

        self.Jurisdiccion = Mendoza
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "30714604356"
        self.clave_fiscal = "Edge2023"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.asyncio
    async def test_mendoza(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,
        )

    @pytest.mark.asyncio
    async def test_mendoza_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,
        )


class TestCordoba(BaseTest, ErrorTest):
    def setup_method(self, method):
        from cordoba import Cordoba

        self.Jurisdiccion = Cordoba
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "20386165476"
        self.clave_fiscal = "Gabriel1994"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.asyncio
    async def test_cordoba(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,
        )

    @pytest.mark.asyncio
    async def test_cordoba_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,
        )


class TestNeuquen(BaseTest, ErrorTest):
    def setup_method(self, method):
        from neuquen import Neuquen

        self.Jurisdiccion = Neuquen
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "30714604356"
        self.clave_fiscal = "Edge2021"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.asyncio
    async def test_neuquen(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,
        )

    @pytest.mark.asyncio
    async def test_neuquen_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,
        )


class TestRioNegro(BaseTest, ErrorTest):
    def setup_method(self, method):
        from rio_negro import RioNegro

        self.Jurisdiccion = RioNegro
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "20386165476"
        self.clave_fiscal = "Gabriel1994"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.asyncio
    async def test_rio_negro(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,
        )

    @pytest.mark.asyncio
    async def test_rio_negro_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,
        )
