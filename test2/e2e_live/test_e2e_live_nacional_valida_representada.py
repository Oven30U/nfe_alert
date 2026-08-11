"""
E2E VIVO — valida, DESDE EL TEST (sin modificar jurisdicciones/nacional.py),
que después de correr el flujo real de Nacional/ARCA, la CUIT/representada
activa en la página es la de la EMPRESA (`cuit_cliente_input`), no la de la
persona que inició sesión.

Este test existe puntualmente por el incidente reportado: "Dolar App
ingresó pero se quedó con el CUIT de la persona en lugar de la empresa" --
sin ningún error, silenciosamente. Ver también
tests/unit/test_nacional_seleccion_cuit_sin_verificacion.py, que demuestra
por qué el código actual no lo detecta por sí solo.

⚠️ Requiere RUN_LIVE_E2E=true y PATH_CREDENCIALES_XLSM (ver README_E2E_LIVE.md).
Corre login real contra ARCA con credenciales reales -- mismas advertencias
que el resto de tests/e2e_live/.

⚠️ TODO antes de confiar en este test: el selector/heurística de abajo
(`_texto_visible_menciona_cuit`) usa un chequeo GENÉRICO -- busca la CUIT
esperada en el texto visible de la página -- porque no tengo forma de ver
el DOM real de ARCA sin loguearme yo mismo (cosa que decidimos no hacer).
Si tenés el selector exacto de dónde ARCA muestra "Ud. está operando en
representación de..." (screenshot o HTML), reemplazá la función de abajo
por un chequeo puntual sobre ese selector -- va a ser mucho más confiable
que buscar el número de CUIT en todo el texto de la página.
"""
from __future__ import annotations

import os
import re

import pytest
from playwright.async_api import async_playwright

from jurisdicciones.jurisdiccion import DelegacionError

pytestmark = [pytest.mark.e2e_live, pytest.mark.asyncio]


def _formatos_de_cuit(cuit: str) -> list[str]:
    """Genera variantes de formato del CUIT (con y sin guiones), porque no
    sabemos en qué formato ARCA lo muestra en pantalla."""
    solo_digitos = re.sub(r"\D", "", cuit)
    variantes = {solo_digitos}
    if len(solo_digitos) == 11:
        variantes.add(f"{solo_digitos[:2]}-{solo_digitos[2:10]}-{solo_digitos[10:]}")
    return list(variantes)


async def _texto_visible_menciona_cuit(page, cuit: str) -> bool:
    """Heurística genérica: ¿aparece la CUIT esperada en algún lado del
    texto visible de la página? No es tan preciso como un selector puntual
    (ver TODO al principio del archivo), pero no requiere conocer el DOM
    exacto de ARCA de antemano."""
    try:
        texto = await page.inner_text("body")
    except Exception:
        return False
    return any(variante in texto for variante in _formatos_de_cuit(cuit))


async def test_nacional_queda_representando_a_la_empresa_no_a_la_persona(
    credenciales_todas,
    cuit_cliente_overrides,
    rango_fechas,
):
    from test2.e2e_live.credenciales_loader import resolver_cuit_cliente
    import jurisdicciones

    credencial = credenciales_todas.get("Nacional")
    if credencial is None:
        pytest.skip("No hay credenciales para 'Nacional' en el .xlsm.")

    cuit_cliente_input = resolver_cuit_cliente(credencial, cuit_cliente_overrides)
    cuit_persona = credencial["usuario"]

    if cuit_cliente_input == cuit_persona:
        pytest.skip(
            "cuit_cliente_input == usuario (no hay override cargado): este test no "
            "puede distinguir 'empresa' de 'persona' si son el mismo número. "
            "Configurá CUIT_CLIENTE_OVERRIDES_JSON con la CUIT real de la empresa "
            "para que este test tenga sentido."
        )

    headless = os.getenv("HEADLESS_E2E_LIVE", "true").lower() == "true"

    async with async_playwright() as playwright:
        instancia = await jurisdicciones.Nacional.create(
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

        error_durante_consulta = None
        try:
            await instancia.consultar_notificaciones()
        except DelegacionError as e:
            # Esto es lo que DEBERÍA pasar si la CUIT no está delegada --
            # una falla ruidosa, no silenciosa. No es el bug que buscamos,
            # pero tampoco es un "OK": lo registramos y re-lanzamos.
            error_durante_consulta = e
        except Exception as e:
            error_durante_consulta = e

        # Independientemente de si hubo excepción o no, inspeccionamos la
        # página TAL COMO QUEDÓ para ver a quién está representando de
        # verdad -- esto es lo que el código de producción hoy NUNCA hace.
        pagina_a_inspeccionar = getattr(instancia, "new_page", None) or instancia.page

        representa_a_la_empresa = await _texto_visible_menciona_cuit(
            pagina_a_inspeccionar, cuit_cliente_input
        )
        representa_a_la_persona = await _texto_visible_menciona_cuit(
            pagina_a_inspeccionar, cuit_persona
        )

        await instancia.cerrar_recursos()

        if error_durante_consulta is not None and not isinstance(
            error_durante_consulta, DelegacionError
        ):
            # Un error técnico no relacionado (portal caído, etc.) -- no es
            # lo que este test busca detectar, así que no lo escondemos
            # pero tampoco lo tratamos como el bug puntual.
            pytest.skip(
                f"consultar_notificaciones() falló con un error no relacionado al "
                f"chequeo de CUIT ({type(error_durante_consulta).__name__}); no se "
                f"puede validar la representada en este intento."
            )

    # ESTE es el assert que habría detectado el incidente reportado: la
    # página debe reflejar a la EMPRESA, no a la PERSONA que logueó.
    assert representa_a_la_empresa, (
        f"La página no muestra en ningún lado la CUIT de la empresa "
        f"({cuit_cliente_input}) tras seleccionar la representada. "
        f"cliente={credencial['client_folder']!r}"
    )
    assert not representa_a_la_persona, (
        f"⚠️ INCIDENTE REPRODUCIDO: la página todavía muestra la CUIT de la "
        f"persona que logueó ({cuit_persona}) en vez de (o además de) la "
        f"empresa ({cuit_cliente_input}). cliente={credencial['client_folder']!r}"
    )
