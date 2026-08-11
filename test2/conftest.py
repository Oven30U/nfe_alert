"""
Configuración global de pytest para nfe_alert.

IMPORTANTE:
- No se modifica ningún archivo de la aplicación. Este conftest únicamente
  prepara variables de entorno y una base de datos SQLite temporal ANTES de
  que se importe cualquier módulo de la app, para que `obtener_datos_clientes.db`
  (que lee DATABASE_URL al importarse) quede apuntando a la DB de test.
- Todas las pruebas de unit/integration/smoke son deterministas: no golpean
  portales reales de AFIP/jurisdicciones provinciales (todo Playwright está
  mockeado). El único paquete que sí pega contra portales reales es
  `e2e_live/`, que está deshabilitado por defecto (ver e2e_live/README_E2E_LIVE.md)
  y se activa explícitamente con RUN_LIVE_E2E=true.

CÓMO SE RESUELVE EL PROYECTO A TESTEAR (REPO_ROOT):
Este directorio (`test2/`) es una suite de tests que vive AL LADO del/los
checkout(s) de la app (`nfe_alert/`), no adentro. Para saber qué copia de
`nfe_alert/` importar, se prueba en este orden:

  1. Variable de entorno NFE_ALERT_REPO_ROOT, si está seteada explícitamente.
  2. El propio padre de `test2/` (por si en algún momento se lo coloca
     directamente adentro de un checkout, ej. `nfe_alert/test2/`).
  3. Buscar, entre los directorios hermanos de `test2/`, el primero que
     contenga `<hermano>/nfe_alert/jurisdicciones/jurisdiccion.py` (el layout
     actual de este repo: `Agip/nfe_alert`, `Nacional/nfe_alert`,
     `Sicena/nfe_alert` son 3 checkouts idénticos del mismo código — se usa
     el primero que se encuentre, alfabéticamente, para tener una corrida
     determinista).

Si ninguna de las 3 estrategias encuentra un `nfe_alert` válido, se falla
rápido y explícito en vez de dejar que 100+ tests fallen con
`ModuleNotFoundError` uno por uno.
"""
import os
import sys
import tempfile
from pathlib import Path

# --- 1) Variables de entorno de test (antes de cualquier import de la app) ---


def _es_repo_nfe_alert_valido(path: Path) -> bool:
    return (path / "jurisdicciones" / "jurisdiccion.py").is_file()


def _resolver_repo_root() -> Path:
    env_override = os.environ.get("NFE_ALERT_REPO_ROOT")
    if env_override:
        candidato = Path(env_override).resolve()
        if _es_repo_nfe_alert_valido(candidato):
            return candidato
        raise RuntimeError(
            f"NFE_ALERT_REPO_ROOT={env_override!r} no contiene un checkout "
            "válido de nfe_alert (falta jurisdicciones/jurisdiccion.py)."
        )

    aqui = Path(__file__).resolve().parent  # test2/
    padre = aqui.parent

    # Caso 2: test2/ vive directamente adentro de un checkout de nfe_alert.
    if _es_repo_nfe_alert_valido(padre):
        return padre

    # Caso 3: test2/ vive al lado de uno o más checkouts (Agip/, Nacional/,
    # Sicena/, o cualquier otro nombre de carpeta que contenga nfe_alert/).
    candidatos = sorted(
        p / "nfe_alert"
        for p in padre.iterdir()
        if p.is_dir() and _es_repo_nfe_alert_valido(p / "nfe_alert")
    )
    if candidatos:
        return candidatos[0]

    raise RuntimeError(
        "No se pudo encontrar un checkout de nfe_alert para testear. "
        f"Se buscó en '{padre}' (directo y en subcarpetas tipo "
        "'<Jurisdiccion>/nfe_alert/'). Si tu layout es distinto, seteá "
        "la variable de entorno NFE_ALERT_REPO_ROOT con la ruta absoluta "
        "a la carpeta nfe_alert/ que querés testear."
    )


REPO_ROOT = _resolver_repo_root()
sys.path.insert(0, str(REPO_ROOT))

_TEST_DB_PATH = Path(tempfile.gettempdir()) / "nfe_alert_test.db"
if _TEST_DB_PATH.exists():
    _TEST_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
