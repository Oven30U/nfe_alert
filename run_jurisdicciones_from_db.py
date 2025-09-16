"""
Runner que obtiene registros desde la base de datos usando ObtenerDatosClientes
y ejecuta las jurisdicciones correspondientes (similar a test_manuales.py pero usando
los registros que están en la base de datos).

Uso:
    python run_jurisdicciones_from_db.py --jurisdiccion agip --headless True --iterations 1
    python run_jurisdicciones_from_db.py --jurisdiccion all

El argumento --jurisdiccion acepta el nombre en minúsculas como en test_manuales (ej: agip, arba, salta,...)
"""

import argparse
import asyncio
import os
import sys
from typing import Any, Dict

# Asegurar que el paquete superior está en sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

# Importar la lógica existente
# Importar clases de jurisdicciones (igual que en test_manuales)
from jurisdicciones import (
    Agip,
    Arba,
    Catamarca,
    Chaco,
    Cordoba,
    Corrientes,
    EntreRios,
    Formosa,
    Jujuy,
    LaPampa,
    Mendoza,
    Nacional,
    Neuquen,
    RioNegro,
    Salta,
    SanJuan,
    SanLuis,
    SantaCruz,
    SantiagoDelEstero,
    Sicnea,
    Tucuman,
)

# Excepciones comunes usadas por las jurisdicciones (para mapear resultados)
from jurisdicciones.jurisdiccion import (
    BuscarNotificacionError,
    ConsultarNotificacionesError,
    DelegacionError,
    LoginError,
    TomarScreenshotError,
)
from obtener_datos_clientes.db import SessionLocal
from obtener_datos_clientes.models import (
    Cliente,
    ClienteJurisdiccion,
    Jurisdiccion,
)
from obtener_datos_clientes.obtener_datos_clientes import ObtenerDatosClientes

JURISDICCION_CLASSES: Dict[str, Any] = {
    "agip": Agip,
    "arba": Arba,
    "catamarca": Catamarca,
    "chaco": Chaco,
    "cordoba": Cordoba,
    "corrientes": Corrientes,
    "entrerios": EntreRios,
    "formosa": Formosa,
    "la_pampa": LaPampa,
    "mendoza": Mendoza,
    "nacional": Nacional,
    "neuquen": Neuquen,
    "rio_negro": RioNegro,
    "salta": Salta,
    "san_luis": SanLuis,
    "san_juan": SanJuan,
    "santa_cruz": SantaCruz,
    "santiago_del_estero": SantiagoDelEstero,
    "sicnea": Sicnea,
    "tucuman": Tucuman,
    "jujuy": Jujuy,
}


