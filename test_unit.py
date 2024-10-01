import pytest
from playwright.async_api import async_playwright

# headless_state = True


class BaseTest:
    """
    Clase base para pruebas unitarias.

    Esta clase proporciona un method `run_base_test` que realiza una serie de
    aserciones para verificar el correcto funcionamiento de la jurisdicción
    procesada. Las pruebas incluyen la verificación de la existencia de la página,
    la presencia de notificaciones, la realización de capturas de pantalla y
    la ausencia de errores.

    Las pruebas se realizan de forma asíncrona para permitir la ejecución
    concurrente y mejorar el rendimiento de las pruebas.

    Args:
        Jurisdiccion: La clase de la jurisdicción a probar.
        client: El cliente a utilizar para las pruebas.
        cuit: El CUIT a utilizar para las pruebas.
        clave_fiscal: La clave fiscal a utilizar para las pruebas.
        fecha_desde: La fecha de inicio del rango de fechas a probar.
        fecha_hasta: La fecha de fin del rango de fechas a probar.
        cuit_cliente_input: El CUIT del cliente a utilizar para las pruebas.

    """

    @pytest.mark.asyncio
    async def run_base_test(
            self,
            Jurisdiccion,
            client,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,  # headless=headless_state,
    ):
        async with async_playwright() as playwright:
            jurisdiccion = await Jurisdiccion.create(
                playwright,
                client,
                cuit,
                clave_fiscal,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,  # headless=headless_state,
            )
            await jurisdiccion.procesar_jurisdiccion()

            assert jurisdiccion.page is not None, "La página es None"
            assert (
                    jurisdiccion.hay_notificacion is not None
            ), "No hay estado en hay_notificación"
            assert (
                    jurisdiccion.hay_screenshot is not None
            ), "No hay estado en hay_screenshot"
            if jurisdiccion.hay_notificacion not in [
                "Hay notificaciones",
                "No hay notificaciones",
            ] or jurisdiccion.hay_screenshot not in [
                "Se realizó screenshot",
                "No se realizó screenshot",
            ]:
                assert (
                        jurisdiccion.error is None
                ), "Ocurrió un error pero no se reflejo en hay_notificación o hay_screenshot"
            assert (
                    jurisdiccion.nombre is not None
            ), "El nombre de la jurisdiccion es None"
            if jurisdiccion.error is not None:
                assert (
                        jurisdiccion.hay_notificacion == "Error al buscar notificación"
                        and jurisdiccion.hay_screenshot == "Error al tomar screenshot"
                ), "Siendo que ocurrió un Error en la notificación o en la captura de pantalla, no se reflejo en hay_notificación o hay_screenshot"


class ErrorTest:
    """
    Clase para pruebas de error.

    Esta clase proporciona un method `run_error_test` que realiza una aserción
    para verificar que no se produzcan errores durante el procesamiento de la jurisdicción.

    Args:
        Jurisdiccion: La clase de la jurisdicción a probar.
        client: El cliente a utilizar para las pruebas.
        cuit: El CUIT a utilizar para las pruebas.
        clave_fiscal: La clave fiscal a utilizar para las pruebas.
        fecha_desde: La fecha de inicio del rango de fechas a probar.
        fecha_hasta: La fecha de fin del rango de fechas a probar.
        cuit_cliente_input: El CUIT del cliente a utilizar para las pruebas.

    """

    @pytest.mark.asyncio
    async def run_error_test(
            self,
            Jurisdiccion,
            client,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,  # headless=headless_state,
    ):
        async with async_playwright() as playwright:
            jurisdiccion = await Jurisdiccion.create(
                playwright,
                client,
                cuit,
                clave_fiscal,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,  # headless=headless_state,
            )
            await jurisdiccion.procesar_jurisdiccion()

            # Verifica que no haya errores
            assert (
                    jurisdiccion.error is None
            ), f"Se encontró un error durante la ejecución: {jurisdiccion.error}"


