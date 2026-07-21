"""
Test de regresión/caracterización (NO se modificó nacional.py) para el
incidente reportado: "Dolar App ingresó pero se quedó con el CUIT de la
persona en lugar de la empresa".

No se agrega ningún fix acá. Este test demuestra, con el código real de
`Nacional._seleccionar_cuit_cliente`, que hoy NO existe ninguna verificación
posterior al click que confirme que ARCA efectivamente cambió de contexto a
la CUIT esperada. La única validación que hace el método es "¿el botón con
ese id estaba visible antes de clickear?" -- nunca vuelve a mirar la página
después del click.

Por qué esto importa: si el click no llega a surtir efecto a tiempo (la
causa más probable del incidente: una demora de render en el dropdown),
`_seleccionar_cuit_cliente()` no lanza ningún error y el flujo sigue de
largo leyendo notificaciones bajo el contexto que haya quedado activo --
que puede ser el de la persona, no el de la empresa.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from jurisdicciones.nacional import Nacional

pytestmark = [pytest.mark.unit, pytest.mark.known_issue, pytest.mark.asyncio]

# Métodos de Page/Locator que servirían para LEER contenido de la página
# (y por lo tanto, para verificar qué CUIT quedó activo). Si ninguno de
# estos se invoca durante _seleccionar_cuit_cliente, es prueba de que el
# método no lee nada de vuelta para confirmar el resultado del click.
METODOS_DE_LECTURA_DE_CONTENIDO = {
    "content",
    "inner_text",
    "text_content",
    "get_by_text",
}


@pytest.fixture
def nacional_instance():
    instance = object.__new__(Nacional)
    instance.cliente = "Cliente QA"
    instance.client_folder = "cliente_qa"
    instance.cuit_cliente_input = "30111111112"
    instance.logger = MagicMock()
    return instance


class _NewPageSpy:
    """Envoltorio mínimo sobre un mock de Page que registra si alguno de los
    métodos de LECTURA de contenido fue invocado, sin dejar de comportarse
    como el mock original para todo lo demás."""

    def __init__(self, boton_visible: bool):
        self.llamadas_de_lectura = []
        self._mock = MagicMock()
        self._mock.is_visible = AsyncMock(return_value=boton_visible)
        self._mock.click = AsyncMock()

        for metodo in METODOS_DE_LECTURA_DE_CONTENIDO:
            def _factory(nombre):
                async def _fake(*args, **kwargs):
                    self.llamadas_de_lectura.append(nombre)
                    return ""
                return _fake
            setattr(self._mock, metodo, AsyncMock(side_effect=_factory(metodo)))

    def __getattr__(self, item):
        return getattr(self._mock, item)


async def test_seleccion_exitosa_no_verifica_identidad_despues_del_click(nacional_instance):
    """
    ⚠️ Documenta el hallazgo: con el botón "visible" (el click se ejecuta
    sin lanzar excepción, el camino "feliz" de `_seleccionar_cuit_cliente`),
    el método TERMINA sin haber leído ni una vez el contenido de la página
    para confirmar qué CUIT/representada quedó activa. No hay ninguna
    verificación de identidad -- sólo se confía en que el click funcionó.

    Este test seguirá pasando mientras esto no se corrija. El día que se
    agregue una verificación post-click (leyendo la representada activa y
    comparándola contra cuit_cliente_input), este test va a empezar a
    fallar -- y ahí hay que reemplazarlo por uno que confirme que la
    verificación nueva SÍ se ejecuta y SÍ corta cuando no coincide.
    """
    new_page_spy = _NewPageSpy(boton_visible=True)
    nacional_instance.new_page = new_page_spy

    await nacional_instance._seleccionar_cuit_cliente()

    assert new_page_spy.llamadas_de_lectura == [], (
        "_seleccionar_cuit_cliente() leyó contenido de la página después del "
        "click -- si ves este fallo, alguien ya agregó una verificación de "
        "identidad; actualizá/borrá este test known_issue."
    )
    new_page_spy._mock.click.assert_awaited_once()


async def test_boton_no_visible_si_lanza_delegacion_error(nacional_instance):
    """
    Caso de control (sí funciona bien hoy): si el botón de la CUIT
    directamente no está en el DOM/visible en el momento del chequeo,
    `_seleccionar_cuit_cliente` SÍ corta con `DelegacionError`. El problema
    no es este camino -- es el intermedio: cuando el botón aparece un
    instante después de que `is_visible()` ya devolvió False, o cuando el
    click "funciona" pero no cambia el contexto real de ARCA a tiempo.
    """
    from jurisdicciones.jurisdiccion import DelegacionError

    new_page_spy = _NewPageSpy(boton_visible=False)
    nacional_instance.new_page = new_page_spy

    with pytest.raises(DelegacionError):
        await nacional_instance._seleccionar_cuit_cliente()

    new_page_spy._mock.click.assert_not_called()
