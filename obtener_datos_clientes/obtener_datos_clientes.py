import datetime
from datetime import timezone, timedelta
import os
from typing import Dict, List, Optional, Union

import pandas as pd
from sqlalchemy.sql import func

from logger import Logger
from obtener_datos_clientes.db import SessionLocal
from obtener_datos_clientes.models import (
    Cliente,
    ClienteJurisdiccion,
    Jurisdiccion,
    ProcesamientosDiariosGlobal,
    MonitoreoBots,
)
from obtener_datos_clientes.query_data import query_data

logger = Logger.get_logger()


class ProcesamientoGlobalManager:
    """Clase para gestionar los procesamientos globales."""

    @staticmethod
    def registrar_procesamiento():
        """Registra un nuevo procesamiento global al comenzar."""
        with SessionLocal() as db:
            # Obtener la fecha actual (solo fecha, sin hora)
            fecha_hoy = datetime.datetime.now().date()

            # SQL Server: comparar año, mes y día individualmente
            max_numero_procesamiento = (
                db.query(ProcesamientosDiariosGlobal.numero_procesamiento)
                .filter(
                    func.year(ProcesamientosDiariosGlobal.fecha) == fecha_hoy.year,
                    func.month(ProcesamientosDiariosGlobal.fecha) == fecha_hoy.month,
                    func.day(ProcesamientosDiariosGlobal.fecha) == fecha_hoy.day,
                )
                .order_by(ProcesamientosDiariosGlobal.numero_procesamiento.desc())
                .first()
            )

            # Incrementar el número de procesamiento o iniciar en 1 si no hay registros
            numero_procesamiento = (
                max_numero_procesamiento[0] + 1 if max_numero_procesamiento else 1
            )

            nuevo_procesamiento = ProcesamientosDiariosGlobal(
                fecha=datetime.datetime.now(timezone.utc),
                numero_procesamiento=numero_procesamiento,
                iniciado=datetime.datetime.now(
                    timezone.utc
                ),  # Aseguramos que sea timezone-aware
                finalizado=None,
                procesamiento_correcto=True,
            )
            db.add(nuevo_procesamiento)
            db.commit()
            db.refresh(
                nuevo_procesamiento
            )  # Refrescar para obtener el ID y otros datos actualizados

            # Incrementar el número de procesamiento para futuras iteraciones
            return nuevo_procesamiento

    @staticmethod
    def finalizar_procesamiento(procesamiento, procesamiento_correcto=True):
        """Marca un procesamiento global como finalizado.

        Args:
            procesamiento: El objeto procesamiento a finalizar
            procesamiento_correcto: True si el procesamiento fue exitoso, False en caso de error (default: True)
        """
        with SessionLocal() as db:
            procesamiento.finalizado = datetime.datetime.now(
                timezone.utc
            )  # Use timezone-aware datetime
            procesamiento.procesamiento_correcto = procesamiento_correcto
            db.merge(
                procesamiento
            )  # Aseguramos que el objeto esté sincronizado con la sesión
            db.commit()
            estado = (
                "finalizado" if procesamiento_correcto else "finalizado con errores"
            )
            print(f"Procesamiento {procesamiento.numero_procesamiento} {estado}.")

    @staticmethod
    def finalizar_procesamiento_sin_clientes(procesamiento_id):
        """
        Marca un procesamiento global como finalizado cuando no hay clientes para procesar.

        Args:
            procesamiento_id: ID del procesamiento global a finalizar
        """
        with SessionLocal() as db:
            procesamiento = (
                db.query(ProcesamientosDiariosGlobal)
                .filter(ProcesamientosDiariosGlobal.id == procesamiento_id)
                .first()
            )

            if procesamiento:
                procesamiento.finalizado = datetime.datetime.now(timezone.utc)
                procesamiento.procesamiento_correcto = True
                db.commit()
                return True
            else:
                return False


