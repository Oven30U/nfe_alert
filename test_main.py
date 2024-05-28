# import pandas as pd
# import main
# import pytest
#
#
# @pytest.mark.main
# @pytest.mark.error
# @pytest.mark.asyncio
# async def test_no_errors():
#     # Ejecutar la función principal y capturar el DataFrame resultante
#     df = await main.main()
#
#     # Verificar que df no sea None antes de intentar acceder a sus elementos
#     assert df is not None, "main no retornó un dataframe"
#
#     # Verificar que ninguna fila en la columna 'Error' tenga un valor distinto de None
#     for error in df["Error"]:
#         assert error is None, "Hay valor en Error de alguna jurisdiccion"
#
#     for notificacion in df["Notificacion"]:
#         assert notificacion in ["Hay notificaciones", "No hay notificaciones"], "Hay valor erroneo en Notificaciones"
#
#     for screenshot in df["Screenshot"]:
#         assert screenshot in ["Se realizó Screenshot", "No se realizó Screenshot"], "Hay valor erroneo en Screenshot"
import asyncio
import unittest
from unittest.mock import patch
from main import main

class TestMain(unittest.TestCase):
    @patch('main.Jujuy.create')
    @patch('main.Chubut.create')
    @patch('main.Misiones.create')
    @patch('main.Tucuman.create')
    @patch('main.RioNegro.create')
    @patch('main.Neuquen.create')
    @patch('main.Cordoba.create')
    @patch('main.Mendoza.create')
    @patch('main.Arba.create')
    @patch('main.Agip.create')
    @patch('main.Nacional.create')
    def test_main(self, nacional_mock, agip_mock, arba_mock, mendoza_mock, cordoba_mock, neuquen_mock, rionegro_mock, tucuman_mock, misiones_mock, chubut_mock, jujuy_mock):
        nacional_mock.return_value = MockInstance()
        agip_mock.return_value = MockInstance()
        arba_mock.return_value = MockInstance()
        mendoza_mock.return_value = MockInstance()
        cordoba_mock.return_value = MockInstance()
        neuquen_mock.return_value = MockInstance()
        rionegro_mock.return_value = MockInstance()
        tucuman_mock.return_value = MockInstance()
        misiones_mock.return_value = MockInstance()
        chubut_mock.return_value = MockInstance()
        jujuy_mock.return_value = MockInstance()

        try:
            asyncio.run(main())
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"main() raised {type(e).__name__} unexpectedly!")

class MockInstance:
    async def procesar_jurisdiccion(self):
        return ["Nombre", "Notificacion", "Screenshot", None]

    async def browser(self):
        class MockBrowser:
            async def close(self):
                pass
        return MockBrowser()

if __name__ == '__main__':
    unittest.main()