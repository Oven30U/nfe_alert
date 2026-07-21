"""
Smoke tests: ¿la app arranca? ¿los módulos importan sin explotar? ¿la config
básica es coherente? Rápidos, sin browser, sin red.
"""
import importlib

import pytest

pytestmark = pytest.mark.smoke

MODULOS_CORE = [
    "config",
    "logger",
    "database",
    "models",
    "conectar_db",
    "cliente_processor",
    "mail",
    "mail_smtp",
    "generar_html",
    "mapa_plot",
    "obtener_datos_clientes.db",
    "obtener_datos_clientes.models",
    "obtener_datos_clientes.obtener_datos_clientes",
    "jurisdicciones.jurisdiccion",
]

# `inputs.py` (y por lo tanto `main.py`, que lo importa) dependen de
# `win32com.client` (pywin32), disponible SOLO en Windows. Es un hallazgo de
# este smoke test, no algo que hayamos decidido excluir por comodidad: en
# Linux/Mac ni siquiera se puede importar `main.py`. Si el equipo quiere
# correr esta suite en un runner Linux (ej. GitHub Actions ubuntu-latest),
# van a necesitar mockear `win32com` o mover ese import a donde realmente se
# usa (dentro de la función que lo necesita), en vez de al nivel del módulo.
MODULOS_SOLO_WINDOWS = ["inputs", "main"]

MODULOS_JURISDICCIONES = [
    "agip", "arba", "catamarca", "chaco", "chubut", "cordoba", "corrientes",
    "entre_rios", "formosa", "jujuy", "la_pampa", "la_rioja", "mendoza",
    "misiones", "nacional", "neuquen", "rio_negro", "salta", "san_juan",
    "san_luis", "santa_cruz", "santiago_del_estero", "sicnea", "tucuman",
]


@pytest.mark.parametrize("modulo", MODULOS_CORE)
def test_modulo_core_importa_sin_errores(modulo):
    importlib.import_module(modulo)


@pytest.mark.parametrize("modulo", MODULOS_JURISDICCIONES)
def test_jurisdiccion_importa_sin_errores(modulo):
    importlib.import_module(f"jurisdicciones.{modulo}")


@pytest.mark.parametrize("modulo", MODULOS_SOLO_WINDOWS)
def test_modulo_windows_only_solo_corre_en_windows(modulo):
    """Documenta y verifica el hallazgo: estos módulos requieren pywin32 y
    no pueden importarse fuera de Windows."""
    import sys

    if sys.platform != "win32":
        pytest.skip(
            f"'{modulo}' depende de win32com (pywin32) y sólo puede importarse en Windows. "
            "Ver TESTS_README.md - hallazgo de portabilidad."
        )
    importlib.import_module(modulo)


def test_todas_las_clases_de_jurisdiccion_configuradas_existen():
    """config.jurisdiccion_clases mapea nombres a nombres de clase; smoke
    check de que cada clase referenciada realmente existe en el paquete
    `jurisdicciones` y hereda de Jurisdiccion.

    NOTA: `jurisdicciones/__init__.py` documenta explícitamente 2
    jurisdicciones "sin DFE relevado" (sin implementar todavía): Santa Fe y
    Tierra del Fuego. Sin embargo `config.py` SÍ las incluye en
    `jurisdiccion_clases` ("921 SANTA FE" -> "SantaFe",
    "923 TIERRA DEL FUEGO" -> "TierraDelFuego"). Si algún día se carga un
    cliente con esa jurisdicción (desde Excel o DB), `crear_instancia_jurisdiccion`
    en cliente_processor.py haría `getattr(jurisdicciones, "SantaFe")` -> `None`
    y reventaría con un `AttributeError` sin ningún manejo específico, en vez
    de saltear esa jurisdicción con un mensaje claro. Este test tolera esas
    2 ausencias conocidas (para no bloquear CI) pero falla si aparece
    CUALQUIER OTRA clase faltante nueva."""
    import jurisdicciones
    from config import jurisdiccion_clases
    from jurisdicciones.jurisdiccion import Jurisdiccion

    CLASES_SIN_IMPLEMENTAR_CONOCIDAS = {"SantaFe", "TierraDelFuego"}

    faltantes = []
    no_heredan = []
    for nombre_clase in jurisdiccion_clases.values():
        clase = getattr(jurisdicciones, nombre_clase, None)
        if clase is None:
            faltantes.append(nombre_clase)
        elif not issubclass(clase, Jurisdiccion):
            no_heredan.append(nombre_clase)

    faltantes_inesperadas = set(faltantes) - CLASES_SIN_IMPLEMENTAR_CONOCIDAS
    assert not faltantes_inesperadas, (
        f"Clases NUEVAS referenciadas en config.py que no existen: {faltantes_inesperadas}"
    )
    assert set(faltantes) == CLASES_SIN_IMPLEMENTAR_CONOCIDAS, (
        "Las jurisdicciones sin implementar cambiaron respecto de lo documentado "
        f"en jurisdicciones/__init__.py. Actual: {set(faltantes)}"
    )
    assert not no_heredan, f"Clases que no heredan de Jurisdiccion: {no_heredan}"


def test_mapa_jurisdiccion_clases_es_inverso_correcto():
    from config import jurisdiccion_clases, mapa_jurisdiccion_clases

    assert len(mapa_jurisdiccion_clases) == len(jurisdiccion_clases)
    for codigo, clase in jurisdiccion_clases.items():
        assert mapa_jurisdiccion_clases[clase] == codigo


def test_logger_singleton_no_explota():
    from logger import Logger

    logger1 = Logger.get_logger()
    logger2 = Logger.get_logger()
    assert logger1 is logger2  # es singleton


def test_db_engine_de_test_queda_configurado_a_sqlite():
    """Confirma que el conftest realmente redirigió la DB antes de importar
    la app (si esto falla, TODOS los demás tests de integración están
    corriendo contra una URL de DB equivocada)."""
    from obtener_datos_clientes.db import engine

    assert str(engine.url).startswith("sqlite:///")
    assert "nfe_alert_test" in str(engine.url)
