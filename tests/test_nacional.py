import asyncio
import os
import sys

# Ensure project root is on sys.path so we can import test_manuales reliably
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from test_manuales import nacional_test

# Lista de clientes para pruebas en lote. Cada entrada es una tupla con:
# (nombre_cliente, carpeta_cliente, cuit_cliente, usuario_afip, clave_fiscal)
# Completar esta lista con los clientes que se deseen probar.
USERS = []


async def nacional_batch_test(
    headless: bool = False,
    iterations: int = 1,
    enable_tracing: bool = True,
    trace_dir: str = "traces",
):
    """
    Ejecuta `nacional_test` para una lista explícita de clientes.

    Para cada entrada establece las variables de entorno que usa
    `generic_test` (TEST_NACIONAL_*) y llama a `nacional_test`.

    Esta función permite probar en lote los clientes proporcionados por el
    equipo sin depender de la base de datos.
    """
    for nombre, client_folder, cuit, usuario, clave in USERS:
        # Configurar variables de entorno utilizadas por generic_test
        os.environ["TEST_NACIONAL_CLIENT"] = nombre 
        os.environ["TEST_NACIONAL_CLIENT_FOLDER"] = client_folder
        os.environ["TEST_NACIONAL_CUIT"] = usuario
        os.environ["TEST_NACIONAL_CLAVE_FISCAL"] = clave
        os.environ["TEST_NACIONAL_CUIT_CLIENTE_INPUT"] = cuit

        # Ejecutar el test para este cliente
        await nacional_test(
            headless=headless, iterations=iterations, enable_tracing=enable_tracing, trace_dir=trace_dir
        )


if __name__ == "__main__":
    asyncio.run(nacional_batch_test(headless=False, iterations=1))