# Logger es un singleton que crea su archivo de log en el primer
# Logger.get_logger(); lo apuntamos a un tmp para no ensuciar el repo.
os.environ.setdefault(
    "log_file_path", str(Path(tempfile.gettempdir()) / "nfe_alert_test_logs" / "logfile.log")
)
os.environ.setdefault("PROYECTO", "NFE_TEST")
os.environ.setdefault("PROCESAMIENTOS_DIARIOS", "3")
os.environ.setdefault("INTERVALO_ESPERA_MINUTOS", "1")
os.environ.setdefault("INPUT_DATA_FROM_DB", "false")
os.environ.setdefault("MODO_CONTINUO", "false")
os.environ.setdefault("SERVIDOR_SMTP", "localhost")
os.environ.setdefault("PUERTO_SMTP", "1025")
os.environ.setdefault("SENDER_EMAIL", "test@example.com")
os.environ.setdefault("CORREO_NOTIFICACION_ERROR", "errores-test@example.com")
os.environ.setdefault("ENVIAR_CORREO_TEST", "false")
os.environ.setdefault("PASS_ZIP_DEFAULT", "test-pass")
os.environ.setdefault("LIMITES_REINTENTO", "2")
os.environ.setdefault("JURISDICCIONES_CONCURRENTES", "2")

import pytest

# `PATH_ESTRUCTURA_ROBOT`/directorio de trabajo: cada test que cree archivos en
# disco debe usar el fixture `estructura_robot_tmp` de más abajo.


# --------------------------------------------------------------------------
# DB de test (SQLite) — usa el mismo engine/SessionLocal que la app real
# --------------------------------------------------------------------------
@pytest.fixture(scope="session")
def test_db_engine():
    from obtener_datos_clientes.db import Base, engine
    from obtener_datos_clientes import models  # noqa: F401  (registra las tablas)

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(test_db_engine):
    """Sesión de DB de test. Limpia todas las tablas de la app al finalizar."""
    from obtener_datos_clientes.db import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(autouse=False)
def limpiar_tablas(test_db_engine):
    """Vacía todas las tablas de obtener_datos_clientes antes de un test puntual."""
    from obtener_datos_clientes.db import Base, SessionLocal

    session = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()
    yield


