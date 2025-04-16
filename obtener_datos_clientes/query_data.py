from obtener_datos_clientes.db import SessionLocal
from obtener_datos_clientes.models import (
    Cliente,
    Jurisdiccion,
    ClienteJurisdiccion,
    UsuariosAutorizados,
    UsuarioCliente,
    MonitoreoBots,
    ClienteProcessor,
)
import datetime
import sqlalchemy as sa
from sqlalchemy import and_
import pandas as pd
import os


def query_data():
    """
    Obtiene datos de clientes y jurisdicciones según los criterios actuales.
    Filtra los clientes que tienen la documentación habilitada y que tienen
    días de ejecución correspondientes al día actual.
    Devuelve un DataFrame con la información de los clientes y jurisdicciones filtrados.
    """
    today = datetime.date.today()
    day_name = today.strftime("%A")  # Full day name (e.g., "Monday")

    # Map English day names to Spanish
    day_name_es = {
        "Monday": "Lunes",
        "Tuesday": "Martes",
        "Wednesday": "Miércoles",
        "Thursday": "Jueves",
        "Friday": "Viernes",
        "Saturday": "Sábado",
        "Sunday": "Domingo",
    }.get(day_name)

    print("\n--- Consultando base de datos ---")

    with SessionLocal() as db:
        # Filtrar clientes según los criterios actuales
        clientes = (
            db.query(Cliente)
            .filter(Cliente.documentacion == True)
            .filter(Cliente.dias_ejecucion.like(f"%{day_name_es}%"))
            .filter(
                ~sa.exists().where(
                    and_(
                        MonitoreoBots.cliente_id == Cliente.id,
                        MonitoreoBots.estado == "Correcto",
                        sa.func.cast(MonitoreoBots.finalizado, sa.Date) == today,
                    )
                )
            )
            .all()
        )


        # Query all relevant data
        data_rows = []

        # Para cada cliente filtrado
        for cliente in clientes:
            # Obtener todas las jurisdicciones del cliente
            cliente_jurisdicciones = (
                db.query(ClienteJurisdiccion)
                .filter(ClienteJurisdiccion.cliente_id == cliente.id)
                .filter(
                    ClienteJurisdiccion.consultar == True
                )
                .all()
            )

            # Calcular fechas para la consulta
            fecha_hasta = today.strftime("%d%m%Y")
            fecha_desde = (
                today - datetime.timedelta(days=cliente.rango_consulta_dias)
            ).strftime("%d%m%Y")

            # Para cada jurisdicción del cliente
            for cj in cliente_jurisdicciones:
                jurisdiccion = db.query(Jurisdiccion).get(cj.jurisdiccion_id)

                # Crear una fila de datos para esta combinación cliente-jurisdicción
                row = {
                    "Jurisdiccion": jurisdiccion.clase,
                    "Consultar": "Si" if cj.consultar else "No",
                    "Usuario": cj.usuario or "",
                    "Password": cj.password or "",
                    "Cliente": cliente.nombre,
                    "cuit_cliente": cliente.cuit,
                    "CC: Equipo Deloitte": cliente.socio_responsable or "",
                    "Correo Output": cliente.correo_output or "",
                    "Rango de consulta días anteriores": cliente.rango_consulta_dias,  # Corregido el nombre de la columna
                    "Schedule": "",  # No está en el modelo actual
                    "Dia/s de ejecución": cliente.dias_ejecucion or "",
                    "ZIP_Password": cliente.zip_password or "",
                    "client_folder": cliente.client_folder,
                    "fecha_hasta": fecha_hasta,
                    "fecha_desde": fecha_desde,
                }

                data_rows.append(row)

        # Crear el DataFrame con todos los datos
        df = pd.DataFrame(data_rows)


        print(f"Se encontraron {len(df)} registros")
        print(df.info())

        return df


if __name__ == "__main__":
    df = query_data()
    print(df.head())
