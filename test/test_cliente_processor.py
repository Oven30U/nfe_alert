import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
from datetime import datetime

class BaseMockJurisdiccion:
    @classmethod
    async def create(cls, **kwargs):
        instance = cls()
        return instance

class SuccessJurisdiccion(BaseMockJurisdiccion):
    async def procesar_jurisdiccion(self):
        return [self.__class__.__name__, True, "screenshot.png", None]

class ErrorJurisdiccion(BaseMockJurisdiccion):
    async def procesar_jurisdiccion(self):
        return [self.__class__.__name__, False, None, "Error"]

class TimeoutJurisdiccion(BaseMockJurisdiccion):
    async def procesar_jurisdiccion(self):
        return [self.__class__.__name__, False, None, "Timeout"]

@pytest.fixture
def mock_playwright():
    return MagicMock()

@pytest.mark.parametrize("jurisdiccion_data", [
    {
        "name": "ARBA",
        "mock_class": SuccessJurisdiccion,
        "expected_notification": True,
        "expected_error": None
    },
    {
        "name": "Cordoba", 
        "mock_class": ErrorJurisdiccion,
        "expected_notification": False,
        "expected_error": "Error"
    },
    {
        "name": "BuenosAires",
        "mock_class": TimeoutJurisdiccion, 
        "expected_notification": False,
        "expected_error": "Timeout"
    }
])
@pytest.mark.asyncio
async def test_procesar_jurisdicciones_parametrized(processor, mock_playwright, jurisdiccion_data):
    with patch(f'jurisdicciones.{jurisdiccion_data["name"]}', jurisdiccion_data["mock_class"]):
        instances, encontradas, no_encontradas = await processor.procesar_jurisdicciones(mock_playwright)
        
        assert len(instances) == 1
        result_df = await processor.ejecutar_jurisdicciones(instances)
        
        assert result_df.iloc[0]["Nombre"] == jurisdiccion_data["name"]
        assert result_df.iloc[0]["Notificacion"] == jurisdiccion_data["expected_notification"]
        assert result_df.iloc[0]["Error"] == jurisdiccion_data["expected_error"]

@pytest.mark.parametrize("initial_error,mock_class,expected_fixed", [
    ("LoginError", SuccessJurisdiccion, True),
    ("TimeoutError", ErrorJurisdiccion, False),
    ("NetworkError", TimeoutJurisdiccion, False)
])
@pytest.mark.asyncio
async def test_reintentar_errores_parametrized(processor, mock_playwright, initial_error, mock_class, expected_fixed):
    df_inicial = pd.DataFrame([
        ["TestJurisdiccion", False, None, initial_error]
    ], columns=["Nombre", "Notificacion", "Screenshot", "Error"])
    
    with patch('jurisdicciones.TestJurisdiccion', mock_class):
        df_result = await processor.reintentar_errores(mock_playwright, df_inicial)
        
        tiene_error = df_result.iloc[0]["Error"] is not None
        assert tiene_error != expected_fixed