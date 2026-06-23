"""
Tests End-to-End — NFE Alert
=============================
Estos tests ejecutan el flujo REAL completo:
  DB → credenciales → Playwright → portal fiscal → resultado → correo

NO usan mocks. Requieren:
  - Conexión a SQL Server (ARBAS0229)
  - Acceso a internet (portales fiscales)
  - Variables de entorno del .env cargadas

Variable de control de correo:
  E2E_RECEPTOR  = destinatario de todos los correos de test
  E2E_CC        = CC de todos los correos de test

Por defecto ambas apuntan a opereyra@deloitte.com para que los
resultados lleguen solo al responsable de testing, sin tocar los
correos reales de los clientes.

Cómo correr un test individual:
  cd nfe_alert
  pytest tests/test_e2e.py::TestE2ENacional::test_nacional_flujo_completo -v -s

Cómo correr todos los e2e:
  pytest tests/test_e2e.py -v -s --timeout=300

Marcadores:
  @pytest.mark.e2e         — requiere red y DB
  @pytest.mark.slow        — puede tardar más de 60 segundos
"""

import asyncio
import os
import sys
import datetime
import pytest
import pytest_asyncio
from dotenv import load_dotenv

# Cargar .env antes de cualquier import del proyecto
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Configuración de correo para tests — SIEMPRE a opereyra, nunca al cliente
# ---------------------------------------------------------------------------
E2E_RECEPTOR = os.getenv("E2E_RECEPTOR", "opereyra@deloitte.com")
E2E_CC       = os.getenv("E2E_CC",       "opereyra@deloitte.com")


# ---------------------------------------------------------------------------
# Helpers compartidos
# ---------------------------------------------------------------------------

def fechas_env():
    """Devuelve (fecha_desde, fecha_hasta) desde el .env, con fallback al mes actual."""
    desde = os.getenv("FECHA_DESDE", datetime.datetime.now().strftime("01%m%Y"))
    hasta = os.getenv("FECHA_HASTA", datetime.datetime.now().strftime("%d%m%Y"))
    return desde, hasta


def crear_directorios(client_folder: str):
    """Crea Output y Backup para el cliente dentro de PATH_ESTRUCTURA_ROBOT."""
    base = os.getenv("PATH_ESTRUCTURA_ROBOT", "Estructura-robot")
    output = os.path.join(base, client_folder, "Output")
    backup = os.path.join(base, client_folder, "Backup")
    os.makedirs(output, exist_ok=True)
    os.makedirs(backup, exist_ok=True)
    return output, backup


async def _ejecutar_jurisdiccion(clase_nombre: str, env_prefix: str, playwright):
    """
    Crea y ejecuta una instancia de jurisdicción usando credenciales del .env.

    Args:
        clase_nombre: Nombre de la clase Python (ej: "Nacional", "Agip")
        env_prefix:   Prefijo de las variables de entorno (ej: "TEST_NACIONAL")
        playwright:   Instancia de Playwright activa

    Returns:
        Tuple (nombre, hay_notificacion, hay_screenshot, error_type)
    """
    import jurisdicciones

    cliente        = os.getenv(f"{env_prefix}_CLIENT")
    client_folder  = os.getenv(f"{env_prefix}_CLIENT_FOLDER")
    cuit           = os.getenv(f"{env_prefix}_CUIT")
    clave_fiscal   = os.getenv(f"{env_prefix}_CLAVE_FISCAL")
    cuit_cliente   = os.getenv(f"{env_prefix}_CUIT_CLIENTE_INPUT")
    fecha_desde, fecha_hasta = fechas_env()

    crear_directorios(client_folder)

    ClaseJurisdiccion = getattr(jurisdicciones, clase_nombre)

    create_args = dict(
        playwright=playwright,
        cliente=cliente,
        client_folder=client_folder,
        cuit=int(cuit),
        clave_fiscal=clave_fiscal,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cuit_cliente_input=int(cuit_cliente),
        headless=False,  # Visible para poder diagnosticar fallos en e2e
    )

    instancia = await ClaseJurisdiccion.create(**create_args)
    return await instancia.procesar_jurisdiccion()