class CorreoManager:
    """Clase para gestionar el envío de correos."""

    @staticmethod
    def enviar_correos(procesamiento):
        """Envía correos a los clientes según el número de procesamiento."""
        with SessionLocal() as db:
            if procesamiento.numero_procesamiento == 3:
                print(
                    "Enviando correos a todos los clientes debido al tercer procesamiento del día."
                )
                clientes = db.query(Cliente).all()
                for cliente in clientes:
                    print(
                        f"Enviando correo a: {cliente.correo_output} para el cliente {cliente.nombre}"
                    )
            else:
                print(
                    f"Procesamiento {procesamiento.numero_procesamiento} del día. No se enviarán correos masivos."
                )


class ObtenerDatosClientes:
    """Clase principal para gestionar el flujo de datos y correos."""

    def __init__(self):
        self.data = None
        self.procesamiento = None

    def run(self):
        """Ejecuta el proceso de obtención y transformación de datos de clientes"""
        try:
            # Obtener datos de clientes
            df_clientes = self.obtener_clientes_desde_db()
            if df_clientes.empty:
                logger.warning("No se encontraron clientes en la base de datos")
                return

            # Obtener datos de jurisdicciones para estos clientes
            df_jurisdicciones = self.obtener_jurisdicciones_desde_db(df_clientes)
            if df_jurisdicciones.empty:
                logger.warning("No se encontraron jurisdicciones para los clientes")
                return

            # Crear DataFrame base con todos los datos
            df_base = self.crear_dataframe_base(df_clientes, df_jurisdicciones)

            # Filtrar jurisdicciones con errores de login recientes
            df_filtrado = self.filtrar_jurisdicciones_por_login_error(df_base)

            # Aplicar transformaciones adicionales al DataFrame
            self.data = self.transformar_dataframe(df_filtrado)

            logger.info(f"Datos obtenidos correctamente: {len(self.data)} filas")

        except Exception as e:
            logger.error(f"Error al obtener datos de clientes: {str(e)}")
            # En caso de error, asignar DataFrame vacío
            self.data = pd.DataFrame()

    def display_data(self):
        """Muestra los datos obtenidos."""
        if self.data is not None and not self.data.empty:
            print(self.data)
        else:
            print("No hay datos para mostrar")

    def gestionar_envio_correos(self):
        """Gestiona el envío de correos y el registro de procesamientos."""
        try:
            # Registrar un nuevo procesamiento global
            self.procesamiento = ProcesamientoGlobalManager.registrar_procesamiento()

            # Enviar correos según el número de procesamiento
            CorreoManager.enviar_correos(self.procesamiento)

            # Finalizar el procesamiento global
            ProcesamientoGlobalManager.finalizar_procesamiento(self.procesamiento)
        except Exception as e:
            print(f"Error en gestión de correos: {str(e)}")
            print("Se continuará con la ejecución principal")

    def obtener_clientes_desde_db(self) -> pd.DataFrame:
        """
        Obtiene los clientes activos desde la base de datos, excluyendo aquellos con estado 'Correcto' en MonitoreoBots para el día actual.

        Returns:
            pd.DataFrame: DataFrame con la información de los clientes
        """
        try:
            from sqlalchemy import select

            with SessionLocal() as db:
                # Obtener la fecha actual
                fecha_hoy = datetime.datetime.now().date()

                # Subquery para obtener los IDs de cliente con estado 'Correcto' en MonitoreoBots para el día actual
                subquery = (
                    db.query(MonitoreoBots.cliente_id)
                    .filter(
                        func.year(MonitoreoBots.iniciado) == fecha_hoy.year,
                        func.month(MonitoreoBots.iniciado) == fecha_hoy.month,
                        func.day(MonitoreoBots.iniciado) == fecha_hoy.day,
                        MonitoreoBots.proceso == "NFE Alert",
                        MonitoreoBots.estado == "Correcto",
                    )
                    .subquery()
                )

                # Convertir el subquery a un SELECT explícito
                subquery_select = select(subquery.c.cliente_id)

                # Excluir los clientes que están en el subquery - usando cliente_id en vez de username
                clientes = (
                    db.query(Cliente).filter(~Cliente.id.in_(subquery_select)).all()
                )

                if not clientes:
                    logger.warning("No se encontraron clientes en la base de datos")
                    return pd.DataFrame()

                # Convertir a DataFrame
                data = []
                for cliente in clientes:
                    if self._cliente_ejecuta_hoy(cliente):
                        data.append(
                            {
                                "id": cliente.id,
                                "nombre": cliente.nombre,
                                "cuit": cliente.cuit,
                                "client_folder": cliente.client_folder,
                                "correo_output": cliente.correo_output
                                ,
                                "socio_responsable": cliente.socio_responsable,
                                "zip_password": cliente.zip_password,
                                "rango_consulta_dias": cliente.rango_consulta_dias,
                            }
                        )

                df_clientes = pd.DataFrame(data)
                logger.info(f"Se obtuvieron {len(df_clientes)} clientes para procesar")
                return df_clientes

        except Exception as e:
            logger.error(f"Error al obtener clientes desde DB: {str(e)}")
            return pd.DataFrame()

    def obtener_jurisdicciones_desde_db(
        self, df_clientes: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Obtiene las jurisdicciones para los clientes especificados.

        Args:
            df_clientes: DataFrame con la información de los clientes

        Returns:
            pd.DataFrame: DataFrame con las jurisdicciones de los clientes
        """
        try:
            with SessionLocal() as db:
                data = []

                for _, cliente_row in df_clientes.iterrows():
                    cliente_id = cliente_row["id"]

                    # Obtener relaciones cliente-jurisdicción
                    cliente_jurisdicciones = (
                        db.query(ClienteJurisdiccion, Jurisdiccion)
                        .join(
                            Jurisdiccion,
                            ClienteJurisdiccion.jurisdiccion_id == Jurisdiccion.id,
                        )
                        .filter(ClienteJurisdiccion.cliente_id == cliente_id)
                        .filter(ClienteJurisdiccion.consultar == True)
                        .all()
                    )

                    for cj, jurisdiccion in cliente_jurisdicciones:
                        data.append(
                            {
                                "cliente_id": cliente_id,
                                "jurisdiccion_id": jurisdiccion.id,
                                "jurisdiccion_clase": jurisdiccion.clase,
                                "jurisdiccion_codigo": jurisdiccion.codigo,
                                "usuario": cj.usuario,
                                "password": cj.password,
                                "headless": jurisdiccion.headless,
                            }
                        )

                df_jurisdicciones = pd.DataFrame(data)
                logger.info(
                    f"Se obtuvieron {len(df_jurisdicciones)} jurisdicciones para los clientes"
                )
                return df_jurisdicciones

        except Exception as e:
            logger.error(f"Error al obtener jurisdicciones desde DB: {str(e)}")
            return pd.DataFrame()

    def crear_dataframe_base(
        self, df_clientes: pd.DataFrame, df_jurisdicciones: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Crea un DataFrame base con la unión de clientes y jurisdicciones.

        Args:
            df_clientes: DataFrame con información de clientes
            df_jurisdicciones: DataFrame con información de jurisdicciones

        Returns:
            pd.DataFrame: DataFrame combinado con toda la información
        """
        try:
            # Fusionar DataFrames
            df_merged = pd.merge(
                df_clientes,
                df_jurisdicciones,
                how="inner",
                left_on="id",
                right_on="cliente_id",
            )

            # Crear campos para fechas de consulta
            today = datetime.datetime.now()

            def calcular_fechas(row):
                dias = row["rango_consulta_dias"] or 7
                fecha_hasta = today.strftime("%d%m%Y")
                fecha_desde = (today - timedelta(days=dias)).strftime("%d%m%Y")
                return pd.Series(
                    {"fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta}
                )

            fechas_df = df_merged.apply(calcular_fechas, axis=1)
            df_merged = pd.concat([df_merged, fechas_df], axis=1)

            # Renombrar y seleccionar columnas
            df_base = df_merged.rename(
                columns={
                    "nombre": "Cliente",
                    "jurisdiccion_clase": "Jurisdiccion",
                    "cuit": "cuit_cliente",
                    "usuario": "Usuario",
                    "password": "Password",
                    "correo_output": "Correo Output",
                    "socio_responsable": "CC: Equipo Deloitte",
                    "zip_password": "ZIP_Password",
                }
            )

            # Seleccionar columnas necesarias
            columns_to_keep = [
                "Cliente",
                "Jurisdiccion",
                "client_folder",
                "cuit_cliente",
                "Usuario",
                "Password",
                "fecha_desde",
                "fecha_hasta",
                "Correo Output",
                "CC: Equipo Deloitte",
                "ZIP_Password",
            ]

            df_base = df_base[columns_to_keep]

            logger.info(f"DataFrame base creado con {len(df_base)} filas")
            return df_base

        except Exception as e:
            logger.error(f"Error al crear DataFrame base: {str(e)}")
            return pd.DataFrame()

    def transformar_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica transformaciones adicionales al DataFrame.

        Args:
            df: DataFrame a transformar

        Returns:
            pd.DataFrame: DataFrame transformado
        """
        try:
            # Crear copia para no modificar el original
            df_result = df.copy()

            # Asegurarse de que los campos cuit sean strings
            if "cuit_cliente" in df_result.columns:
                df_result["cuit_cliente"] = df_result["cuit_cliente"].astype(str)

            # Rellenar valores nulos en ciertas columnas
            for col in ["Correo Output", "CC: Equipo Deloitte", "ZIP_Password"]:
                if col in df_result.columns:
                    df_result[col] = df_result[col].fillna("")

            # Agregar columnas de configuración si es necesario
            df_result["ZIP_Password"] = df_result["ZIP_Password"]

            # Verificar si estamos en modo desarrollo para usar correos de prueba
            dev_mode = os.getenv("DEV_MODE", "False").lower()
            if dev_mode == "true" and not df_result.empty:
                logger.info(
                    "Modo desarrollo: Usando correo de prueba para todos los clientes"
                )
                test_email = os.getenv(
                    "CORREO_RECEPTOR_TEST_MAIL", "lmarinaro@deloitte.com"
                )
                # Reemplazar correos con el correo de prueba
                if "Correo Output" in df_result.columns:
                    df_result["Correo Output"] = test_email
                if "CC: Equipo Deloitte" in df_result.columns:
                    df_result["CC: Equipo Deloitte"] = test_email

                logger.info(f"Correos reemplazados por: {test_email}")

            # Mantener la compatibilidad con el formato anterior de query_data
            # Esto puede personalizarse según las necesidades específicas

            return df_result

        except Exception as e:
            logger.error(f"Error al transformar DataFrame: {str(e)}")
            return df

    def _cliente_ejecuta_hoy(self, cliente: Cliente) -> bool:
        """
        Verifica si un cliente debe ejecutarse hoy según su configuración de días.

        Args:
            cliente: Objeto Cliente a evaluar

        Returns:
            bool: True si el cliente debe ejecutarse hoy, False en caso contrario
        """
        try:
            # Si no hay configuración de días, no ejecutar
            if not cliente.dias_ejecucion:
                return False

            # Obtener día de la semana (0-6, donde 0 es lunes)
            dia_hoy = datetime.datetime.now().weekday()

            separador = ";" if ";" in cliente.dias_ejecucion else ","

            # Convertir a números (0-6) los días configurados
            dias_config = [
                int(d.strip())
                for d in cliente.dias_ejecucion.split(separador)
                if d.strip().isdigit()
            ]

            # Verificar si el día actual está en la configuración
            return dia_hoy in dias_config

        except Exception as e:
            logger.error(
                f"Error al verificar días de ejecución del cliente {cliente.nombre}: {str(e)}"
            )
            # En caso de error, permitir ejecución por seguridad
            return False

    def filtrar_jurisdicciones_por_login_error(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filtra las jurisdicciones que no deben procesarse debido a errores de login recientes,
        pero las mantiene en el DataFrame con un mensaje indicativo para mostrarlas en el resultado final.

        Args:
            df: DataFrame con datos de jurisdicciones por cliente

        Returns:
            pd.DataFrame: DataFrame con jurisdicciones marcadas pero no eliminadas
        """
        from sqlalchemy import text

        # Crear una copia para no modificar el original durante la iteración
        df_result = df.copy()

        # Añadir columnas para el resultado final si no existen
        if "Notificacion" not in df_result.columns:
            df_result["Notificacion"] = None
        if "Error" not in df_result.columns:
            df_result["Error"] = None
        if "Saltar" not in df_result.columns:
            df_result["Saltar"] = False

        try:
            with SessionLocal() as db:
                # Para cada fila en el DataFrame
                for idx, row in df.iterrows():
                    cliente_folder = row["client_folder"]
                    jurisdiccion_nombre = row["Jurisdiccion"]

                    # Obtener IDs de cliente y jurisdicción
                    cliente = (
                        db.query(Cliente)
                        .filter(Cliente.client_folder == cliente_folder)
                        .first()
                    )

                    if not cliente:
                        logger.warning(
                            f"No se encontró cliente con client_folder={cliente_folder}"
                        )
                        continue

                    jurisdiccion = (
                        db.query(Jurisdiccion)
                        .filter(Jurisdiccion.clase == jurisdiccion_nombre)
                        .first()
                    )

                    if not jurisdiccion:
                        logger.warning(
                            f"No se encontró jurisdicción con clase={jurisdiccion_nombre}"
                        )
                        continue

                    # Obtener el registro ClienteJurisdiccion
                    cliente_jurisdiccion = (
                        db.query(ClienteJurisdiccion)
                        .filter(
                            ClienteJurisdiccion.cliente_id == cliente.id,
                            ClienteJurisdiccion.jurisdiccion_id == jurisdiccion.id,
                        )
                        .first()
                    )

                    if not cliente_jurisdiccion:
                        logger.warning(
                            f"No se encontró relación cliente-jurisdicción para {cliente_folder}-{jurisdiccion_nombre}"
                        )
                        continue

                    # Verificar si se debe procesar
                    procesar = self.debe_procesar_jurisdiccion(cliente_jurisdiccion)
                    if not procesar:
                        # En lugar de eliminar, marcar la fila como que debe saltarse
                        df_result.loc[idx, "Notificacion"] = "Credenciales inválidas"
                        df_result.loc[idx, "Error"] = "LoginError"
                        df_result.loc[idx, "Saltar"] = True
                        logger.info(
                            f"Marcando jurisdicción {jurisdiccion_nombre} para cliente {cliente_folder} por error de login reciente"
                        )

        except Exception as e:
            logger.error(f"Error al filtrar jurisdicciones por login_error: {str(e)}")

        return df_result

    def debe_procesar_jurisdiccion(self, cliente_jurisdiccion) -> bool:
        """
        Determina si una jurisdicción debe procesarse basada en fecha_login_error y fecha_actualizacion.

        Esta función implementa la lógica de negocio para gestionar los errores de login:
        - Si no hay error de login registrado, siempre procesar
        - Si se actualizaron credenciales después del último error, procesar y resetear error
        - Si el error es más reciente que la última actualización, no procesar

        Args:
            cliente_jurisdiccion: Objeto ClienteJurisdiccion a evaluar

        Returns:
            bool: True si se debe procesar, False si se debe omitir
        """
        # Si no hay error de login registrado, siempre procesar
        if cliente_jurisdiccion.fecha_login_error is None:
            return True

        # Si hay error de login pero se han actualizado las credenciales después, procesar
        if (
            cliente_jurisdiccion.fecha_actualizacion
            and cliente_jurisdiccion.fecha_login_error
            < cliente_jurisdiccion.fecha_actualizacion
        ):
            # En este caso, deberíamos también resetear fecha_login_error
            from sqlalchemy import text

            with SessionLocal() as db:
                try:
                    # Usamos SQL directo para no actualizar fecha_actualizacion
                    sql = text("""
                        UPDATE cliente_jurisdiccion
                        SET fecha_login_error = NULL
                        WHERE id = :id
                    """)

                    db.execute(sql, {"id": cliente_jurisdiccion.id})
                    db.commit()
                    logger.info(
                        f"Reset de fecha_login_error para ClienteJurisdiccion id={cliente_jurisdiccion.id}"
                    )
                except Exception as e:
                    logger.warning(f"Error al resetear fecha_login_error: {str(e)}")

            return True

        # Si el error de login es más reciente que la actualización de credenciales, no procesar
        logger.info(
            f"Saltando jurisdicción {cliente_jurisdiccion.jurisdiccion.clase} por error de login reciente"
        )
        return False


if __name__ == "__main__":
    main_instance = ObtenerDatosClientes()
    main_instance.run()
    main_instance.gestionar_envio_correos()