# --------------------------------------------------------------------------
# Directorios de trabajo (Estructura-robot/, screenshots, etc.)
# --------------------------------------------------------------------------
@pytest.fixture()
def estructura_robot_tmp(tmp_path, monkeypatch):
    """Ejecuta el test con cwd en un directorio temporal, para que
    ClienteProcessor cree 'Estructura-robot/...' sin ensuciar el repo."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH_ESTRUCTURA_ROBOT", str(tmp_path))
    return tmp_path


# --------------------------------------------------------------------------
# Fábricas de datos de clientes/jurisdicciones (DataFrames de entrada)
# --------------------------------------------------------------------------
@pytest.fixture()
def fila_jurisdiccion_factory():
    """Devuelve una función que arma una fila (dict) tipo la que produce
    inputs.obtener_clientes()/obtener_datos_clientes, con overrides opcionales."""

    def _make(**overrides):
        base = {
            "Cliente": "Cliente Demo SA",
            "client_folder": "cliente_demo",
            "cuit_cliente": "30111111112",
            "Usuario": "20222222223",
            "Password": "clave-secreta",
            "Jurisdiccion": "Chaco",
            "Nombre": "906 CHACO",
            "fecha_desde": "01/01/2026",
            "fecha_hasta": "31/01/2026",
            "Correo Output": "cliente@example.com",
            "CC: Equipo Deloitte": "equipo@example.com",
        }
        base.update(overrides)
        return base

    return _make


@pytest.fixture()
def df_cliente_factory(fila_jurisdiccion_factory):
    import pandas as pd

    def _make(filas: list[dict] | None = None):
        filas = filas or [fila_jurisdiccion_factory()]
        return pd.DataFrame(filas)

    return _make


# --------------------------------------------------------------------------
# Doble (fake) de Jurisdiccion para tests unitarios que no necesitan Playwright
# --------------------------------------------------------------------------
@pytest.fixture()
def jurisdiccion_testable_cls():
    """Subclase concreta mínima de Jurisdiccion (que es ABC) para poder
    instanciarla directamente en tests unitarios sin levantar un browser."""
    from jurisdicciones.jurisdiccion import Jurisdiccion

    class _JurisdiccionTestable(Jurisdiccion):
        async def consultar_notificaciones(self):
            return None

    return _JurisdiccionTestable


@pytest.fixture()
def make_jurisdiccion_fake(jurisdiccion_testable_cls):
    """Crea una instancia de Jurisdiccion (subclase testeable) SIN levantar
    un browser real: útil para tests unitarios de la lógica de clasificación
    de errores. `page` se inyecta manualmente (mock o página real de Playwright)."""
    from logger import Logger

    def _make(nombre="Chaco", page=None, cliente="Cliente Test"):
        instancia = jurisdiccion_testable_cls(
            nombre=nombre,
            codigo="000 TEST",
            cliente=cliente,
            client_folder="cliente_test",
            cuit="20111111112",
            clave_fiscal="clave-test",
            fecha_desde="01/01/2026",
            fecha_hasta="31/01/2026",
            cuit_cliente_input="30111111112",
        )
        instancia.logger = Logger.get_logger()
        instancia.page = page
        return instancia

    return _make


# ---- Hook de "Cómo reproducir manualmente" (ver tests/SNIPPET_PARA_CONFTEST_RAIZ.py) ----
import pytest as _pytest_for_hook


@_pytest_for_hook.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.outcome != "failed":
        return
    marker = item.get_closest_marker("manual_repro")
    if marker is None:
        return
    # IMPORTANTE: nunca pasar una función como único argumento POSICIONAL a
    # este marker (`@pytest.mark.manual_repro(mi_funcion)`) -- pytest lo
    # interpreta como "aplicar el marker directamente a mi_funcion" (el
    # atajo de `@pytest.mark.foo` sin paréntesis) y pisa el nombre del test
    # con lo que devuelva esa función, dejando "0 tests collected" sin
    # ningún error visible. Usar texto fijo como único positional
    # (`@pytest.mark.manual_repro("...")`) o una función vía keyword
    # (`@pytest.mark.manual_repro(callback=mi_funcion)`).
    if "callback" in marker.kwargs:
        contenido = marker.kwargs["callback"]
    elif marker.args:
        contenido = marker.args[0]
    else:
        return
    if callable(contenido):
        try:
            contenido = contenido(item)
        except Exception as e:
            contenido = f"(no se pudieron generar los pasos manuales: {e})"
    pytest_html = item.config.pluginmanager.getplugin("html")
    if pytest_html is None:
        return
    extra = getattr(report, "extras", [])
    extra.append(pytest_html.extras.text(contenido, name="Cómo reproducir manualmente"))
    report.extras = extra


# --------------------------------------------------------------------------
# pytest-html: título del reporte + info de entorno (qué checkout de
# nfe_alert se testeó, para que quede trazable en el HTML que se manda al
# dev/al jefe).
# --------------------------------------------------------------------------
def pytest_html_report_title(report):
    report.title = "NFE Alert — Reporte de Tests"


def pytest_configure(config):
    # pytest-metadata (dependencia de pytest-html) expone config._metadata;
    # en versiones donde no está disponible, no rompemos la corrida por esto.
    metadata = getattr(config, "_metadata", None)
    if metadata is not None:
        metadata["Proyecto testeado (REPO_ROOT)"] = str(REPO_ROOT)
        metadata["DATABASE_URL de test"] = os.environ.get("DATABASE_URL", "")


# --------------------------------------------------------------------------
# Seguridad: bajo ninguna circunstancia un test debe enviar un mail real.
# Esta suite mockea el envío explícitamente donde corresponde, pero como
# defensa en profundidad se bloquea acá también, a nivel global y para
# TODOS los tests (autouse), cualquier intento de abrir una conexión SMTP
# real o de llamar a la función de envío de la app si no fue mockeada.
# Si un test necesita "enviar mail", tiene que mockear explícitamente lo
# que use (smtplib.SMTP, o la función enviar_correo de la app) ANTES de
# que corra este fixture, o el intento va a levantar RuntimeError.
# --------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _bloquear_envio_de_mail_real(monkeypatch):
    import smtplib

    def _bloqueado(*args, **kwargs):
        raise RuntimeError(
            "Intento de conexión SMTP real durante un test (bloqueado por "
            "conftest.py). Si tu test necesita mail, mockealo explícitamente."
        )

    monkeypatch.setattr(smtplib, "SMTP", _bloqueado)
    monkeypatch.setattr(smtplib, "SMTP_SSL", _bloqueado)

    for modulo in ("mail", "mail_smtp"):
        try:
            mod = __import__(modulo)
        except ImportError:
            continue
        monkeypatch.setattr(mod, "enviar_correo", _bloqueado, raising=False)