def _enviar_correo_resultado(resultado, cliente: str, cuit: str, inicio: datetime.datetime):
    """
    Envía el correo con los resultados del test e2e.
    Receptor y CC siempre apuntan a E2E_RECEPTOR / E2E_CC (opereyra@deloitte.com).
    """
    import pandas as pd
    from mail import enviar_correo

    nombre, notif, screenshot, error = resultado
    df = pd.DataFrame([{
        "Jurisdiccion": nombre,
        "Notificacion": notif,
        "Screenshot":   screenshot,
        "Error":        error or "",
    }])

    enviar_correo(
        receptor=E2E_RECEPTOR,
        cliente=cliente,
        cuit=cuit,
        inicio=inicio,
        df=df,
        cc=E2E_CC,
    )


# ---------------------------------------------------------------------------
# Fixture de Playwright real (no mock)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def pw():
    """Inicia y cierra Playwright real para cada test."""
    from playwright.async_api import async_playwright
    async with async_playwright() as playwright:
        yield playwright


# ===========================================================================
# Bloque 1 — Conectividad a la base de datos
# ===========================================================================

@pytest.mark.e2e
class TestE2EConectividadDB:
    """
    Verifica que la DB es accesible y que los clientes de prueba
    están correctamente configurados antes de correr los tests reales.
    """

    def test_conexion_a_sqlserver(self):
        """La DB debe ser accesible con las credenciales del .env."""
        from obtener_datos_clientes.db import SessionLocal
        with SessionLocal() as db:
            result = db.execute(__import__("sqlalchemy").text("SELECT 1")).fetchone()
        assert result is not None
        assert result[0] == 1

    def test_cliente_nacional_existe_en_db(self):
        """El cliente configurado para Nacional debe estar en la tabla clientes."""
        from obtener_datos_clientes.db import SessionLocal
        from obtener_datos_clientes.models import Cliente
        client_folder = os.getenv("TEST_NACIONAL_CLIENT_FOLDER")
        with SessionLocal() as db:
            cliente = db.query(Cliente).filter(
                Cliente.client_folder == client_folder
            ).first()
        assert cliente is not None, (
            f"Cliente '{client_folder}' no encontrado en DB. "
            "Verificar TEST_NACIONAL_CLIENT_FOLDER en .env"
        )

    def test_cliente_agip_existe_en_db(self):
        from obtener_datos_clientes.db import SessionLocal
        from obtener_datos_clientes.models import Cliente
        client_folder = os.getenv("TEST_AGIP_CLIENT_FOLDER")
        with SessionLocal() as db:
            cliente = db.query(Cliente).filter(
                Cliente.client_folder == client_folder
            ).first()
        assert cliente is not None, f"Cliente '{client_folder}' no encontrado en DB"

    def test_credenciales_nacional_en_cliente_jurisdiccion(self):
        """La relación cliente-jurisdiccion para Nacional debe tener usuario y password."""
        from obtener_datos_clientes.db import SessionLocal
        from obtener_datos_clientes.models import Cliente, ClienteJurisdiccion, Jurisdiccion
        client_folder = os.getenv("TEST_NACIONAL_CLIENT_FOLDER")
        with SessionLocal() as db:
            cliente = db.query(Cliente).filter(
                Cliente.client_folder == client_folder
            ).first()
            assert cliente is not None, f"Cliente '{client_folder}' no encontrado"

            cj = (
                db.query(ClienteJurisdiccion)
                .join(Jurisdiccion)
                .filter(
                    ClienteJurisdiccion.cliente_id == cliente.id,
                    Jurisdiccion.clase == "Nacional",
                )
                .first()
            )
        assert cj is not None, "Relación cliente-Nacional no encontrada en DB"
        assert cj.usuario, "Campo 'usuario' vacío en cliente_jurisdiccion para Nacional"
        assert cj.password, "Campo 'password' vacío en cliente_jurisdiccion para Nacional"

    @pytest.mark.parametrize("env_prefix,clase", [
        ("TEST_AGIP",       "Agip"),
        ("TEST_CORDOBA",    "Cordoba"),
        ("TEST_NEUQUEN",    "Neuquen"),
        ("TEST_ENTRERIOS",  "EntreRios"),
        ("TEST_CATAMARCA",  "Catamarca"),
        ("TEST_CHACO",      "Chaco"),
        ("TEST_LA_PAMPA",   "LaPampa"),
        ("TEST_MENDOZA",    "Mendoza"),
        ("TEST_SALTA",      "Salta"),
        ("TEST_SAN_JUAN",   "SanJuan"),
        ("TEST_SANLUIS",    "SanLuis"),
        ("TEST_SANTA_CRUZ", "SantaCruz"),
    ])
    def test_credenciales_en_db(self, env_prefix, clase):
        """Cada jurisdicción debe tener usuario y password configurados en la DB."""
        from obtener_datos_clientes.db import SessionLocal
        from obtener_datos_clientes.models import Cliente, ClienteJurisdiccion, Jurisdiccion
        client_folder = os.getenv(f"{env_prefix}_CLIENT_FOLDER")
        if not client_folder:
            pytest.skip(f"No se encontró {env_prefix}_CLIENT_FOLDER en .env")

        with SessionLocal() as db:
            cliente = db.query(Cliente).filter(
                Cliente.client_folder == client_folder
            ).first()
            if not cliente:
                pytest.skip(f"Cliente '{client_folder}' no encontrado en DB")

            cj = (
                db.query(ClienteJurisdiccion)
                .join(Jurisdiccion)
                .filter(
                    ClienteJurisdiccion.cliente_id == cliente.id,
                    Jurisdiccion.clase == clase,
                )
                .first()
            )
        assert cj is not None, f"Relación cliente-{clase} no encontrada en DB"
        assert cj.usuario,  f"'usuario' vacío para {clase}"
        assert cj.password, f"'password' vacío para {clase}"