async def run_instance_for_row(row: dict, clase, headless: bool, iterations: int):
    """Crea la instancia de jurisdicción y ejecuta procesar_jurisdiccion.

    Devuelve una lista de dicts con los resultados por cada iteración.
    Cada dict tendrá al menos: cliente, jurisdiccion, iteration, status, result, error
    """
    # Extraer campos necesarios, adaptando a las claves usadas en crear_dataframe_base
    client_folder = row.get("client_folder")
    cliente = row.get("Cliente") or row.get("nombre") or client_folder
    cuit = row.get("cuit_cliente")
    # Soporte para claves con mayúscula/minúscula según cómo esté el DataFrame
    usuario = row.get("usuario") or row.get("Usuario")
    password = row.get("password") or row.get("Password")
    fecha_desde = row.get("fecha_desde")
    fecha_hasta = row.get("fecha_hasta")
    cuit_cliente_input = (
        row.get("cuit_cliente_input") if "cuit_cliente_input" in row else None
    )

    # Ejecutar iteraciones usando Playwright async API
    from playwright.async_api import async_playwright

    results = []
    for i in range(iterations):
        async with async_playwright() as playwright:
            try:
                # Muchas clases en `jurisdicciones` esperan el objeto `playwright` y los parámetros en ese orden
                # Mapeo: la clase espera (playwright, cliente, client_folder, cuit, clave_fiscal,
                # fecha_desde, fecha_hasta, cuit_cliente_input,...)
                # Según lo solicitado: _cuit <- usuario, _clave_fiscal <- password, _cuit_cliente_input <- cuit
                instance = await clase.create(
                    playwright,
                    cliente,
                    client_folder,
                    usuario,  # será self._cuit
                    password,  # será self._clave_fiscal
                    fecha_desde,
                    fecha_hasta,
                    cuit,  # será self._cuit_cliente_input
                    headless=headless,
                )

                # Ejecutar la jurisdicción y capturar el resultado (si la función lo retorna)
                result = await instance.procesar_jurisdiccion()

                results.append(
                    {
                        "cliente": cliente,
                        "jurisdiccion": clase.__name__,
                        "iteration": i + 1,
                        "status": "success",
                        "result": result,
                        "error": None,
                    }
                )
            except LoginError as le:
                results.append(
                    {
                        "cliente": cliente,
                        "jurisdiccion": clase.__name__,
                        "iteration": i + 1,
                        "status": "login_error",
                        "result": None,
                        "error": str(le),
                    }
                )
            except DelegacionError as de:
                results.append(
                    {
                        "cliente": cliente,
                        "jurisdiccion": clase.__name__,
                        "iteration": i + 1,
                        "status": "delegacion",
                        "result": None,
                        "error": str(de),
                    }
                )
            except ConsultarNotificacionesError as ce:
                results.append(
                    {
                        "cliente": cliente,
                        "jurisdiccion": clase.__name__,
                        "iteration": i + 1,
                        "status": "consult_error",
                        "result": None,
                        "error": str(ce),
                    }
                )
            except BuscarNotificacionError as be:
                results.append(
                    {
                        "cliente": cliente,
                        "jurisdiccion": clase.__name__,
                        "iteration": i + 1,
                        "status": "buscar_error",
                        "result": None,
                        "error": str(be),
                    }
                )
            except TomarScreenshotError as te:
                results.append(
                    {
                        "cliente": cliente,
                        "jurisdiccion": clase.__name__,
                        "iteration": i + 1,
                        "status": "screenshot_error",
                        "result": None,
                        "error": str(te),
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "cliente": cliente,
                        "jurisdiccion": clase.__name__,
                        "iteration": i + 1,
                        "status": "exception",
                        "result": None,
                        "error": str(e),
                    }
                )

    return results


