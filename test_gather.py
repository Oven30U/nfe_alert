import asyncio
import pytest
from test_unit import TestNacional, TestArba, TestAgip, TestMendoza, TestCordoba, TestNeuquen, TestRioNegro, \
    TestTucuman, TestMisiones, TestEntreRios, TestJujuy, TestChubut, TestLaPampa, TestChaco


class TestAll:
    @pytest.mark.asyncio
    async def test_all_jurisdictions(self):
        # Crear instancias de todas las clases de prueba
        tests = [
            TestNacional(),
            TestArba(),
            TestAgip(),
            TestMendoza(),
            TestCordoba(),
            TestNeuquen(),
            TestRioNegro(),
            TestTucuman(),
            TestMisiones(),
            TestEntreRios(),
            TestJujuy(),
            TestChubut(),
            TestLaPampa(),
            TestChaco(),
        ]

        # Crear una lista de tareas para ejecutar el método procesar_jurisdiccion() para cada jurisdicción
        tasks = [test.procesar_jurisdiccion() for test in tests]
        # tasks = [test.run_error_test() for test in tests]

        # Ejecutar todas las tareas de forma concurrente
        await asyncio.gather(*tasks)