# ===========================================================================
# Bloque 2 — Flujo completo por jurisdicción
# ===========================================================================

@pytest.mark.e2e
@pytest.mark.slow
class TestE2ENacional:
    """Test e2e de la jurisdicción Nacional (AFIP/ARCA)."""

    @pytest.mark.asyncio
    async def test_nacional_flujo_completo(self, pw):
        """
        Flujo completo: login AFIP → acceso DFE → búsqueda → screenshot → correo.
        El correo llega a opereyra@deloitte.com.
        """
        inicio = datetime.datetime.now()
        resultado = await _ejecutar_jurisdiccion("Nacional", "TEST_NACIONAL", pw)
        nombre, notif, screenshot, error = resultado

        # El resultado siempre debe tener los 4 campos
        assert nombre == "Nacional"
        assert notif is not None and notif is not False
        assert screenshot is not None

        # Enviar correo con resultado — solo a opereyra
        _enviar_correo_resultado(
            resultado,
            cliente=os.getenv("TEST_NACIONAL_CLIENT"),
            cuit=os.getenv("TEST_NACIONAL_CUIT"),
            inicio=inicio,
        )

    @pytest.mark.asyncio
    async def test_nacional_no_termina_sin_resultado(self, pw):
        """Invariante: procesar_jurisdiccion nunca retorna None."""
        resultado = await _ejecutar_jurisdiccion("Nacional", "TEST_NACIONAL", pw)
        assert resultado is not None
        assert len(resultado) == 4


@pytest.mark.e2e
@pytest.mark.slow
class TestE2EAgip:
    """Test e2e de AGIP (Ciudad de Buenos Aires)."""

    @pytest.mark.asyncio
    async def test_agip_flujo_completo(self, pw):
        inicio = datetime.datetime.now()
        resultado = await _ejecutar_jurisdiccion("Agip", "TEST_AGIP", pw)
        nombre, notif, screenshot, error = resultado

        assert nombre == "Agip"
        assert notif is not None

        _enviar_correo_resultado(
            resultado,
            cliente=os.getenv("TEST_AGIP_CLIENT"),
            cuit=os.getenv("TEST_AGIP_CUIT"),
            inicio=inicio,
        )


@pytest.mark.e2e
@pytest.mark.slow
class TestE2ECordoba:

    @pytest.mark.asyncio
    async def test_cordoba_flujo_completo(self, pw):
        inicio = datetime.datetime.now()
        resultado = await _ejecutar_jurisdiccion("Cordoba", "TEST_CORDOBA", pw)
        nombre, notif, screenshot, error = resultado

        assert nombre == "Cordoba"
        assert notif is not None

        _enviar_correo_resultado(
            resultado,
            cliente=os.getenv("TEST_CORDOBA_CLIENT"),
            cuit=os.getenv("TEST_CORDOBA_CUIT"),
            inicio=inicio,
        )