class TestNacional(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.nacional import Nacional

        self.Jurisdiccion = Nacional
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "20386165476"
        self.clave_fiscal = "1994Gabriel"
        self.fecha_desde = "28052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_nacional(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_nacional_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestArba(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.arba import Arba

        self.Jurisdiccion = Arba
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "30714604356"
        self.clave_fiscal = "Edge2018"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_arba(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_arba_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestAgip(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.agip import Agip

        self.Jurisdiccion = Agip
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "20236063586"
        self.clave_fiscal = "Bart41051"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_agip(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_agip_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestMendoza(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.mendoza import Mendoza

        self.Jurisdiccion = Mendoza
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "30714604356"
        self.clave_fiscal = "Edge2023"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_mendoza(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_mendoza_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestCordoba(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.cordoba import Cordoba

        self.Jurisdiccion = Cordoba
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "20386165476"
        self.clave_fiscal = "1994Gabriel"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_cordoba(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_cordoba_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestNeuquen(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.neuquen import Neuquen

        self.Jurisdiccion = Neuquen
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "30714604356"
        self.clave_fiscal = "Edge2021"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_neuquen(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_neuquen_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestRioNegro(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.rio_negro import RioNegro

        self.Jurisdiccion = RioNegro
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "20386165476"
        self.clave_fiscal = "1994Gabriel"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_rio_negro(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_rio_negro_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestTucuman(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.tucuman import Tucuman

        self.Jurisdiccion = Tucuman
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "20386165476"
        self.clave_fiscal = "1994Gabriel"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_tucuman(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_tucuman_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestMisiones(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.misiones import Misiones

        self.Jurisdiccion = Misiones
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "30714604356"
        self.clave_fiscal = "Edge2021"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_misiones(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_misiones_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestEntreRios(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.entre_rios import EntreRios

        self.Jurisdiccion = EntreRios
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "20386165476"
        self.clave_fiscal = "1994Gabriel"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_entre_rios(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_entre_rios_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestJujuy(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.jujuy import Jujuy

        self.Jurisdiccion = Jujuy
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "30714604356"
        self.clave_fiscal = "Edge2021!"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_jujuy(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_jujuy_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestChubut(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.chubut import Chubut

        self.Jurisdiccion = Chubut
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "30714604356"
        self.clave_fiscal = "Edge2023"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_chubut(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_chubut_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestLaPampa(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.la_pampa import LaPampa

        self.Jurisdiccion = LaPampa
        self.client = "NATURA COSMETICOS S.A"
        self.cuit = "20252501852"
        self.clave_fiscal = "natura2014"
        self.fecha_desde = "01072024"
        self.fecha_hasta = "30072024"
        self.cuit_cliente_input = "30677757295"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_la_pampa(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_la_pampa_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestChaco(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.chaco import Chaco

        self.Jurisdiccion = Chaco
        self.client = "NATURA COSMETICOS S.A"
        self.cuit = "30677757295"
        self.clave_fiscal = "Natura0."
        self.fecha_desde = "01072024"
        self.fecha_hasta = "30072024"
        self.cuit_cliente_input = "30677757295"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_chaco(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_chaco_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestSanLuis(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.san_luis import SanLuis

        self.Jurisdiccion = SanLuis
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "20104314075"
        self.clave_fiscal = "Edge2021"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_san_luis(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_san_luis_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestSantiagoDelEstero(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.santiago_del_estero import SantiagoDelEstero

        self.Jurisdiccion = SantiagoDelEstero
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "30714604356"
        self.clave_fiscal = "Edge2023"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_santiago_del_estero(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_santiago_del_estero_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestSicnea(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.sicnea import Sicnea

        self.Jurisdiccion = Sicnea
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "20386165476"
        self.clave_fiscal = "1994Gabriel"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_sicnea(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_sicnea_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestTucuman(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.tucuman import Tucuman

        self.Jurisdiccion = Tucuman
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "20386165476"
        self.clave_fiscal = "1994Gabriel"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_tucuman(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_tucuman_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestCatamarca(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.catamarca import Catamarca

        self.Jurisdiccion = Catamarca
        self.client = "EDGE ARGENTINA S.R.L"
        self.cuit = "20408964823"
        self.clave_fiscal = "Elcolo_1998&"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30714604356"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_catamarca(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_catamarca_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestCorrientes(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.corrientes import Corrientes

        self.Jurisdiccion = Corrientes
        self.client = "NATURA COSMETICOS S.A"
        self.cuit = "30677757295"
        self.clave_fiscal = "natura18"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30677757295"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_corrientes(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_corrientes_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestFormosa(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.formosa import Formosa

        self.Jurisdiccion = Formosa
        self.client = "NATURA COSMETICOS S.A"
        self.cuit = "30677757295"
        self.clave_fiscal = "natura2014"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30677757295"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_formosa(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_formosa_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestLaRioja(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.la_rioja import LaRioja

        self.Jurisdiccion = LaRioja
        self.client = "NATURA COSMETICOS S.A"
        self.cuit = "30677757295"
        self.clave_fiscal = "Natura2024"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30677757295"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_la_rioja(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_la_rioja_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestSalta(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.salta import Salta

        self.Jurisdiccion = Salta
        self.client = "NATURA COSMETICOS S.A"
        self.cuit = "30677757295"
        self.clave_fiscal = "natura18"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30677757295"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_salta(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_salta_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )


class TestSanJuan(BaseTest, ErrorTest):
    def setup_method(self, method):
        from jurisdicciones.san_juan import SanJuan

        self.Jurisdiccion = SanJuan
        self.client = "NATURA COSMETICOS S.A"
        self.cuit = "30677757295"
        self.clave_fiscal = "GJdd0x"
        self.fecha_desde = "01052024"
        self.fecha_hasta = "30052024"
        self.cuit_cliente_input = "30677757295"

    @pytest.mark.base
    @pytest.mark.asyncio
    async def test_san_juan(self):
        await self.run_base_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_san_juan_error(self):
        await self.run_error_test(
            self.Jurisdiccion,
            self.client,
            self.cuit,
            self.clave_fiscal,
            self.fecha_desde,
            self.fecha_hasta,
            self.cuit_cliente_input,  # headless=headless_state,
        )
