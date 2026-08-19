"""
Tests de integración (DB SQLite real, sin mocks de SQLAlchemy) sobre el ciclo
completo de "errores de login recientes" en ClienteProcessor:

  actualizar_fecha_login_error()  -> escribe cliente_jurisdiccion.fecha_login_error
  filtrar_jurisdicciones_por_login_error() -> lee ese campo para decidir si
                                               saltea la jurisdicción y le
                                               dice al cliente "Credenciales
                                               inválidas" en el próximo run.

Este es el circuito de negocio donde un LoginError mal clasificado (que en
realidad era un timeout de portal, ver tests/unit/test_salta_timeout_vs_credenciales.py,
tests/unit/test_sicnea_timeout_vs_credenciales.py y
tests/unit/test_neuquen_timeout_vs_credenciales.py) termina impactando al
cliente final: se le pide "actualizar credenciales" que en realidad nunca
estuvieron mal, y la jurisdicción queda sin consultarse por 24hs.

Por eso el test central de este archivo es:
`test_login_timeout_error_nunca_persiste_fecha_login_error`.
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from cliente_processor import ClienteProcessor
from obtener_datos_clientes.models import Cliente, ClienteJurisdiccion, Jurisdiccion

pytestmark = pytest.mark.integration


@pytest.fixture()
def cliente_seed(db_session, limpiar_tablas):
    """Crea Cliente + Jurisdiccion + ClienteJurisdiccion en la DB de test."""
    cliente = Cliente(
        nombre="Cliente Demo SA",
        cuit="30111111112",
        client_folder="cliente_demo",
    )
    jurisdiccion = Jurisdiccion(codigo="906 CHACO", clase="Chaco")
    db_session.add_all([cliente, jurisdiccion])
    db_session.commit()

    cliente_jurisdiccion = ClienteJurisdiccion(
        cliente_id=cliente.id,
        jurisdiccion_id=jurisdiccion.id,
        usuario="20222222223",
        password="clave-secreta",
        consultar=True,
    )
    db_session.add(cliente_jurisdiccion)
    db_session.commit()

    return {
        "cliente": cliente,
        "jurisdiccion": jurisdiccion,
        "cliente_jurisdiccion": cliente_jurisdiccion,
    }


def _make_processor(cliente_id, estructura_robot_tmp, df_cliente_factory):
    group = df_cliente_factory()
    return ClienteProcessor(
        cliente="Cliente Demo SA",
        group=group,
        cuit_cliente="30111111112",
        inicio=pd.Timestamp.now(),
        client_folder="cliente_demo",
        cliente_id=cliente_id,
        procesamiento_id=None,
    )


class TestActualizarFechaLoginError:
    @pytest.mark.asyncio
    async def test_login_error_si_persiste_fecha_login_error(
        self, cliente_seed, estructura_robot_tmp, df_cliente_factory, db_session
    ):
        processor = _make_processor(
            cliente_seed["cliente"].id, estructura_robot_tmp, df_cliente_factory
        )
        df_final = pd.DataFrame(
            {
                "Nombre": ["Chaco"],
                "Notificacion": ["Credenciales inválidas"],
                "Screenshot": ["No se realizó Screenshot"],
                "Error": ["LoginError"],
            }
        )

        await processor.actualizar_fecha_login_error(df_final)

        db_session.expire_all()
        cj = db_session.get(ClienteJurisdiccion, cliente_seed["cliente_jurisdiccion"].id)
        assert cj.fecha_login_error is not None

    @pytest.mark.asyncio
    async def test_login_timeout_error_nunca_persiste_fecha_login_error(
        self, cliente_seed, estructura_robot_tmp, df_cliente_factory, db_session
    ):
        """CASO CENTRAL solicitado: un LoginTimeoutError (portal caído/lento)
        NO debe dejar rastro en fecha_login_error. Si esto fallara, el
        cliente vería "Credenciales inválidas" al día siguiente por culpa de
        un simple timeout de portal, y la jurisdicción quedaría sin
        consultarse un día entero sin motivo real."""
        processor = _make_processor(
            cliente_seed["cliente"].id, estructura_robot_tmp, df_cliente_factory
        )
        df_final = pd.DataFrame(
            {
                "Nombre": ["Chaco"],
                "Notificacion": ["Timeout esperando confirmación de login"],
                "Screenshot": ["No se realizó Screenshot"],
                "Error": ["LoginTimeoutError"],
            }
        )

        await processor.actualizar_fecha_login_error(df_final)

        db_session.expire_all()
        cj = db_session.get(ClienteJurisdiccion, cliente_seed["cliente_jurisdiccion"].id)
        assert cj.fecha_login_error is None


class TestFiltrarJurisdiccionesPorLoginError:
    """
    ⚠️ HALLAZGO DURANTE LA CONSTRUCCIÓN DE ESTOS TESTS (no es el bug que pediste
    revisar, pero está en el mismo circuito y es igual de importante):

    `actualizar_fecha_login_error()` graba `fecha_login_error` con
    `datetime.now()` (naive, SQL crudo). `filtrar_jurisdicciones_por_login_error()`
    calcula `ahora = pd.Timestamp.now(tz='UTC')` (aware) y hace `ahora - fecha_dt`.
    Restar un datetime aware menos uno naive lanza
    `TypeError: Cannot subtract tz-naive and tz-aware datetime-like objects`
    SIEMPRE que fecha_login_error tenga un valor, sin importar el motor de DB
    (se reproduce igual con SQLite que con SQL Server/pyodbc, ver
    TESTS_README.md). Ese error queda silenciado por el `except Exception`
    que envuelve todo el método, así que:

      - Nunca se llega a marcar `Saltar=True` (el "salteo por 24hs" en la
        práctica NO está funcionando).
      - Nunca se llega a resetear `fecha_login_error` tras 24hs o tras
        actualizar credenciales (el "auto-reset" tampoco funciona).

    Los tests `test_bug_tz_*` documentan el comportamiento ACTUAL (pasan hoy).
    Los tests `test_intencion_*` (marcados `xfail(strict=True)`) documentan el
    comportamiento que el docstring del método promete; si algún día se
    corrige el bug de timezone, esos tests van a empezar a pasar (lo cual
    hará fallar el xfail estricto) y ahí hay que promoverlos a tests
    normales y borrar los `test_bug_tz_*`.
    """

    @pytest.mark.known_issue
    def test_bug_tz_error_reciente_no_se_marca_para_saltar_por_excepcion_interna(
        self, cliente_seed, estructura_robot_tmp, df_cliente_factory, db_session, caplog
    ):
        cj = cliente_seed["cliente_jurisdiccion"]
        cj.fecha_login_error = datetime.now(timezone.utc)
        db_session.add(cj)
        db_session.commit()

        processor = _make_processor(
            cliente_seed["cliente"].id, estructura_robot_tmp, df_cliente_factory
        )
        # No debe lanzar excepción hacia afuera (queda contenida adentro).
        processor.filtrar_jurisdicciones_por_login_error()

        fila = processor.group.iloc[0]
        assert bool(fila["Saltar"]) is False  # comportamiento actual, no el deseado

    @pytest.mark.known_issue
    def test_bug_tz_error_antiguo_tampoco_se_resetea_por_excepcion_interna(
        self, cliente_seed, estructura_robot_tmp, df_cliente_factory, db_session
    ):
        cj = cliente_seed["cliente_jurisdiccion"]
        cj.fecha_login_error = datetime.now(timezone.utc) - timedelta(days=2)
        db_session.add(cj)
        db_session.commit()

        processor = _make_processor(
            cliente_seed["cliente"].id, estructura_robot_tmp, df_cliente_factory
        )
        processor.filtrar_jurisdicciones_por_login_error()

        db_session.expire_all()
        cj_actualizado = db_session.get(ClienteJurisdiccion, cj.id)
        # Comportamiento actual: NO se resetea (a diferencia de lo que promete
        # el docstring del método), porque la excepción de tz corta el loop
        # antes de llegar a la rama de reset.
        assert cj_actualizado.fecha_login_error is not None

    @pytest.mark.xfail(
        strict=True,
        reason="Bug conocido de tz-naive/tz-aware en filtrar_jurisdicciones_por_login_error "
        "(ver docstring de esta clase). Cuando se corrija, este test debe empezar a pasar.",
    )
    def test_intencion_marcar_para_saltar_con_error_reciente(
        self, cliente_seed, estructura_robot_tmp, df_cliente_factory, db_session
    ):
        cj = cliente_seed["cliente_jurisdiccion"]
        cj.fecha_login_error = datetime.now(timezone.utc)
        db_session.add(cj)
        db_session.commit()

        processor = _make_processor(
            cliente_seed["cliente"].id, estructura_robot_tmp, df_cliente_factory
        )
        processor.filtrar_jurisdicciones_por_login_error()

        fila = processor.group.iloc[0]
        assert bool(fila["Saltar"]) is True
        assert fila["Error"] == "LoginError"
        assert fila["Notificacion"] == "Credenciales inválidas"

    @pytest.mark.xfail(
        strict=True,
        reason="Bug conocido de tz-naive/tz-aware en filtrar_jurisdicciones_por_login_error "
        "(ver docstring de esta clase). Cuando se corrija, este test debe empezar a pasar.",
    )
    def test_intencion_resetear_error_antiguo_y_no_saltear(
        self, cliente_seed, estructura_robot_tmp, df_cliente_factory, db_session
    ):
        cj = cliente_seed["cliente_jurisdiccion"]
        cj.fecha_login_error = datetime.now(timezone.utc) - timedelta(days=2)
        db_session.add(cj)
        db_session.commit()

        processor = _make_processor(
            cliente_seed["cliente"].id, estructura_robot_tmp, df_cliente_factory
        )
        processor.filtrar_jurisdicciones_por_login_error()

        fila = processor.group.iloc[0]
        assert bool(fila["Saltar"]) is False

        db_session.expire_all()
        cj_actualizado = db_session.get(ClienteJurisdiccion, cj.id)
        assert cj_actualizado.fecha_login_error is None

    def test_sin_error_previo_no_se_saltea(
        self, cliente_seed, estructura_robot_tmp, df_cliente_factory
    ):
        """Caso feliz, no afectado por el bug de tz: si nunca hubo
        fecha_login_error, la jurisdicción se procesa normalmente."""
        processor = _make_processor(
            cliente_seed["cliente"].id, estructura_robot_tmp, df_cliente_factory
        )
        processor.filtrar_jurisdicciones_por_login_error()
        fila = processor.group.iloc[0]
        assert bool(fila["Saltar"]) is False

    def test_sin_cliente_id_no_filtra_nada(self, estructura_robot_tmp, df_cliente_factory):
        """Si no hay cliente_id (ej. viene de archivo de config, no de DB),
        no debe intentar filtrar ni fallar."""
        processor = _make_processor(None, estructura_robot_tmp, df_cliente_factory)
        # No debe lanzar excepción.
        processor.filtrar_jurisdicciones_por_login_error()
        assert "Saltar" in processor.group.columns
        assert bool(processor.group.iloc[0]["Saltar"]) is False