@pytest.mark.e2e
@pytest.mark.slow
class TestE2ENeuquen:

    @pytest.mark.asyncio
    async def test_neuquen_flujo_completo(self, pw):
        inicio = datetime.datetime.now()
        resultado = await _ejecutar_jurisdiccion("Neuquen", "TEST_NEUQUEN", pw)
        nombre, notif, screenshot, error = resultado

        assert nombre == "Neuquen"
        assert notif is not None

        _enviar_correo_resultado(
            resultado,
            cliente=os.getenv("TEST_NEUQUEN_CLIENT"),
            cuit=os.getenv("TEST_NEUQUEN_CUIT"),
            inicio=inicio,
        )


@pytest.mark.e2e
@pytest.mark.slow
class TestE2EEntreRios:

    @pytest.mark.asyncio
    async def test_entre_rios_flujo_completo(self, pw):
        inicio = datetime.datetime.now()
        resultado = await _ejecutar_jurisdiccion("EntreRios", "TEST_ENTRERIOS", pw)
        nombre, notif, screenshot, error = resultado

        assert nombre == "EntreRios"
        assert notif is not None

        _enviar_correo_resultado(
            resultado,
            cliente=os.getenv("TEST_ENTRERIOS_CLIENT"),
            cuit=os.getenv("TEST_ENTRERIOS_CUIT"),
            inicio=inicio,
        )


@pytest.mark.e2e
@pytest.mark.slow
class TestE2ECatamarca:

    @pytest.mark.asyncio
    async def test_catamarca_flujo_completo(self, pw):
        inicio = datetime.datetime.now()
        resultado = await _ejecutar_jurisdiccion("Catamarca", "TEST_CATAMARCA", pw)
        nombre, notif, screenshot, error = resultado

        assert nombre == "Catamarca"
        assert notif is not None

        _enviar_correo_resultado(
            resultado,
            cliente=os.getenv("TEST_CATAMARCA_CLIENT"),
            cuit=os.getenv("TEST_CATAMARCA_CUIT"),
            inicio=inicio,
        )


@pytest.mark.e2e
@pytest.mark.slow
class TestE2EChaco:

    @pytest.mark.asyncio
    async def test_chaco_flujo_completo(self, pw):
        inicio = datetime.datetime.now()
        resultado = await _ejecutar_jurisdiccion("Chaco", "TEST_CHACO", pw)
        nombre, notif, screenshot, error = resultado

        assert nombre == "Chaco"
        assert notif is not None

        _enviar_correo_resultado(
            resultado,
            cliente=os.getenv("TEST_CHACO_CLIENT"),
            cuit=os.getenv("TEST_CHACO_CUIT"),
            inicio=inicio,
        )


@pytest.mark.e2e
@pytest.mark.slow
class TestE2ELaPampa:

    @pytest.mark.asyncio
    async def test_la_pampa_flujo_completo(self, pw):
        inicio = datetime.datetime.now()
        resultado = await _ejecutar_jurisdiccion("LaPampa", "TEST_LA_PAMPA", pw)
        nombre, notif, screenshot, error = resultado

        assert nombre == "LaPampa"
        assert notif is not None

        _enviar_correo_resultado(
            resultado,
            cliente=os.getenv("TEST_LA_PAMPA_CLIENT"),
            cuit=os.getenv("TEST_LA_PAMPA_CUIT"),
            inicio=inicio,
        )


@pytest.mark.e2e
@pytest.mark.slow
class TestE2EMendoza:

    @pytest.mark.asyncio
    async def test_mendoza_flujo_completo(self, pw):
        inicio = datetime.datetime.now()
        resultado = await _ejecutar_jurisdiccion("Mendoza", "TEST_MENDOZA", pw)
        nombre, notif, screenshot, error = resultado

        assert nombre == "Mendoza"
        assert notif is not None

        _enviar_correo_resultado(
            resultado,
            cliente=os.getenv("TEST_MENDOZA_CLIENT"),
            cuit=os.getenv("TEST_MENDOZA_CUIT"),
            inicio=inicio,
        )


@pytest.mark.e2e
@pytest.mark.slow
class TestE2ESalta:

    @pytest.mark.asyncio
    async def test_salta_flujo_completo(self, pw):
        inicio = datetime.datetime.now()
        resultado = await _ejecutar_jurisdiccion("Salta", "TEST_SALTA", pw)
        nombre, notif, screenshot, error = resultado

        assert nombre == "Salta"
        assert notif is not None

        _enviar_correo_resultado(
            resultado,
            cliente=os.getenv("TEST_SALTA_CLIENT"),
            cuit=os.getenv("TEST_SALTA_CUIT"),
            inicio=inicio,
        )