async def main_async(jurisdiccion: str, headless: bool, iterations: int):
    odc = ObtenerDatosClientes()

    # --- Obtener clientes directamente desde la DB (sin subquery de MonitoreoBots) ---
    with SessionLocal() as db:
        clientes = db.query(Cliente).all()

        if not clientes:
            print("No se encontraron clientes en la base de datos (consulta directa)")
            return

        data_clientes = []
        for cliente in clientes:
            # No aplicamos filtros por MonitoreoBots ni por días; obtenemos todos los clientes
            data_clientes.append(
                {
                    "id": cliente.id,
                    "nombre": cliente.nombre,
                    "cuit": cliente.cuit,
                    "client_folder": cliente.client_folder,
                    "correo_output": cliente.correo_output,
                    "socio_responsable": cliente.socio_responsable,
                    "zip_password": cliente.zip_password,
                    "rango_consulta_dias": cliente.rango_consulta_dias,
                    "filtro_fce": cliente.filtro_fce,
                }
            )

        import pandas as pd

        df_clientes = pd.DataFrame(data_clientes)

        # --- Obtener jurisdicciones para esos clientes directamente desde la DB ---
        data_jur = []
        for _, cliente_row in df_clientes.iterrows():
            cliente_id = cliente_row["id"]
            # obtener las relaciones cliente_jurisdiccion vinculadas
            cj_rows = (
                db.query(ClienteJurisdiccion, Jurisdiccion)
                .join(
                    Jurisdiccion, ClienteJurisdiccion.jurisdiccion_id == Jurisdiccion.id
                )
                .filter(ClienteJurisdiccion.cliente_id == cliente_id)
                .filter(ClienteJurisdiccion.consultar == True)
                .all()
            )

            for cj, jur in cj_rows:
                data_jur.append(
                    {
                        "cliente_id": cliente_id,
                        "jurisdiccion_id": jur.id,
                        "jurisdiccion_clase": jur.clase,
                        "jurisdiccion_codigo": jur.codigo,
                        "usuario": cj.usuario,
                        "password": cj.password,
                        "headless": jur.headless,
                    }
                )

        df_jurisdicciones = pd.DataFrame(data_jur)

    if df_jurisdicciones.empty:
        print("No se encontraron jurisdicciones para los clientes (consulta directa)")
        return

    # Crear el dataframe base (sin aplicar filtrado adicional de login errors)
    df_base = odc.crear_dataframe_base(df_clientes, df_jurisdicciones)
    if df_base.empty:
        print("El DataFrame base quedó vacío después de unir clientes y jurisdicciones")
        return

    # Usar df_base directamente como fuente de filas
    odc.data = df_base

    # Normalizar nombre de jurisdicción sin sobrescribir la variable original.
    if isinstance(jurisdiccion, str):
        jurisdiccion_key = jurisdiccion.lower()
    elif isinstance(jurisdiccion, Jurisdiccion):
        jurisdiccion_key = jurisdiccion.clase.lower()
    else:
        jurisdiccion_key = str(jurisdiccion).lower()

    # Filtrar filas a procesar
    if jurisdiccion_key != "all":
        # Algunas clases usan nombres con espacios o mayúsculas, así que comparamos con la columna 'Jurisdiccion' en minúsculas
        df_filtered = odc.data[
            odc.data["Jurisdiccion"].str.lower().str.replace(" ", "_")
            == jurisdiccion_key
        ]
    else:
        df_filtered = odc.data

    if df_filtered.empty:
        print(f"No se encontraron filas para la jurisdicción: {jurisdiccion_key}")
        return

    # Mapear y ejecutar secuencialmente, recolectando resultados
    all_results = []
    for _, row in df_filtered.iterrows():
        clase = JURISDICCION_CLASSES.get(jurisdiccion_key)
        if clase is None and jurisdiccion_key == "all":
            # Cuando es 'all', intentar deducir la clase por el nombre de la Jurisdiccion
            key = row["Jurisdiccion"].lower().replace(" ", "_")
            clase = JURISDICCION_CLASSES.get(key)
        if clase is None:
            print(f"No existe clase para la jurisdicción: {row['Jurisdiccion']}")
            continue

        # Ejecutar de a una instancia para poder visualizar/depurar y recolectar resultados
        results = await run_instance_for_row(row.to_dict(), clase, headless, iterations)
        all_results.extend(results)

    # Mostrar y validar resultados
    import pandas as pd

    df_results = pd.DataFrame(all_results)
    # Imprimir DataFrame en consola
    print("\nResultados:")
    print(df_results.to_string(index=False))

    # Validar que los status estén dentro de los permitidos
    allowed_statuses = {
        "success",
        "login_error",
        "delegacion",
        "consult_error",
        "buscar_error",
        "screenshot_error",
        "exception",
    }

    # Aserción: cada status debe ser uno de los permitidos
    invalid_rows = df_results[~df_results["status"].isin(allowed_statuses)]
    assert invalid_rows.empty, (
        f"Se encontraron status inválidos:\n{invalid_rows.to_string(index=False)}"
    )

    return df_results


def parse_args():
    parser = argparse.ArgumentParser(description="Ejecutar jurisdicciones desde DB")
    parser.add_argument(
        "--jurisdiccion",
        default="all",
        help="jurisdiccion a ejecutar (ej: agip) o 'all'",
    )
    parser.add_argument("--headless", default="True", help="True/False para headless")
    parser.add_argument(
        "--iterations", type=int, default=1, help="veces a ejecutar cada instancia"
    )
    return parser.parse_args()


if __name__ == "__main__":
    JURISDICCION = "agip"
    HEADLESS = False
    ITERATIONS = 1

    # Execute
    asyncio.run(main_async(JURISDICCION, HEADLESS, ITERATIONS))
