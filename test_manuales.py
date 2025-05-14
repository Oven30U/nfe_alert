import asyncio
import functools
import os
import sys

from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Agregar el directorio que contiene el módulo 'jurisdicciones' al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jurisdicciones import (
    Agip,
    Arba,
    Catamarca,
    Chaco,
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
    SantiagoDelEstero,
    Sicnea,
    Tucuman,
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


async def generic_test(jurisdiccion, clase_jurisdiccion, headless=False, iterations=1):
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

                # Crear instancia de la jurisdicción
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

                # Procesar la jurisdicción
                await instance.procesar_jurisdiccion()

            if iterations > 1:
                print(f"Iteración {i + 1} completada con éxito.")

        except Exception as e:
            print(f"Error en {jurisdiccion} (iteración {i + 1}): {e}")
            if iterations == 1:  # Si solo hay una iteración, propagar el error
                raise


# Definir funciones específicas para cada jurisdicción que usan la función genérica
async def catamarca_test(headless=False, iterations=1):
    await generic_test("CATAMARCA", Catamarca, headless, iterations)


async def santiago_test(headless=False, iterations=1):
    await generic_test("SANTIAGO_DEL_ESTERO", SantiagoDelEstero, headless, iterations)


async def cordoba_test(headless=False, iterations=1):
    await generic_test("CORDOBA", Cordoba, headless, iterations)


async def arba_test(headless=False, iterations=1):
    await generic_test("ARBA", Arba, headless, iterations)


async def salta_test(headless=False, iterations=1):
    await generic_test("SALTA", Salta, headless, iterations)


async def sicnea_test(headless=False, iterations=1):
    await generic_test("SICNEA", Sicnea, headless, iterations)


async def chaco_test(headless=False, iterations=1):
    await generic_test("CHACO", Chaco, headless, iterations)


async def agip_test(headless=False, iterations=1):
    await generic_test("AGIP", Agip, headless, iterations)


async def rio_negro_test(headless=False, iterations=1):
    await generic_test("RIO_NEGRO", RioNegro, headless, iterations)


async def nacional_test(headless=False, iterations=1):
    await generic_test("NACIONAL", Nacional, headless, iterations)

async def corrientes_test(headless=False, iterations=1):
    await generic_test("CORRIENTES", Corrientes, headless, iterations)


async def entre_rios_test(headless=False, iterations=1):
    await generic_test("ENTRERIOS", EntreRios, headless, iterations)


async def san_luis_test(headless=False, iterations=1):
    await generic_test("SANLUIS", SanLuis, headless, iterations)


async def tucuman_test(headless=False, iterations=1):
    await generic_test("TUCUMAN", Tucuman, headless, iterations)


async def la_pampa_test(headless=False, iterations=1):
    await generic_test("LA_PAMPA", LaPampa, headless, iterations)


async def mendoza_test(headless=False, iterations=1):
    await generic_test("MENDOZA", Mendoza, headless, iterations)


async def formosa_test(headless=False, iterations=1):
    await generic_test("FORMOSA", Formosa, headless, iterations)


async def neuquen_test(headless=False, iterations=1):
    await generic_test("NEUQUEN", Neuquen, headless, iterations)


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
async def run_test_by_name(test_name, headless=False, iterations=1):
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
    }

    if test_name.lower() in tests:
        await tests[test_name.lower()](headless, iterations)
    else:
        print(
            f"Test '{test_name}' no encontrado. Tests disponibles: {', '.join(tests.keys())}"
        )


if __name__ == "__main__":
    # Ejemplos de cómo ejecutar los tests:

    # 1. Ejecutar un test específico:
    asyncio.run(catamarca_test(headless=False))

    # 2. Ejecutar un test con múltiples iteraciones:
    # asyncio.run(santiago_test(headless=False, iterations=5))

    # 3. Ejecutar un test por nombre:
    # asyncio.run(run_test_by_name('nacional', headless=False))

    # 4. Ejecutar el test de email:
    # send_email_smtp_test()

    # Descomentar la línea correspondiente al test que se desea ejecutar
    # pass
