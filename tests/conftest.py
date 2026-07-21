"""
Configuración global de pytest para nfe_alert.

IMPORTANTE:
- No se modifica ningún archivo de la aplicación. Este conftest únicamente
  prepara variables de entorno y una base de datos SQLite temporal ANTES de
  que se importe cualquier módulo de la app, para que `obtener_datos_clientes.db`
  (que lee DATABASE_URL al importarse) quede apuntando a la DB de test.
- Todas las pruebas son deterministas: no golpean portales reales de AFIP/
  jurisdicciones provinciales. Los e2e usan un servidor HTTP local (ver
  tests/fixtures/portal_server.py) que simula los 3 escenarios relevantes:
  login OK, credenciales inválidas (mensaje explícito) y timeout/portal caído.
"""
import os
import sys
import tempfile
from pathlib import Path

# --- 1) Variables de entorno de test (antes de cualquier import de la app) ---
REPO_ROOT = Path(__file__).resolve().parent.parent
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
# Servidor HTTP local para los tests e2e (sin depender de portales reales)
# --------------------------------------------------------------------------
@pytest.fixture(scope="session")
def portal_server():
    from tests.fixtures.portal_server import PortalTestServer

    server = PortalTestServer()
    server.start()
    yield server
    server.stop()


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
