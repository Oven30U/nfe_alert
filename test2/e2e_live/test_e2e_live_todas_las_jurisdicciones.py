"""
E2E VIVO — login real + consulta de notificaciones real, para cada
jurisdicción implementada, usando las credenciales del .xlsm de mapeo.

⚠️ LEER README_E2E_LIVE.md ANTES DE CORRER ESTO. Resumen:
- Deshabilitado por defecto. Requiere RUN_LIVE_E2E=true.
- Pega contra portales reales (AFIP/ARCA + rentas provinciales) con
  credenciales reales de clientes reales.
- NO envía mails (ver conftest.py: bloqueado activamente + estos tests
  sólo ejercitan Jurisdiccion.procesar_jurisdiccion(), nunca
  ClienteProcessor.enviar_email/ClienteProcessor completo).
- Corré esto manualmente, nunca en un pipeline de CI automático.

Qué hace cada test, en detalle:
  1. Carga las credenciales de esa jurisdicción desde el .xlsm.
  2. Instancia la clase real (jurisdicciones.<Clase>) con Playwright real.
  3. Ejecuta el flujo real y completo: login -> consultar notificaciones ->
     buscar notificación -> tomar screenshot -> cerrar navegador (todo esto
     ya encapsulado en Jurisdiccion.procesar_jurisdiccion(), no se reinventa
     ninguna lógica de scraping acá).
  4. Registra resultado detallado (éxito/error, tipo de error, si hubo
     notificación, si se tomó screenshot, cuánto tardó) para el reporte
     final (tests/e2e_live/REPORTE_ULTIMA_CORRIDA.md).
  5. Assert principal: el login no debe rechazar las credenciales
     (LoginError / LoginErrorAfip). Cualquier otro tipo de error técnico
     (portal lento, selector cambiado, etc.) se reporta pero NO hace
     fallar el test individual -- para eso está el reporte detallado, que
     hay que revisar a mano tras cada corrida.
"""
from __future__ import annotations

import os
import time
from typing import Optional

import pytest
from playwright.async_api import async_playwright

from .manual_repro import pasos_para_item_e2e_live

pytestmark = [pytest.mark.e2e_live, pytest.mark.asyncio]

# Errores que si aparecen, SÍ hacen fallar el test (indican que la
# credencial fue rechazada por el portal real -- la señal más importante
# que esta suite puede darte).
ERRORES_DE_CREDENCIALES = {"LoginError", "LoginErrorAfip"}

# Errores técnicos conocidos que NO deben hacer fallar el test individual
# (se reportan igual en el resumen final, para revisión manual).
ERRORES_TECNICOS_TOLERADOS = {
    "ConsultarNotificacionesError",
    "BuscarNotificacionError",
    "TomarScreenshotError",
    "DelegacionError",
    None,
}


def _jurisdicciones_a_testear():
    """Arma la lista de (clase, codigo) a partir de config.jurisdiccion_clases,
    excluyendo las 2 sin implementar (Santa Fe, Tierra del Fuego)."""
    from config import jurisdiccion_clases

    NO_IMPLEMENTADAS = {"SantaFe", "TierraDelFuego"}
    items = []
    for codigo, clase in jurisdiccion_clases.items():
        if clase in NO_IMPLEMENTADAS:
            continue
        items.append(pytest.param(clase, codigo, id=clase))
    return items


@pytest.mark.manual_repro(callback=pasos_para_item_e2e_live)
@pytest.mark.parametrize("clase,codigo", _jurisdicciones_a_testear())
async def test_login_y_consulta_real(
    clase: str,
    codigo: str,
    credenciales_todas,
    cuit_cliente_overrides,
    rango_fechas,
    reporte_resultados,
):
    import jurisdicciones
    from config import jurisdiccion_clases  # noqa: F401 (usado para validar mapeo)
    from .credenciales_loader import resolver_cuit_cliente
    headless = os.getenv("HEADLESS_E2E_LIVE", "true").lower() == "true"

    credencial = credenciales_todas.get(clase)
    if credencial is None:
        pytest.skip(
            f"No hay credenciales para '{clase}' en el .xlsm (o están marcadas "
            "NO DESARROLLADO)."
        )

    cuit_cliente_input = resolver_cuit_cliente(credencial, cuit_cliente_overrides)
    if cuit_cliente_input == credencial["usuario"] and clase not in cuit_cliente_overrides:
        # Aviso explícito, no un fallo: puede ser incorrecto para
        # jurisdicciones con acceso delegado (ver credenciales_loader.py).
        print(
            f"[AVISO] '{clase}': usando cuit_cliente_input = usuario (no hay "
            "override ni columna cuit_cliente en el .xlsm). Puede ser "
            "incorrecto si el login es de un estudio contable delegado."
        )

    JurisdictionClass = getattr(jurisdicciones, clase, None)
    if JurisdictionClass is None:
        pytest.fail(f"'{clase}' está en config.py pero no existe en el paquete jurisdicciones.")

    inicio = time.monotonic()
    resultado_dict = {
        "resultado": "ERROR_INESPERADO",
        "error_type": None,
        "hay_notificacion": None,
        "hay_screenshot": None,
        "duracion_seg": None,
    }

    try:
        async with async_playwright() as playwright:
            create_kwargs = dict(
                playwright=playwright,
                cliente=credencial["client_folder"],
                client_folder=credencial["client_folder"],
                cuit=credencial["usuario"],
                clave_fiscal=credencial["password"],
                fecha_desde=rango_fechas["fecha_desde"],
                fecha_hasta=rango_fechas["fecha_hasta"],
                cuit_cliente_input=cuit_cliente_input,
                headless=headless,
            )
            instancia = await JurisdictionClass.create(**create_kwargs)

            nombre, hay_notificacion, hay_screenshot, error_type = (
                await instancia.procesar_jurisdiccion()
            )

            resultado_dict["error_type"] = error_type
            resultado_dict["hay_notificacion"] = hay_notificacion
            resultado_dict["hay_screenshot"] = hay_screenshot

            if error_type in ERRORES_DE_CREDENCIALES:
                resultado_dict["resultado"] = "CREDENCIALES_RECHAZADAS"
            elif error_type in ERRORES_TECNICOS_TOLERADOS:
                resultado_dict["resultado"] = "OK" if error_type is None else "ERROR_TECNICO_TOLERADO"
            else:
                resultado_dict["resultado"] = f"ERROR_NO_CLASIFICADO({error_type})"

    except Exception as e:
        resultado_dict["resultado"] = f"EXCEPCION_NO_CONTROLADA({type(e).__name__})"
        resultado_dict["error_type"] = type(e).__name__
        raise
    finally:
        resultado_dict["duracion_seg"] = round(time.monotonic() - inicio, 1)
        reporte_resultados[clase] = resultado_dict

    # ÚNICO assert duro: las credenciales no deben ser rechazadas.
    # Cualquier otro tipo de error queda registrado en el reporte pero no
    # tumba el test (portales caídos/selectores cambiados son "ruido"
    # esperable de un e2e contra sitios reales, no algo que deba bloquear
    # la corrida completa).
    assert error_type not in ERRORES_DE_CREDENCIALES, (
        f"'{clase}': el portal rechazó las credenciales ({error_type}). "
        f"Notificación devuelta: {hay_notificacion!r}"
    )
