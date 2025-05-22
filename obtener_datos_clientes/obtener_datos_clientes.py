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
        Obtiene los clientes activos desde la base de datos.

        Si la variable de entorno TEST_CLIENT_FOLDERS está definida, filtra solo los clientes
        especificados y omite los filtros estándar de procesamiento diario y ejecución programada.

        Returns:
            pd.DataFrame: DataFrame con la información de los clientes
        """
        try:
            from sqlalchemy import select

            with SessionLocal() as db:
                # Verificar si existe la variable de entorno TEST_CLIENT_FOLDERS
                test_clients_str = os.getenv("TEST_CLIENT_FOLDERS")

                if test_clients_str:
                    # Modo test: obtener solo los clientes especificados
                    test_clients = [
                        client.strip() for client in test_clients_str.split(",")
                    ]
                    logger.info(
                        f"Modo test activado: procesando únicamente los clientes: {test_clients}"
                    )

                    # Filtrar por client_folder
                    clientes = (
                        db.query(Cliente)
                        .filter(Cliente.client_folder.in_(test_clients))
                        .all()
                    )

                    if not clientes:
                        logger.warning(
                            f"No se encontraron los clientes de prueba: {test_clients}"
                        )
                        return pd.DataFrame()
                else:
                    # Modo normal: aplicar filtros estándar
                    fecha_hoy = datetime.datetime.now().date()

                    # Subquery para obtener los IDs de cliente con estado 'Correcto' en MonitoreoBots
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

                    # Excluir los clientes que están en el subquery
                    clientes = (
                        db.query(Cliente).filter(~Cliente.id.in_(subquery_select)).all()
                    )

                if not clientes:
                    logger.warning("No se encontraron clientes en la base de datos")
                    return pd.DataFrame()

                # Convertir a DataFrame
                data = []
                for cliente in clientes:
                    # Si estamos en modo test, omitir verificación de días de ejecución
                    if test_clients_str or self._cliente_ejecuta_hoy(cliente):
                        data.append(
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

                    # Verificar documentación del cliente
                    cliente = self._verificar_documentacion_cliente(db, cliente_id)
                    if not cliente:
                        continue

                    # Obtener jurisdicciones para este cliente
                    jurisdicciones = self._obtener_jurisdicciones_para_cliente(
                        db, cliente_id
                    )

                    # Transformar a formato de datos
                    self._agregar_jurisdicciones_a_data(
                        jurisdicciones, cliente_id, data
                    )

                # Crear DataFrame final
                return self._crear_dataframe_jurisdicciones(data)

        except Exception as e:
            logger.error(f"Error al obtener jurisdicciones desde DB: {str(e)}")
            return pd.DataFrame()

    def _verificar_documentacion_cliente(
        self, db, cliente_id: int
    ) -> Optional[Cliente]:
        """
        Verifica si un cliente tiene la documentación habilitada.

        Args:
            db: Sesión de base de datos
            cliente_id: ID del cliente a verificar

        Returns:
            Cliente: Objeto cliente si tiene documentación habilitada, None en caso contrario
        """
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente or not cliente.documentacion:
            logger.info(
                f"Cliente {cliente_id} - {cliente.nombre} - excluido por no tener documentacion"
            )
            return None
        return cliente

    def _obtener_jurisdicciones_para_cliente(self, db, cliente_id: int) -> list:
        """
        Obtiene las jurisdicciones configuradas para un cliente.

        Args:
            db: Sesión de base de datos
            cliente_id: ID del cliente

        Returns:
            list: Lista de tuplas (ClienteJurisdiccion, Jurisdiccion)
        """
        return (
            db.query(ClienteJurisdiccion, Jurisdiccion)
            .join(
                Jurisdiccion,
                ClienteJurisdiccion.jurisdiccion_id == Jurisdiccion.id,
            )
            .filter(ClienteJurisdiccion.cliente_id == cliente_id)
            .filter(ClienteJurisdiccion.consultar == True)
            .all()
        )

    def _agregar_jurisdicciones_a_data(
        self, jurisdicciones: list, cliente_id: int, data: list
    ) -> None:
        """
        Agrega las jurisdicciones del cliente al listado de datos.

        Args:
            jurisdicciones: Lista de tuplas (ClienteJurisdiccion, Jurisdiccion)
            cliente_id: ID del cliente
            data: Lista donde se agregarán los datos
        """
        for cj, jurisdiccion in jurisdicciones:
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

    def _crear_dataframe_jurisdicciones(self, data: list) -> pd.DataFrame:
        """
        Crea un DataFrame con los datos de jurisdicciones.

        Args:
            data: Lista de diccionarios con datos de jurisdicciones

        Returns:
            pd.DataFrame: DataFrame con las jurisdicciones
        """
        df_jurisdicciones = pd.DataFrame(data)
        logger.info(
            f"Se obtuvieron {len(df_jurisdicciones)} jurisdicciones para los clientes"
        )
        return df_jurisdicciones

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
                "filtro_fce",
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
        Filtra jurisdicciones con errores de login recientes en una sola consulta eficiente.

        Args:
            df: DataFrame con datos de jurisdicciones por cliente

        Returns:
            pd.DataFrame: DataFrame con jurisdicciones marcadas pero no eliminadas
        """
        # Crear una copia para no modificar el original
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
                # Recolectar todos los client_folder y jurisdicción_nombre únicos
                client_folders = df["client_folder"].unique().tolist()
                jurisdiccion_nombres = df["Jurisdiccion"].unique().tolist()

                # Obtener todos los clientes relevantes en una sola consulta
                clientes_dict = {
                    cliente.client_folder: cliente
                    for cliente in db.query(Cliente)
                    .filter(Cliente.client_folder.in_(client_folders))
                    .all()
                }

                # Obtener todas las jurisdicciones relevantes en una sola consulta
                jurisdicciones_dict = {
                    jurisdiccion.clase: jurisdiccion
                    for jurisdiccion in db.query(Jurisdiccion)
                    .filter(Jurisdiccion.clase.in_(jurisdiccion_nombres))
                    .all()
                }

                # Obtener todos los registros cliente_jurisdiccion relevantes
                cliente_ids = [
                    cliente.id for cliente in clientes_dict.values() if cliente
                ]
                jurisdiccion_ids = [
                    jurisdiccion.id
                    for jurisdiccion in jurisdicciones_dict.values()
                    if jurisdiccion
                ]

                # Solo hacer la consulta si hay IDs para buscar
                cj_mapping = {}
                if cliente_ids and jurisdiccion_ids:
                    cliente_jurisdicciones = (
                        db.query(ClienteJurisdiccion)
                        .filter(
                            ClienteJurisdiccion.cliente_id.in_(cliente_ids),
                            ClienteJurisdiccion.jurisdiccion_id.in_(jurisdiccion_ids),
                        )
                        .all()
                    )

                    # Crear un mapa para acceso rápido: (cliente_id, jurisdiccion_id) -> cliente_jurisdiccion
                    for cj in cliente_jurisdicciones:
                        cj_mapping[(cj.cliente_id, cj.jurisdiccion_id)] = cj

                # Ahora procesar el DataFrame usando las estructuras de datos en memoria
                for idx, row in df.iterrows():
                    cliente_folder = row["client_folder"]
                    jurisdiccion_nombre = row["Jurisdiccion"]

                    # Buscar cliente y jurisdicción en los diccionarios
                    cliente = clientes_dict.get(cliente_folder)
                    jurisdiccion = jurisdicciones_dict.get(jurisdiccion_nombre)

                    if not cliente:
                        logger.warning(
                            f"No se encontró cliente con client_folder={cliente_folder}"
                        )
                        continue

                    if not jurisdiccion:
                        logger.warning(
                            f"No se encontró jurisdicción con clase={jurisdiccion_nombre}"
                        )
                        continue

                    # Buscar cliente_jurisdiccion en el mapa
                    cliente_jurisdiccion = cj_mapping.get((cliente.id, jurisdiccion.id))

                    if not cliente_jurisdiccion:
                        logger.warning(
                            f"No se encontró relación cliente-jurisdicción para {cliente_folder}-{jurisdiccion_nombre}"
                        )
                        continue

                    # Verificar si se debe procesar usando la misma lógica
                    procesar = self._debe_procesar_jurisdiccion_local(
                        cliente_jurisdiccion
                    )
                    if not procesar:
                        # Marcar la fila como que debe saltarse
                        df_result.loc[idx, "Notificacion"] = "Credenciales inválidas"
                        df_result.loc[idx, "Error"] = "LoginError"
                        df_result.loc[idx, "Saltar"] = True
                        logger.info(
                            f"Marcando jurisdicción {jurisdiccion_nombre} para cliente {cliente_folder} por error de login reciente"
                        )

                # Actualizar todos los registros que necesitan resetear fecha_login_error en una sola operación
                self._resetear_errores_login_batch(db, cliente_jurisdicciones)

        except Exception as e:
            logger.error(f"Error al filtrar jurisdicciones por login_error: {str(e)}")

        return df_result

    def _debe_procesar_jurisdiccion_local(self, cliente_jurisdiccion) -> bool:
        """
        Versión local de debe_procesar_jurisdiccion que no necesita conexión a DB.
        Solo para evaluación, no resetea fecha_login_error.

        Args:
            cliente_jurisdiccion: Objeto ClienteJurisdiccion a evaluar

        Returns:
            bool: True si se debe procesar, False si se debe omitir
        """
        # Si no hay error de login registrado, siempre procesar
        if cliente_jurisdiccion.fecha_login_error is None:
            return True

        # Si hay error pero se actualizaron credenciales después, procesar
        if (
            cliente_jurisdiccion.fecha_actualizacion
            and cliente_jurisdiccion.fecha_login_error
            < cliente_jurisdiccion.fecha_actualizacion
        ):
            return True

        # Error de login más reciente que la actualización de credenciales
        return False

    def _resetear_errores_login_batch(self, db, cliente_jurisdicciones: list) -> None:
        """
        Resetea fecha_login_error para múltiples registros en una sola operación.

        Args:
            db: Sesión de base de datos activa
            cliente_jurisdicciones: Lista de objetos ClienteJurisdiccion a evaluar
        """
        try:
            # Identificar IDs que necesitan reset
            ids_to_reset = []
            for cj in cliente_jurisdicciones:
                if (
                    cj.fecha_login_error
                    and cj.fecha_actualizacion
                    and cj.fecha_login_error < cj.fecha_actualizacion
                ):
                    ids_to_reset.append(cj.id)

            if not ids_to_reset:
                return

            # Ejecutar actualización en lote
            from sqlalchemy import text

            sql = text("""
                UPDATE cliente_jurisdiccion
                SET fecha_login_error = NULL
                WHERE id IN :ids
            """)

            db.execute(sql, {"ids": tuple(ids_to_reset)})
            db.commit()
            logger.info(
                f"Reset de fecha_login_error para {len(ids_to_reset)} registros"
            )
        except Exception as e:
            logger.warning(f"Error al resetear fecha_login_error en lote: {str(e)}")


if __name__ == "__main__":
    main_instance = ObtenerDatosClientes()
    main_instance.run()
    main_instance.gestionar_envio_correos()
