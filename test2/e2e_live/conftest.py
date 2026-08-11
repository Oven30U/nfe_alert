"""
Conftest exclusivo de tests/e2e_live/.

Estos tests NO son parte de la suite normal (`pytest -m "not slow"` ni
siquiera `pytest -m e2e`): pegan contra portales reales de AFIP/ARCA y
rentas provinciales con credenciales reales de clientes. Por eso:

1. Están gateados por la variable de entorno RUN_LIVE_E2E=true. Sin ella,
   TODO lo que está en esta carpeta se skipea automáticamente, incluso si
   alguien corre `pytest` a secas desde la raíz del repo.
2. Bloquean activamente cualquier intento de enviar un mail real (aunque
   estos tests no deberían ni acercarse a esa lógica, es un cinturón de
   seguridad adicional: no probamos ClienteProcessor acá, sólo el login y
   la consulta de notificaciones a nivel Jurisdiccion).
3. Nunca loggean ni imprimen usuario/password (ver credenciales_loader.py).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RUN_LIVE_E2E = os.getenv("RUN_LIVE_E2E", "").lower() == "true"
HEADLESS_E2E_LIVE = os.getenv("HEADLESS_E2E_LIVE", "true").lower() == "true"


def pytest_collection_modifyitems(config, items):
    """Sin RUN_LIVE_E2E=true, se skipea TODO lo de esta carpeta."""
    if RUN_LIVE_E2E:
        return
    skip_live = pytest.mark.skip(
        reason=(
            "Suite e2e_live deshabilitada por defecto (pega contra portales "
            "reales con credenciales reales). Correr con RUN_LIVE_E2E=true "
            "para habilitarla explícitamente. Ver README_E2E_LIVE.md."
        )
    )
    for item in items:
        if "e2e_live" in str(item.fspath):
            item.add_marker(skip_live)


@pytest.fixture(scope="session", autouse=True)
def bloquear_envio_de_mail():
    """
    Cinturón de seguridad: si por error algún test de esta carpeta llegara a
    ejecutar código que intenta enviar un mail real (smtplib o las
    funciones enviar_correo de mail.py/mail_smtp.py/mail_outlook.py), que
    explote fuerte en vez de mandar algo a un cliente real.
    """
    import smtplib
    from unittest.mock import patch

    def _bloqueado(*args, **kwargs):
        raise RuntimeError(
            "BLOQUEADO por seguridad: la suite e2e_live no debe enviar mails. "
            "Si estás viendo este error, algo en el flujo bajo test intentó "
            "mandar un correo real -- revisar antes de continuar."
        )

    parches = [
        patch.object(smtplib, "SMTP", side_effect=_bloqueado),
        patch.object(smtplib, "SMTP_SSL", side_effect=_bloqueado),
    ]
    try:
        import mail

        parches.append(patch.object(mail, "enviar_correo", side_effect=_bloqueado))
    except Exception:
        pass

    for p in parches:
        try:
            p.start()
        except Exception:
            pass

    yield

    for p in parches:
        try:
            p.stop()
        except Exception:
            pass


@pytest.fixture(scope="session")
def credenciales_todas():
    from .credenciales_loader import cargar_credenciales

    return cargar_credenciales()


@pytest.fixture(scope="session")
def cuit_cliente_overrides() -> Dict[str, str]:
    """
    Overrides opcionales de cuit_cliente por clase, vía variable de entorno
    CUIT_CLIENTE_OVERRIDES_JSON (JSON: {"Agip": "30xxxxxxxxx", "Arba": "..."}).
    El archivo .xlsm de credenciales no trae esta columna -- ver
    credenciales_loader.resolver_cuit_cliente para el detalle.
    """
    raw = os.getenv("CUIT_CLIENTE_OVERRIDES_JSON", "")
    if not raw:
        return {}
    return json.loads(raw)


@pytest.fixture(scope="session")
def rango_fechas():
    """Ventana chica (últimos 7 días) para minimizar carga sobre los
    portales reales en cada corrida.

    Formato ddmmyyyy SIN separadores (ej. "07072026") -- confirmado con
    `grep -rn "strptime(.*fecha_desde" jurisdicciones/*.py`: las 24
    jurisdicciones parsean con `datetime.strptime(fecha_desde, "%d%m%Y")`.
    Una versión anterior de este fixture generaba "%d/%m/%Y" (con barras),
    lo cual rompía sicnea.py (falla eager en su create()) y probablemente
    quedaba enmascarado como ConsultarNotificacionesError -- "tolerado" por
    el assert de test_e2e_live_todas_las_jurisdicciones.py -- en el resto.
    """
    hoy = datetime.now()
    hace_7_dias = hoy.replace(day=max(1, hoy.day - 7))
    return {
        "fecha_desde": hace_7_dias.strftime("%d%m%Y"),
        "fecha_hasta": hoy.strftime("%d%m%Y"),
    }


@pytest.fixture(scope="session")
def reporte_resultados():
    """Acumula resultados detallados por jurisdicción durante toda la
    sesión y los vuelca a un archivo al finalizar (ver pytest_sessionfinish
    más abajo)."""
    return {}


def pytest_sessionfinish(session, exitstatus):
    """Al terminar, si se acumularon resultados, escribe un reporte
    markdown detallado (sin credenciales) a disco."""
    resultados = getattr(session.config, "_e2e_live_resultados", None)
    if not resultados:
        return

    out_path = Path(__file__).resolve().parent / "REPORTE_ULTIMA_CORRIDA.md"
    lineas = [
        "# Reporte e2e_live — última corrida",
        "",
        f"Fecha: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "| Jurisdicción | Resultado | Tipo de error | Notificación | Screenshot | Duración (s) |",
        "|---|---|---|---|---|---:|",
    ]
    for clase, r in sorted(resultados.items()):
        lineas.append(
            f"| {clase} | {r['resultado']} | {r.get('error_type') or '-'} | "
            f"{r.get('hay_notificacion') or '-'} | {r.get('hay_screenshot') or '-'} | "
            f"{r.get('duracion_seg', '-')} |"
        )
    out_path.write_text("\n".join(lineas), encoding="utf-8")


@pytest.fixture(autouse=True)
def _registrar_resultado(request, reporte_resultados):
    """Hook simple para que cada test individual pueda registrar su
    resultado en session.config, sin depender del orden de fixtures."""
    request.config._e2e_live_resultados = reporte_resultados
    yield
