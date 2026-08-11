"""
Pasos de reproducción manual para el reporte HTML de pytest-html.

Objetivo: que un dev (o vos) mirando el reporte pueda entender y confirmar
un fallo sin correr pytest ni leer código -- siguiendo pasos concretos en
el navegador, contra el portal real.

Esto NO reemplaza el traceback técnico (pytest-html lo sigue mostrando
igual); se agrega COMO SECCIÓN ADICIONAL, sólo en tests que fallan o dan
error (ver el hook `pytest_runtest_makereport` en conftest.py).
"""
from __future__ import annotations

URL_LOGIN_POR_JURISDICCION: dict[str, str] = {
    "Agip": "https://claveciudad.agip.gob.ar/",
    "Arba": "https://www.arba.gov.ar/Gestionar/PanelAutogestion.asp",
    "Catamarca": "https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=arca_dgr_contrib",
    "Chaco": "https://atp-lb1.ecomchaco.com.ar/ATPWeb/servlet/iniciocontribuyente",
    "Chubut": "https://servicios.dgrchubut.gov.ar/modulos/login_siat.php",
    "Cordoba": "https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=afip-gobcba",
    "Corrientes": "https://miportal.dgrcorrientes.gov.ar/",
    "EntreRios": "https://portal.ater.gob.ar/ventanillaVirtual/adhesionVentanilla.aspx",
    "Formosa": "https://www.atpformosa.gob.ar/consultas/index.php",
    "Jujuy": "https://www.rentasjujuyonline.gob.ar/",
    "LaPampa": "https://dgr.lapampa.gob.ar/ServiciosEnLinea/?programa=MenuCuenta",
    "LaRioja": "https://www.dgiplarioja.gob.ar/frontend51/page?1,principal,LR-Aplicacion,O,es,0,",
    "Mendoza": "https://atm.mendoza.gov.ar/portalatm/misTramites/misTramitesLogin.jsp",
    "Misiones": "https://extranet.atmisiones.gob.ar/Extranet/index.php",
    "Nacional": "https://auth.afip.gob.ar/contribuyente_/login.xhtml",
    "Neuquen": "https://rentasneuquenweb.gob.ar/nqn/Extranet/index.php",
    "RioNegro": "https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=dgrrn_sitio_seguro",
    "Salta": "https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=dgrsalta_rentas",
    "SanJuan": "https://rentas.dgrsj.gob.ar/",
    "SanLuis": "https://sistematributario.dpip.sanluis.gov.ar/ords/clavefiscal/r/miclave/login",
    "SantaCruz": "https://sit.asip.gob.ar/stsc/Extranet/index.php",
    "SantiagoDelEstero": "https://dgronline.dgrsantiago.gob.ar/dgronline/hlogin.aspx",
    "Sicnea": "https://auth.afip.gob.ar/contribuyente_/login.xhtml",
    "Tucuman": "https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=dgrtuc_ddjj",
}

# Notas puntuales para las jurisdicciones con el patrón riesgoso confirmado
# (ver COBERTURA_TIMEOUT_VS_CREDENCIALES.md): qué mirar específicamente
# para reconocer el escenario de "timeout ambiguo" en cada una.
NOTAS_ESPECIFICAS: dict[str, str] = {
    "Salta": (
        "Después de tocar 'Ingresar', el sistema espera el selector "
        "#enviaLogout (confirmación de login) por 15s. Si tarda más de "
        "eso -pero SIN mostrar ningún cartel de 'usuario o clave "
        "incorrecta'- el robot hoy lo reporta igual como si las "
        "credenciales estuvieran mal ('Servicio no disponible')."
    ),
    "Sicnea": (
        "Después del login AFIP, el robot intenta seleccionar la empresa "
        "en un dropdown. Si esa selección tarda o el frame no responde a "
        "tiempo (sin relación con la contraseña), el robot lo reporta "
        "igual como error de credenciales."
    ),
    "Neuquen": (
        "Tras el login vía AFIP y la redirección a SiNATrA, el robot "
        "espera el texto 'Bandeja de Mensajes - Notificaciones'. Un "
        "timeout ahí (portal lento, ventana emergente que no abrió a "
        "tiempo, etc.) se reporta igual como 'Servicio no disponible' "
        "-tipo credenciales-, aunque el usuario/clave estén bien."
    ),
    "Agip": (
        "En el flujo de Clave Ciudad, tras loguear, el robot espera el "
        "encabezado 'Búsqueda de aplicativos/servicios'. Si tarda más de "
        "2 minutos (timeout real y largo, portal lento), hoy escapa como "
        "un error interno de Python (AssertionError) en vez de un error "
        "claro de timeout -distinto de credenciales inválidas, pero "
        "tampoco es un mensaje útil para diagnosticar-."
    ),
}

PASOS_GENERICOS = """\
Cómo reproducir esto a mano, sin correr pytest ni leer código:

1. Abrí una ventana de incógnito en Chrome (para no arrastrar sesiones previas).
2. Andá a: {url}
3. Iniciá sesión con el CUIT/clave de "{cliente_o_generico}" (ver el .xlsm de
   credenciales de test para el usuario/clave exactos de esta jurisdicción).
4. Prestá atención a qué pasa entre 5 y 30 segundos después de tocar
   "Ingresar"/"Confirmar": ¿aparece algún cartel de error ("usuario o clave
   incorrecta", "servicio no disponible", etc.), o la pantalla se queda
   "pensando" sin decir nada?
5. Si la pantalla se queda sin responder nada claro por más de ese lapso,
   eso es exactamente la ambigüedad que el robot hoy resuelve mal: la
   reporta como si fueran credenciales inválidas, aunque en realidad el
   portal esté simplemente lento o caído.
{nota_especifica}
Resultado de esta corrida automática: {resultado}
"""


def generar_pasos_manuales(
    clase: str, error_type: str | None = None, notificacion: str | None = None
) -> str:
    """Arma el texto de reproducción manual para una jurisdicción puntual,
    incluyendo la URL real y (si existe) la nota específica del patrón
    riesgoso ya identificado para esa jurisdicción."""
    url = URL_LOGIN_POR_JURISDICCION.get(clase, "(URL no mapeada, revisar jurisdicciones/*.py)")
    nota = NOTAS_ESPECIFICAS.get(clase)
    nota_texto = f"\n⚠️ Específico de {clase}: {nota}\n" if nota else ""
    resultado = f"error_type={error_type!r}, notificación devuelta={notificacion!r}"
    return PASOS_GENERICOS.format(
        url=url,
        cliente_o_generico="la empresa correspondiente",
        nota_especifica=nota_texto,
        resultado=resultado,
    )


def pasos_para_item_e2e_live(item) -> str:
    """Callable pensado para @pytest.mark.manual_repro en el test
    parametrizado de test_e2e_live_todas_las_jurisdicciones.py: extrae la
    jurisdicción del parámetro de pytest y el resultado ya capturado en el
    fixture `reporte_resultados` (mutado durante el propio test) para armar
    el texto con el error real de ESA corrida puntual."""
    clase = None
    if getattr(item, "callspec", None) is not None:
        clase = item.callspec.params.get("clase")
    if clase is None:
        return "No se pudo determinar la jurisdicción de este test para armar los pasos."

    reporte = {}
    if hasattr(item, "funcargs"):
        reporte = item.funcargs.get("reporte_resultados", {}) or {}
    resultado = reporte.get(clase, {})
    return generar_pasos_manuales(
        clase,
        error_type=resultado.get("error_type"),
        notificacion=resultado.get("hay_notificacion"),
    )
