import random

import pytest

from main import main


@pytest.mark.asyncio
async def test_main():
    from config import clientes_si_verificar_config

    # Seleccionar un valor aleatorio de la lista clientes_si_verificar_config
    cliente_random = random.choice(clientes_si_verificar_config)

    # Configurar los argumentos necesarios
    DEBUG = False
    SIN_DEBUG_EJECUTAR_LISTA = True
    ENVIAR_CORREO_TEST = True
    headless_state = False if DEBUG else True
    EJECUTAR_TODOS_CLIENTES = False
    EJECUTAR_CLIENTES_LISTA = False

    # Ejecutar la función main con los argumentos configurados
    try:
        estado_value, correo_enviado_exitosamente = await main(
            debug=DEBUG,
            enviar_correo_test=ENVIAR_CORREO_TEST,
            headless_state=headless_state,
            ejecutar_todos_clientes=EJECUTAR_TODOS_CLIENTES,
            ejecutar_clientes_lista=EJECUTAR_CLIENTES_LISTA,
            sin_debug_ejecutar_lista=SIN_DEBUG_EJECUTAR_LISTA,
            clientes_si_verificar_config=clientes_si_verificar_config
        )
    except Exception as e:
        pytest.fail(f"main() raised an exception: {e}")

    # Aserciones para verificar el comportamiento esperado
    assert estado_value == "Correcto", "estado_value debe ser  'Correcto'"
    assert correo_enviado_exitosamente is True, "correo_enviado_exitosamente debe ser True"