@pytest.mark.e2e
@pytest.mark.slow
class TestE2ESanJuan:

    @pytest.mark.asyncio
    async def test_san_juan_flujo_completo(self, pw):
        inicio = datetime.datetime.now()
        resultado = await _ejecutar_jurisdiccion("SanJuan", "TEST_SAN_JUAN", pw)
        nombre, notif, screenshot, error = resultado

        assert nombre == "SanJuan"
        assert notif is not None

        _enviar_correo_resultado(
            resultado,
            cliente=os.getenv("TEST_SAN_JUAN_CLIENT"),
            cuit=os.getenv("TEST_SAN_JUAN_CUIT"),
            inicio=inicio,
        )


@pytest.mark.e2e
@pytest.mark.slow
class TestE2ESanLuis:

    @pytest.mark.asyncio
    async def test_san_luis_flujo_completo(self, pw):
        inicio = datetime.datetime.now()
        resultado = await _ejecutar_jurisdiccion("SanLuis", "TEST_SANLUIS", pw)
        nombre, notif, screenshot, error = resultado

        assert nombre == "SanLuis"
        assert notif is not None

        _enviar_correo_resultado(
            resultado,
            cliente=os.getenv("TEST_SANLUIS_CLIENT"),
            cuit=os.getenv("TEST_SANLUIS_CUIT"),
            inicio=inicio,
        )


@pytest.mark.e2e
@pytest.mark.slow
class TestE2ESantaCruz:

    @pytest.mark.asyncio
    async def test_santa_cruz_flujo_completo(self, pw):
        inicio = datetime.datetime.now()
        resultado = await _ejecutar_jurisdiccion("SantaCruz", "TEST_SANTA_CRUZ", pw)
        nombre, notif, screenshot, error = resultado

        assert nombre == "SantaCruz"
        assert notif is not None

        _enviar_correo_resultado(
            resultado,
            cliente=os.getenv("TEST_SANTA_CRUZ_CLIENT"),
            cuit=os.getenv("TEST_SANTA_CRUZ_CUIT"),
            inicio=inicio,
        )


@pytest.mark.e2e
@pytest.mark.slow
class TestE2EChubut:

    @pytest.mark.asyncio
    async def test_chubut_flujo_completo(self, pw):
        inicio = datetime.datetime.now()
        resultado = await _ejecutar_jurisdiccion("Chubut", "TEST_CHUBUT", pw)
        nombre, notif, screenshot, error = resultado

        assert nombre == "Chubut"
        assert notif is not None

        _enviar_correo_resultado(
            resultado,
            cliente=os.getenv("TEST_CHUBUT_CLIENT"),
            cuit=os.getenv("TEST_CHUBUT_CUIT"),
            inicio=inicio,
        )


@pytest.mark.e2e
@pytest.mark.slow
class TestE2ESantiagoDelEstero:

    @pytest.mark.asyncio
    async def test_santiago_del_estero_flujo_completo(self, pw):
        inicio = datetime.datetime.now()
        resultado = await _ejecutar_jurisdiccion(
            "SantiagoDelEstero", "TEST_SANTIAGO_DEL_ESTERO", pw
        )
        nombre, notif, screenshot, error = resultado

        assert nombre == "SantiagoDelEstero"
        assert notif is not None

        _enviar_correo_resultado(
            resultado,
            cliente=os.getenv("TEST_SANTIAGO_DEL_ESTERO_CLIENT"),
            cuit=os.getenv("TEST_SANTIAGO_DEL_ESTERO_CUIT"),
            inicio=inicio,
        )


@pytest.mark.e2e
@pytest.mark.slow
class TestE2ELaRioja:

    @pytest.mark.asyncio
    async def test_la_rioja_flujo_completo(self, pw):
        inicio = datetime.datetime.now()
        resultado = await _ejecutar_jurisdiccion("LaRioja", "TEST_LA_RIOJA", pw)
        nombre, notif, screenshot, error = resultado

        assert nombre == "LaRioja"
        assert notif is not None

        _enviar_correo_resultado(
            resultado,
            cliente=os.getenv("TEST_LA_RIOJA_CLIENT"),
            cuit=os.getenv("TEST_LA_RIOJA_CUIT"),
            inicio=inicio,
        )


# ===========================================================================
# Bloque 3 — Flujo combinado: múltiples jurisdicciones del mismo cliente
# ===========================================================================

