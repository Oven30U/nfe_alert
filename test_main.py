import pandas as pd
import main
import pytest


@pytest.mark.main
@pytest.mark.error
@pytest.mark.asyncio
async def test_no_errors():
    # Ejecutar la función principal y capturar el DataFrame resultante
    df = await main.main()

    # Verificar que ninguna fila en la columna 'Error' tenga un valor distinto de None
    for error in df["Error"]:
        assert error is None, "Hay valor en Error de alguna jurisdiccion"

    for notificacion in df["Notificacion"]:
        assert notificacion in ["Hay notificaciones", "No hay notificaciones"], "Hay valor erroneo en Notificaciones"

    for screenshot in df["Screenshot"]:
        assert screenshot in ["Se realizó Screenshot", "No se realizó Screenshot"], "Hay valor erroneo en Screenshot"
