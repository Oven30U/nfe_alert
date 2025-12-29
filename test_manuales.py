import asyncio
import functools
import os
import sys

from dotenv import load_dotenv
from playwright.async_api import async_playwright

from logger import Logger
from database import get_session
from obtener_datos_clientes.models import (
    Cliente,
    Jurisdiccion,
    ClienteJurisdiccion,
)  # Agregar imports necesarios


# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Agregar el directorio que contiene el módulo 'jurisdicciones' al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jurisdicciones import (
    Agip,
    Arba,
    Catamarca,
    Chaco,
    Chubut,
    Cordoba,
    Corrientes,
    EntreRios,
    Formosa,
    LaPampa,
    Mendoza,
    Nacional,
    Neuquen,
    RioNegro,
    Salta,
    SanLuis,
    SanJuan,
    SantaCruz,
    SantiagoDelEstero,
    Sicnea,
    Tucuman,
    Jujuy,
    LaRioja,
)


def run_multiple(iterations: int = 5):
    """
    Decorador que ejecuta la función decorada 'iterations' veces,
    mostrando si hubo algún error en cada iteración.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for i in range(iterations):
                print(f"Ejecutando iteración {i + 1}")
                try:
                    await func(*args, **kwargs)
                    print(f"Iteración {i + 1} finalizada con éxito.")
                except Exception as e:
                    print(f"Error en la iteración {i + 1}: {e}")

        return wrapper

    return decorator


async def generic_test(
    jurisdiccion,
    clase_jurisdiccion,
    headless: bool = False,
    iterations: int = 1,
    enable_tracing: bool = True,
    trace_dir: str = "traces",
):
    """
    Función genérica para ejecutar tests de jurisdicciones.

    Args:
        jurisdiccion: Nombre de la jurisdicción en mayúscula (igual que la variable de entorno)
        clase_jurisdiccion: Clase correspondiente a la jurisdicción a probar
        headless: Indica si el navegador debe correr en modo sin interfaz gráfica
        iterations: Número de veces que se debe repetir el test
    """
    jurisdiccion_upper = jurisdiccion.upper()

    for i in range(iterations):
        if iterations > 1:
            print(f"Ejecutando iteración {i + 1} de {iterations} para {jurisdiccion}")

        try:
            async with async_playwright() as playwright:
                fecha_desde = os.getenv("FECHA_DESDE")
                fecha_hasta = os.getenv("FECHA_HASTA")

                # Obtener variables específicas de la jurisdicción
                client = os.getenv(f"TEST_{jurisdiccion_upper}_CLIENT")
                client_folder = os.getenv(
                    f"TEST_{jurisdiccion_upper}_CLIENT_FOLDER", client
                )
                cuit = os.getenv(f"TEST_{jurisdiccion_upper}_CUIT")
                clave_fiscal = os.getenv(f"TEST_{jurisdiccion_upper}_CLAVE_FISCAL")
                cuit_cliente_input = os.getenv(
                    f"TEST_{jurisdiccion_upper}_CUIT_CLIENTE_INPUT"
                )

                # Preparar browser/context para poder iniciar tracing y pasarlo a la jurisdicción
                browser = await playwright.chromium.launch(headless=headless)
                context = await browser.new_context()

                trace_path = None
                if enable_tracing:
                    os.makedirs(trace_dir, exist_ok=True)
                    trace_path = os.path.join(trace_dir, f"{jurisdiccion}_{i + 1}.zip")
                    await context.tracing.start(
                        screenshots=True, snapshots=True, sources=True
                    )

                # Crear instancia de la jurisdicción reusando browser/context para que la traza capture todo
                try:
                    instance = await clase_jurisdiccion.create(
                        playwright,
                        client,
                        client_folder,
                        cuit,
                        clave_fiscal,
                        fecha_desde,
                        fecha_hasta,
                        cuit_cliente_input,
                        headless=headless,
                        browser=browser,
                        context=context,
                    )
                except TypeError:
                    # Fallback si la firma create() no acepta browser/context (compatibilidad hacia atrás)
                    instance = await clase_jurisdiccion.create(
                        playwright,
                        client,
                        client_folder,
                        cuit,
                        clave_fiscal,
                        fecha_desde,
                        fecha_hasta,
                        cuit_cliente_input,
                        headless=headless,
                    )

                resultado: dict[str] = await instance.procesar_jurisdiccion()
                logger = Logger.get_logger()
                logger.info(
                    f"Resultado de procesar_jurisdiccion para {jurisdiccion}: {resultado}"
                )

                # Detener tracing si fue iniciado y guardar el zip
                if enable_tracing and trace_path:
                    stopped = False
                    try:
                        await context.tracing.stop(path=trace_path)
                        stopped = True
                    except Exception:
                        # Intentar detener tracing desde la instancia (si implementó helper)
                        try:
                            await instance.stop_tracing(trace_path)
                            stopped = True
                        except Exception:
                            stopped = False

                    if stopped:
                        logger.info(f"Traza guardada en: {trace_path}")
                        print(f"Traza guardada en: {trace_path}")
                    else:
                        logger.warning(
                            f"No se pudo guardar la traza para {jurisdiccion} iteration {i + 1}."
                        )

                # Cerrar browser que abrimos localmente (si la instancia no es propietaria)
                try:
                    await browser.close()
                except Exception:
                    pass

            if iterations > 1:
                print(f"Iteración {i + 1} completada con éxito.")

        except Exception as e:
            print(f"Error en {jurisdiccion} (iteración {i + 1}): {e}")
            if iterations == 1:  # Si solo hay una iteración, propagar el error
                raise


# Definir funciones específicas para cada jurisdicción que usan la función genérica
async def catamarca_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "CATAMARCA",
        Catamarca,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def santiago_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "SANTIAGO_DEL_ESTERO",
        SantiagoDelEstero,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def santa_cruz_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "SANTA_CRUZ",
        SantaCruz,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def cordoba_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "CORDOBA",
        Cordoba,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def arba_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "ARBA",
        Arba,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def salta_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "SALTA",
        Salta,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def sicnea_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "SICNEA",
        Sicnea,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def chaco_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "CHACO",
        Chaco,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def agip_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "AGIP",
        Agip,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def rio_negro_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "RIO_NEGRO",
        RioNegro,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def nacional_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "NACIONAL",
        Nacional,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def corrientes_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "CORRIENTES",
        Corrientes,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def entre_rios_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "ENTRERIOS",
        EntreRios,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def san_luis_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "SANLUIS",
        SanLuis,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def tucuman_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "TUCUMAN",
        Tucuman,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def la_pampa_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "LA_PAMPA",
        LaPampa,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def mendoza_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "MENDOZA",
        Mendoza,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def formosa_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "FORMOSA",
        Formosa,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def neuquen_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "NEUQUEN",
        Neuquen,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def jujuy_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "JUJUY",
        Jujuy,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def san_juan_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "SAN_JUAN",
        SanJuan,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def chubut_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "CHUBUT",
        Chubut,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


async def la_rioja_test(
    headless=False, iterations=1, enable_tracing: bool = True, trace_dir: str = "traces"
):
    await generic_test(
        "LA_RIOJA",
        LaRioja,
        headless,
        iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


def send_email_smtp_test():
    """
    Test manual para enviar el correo con contraseña del zip
    """
    from conectar_db import read_and_modify_html
    from correo_cli import send_email_smtp

    # Lista de elementos para el cuarto atributo de read_and_modify_html
    elementos = list(
        set(
            [
                # "fracabrera@deloitte.com",
                # "julia.gonzalo@adidas.com",
                # "lsantellan@deloitte.com",
                # "mfasolis@deloitte.com",
                # "nlordi@deloitte.com",
                # "ssteinhardt@deloitte.com",
                # "vespindola@deloitte.com",
            ]
        )
    )

    for elemento in elementos:
        nombre_usuario = elemento.split("@")[0]

        send_email_smtp(
            sender_email="taxtecarg@deloitte.com",
            receiver_emails=[elemento],
            subject=f"Actualización de clave de seguridad para NFE Alert: Revisión de Domicilios Fiscales Electrónicos - adidas Argentina S.A.",
            html_file_path=None,
            zip_file_paths=None,
            html_content=read_and_modify_html(
                "adidas Argentina S.A",
                "Dttadidas2025.",
                "indeterminados",
                nombre_usuario,
            ),
        )


# Función para ejecutar fácilmente cualquier test enviando su nombre
async def run_test_by_name(
    test_name,
    headless=False,
    iterations=1,
    enable_tracing: bool = True,
    trace_dir: str = "traces",
):
    tests = {
        "catamarca": catamarca_test,
        "santiago": santiago_test,
        "cordoba": cordoba_test,
        "arba": arba_test,
        "salta": salta_test,
        "sicnea": sicnea_test,
        "chaco": chaco_test,
        "agip": agip_test,
        "rio_negro": rio_negro_test,
        "nacional": nacional_test,
        "entre_rios": entre_rios_test,
        "san_luis": san_luis_test,
        "tucuman": tucuman_test,
        "la_pampa": la_pampa_test,
        "mendoza": mendoza_test,
        "formosa": formosa_test,
        "neuquen": neuquen_test,
        "santa_cruz": santa_cruz_test,
        "san_juan": san_juan_test,
        "chubut": chubut_test,
        "la_rioja": la_rioja_test,
    }

    if test_name.lower() in tests:
        await tests[test_name.lower()](
            headless, iterations, enable_tracing=enable_tracing, trace_dir=trace_dir
        )
    else:
        print(
            f"Test '{test_name}' no encontrado. Tests disponibles: {', '.join(tests.keys())}"
        )


async def generic_test_from_db(
    clase_jurisdiccion,
    jurisdiccion: str = None,
    headless: bool = False,
    iterations: int = 1,
    enable_tracing: bool = True,
    trace_dir: str = "traces",
    db_session=None,
) -> None:
    """
    Función genérica para ejecutar tests de jurisdicciones iterando sobre datos de la base de datos.
    Filtra clientes que tienen una relación con la jurisdicción especificada y donde consultar=True.

    Args:
        clase_jurisdiccion: Clase correspondiente a la jurisdicción.
        jurisdiccion: Nombre de la jurisdicción en mayúscula (e.g., "CORDOBA").
                     Si no se proporciona, se infiere del nombre de la clase.
        headless: Indica si el navegador debe correr en modo sin interfaz gráfica.
        iterations: Número de veces que se debe repetir el test por cliente.
        enable_tracing: Si se debe habilitar tracing.
        trace_dir: Directorio para guardar traces.
        db_session: Sesión de DB opcional (para inyección de dependencias).
    """
    # Si no se proporciona jurisdiccion, intentar inferirla del nombre de la clase
    if jurisdiccion is None:
        class_name = clase_jurisdiccion.__name__
        # Mapeo directo de clases conocidas a nombres de jurisdicción
        class_to_jurisdiccion = {
            "Cordoba": "CORDOBA",
            "Arba": "ARBA",
            "Catamarca": "CATAMARCA",
            "Chaco": "CHACO",
            "Chubut": "CHUBUT",
            "Corrientes": "CORRIENTES",
            "EntreRios": "ENTRERIOS",
            "Formosa": "FORMOSA",
            "Jujuy": "JUJUY",
            "LaPampa": "LA_PAMPA",
            "LaRioja": "LA_RIOJA",
            "Mendoza": "MENDOZA",
            "Nacional": "NACIONAL",
            "Neuquen": "NEUQUEN",
            "RioNegro": "RIO_NEGRO",
            "Salta": "SALTA",
            "SanJuan": "SAN_JUAN",
            "SanLuis": "SANLUIS",
            "SantaCruz": "SANTA_CRUZ",
            "SantiagoDelEstero": "SANTIAGO_DEL_ESTERO",
            "Sicnea": "SICNEA",
            "Tucuman": "TUCUMAN",
            "Agip": "AGIP",
        }
        jurisdiccion = class_to_jurisdiccion.get(class_name)
        if jurisdiccion is None:
            # Fallback: convertir CamelCase a UPPER_CASE con guiones bajos
            jurisdiccion = "".join(
                [
                    "_" + c.lower() if c.isupper() and i > 0 else c.lower()
                    for i, c in enumerate(class_name)
                ]
            ).upper()
    logger = Logger.get_logger()
    if db_session is None:
        db_session = get_session()

    try:
        # Filtrar clientes que tienen una ClienteJurisdiccion con la jurisdicción especificada y consultar=True
        clientes = (
            db_session.query(Cliente)
            .join(Cliente.cliente_jurisdicciones)
            .join(ClienteJurisdiccion.jurisdiccion)
            .filter(Jurisdiccion.clase == jurisdiccion)
            .filter(ClienteJurisdiccion.consultar == True)
            .filter(Cliente.documentacion == True)
            .all()
        )

        if not clientes:
            logger.warning(
                f"No se encontraron clientes para la jurisdicción {jurisdiccion} en la DB."
            )
            return

        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        for cliente in clientes:
            # Obtener la ClienteJurisdiccion específica para esta jurisdicción
            cj = (
                db_session.query(ClienteJurisdiccion)
                .filter(ClienteJurisdiccion.cliente_id == cliente.id)
                .join(ClienteJurisdiccion.jurisdiccion)
                .filter(Jurisdiccion.clase == jurisdiccion)
                .filter(ClienteJurisdiccion.consultar == True)
                .first()
            )

            if not cj:
                logger.warning(
                    f"No se encontró configuración de jurisdicción para cliente {cliente.nombre}."
                )
                continue

            for i in range(iterations):
                logger.info(
                    f"Ejecutando iteración {i + 1} para {jurisdiccion} - Cliente: {cliente.nombre}"
                )

                try:
                    async with async_playwright() as playwright:
                        # Preparar browser/context
                        browser = await playwright.chromium.launch(headless=headless)
                        context = await browser.new_context()

                        trace_path = None
                        if enable_tracing:
                            os.makedirs(trace_dir, exist_ok=True)
                            trace_path = os.path.join(
                                trace_dir,
                                f"{jurisdiccion}_{cliente.nombre}_{i + 1}.zip",
                            )
                            await context.tracing.start(
                                screenshots=True, snapshots=True, sources=True
                            )

                        # Crear instancia con datos de DB
                        instance = await clase_jurisdiccion.create(
                            playwright,
                            cliente.nombre,  # cliente
                            cliente.client_folder,  # client_folder
                            cj.usuario,  # cuit
                            cj.password,  # clave_fiscal (usuario en ClienteJurisdiccion)
                            fecha_desde,
                            fecha_hasta,
                            cliente.cuit,  # cuit_cliente_input (usando cuit del cliente como ejemplo; ajusta si hay campo específico)
                            razon_social_cliente_input=None,  # Ajusta si hay dato en DB
                            texto_notificacion=None,  # Ajusta si hay dato en DB
                            headless=headless,
                            browser=browser,
                            context=context,
                        )

                        resultado = await instance.procesar_jurisdiccion()
                        logger.info(
                            f"Resultado para {jurisdiccion} - {cliente.nombre}: {resultado}"
                        )

                        # Detener tracing
                        if enable_tracing and trace_path:
                            try:
                                await context.tracing.stop(path=trace_path)
                                logger.info(f"Traza guardada en: {trace_path}")
                            except Exception as e:
                                logger.error(f"Error al guardar trace: {e}")

                        await browser.close()

                except Exception as e:
                    logger.error(
                        f"Error en {jurisdiccion} - {cliente.nombre} (iteración {i + 1}): {e}"
                    )
                    if iterations == 1:
                        raise
    finally:
        db_session.close()


# Funciones helper para facilitar el uso de generic_test_from_db con clases específicas
async def test_jurisdiccion_from_db(
    clase_jurisdiccion,
    headless: bool = False,
    iterations: int = 1,
    enable_tracing: bool = True,
    trace_dir: str = "traces",
):
    """
    Función helper para ejecutar tests de jurisdicciones desde la base de datos
    pasando directamente la clase de jurisdicción.

    Args:
        clase_jurisdiccion: Clase de la jurisdicción a testear (ej: Cordoba, Arba)
        headless: Si ejecutar en modo headless
        iterations: Número de iteraciones por cliente
        enable_tracing: Si habilitar tracing
        trace_dir: Directorio para traces
    """
    await generic_test_from_db(
        clase_jurisdiccion=clase_jurisdiccion,
        headless=headless,
        iterations=iterations,
        enable_tracing=enable_tracing,
        trace_dir=trace_dir,
    )


if __name__ == "__main__":
    # Ejemplos de cómo ejecutar los tests:

    # 1. Ejecutar un test específico:
    asyncio.run(la_pampa_test(headless=False))

    # 2. Ejecutar un test con múltiples iteraciones:
    # asyncio.run(cordoba_test(headless=False, iterations=15))

    # 3. Ejecutar un test por nombre:
    # asyncio.run(run_test_by_name('nacional', headless=False))

    # 4. Ejecutar el test de email:
    # send_email_smtp_test()

    # 5. Ejecutar test desde DB pasando directamente la clase:
    # asyncio.run(test_jurisdiccion_from_db(EntreRios, headless=False))

    # O usando generic_test_from_db directamente:
    # asyncio.run(generic_test_from_db(Cordoba, headless=False))

    # O especificando el nombre de jurisdicción explícitamente:
    # asyncio.run(generic_test_from_db(Cordoba, jurisdiccion="CORDOBA", headless=False))

    # Descomentar la línea correspondiente al test que se desea ejecutar
    # pass