@pytest.mark.e2e
@pytest.mark.slow
class TestE2EClienteCompleto:
    """
    Ejecuta todas las jurisdicciones de un cliente en paralelo,
    replicando exactamente lo que hace el sistema en producción.
    Usa el cliente JANSSEN que tiene varias jurisdicciones configuradas.
    """

    @pytest.mark.asyncio
    async def test_janssen_todas_las_jurisdicciones(self, pw):
        """
        Ejecuta en paralelo todas las jurisdicciones de JANSSEN CILAG
        y envía UN solo correo consolidado a opereyra@deloitte.com.
        """
        import pandas as pd
        from mail import enviar_correo

        inicio = datetime.datetime.now()

        # Jurisdicciones de JANSSEN según el .env
        jurisdicciones_janssen = [
            ("Chaco",       "TEST_CHACO"),
            ("LaPampa",     "TEST_LA_PAMPA"),
            ("SanLuis",     "TEST_SANLUIS"),
            ("LaRioja",     "TEST_LA_RIOJA"),
            ("Chubut",      "TEST_CHUBUT"),
        ]

        # Ejecutar en paralelo
        tareas = [
            _ejecutar_jurisdiccion(clase, prefix, pw)
            for clase, prefix in jurisdicciones_janssen
        ]
        resultados = await asyncio.gather(*tareas, return_exceptions=True)

        # Armar DataFrame consolidado
        filas = []
        for i, resultado in enumerate(resultados):
            clase, prefix = jurisdicciones_janssen[i]
            if isinstance(resultado, Exception):
                filas.append({
                    "Jurisdiccion": clase,
                    "Notificacion": f"Error: {resultado}",
                    "Screenshot":   "No",
                    "Error":        type(resultado).__name__,
                })
            else:
                nombre, notif, screenshot, error = resultado
                filas.append({
                    "Jurisdiccion": nombre,
                    "Notificacion": notif,
                    "Screenshot":   screenshot,
                    "Error":        error or "",
                })

        df = pd.DataFrame(filas)

        # Todos los resultados deben tener nombre
        assert all(df["Jurisdiccion"].notna())
        assert len(df) == len(jurisdicciones_janssen)

        # Correo consolidado — solo a opereyra
        enviar_correo(
            receptor=E2E_RECEPTOR,
            cliente="JANSSEN CILAG FARMACEUTICA S.A — E2E Test",
            cuit=os.getenv("TEST_CHACO_CUIT_CLIENTE_INPUT"),
            inicio=inicio,
            df=df,
            cc=E2E_CC,
        )

    @pytest.mark.asyncio
    async def test_pfizer_todas_las_jurisdicciones(self, pw):
        """
        Ejecuta en paralelo todas las jurisdicciones de PFIZER
        y envía un correo consolidado a opereyra@deloitte.com.
        """
        import pandas as pd
        from mail import enviar_correo

        inicio = datetime.datetime.now()

        jurisdicciones_pfizer = [
            ("EntreRios",         "TEST_ENTRERIOS"),
            ("Salta",             "TEST_SALTA"),
            ("SantiagoDelEstero", "TEST_SANTIAGO_DEL_ESTERO"),
        ]

        tareas = [
            _ejecutar_jurisdiccion(clase, prefix, pw)
            for clase, prefix in jurisdicciones_pfizer
        ]
        resultados = await asyncio.gather(*tareas, return_exceptions=True)

        filas = []
        for i, resultado in enumerate(resultados):
            clase, prefix = jurisdicciones_pfizer[i]
            if isinstance(resultado, Exception):
                filas.append({
                    "Jurisdiccion": clase,
                    "Notificacion": f"Error: {resultado}",
                    "Screenshot":   "No",
                    "Error":        type(resultado).__name__,
                })
            else:
                nombre, notif, screenshot, error = resultado
                filas.append({
                    "Jurisdiccion": nombre,
                    "Notificacion": notif,
                    "Screenshot":   screenshot,
                    "Error":        error or "",
                })

        df = pd.DataFrame(filas)
        assert len(df) == len(jurisdicciones_pfizer)

        enviar_correo(
            receptor=E2E_RECEPTOR,
            cliente="PFIZER S.R.L. — E2E Test",
            cuit=os.getenv("TEST_ENTRERIOS_CUIT_CLIENTE_INPUT"),
            inicio=inicio,
            df=df,
            cc=E2E_CC,
        )


# ===========================================================================
# Bloque 4 — Flujo desde la base de datos (ObtenerDatosClientes)
# ===========================================================================

@pytest.mark.e2e
@pytest.mark.slow
class TestE2EDesdeDB:
    """
    Usa ObtenerDatosClientes para obtener clientes y credenciales
    directamente desde la DB, exactamente como hace el sistema en producción.
    Procesa un cliente piloto y envía el resultado a opereyra@deloitte.com.
    """

    @pytest.mark.asyncio
    async def test_obtener_datos_cliente_desde_db_y_ejecutar(self, pw, monkeypatch):
        """
        1. Obtiene datos del cliente piloto desde la DB
        2. Ejecuta todas sus jurisdicciones
        3. Envía resultado a opereyra@deloitte.com

        Usa TEST_CLIENT_FOLDERS para limitar a un único cliente piloto.
        """
        import pandas as pd
        from mail import enviar_correo
        import jurisdicciones as jur_module

        cliente_piloto = os.getenv("TEST_NACIONAL_CLIENT_FOLDER", "Dolar App Mexico S.E.")
        monkeypatch.setenv("TEST_CLIENT_FOLDERS", cliente_piloto)
        # En DEV_MODE los correos ya se redirigen, pero lo forzamos por las dudas
        monkeypatch.setenv("DEV_MODE", "true")
        monkeypatch.setenv("CORREO_RECEPTOR_TEST_MAIL", E2E_RECEPTOR)

        from obtener_datos_clientes.obtener_datos_clientes import ObtenerDatosClientes
        odc = ObtenerDatosClientes()
        odc.run()

        assert odc.data is not None, "ObtenerDatosClientes.run() retornó None"
        assert not odc.data.empty, (
            f"No se encontraron datos para el cliente '{cliente_piloto}'. "
            "Verificar que existe en la DB y tiene jurisdicciones activas."
        )

        # Ejecutar cada jurisdicción del cliente
        inicio = datetime.datetime.now()
        resultados = []

        for _, row in odc.data.iterrows():
            clase_nombre = row["Jurisdiccion"]
            ClaseJurisdiccion = getattr(jur_module, clase_nombre, None)
            if ClaseJurisdiccion is None:
                continue

            crear_directorios(row["client_folder"])

            instancia = await ClaseJurisdiccion.create(
                playwright=pw,
                cliente=row["Cliente"],
                client_folder=row["client_folder"],
                cuit=int(row["Usuario"]),
                clave_fiscal=row["Password"],
                fecha_desde=row["fecha_desde"],
                fecha_hasta=row["fecha_hasta"],
                cuit_cliente_input=int(row["cuit_cliente"]),
                headless=False,
            )
            resultado = await instancia.procesar_jurisdiccion()
            nombre, notif, screenshot, error = resultado
            resultados.append({
                "Jurisdiccion": nombre,
                "Notificacion": notif,
                "Screenshot":   screenshot,
                "Error":        error or "",
            })

        assert len(resultados) > 0, "No se procesó ninguna jurisdicción"

        df = pd.DataFrame(resultados)

        # Correo consolidado — solo a opereyra
        enviar_correo(
            receptor=E2E_RECEPTOR,
            cliente=f"{cliente_piloto} — E2E Test desde DB",
            cuit=os.getenv("TEST_NACIONAL_CUIT_CLIENTE_INPUT", ""),
            inicio=inicio,
            df=df,
            cc=E2E_CC,
        )

    def test_odc_retorna_columnas_requeridas(self, monkeypatch):
        """
        Verifica que el DataFrame de ObtenerDatosClientes tiene
        todas las columnas que necesita ClienteProcessor.
        """
        cliente_piloto = os.getenv("TEST_NACIONAL_CLIENT_FOLDER", "Dolar App Mexico S.E.")
        monkeypatch.setenv("TEST_CLIENT_FOLDERS", cliente_piloto)

        from obtener_datos_clientes.obtener_datos_clientes import ObtenerDatosClientes
        odc = ObtenerDatosClientes()
        odc.run()

        if odc.data is None or odc.data.empty:
            pytest.skip(f"Cliente '{cliente_piloto}' no disponible en DB")

        columnas_requeridas = [
            "Cliente", "Jurisdiccion", "client_folder", "cuit_cliente",
            "Usuario", "Password", "fecha_desde", "fecha_hasta",
            "Correo Output",
        ]
        for col in columnas_requeridas:
            assert col in odc.data.columns, f"Columna '{col}' ausente en el DataFrame"
