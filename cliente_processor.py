import asyncio
import glob
import os
import shutil
from datetime import datetime, timedelta
from typing import Optional, List
import pandas as pd
import pyminizip
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from PIL import Image
import jurisdicciones
from conectar_db import conectar_db
from logger import Logger
from mail import enviar_correo
from mapa_plot import crear_mapa, crear_mapa_argentina
from obtener_datos_clientes.db import SessionLocal
from obtener_datos_clientes.models import ProcesamientosDiariosGlobal
from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError

logger = Logger.get_logger()

CORREO_NOTIFICACION_ERROR = os.getenv(
    "CORREO_NOTIFICACION_ERROR", "rpa-tax-ar@deloitte.com"
)
CORREO_TEST = os.getenv("CORREO_TEST", "amiriarte@deloitte.com")
ENVIAR_CORREO_TEST = os.getenv("ENVIAR_CORREO_TEST", "False").lower() == "true"
LIMITES_REINTENTO = int(os.getenv("LIMITES_REINTENTO", 5))

CLIENTES_ENVIAR_AUNQUE_ERROR_RAW: str = os.getenv("CLIENTES_ENVIAR_AUNQUE_ERROR", "")
CLIENTES_ENVIAR_AUNQUE_ERROR_LIST: List[str] = [
    cliente.strip()
    for cliente in CLIENTES_ENVIAR_AUNQUE_ERROR_RAW.split(",")
    if cliente.strip()
]
if CLIENTES_ENVIAR_AUNQUE_ERROR_LIST:
    logger.info(
        f"Los siguientes clientes recibirán correo a su destinatario habitual aunque haya errores: {CLIENTES_ENVIAR_AUNQUE_ERROR_LIST}"
    )


class ClienteProcessor:
    def __init__(
        self,
        cliente: str,
        group: pd.DataFrame,
        cuit_cliente: str,
        inicio: datetime,
        client_folder: str,
        cliente_id: int = None,
        procesamiento_id: int = None,
    ):
        self.cliente: str = cliente
        self.client_folder = client_folder
        self.group: pd.DataFrame = group
        self.cuit_cliente: str = cuit_cliente
        self.inicio: datetime = inicio
        self.client_folder: str = client_folder
        self.cliente_id = cliente_id
        self.procesamiento_id = procesamiento_id
        self.output_folder, self.backup_folder = self.preparar_directorios()
        self.correo_output: str = self.obtener_correo()
        self.socio_responsable: str = self.obtener_socio()
        self.zip_path: str = None
        self.zip_name: str = None
        self.pdf_path: str = None

        if "ZIP_Password" in group.columns:
            self.zip_password = group["ZIP_Password"].iloc[0]
        else:
            self.zip_password = os.getenv("PASS_ZIP_DEFAULT", "")

    def preparar_directorios(self):
        base_folder = f"Estructura-robot/{self.client_folder}"
        output_folder = os.path.join(base_folder, "Output")
        backup_folder = os.path.join(base_folder, "Backup")
        os.makedirs(output_folder, exist_ok=True)
        os.makedirs(backup_folder, exist_ok=True)
        return output_folder, backup_folder

    def respaldar_archivos(self):
        files = os.listdir(self.output_folder)
        for file in files:
            file_path = os.path.join(self.output_folder, file)
            backup_path = os.path.join(self.backup_folder, file)
            if file.endswith(".zip"):
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                shutil.move(file_path, self.backup_folder)
            else:
                os.remove(file_path)

    def obtener_correo(self):
        if ENVIAR_CORREO_TEST:
            return CORREO_TEST
        if "Correo Output" in self.group.columns:
            correo_output = self.group["Correo Output"].iloc[0]
            return correo_output if pd.notna(correo_output) else None
        else:
            return None

    def obtener_socio(self):
        if ENVIAR_CORREO_TEST:
            return CORREO_TEST
        if "CC: Equipo Deloitte" in self.group.columns:
            socio_responsable = self.group["CC: Equipo Deloitte"].iloc[0]
            return socio_responsable if pd.notna(socio_responsable) else None
        else:
            return None

    def filtrar_jurisdicciones_por_login_error(self) -> None:
        """
        Filtra las jurisdicciones que no deben procesarse debido a errores de login recientes,
        pero las mantiene en el DataFrame con un mensaje indicativo para mostrarlas en el resultado final.

        Modifica el DataFrame self.group añadiendo las columnas 'Saltar', 'Error' y 'Notificacion'
        para las jurisdicciones que deben saltarse por error de login reciente.
        """
        from sqlalchemy import text
        from obtener_datos_clientes.db import SessionLocal
        from obtener_datos_clientes.models import (
            ClienteJurisdiccion,
            Jurisdiccion,
        )

        # Añadir columnas para marcar jurisdicciones a saltar
        if "Saltar" not in self.group.columns:
            self.group["Saltar"] = False
        if "Error" not in self.group.columns:
            self.group["Error"] = None
        if "Notificacion" not in self.group.columns:
            self.group["Notificacion"] = None

        # Solo continuar si tenemos cliente_id
        if self.cliente_id is None:
            logger.debug("No se puede filtrar por login_error: cliente_id es None")
            return
        
        try:
            with SessionLocal() as db:
                # Obtener todas las jurisdicciones del cliente actual
                for idx, row in self.group.iterrows():
                    jurisdiccion_name = row["Jurisdiccion"]

                    # Obtener IDs de cliente y jurisdicción
                    jurisdiccion = (
                        db.query(Jurisdiccion)
                        .filter(Jurisdiccion.clase == jurisdiccion_name)
                        .first()
                    )

                    if not jurisdiccion:
                        logger.warning(
                            f"No se encontró jurisdicción con clase={jurisdiccion_name}"
                        )
                        continue

                    # Obtener el registro ClienteJurisdiccion
                    cliente_jurisdiccion = (
                        db.query(ClienteJurisdiccion)
                        .filter(
                            ClienteJurisdiccion.cliente_id == self.cliente_id,
                            ClienteJurisdiccion.jurisdiccion_id == jurisdiccion.id,
                        )
                        .first()
                    )

                    if not cliente_jurisdiccion:
                        logger.warning(
                            f"No se encontró relación cliente-jurisdicción para {self.client_folder}-{jurisdiccion_name}"
                        )
                        continue

                    # Verificar si se debe procesar
                    if cliente_jurisdiccion.fecha_login_error is None:
                        # No hay error de login, procesar normalmente
                        continue

                    # Si hay error de login pero se han actualizado las credenciales después (o pasó 1 día),s procesar y resetear error
                    fecha_dt = pd.to_datetime(cliente_jurisdiccion.fecha_login_error)
                    ahora = pd.Timestamp.now(tz='UTC')
                    diff: timedelta = ahora - fecha_dt
                    if (
                        cliente_jurisdiccion.fecha_actualizacion
                        and cliente_jurisdiccion.fecha_login_error
                        < cliente_jurisdiccion.fecha_actualizacion
                        or diff.days >= 1
                    ):
                        # En este caso, resetear fecha_login_error
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
                            logger.warning(
                                f"Error al resetear fecha_login_error: {str(e)}"
                            )

                        continue

                    # Si el error es más reciente que la actualización (y pasó más de un días), marcar para saltar
                    self.group.loc[idx, "Saltar"] = True
                    self.group.loc[idx, "Error"] = "LoginError"
                    self.group.loc[idx, "Notificacion"] = "Credenciales inválidas"
                    logger.info(
                        f"Marcando jurisdicción {jurisdiccion_name} para saltarla por error de login reciente"
                    )

        except Exception as e:
            logger.error(f"Error al filtrar jurisdicciones por login_error: {str(e)}")

    async def procesar_jurisdicciones(self, playwright):
        """
        Procesa todas las jurisdicciones del cliente con un orden específico.
        Respeta las marcas de jurisdicciones que deben saltarse por errores de login recientes.

        Returns:
            Tuple con (instancias, encontradas, no_encontradas, saltadas_por_dependencia, login_error_nacional)
        """
        # Filtrar jurisdicciones con errores de login recientes
        self.filtrar_jurisdicciones_por_login_error()

        jurisdicciones_dependientes = os.getenv(
            "JURISDICCIONES_DEPENDIENTES_NACIONAL", ""
        ).split(",")
        instances = []
        encontradas = []
        no_encontradas = []
        saltadas_por_dependencia = []
        login_error_nacional = None

        # Resultados pre-marcados para jurisdicciones con error de login reciente
        jurisdicciones_con_error_login = []

        # 1. Clasificar las jurisdicciones en distintos grupos
        nacional_instance = None
        jurisdicciones_dependientes_instances = []
        otras_jurisdicciones_instances = []

        for _, row in self.group.iterrows():
            try:
                jurisdiction = row["Jurisdiccion"]

                # Verificar si esta jurisdicción debe saltarse por error de login reciente
                if "Saltar" in row and row["Saltar"]:
                    # Agregar a la lista de jurisdicciones con error pero sin procesarlas
                    jurisdicciones_con_error_login.append(
                        {
                            "nombre": jurisdiction,
                            "notificacion": row["Notificacion"],
                            "screenshot": "No se realizó Screenshot",
                            "error": row["Error"],
                        }
                    )
                    encontradas.append(jurisdiction)
                    continue

                # Procesamiento normal para jurisdicciones sin error de login reciente
                instance = await self.crear_instancia_jurisdiccion(
                    playwright, row, jurisdiction
                )

                # Clasificar según el tipo
                if jurisdiction == "Nacional":
                    nacional_instance = instance
                    encontradas.append(jurisdiction)
                elif jurisdiction in jurisdicciones_dependientes:
                    jurisdicciones_dependientes_instances.append(instance)
                    encontradas.append(jurisdiction)
                else:
                    otras_jurisdicciones_instances.append(instance)
                    encontradas.append(jurisdiction)

            except Exception as e:
                logger.error(f"Error creando instancia {jurisdiction}: {e}")
                no_encontradas.append(jurisdiction)

        # 2. Procesar Nacional primero si existe
        error_nacional = False
        if nacional_instance:
            try:
                result = await nacional_instance.procesar_jurisdiccion()
                instances.append(nacional_instance)

                # Verificar si hubo error que afecta jurisdicciones dependientes
                # NOTA: DelegacionError NO saltea jurisdicciones dependientes
                error_type = result[3]
                if error_type in ["LoginError", "LoginErrorAfip"]:
                    logger.warning(
                        f"Error en Nacional ({error_type}). Filtrando jurisdicciones dependientes."
                    )
                    error_nacional = True
                    login_error_nacional = error_type

            except Exception as e:
                logger.error(f"Error procesando Nacional: {e}")
                error_nacional = True

        # 3. Si hubo error en Nacional, registrar las jurisdicciones dependientes como saltadas
        if error_nacional:
            for instance in jurisdicciones_dependientes_instances:
                encontradas.remove(instance.nombre)
                saltadas_por_dependencia.append((instance, login_error_nacional))
                no_encontradas.append(instance.nombre)
                logger.info(
                    f"Saltando {instance.nombre} debido a error ({login_error_nacional}) en Nacional"
                )
        else:
            instances.extend(jurisdicciones_dependientes_instances)

        # 4. Añadir el resto de jurisdicciones
        instances.extend(otras_jurisdicciones_instances)

        return (
            instances,
            encontradas,
            no_encontradas,
            saltadas_por_dependencia,
            login_error_nacional,
            jurisdicciones_con_error_login,  # Nueva lista de jurisdicciones con error de login reciente
        )

    async def crear_instancia_jurisdiccion(
        self, playwright, row, jurisdiction, retry=False
    ):
        """
        Crea una instancia de la clase jurisdicción especificada.

        Args:
            playwright: Instancia de Playwright
            row: Fila del DataFrame con los datos de la jurisdicción
            jurisdiction: Nombre de la clase de jurisdicción a instanciar
            retry: Indica si es un reintento (default: False)

        Returns:
            Instancia de la jurisdicción
        """
        JurisdictionClass = getattr(jurisdicciones, jurisdiction)

        instancia_visible = os.getenv("MODO_VISIBLE", "False").lower() == "true"
        is_retry = retry if retry is True else instancia_visible
        headless = not is_retry
        if is_retry:
            logger.info(f"Creando instancia de {jurisdiction} en modo visible")

        create_args = {
            "playwright": playwright,
            "cliente": row["Cliente"],
            "client_folder": row["client_folder"],
            "cuit": int(row["Usuario"]),
            "clave_fiscal": row["Password"],
            "fecha_desde": row["fecha_desde"],
            "fecha_hasta": row["fecha_hasta"],
            "cuit_cliente_input": int(row["cuit_cliente"]),
            "headless": headless,
        }

        # Añadir filtro_fce solo para la jurisdicción Nacional
        if jurisdiction == "Nacional" and "filtro_fce" in row:
            create_args["filtro_fce"] = bool(row["filtro_fce"])
            logger.debug(
                f"Aplicando filtro_fce={row['filtro_fce']} para jurisdicción Nacional"
            )

        return await JurisdictionClass.create(**create_args)

    async def ejecutar_jurisdicciones(
        self,
        instances: list[Jurisdiccion],
        saltadas_por_dependencia: Optional[list] = None,
        login_error_nacional: Optional[str] = None,
        jurisdicciones_con_error_login: Optional[list] = None,
    ) -> pd.DataFrame:
        """
        Ejecuta todas las instancias en paralelo y devuelve los resultados en un DataFrame.

        Args:
            instances: Lista de instancias de jurisdicciones a procesar.
            saltadas_por_dependencia: Lista de jurisdicciones saltadas por dependencia.
            login_error_nacional: Error de login en jurisdicción Nacional, si aplica.
            jurisdicciones_con_error_login: Lista de jurisdicciones con errores de login recientes.

        Returns:
            pd.DataFrame: DataFrame con los resultados de la ejecución.
        """
        # Instancias de Nacional ya fueron procesadas, solo procesar el resto
        nacional_results = []
        instancias_a_procesar = []

        for instance in instances:
            if instance.nombre == "Nacional":
                nacional_results.append(
                    (
                        instance.nombre,
                        instance.hay_notificacion,
                        instance.hay_screenshot,
                        login_error_nacional,
                    )
                )
            else:
                instancias_a_procesar.append(instance)

        cantidad_jurisdicciones_concurrentes = int(
            os.getenv("JURISDICCIONES_CONCURRENTES", 5)
        )
        semaforo = asyncio.Semaphore(cantidad_jurisdicciones_concurrentes)

        async def _procesar_con_limite(instance: Jurisdiccion):
            async with semaforo:
                try:
                    return await instance.procesar_jurisdiccion()
                except Exception as e:
                    logger.error(f"Error ejecutando {instance.nombre}: {e}")
                    return (
                        instance.nombre,
                        "Error al procesar jurisdicción",
                        "No se realizó Screenshot",
                        str(type(e).__name__),
                    )

        # Ejecutar las jurisdicciones en paralelo
        resultados = nacional_results

        if instancias_a_procesar:
            resultados_paralelos = await asyncio.gather(
                *[_procesar_con_limite(instance) for instance in instancias_a_procesar]
            )
            resultados.extend(list(resultados_paralelos))

        # Añadir jurisdicciones saltadas por dependencia
        if saltadas_por_dependencia:
            for instance, error_type in saltadas_por_dependencia:
                instance: Jurisdiccion
                # Determinar el mensaje de notificación según el tipo de error
                if error_type == "LoginErrorAfip":
                    from jurisdicciones.jurisdiccion import LoginErrorAfip

                    mensaje_notificacion = LoginErrorAfip.DEFAULT_MESSAGE
                elif error_type == "LoginError":
                    mensaje_notificacion = "Credenciales ARCA inválidas"
                else:
                    # Para otros tipos de error, usar mensaje por defecto
                    mensaje_notificacion = "Credenciales ARCA inválidas"

                resultados.append(
                    (
                        instance.nombre,
                        mensaje_notificacion,
                        "No procesada",
                        error_type,
                    )
                )
                # Cerrar recursos de la instancia saltada
                try:
                    await instance.cerrar_recursos()
                    logger.info(f"Recursos de {instance.nombre} cerrados correctamente")
                except Exception as e:
                    logger.warning(
                        f"Error al cerrar recursos de {instance.nombre}: {e}"
                    )

        # Añadir jurisdicciones con error de login reciente
        if jurisdicciones_con_error_login:
            for jurisdiccion in jurisdicciones_con_error_login:
                resultados.append(
                    (
                        jurisdiccion["nombre"],
                        "Credenciales inválidas",  # Notificación específica
                        jurisdiccion.get("screenshot", "No disponible"),
                        jurisdiccion.get("error", "LoginError"),
                    )
                )

        # Crear el DataFrame final
        df = pd.DataFrame(
            resultados, columns=["Nombre", "Notificacion", "Screenshot", "Error"]
        )

        # Actualizar fecha_login_error para nuevos errores de login
        if self.cliente_id is not None:
            await self.actualizar_fecha_login_error(df)

        return df

    async def actualizar_fecha_login_error(self, df_final: pd.DataFrame) -> None:
        """
        Actualiza el campo fecha_login_error en la tabla ClienteJurisdiccion
        cuando se detectan errores de login, sin modificar fecha_actualizacion.

        Args:
            df_final: DataFrame con los resultados de la ejecución
        """
        from datetime import datetime
        from sqlalchemy import text
        from obtener_datos_clientes.db import SessionLocal
        from obtener_datos_clientes.models import Jurisdiccion

        # Verificar si hay errores de login
        login_errors = df_final[
            df_final["Error"].isin(["LoginError", "LoginErrorAfip"])
            & ~(
                (df_final["Error"] == "LoginError")
                & (df_final["Notificacion"] == LoginError.SERVICIO_NO_DISPONIBLE)
            )
        ]

        if login_errors.empty:
            logger.debug("No se encontraron errores de login para actualizar")
            return

        try:
            with SessionLocal() as db:
                # Para cada jurisdicción con error de login
                for _, row in login_errors.iterrows():
                    jurisdiccion_name = row["Nombre"]

                    # Obtener el ID de la jurisdicción
                    jurisdiccion = (
                        db.query(Jurisdiccion)
                        .filter(Jurisdiccion.clase == jurisdiccion_name)
                        .first()
                    )

                    if not jurisdiccion:
                        logger.warning(
                            f"No se encontró la jurisdicción '{jurisdiccion_name}' en la base de datos"
                        )
                        continue

                    # Usamos SQL directo para evitar que onupdate se active en fecha_actualizacion
                    sql = text("""
                        UPDATE cliente_jurisdiccion
                        SET fecha_login_error = :now
                        WHERE cliente_id = :cliente_id AND jurisdiccion_id = :jurisdiccion_id
                    """)

                    result = db.execute(
                        sql,
                        {
                            "now": datetime.now(),
                            "cliente_id": self.cliente_id,
                            "jurisdiccion_id": jurisdiccion.id,
                        },
                    )
                    db.commit()

                    logger.info(
                        f"Actualizado fecha_login_error para cliente_id={self.cliente_id}, "
                        f"jurisdiccion='{jurisdiccion_name}' (id={jurisdiccion.id}). "
                        f"Filas afectadas: {result.rowcount}"
                    )

        except Exception as e:
            logger.error(f"Error al actualizar fecha_login_error: {str(e)}")
            # No propagamos la excepción para que el flujo principal del programa continúe

    async def reintentar_errores(
        self, playwright, df_final: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Reintenta el procesamiento de jurisdicciones que presentaron errores,
        excluyendo ciertos tipos de error que no deben reintentarse.

        Args:
            playwright: Instancia de Playwright para crear nuevas instancias
            df_final: DataFrame con los resultados del procesamiento inicial

        Returns:
            pd.DataFrame: DataFrame actualizado con los resultados de los reintentos
        """
        errores = df_final[
            (df_final["Error"].notna())
            | (df_final["Screenshot"] != "Se realizó Screenshot")
            | (df_final["Notificacion"] == "La página se encuentra caída")
        ]

        for _, error_row in errores.iterrows():
            jurisdiction = error_row["Nombre"]
            error_type = error_row["Error"]
            notificacion = error_row["Notificacion"]

            # Evitar reintento para ciertos tipos de error
            tipos_error_sin_reintento = [
                "LoginError",
                "LoginErrorAfip",
            ]

            tipos_notificaciones_sin_reintento = [
                "Credenciales inválidas",
            ]

            if error_type in tipos_error_sin_reintento and notificacion in tipos_notificaciones_sin_reintento:
                logger.info(
                    f"Saltando reintento de {jurisdiction} | '{notificacion}' | {error_type}"
                )
                continue

            self.renombrar_screenshots_error(jurisdiction)
            row = self.group[self.group["Jurisdiccion"] == jurisdiction].iloc[0]

            for intento in range(LIMITES_REINTENTO):
                instance: Jurisdiccion = await self.crear_instancia_jurisdiccion(
                    playwright, row, jurisdiction, retry=True
                )
                resultado = await instance.procesar_jurisdiccion()
                logger.debug(
                    f"Resultado del reintento #{intento + 1} para la jurisdicción '{jurisdiction}': {resultado}"
                )
                df_final.loc[df_final["Nombre"] == jurisdiction] = list(resultado)

                # Verificar si se resolvió el error
                if pd.isna(
                    df_final.loc[df_final["Nombre"] == jurisdiction, "Error"]
                ).all():
                    self.eliminar_screenshots_errores(jurisdiction)
                    break

                # Verificar ciertos tipos de error que no deberían reintentarse
                nuevo_error_type = resultado[3]
                if nuevo_error_type in tipos_error_sin_reintento:
                    logger.info(
                        f"Deteniendo reintentos de {jurisdiction} por error de credenciales/delegación: {nuevo_error_type}"
                    )
                    break

                if intento == LIMITES_REINTENTO - 1:
                    # Solo cambiar a "La página se encuentra caída" si NO es DelegacionError
                    current_error = df_final.loc[
                        df_final["Nombre"] == jurisdiction, "Error"
                    ].iloc[0]
                    if current_error != "DelegacionError":
                        df_final.loc[
                            df_final["Nombre"] == jurisdiction, "Notificacion"
                        ] = "La página se encuentra caída"
                        logger.info(
                            f"Jurisdicción {jurisdiction} marcada como 'página caída' después de {LIMITES_REINTENTO} reintentos"
                        )
                    else:
                        logger.info(
                            f"Manteniendo mensaje original de DelegacionError para {jurisdiction}"
                        )

        self.limpiar_screenshots_errores()
        return df_final

    def renombrar_screenshots_error(self, jurisdiction):
        """
        Renombra screenshots existentes agregando sufijo '_error'

        Args:
            jurisdiction (str): Solo renombra screenshots de esta jurisdicción
        """
        try:
            archivos_a_renombrar = glob.glob(
                os.path.join(self.output_folder, f"*{jurisdiction}*.png")
            )
            logger.info(
                f"Renombrando {len(archivos_a_renombrar)} screenshots de {jurisdiction}"
            )

            for file_path in archivos_a_renombrar:
                try:
                    base_name = os.path.basename(file_path)
                    if (
                        "_error" not in base_name
                    ):  # Evitar renombrar archivos ya renombrados
                        new_name = base_name.replace(".png", "_error.png")
                        new_path = os.path.join(self.output_folder, new_name)
                        os.rename(file_path, new_path)
                        logger.info(f"Archivo renombrado: {base_name} -> {new_name}")
                except Exception as e:
                    logger.warning(
                        f"No se pudo renombrar el archivo {os.path.basename(file_path)}: {e}"
                    )
        except Exception as e:
            logger.error(f"Error al renombrar screenshots: {e}")

    def eliminar_screenshots_errores(self, jurisdiction):
        """
        Elimina screenshots que contienen la palabra "error" en cualquier parte del nombre
        filtrando por jurisdicción.

        Args:
            jurisdiction (str): Solo elimina screenshots de esta jurisdicción
        """
        try:
            # Primero obtenemos todos los archivos PNG relacionados con la jurisdicción
            archivos_jurisdiccion = glob.glob(
                os.path.join(self.output_folder, f"*{jurisdiction}*.png")
            )

            # Filtrar solo aquellos que contienen la palabra "error" en cualquier parte del nombre
            archivos_a_eliminar = [
                archivo
                for archivo in archivos_jurisdiccion
                if "error" in os.path.basename(archivo).lower()
            ]

            logger.info(
                f"Eliminando {len(archivos_a_eliminar)} screenshots de error de {jurisdiction}"
            )

            for file_path in archivos_a_eliminar:
                try:
                    os.remove(file_path)
                    logger.info(f"Archivo eliminado: {os.path.basename(file_path)}")
                except Exception as e:
                    logger.warning(
                        f"No se pudo eliminar el archivo {os.path.basename(file_path)}: {e}"
                    )
        except Exception as e:
            logger.error(f"Error al eliminar screenshots: {e}")

    def limpiar_screenshots_errores(self) -> None:
        """
        Elimina screenshots de error cuando existen screenshots correctos para la misma jurisdicción.
        """
        try:
            # Obtener todos los archivos PNG en el directorio de salida
            all_png_files = glob.glob(os.path.join(self.output_folder, "*.png"))

            # Agrupar archivos por jurisdicción
            jurisdicciones = {}
            for file_path in all_png_files:
                file_name = os.path.basename(file_path)
                parts = file_name.split("_")
                if len(parts) >= 2:
                    jurisdiccion = parts[0]
                    if jurisdiccion not in jurisdicciones:
                        jurisdicciones[jurisdiccion] = []
                    jurisdicciones[jurisdiccion].append(file_path)

            # Procesar cada jurisdicción
            for jurisdiccion, files in jurisdicciones.items():
                normal_files = [f for f in files if "_error" not in os.path.basename(f)]
                error_files = [f for f in files if "_error" in os.path.basename(f)]

                # Si hay archivos normales y de error, eliminar los de error
                if normal_files and error_files:
                    logger.info(
                        f"Eliminando {len(error_files)} screenshots de error para {jurisdiccion} porque existen {len(normal_files)} screenshots normales"
                    )
                    for file_path in error_files:
                        try:
                            os.remove(file_path)
                            logger.info(
                                f"Archivo de error eliminado: {os.path.basename(file_path)}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"No se pudo eliminar el archivo {os.path.basename(file_path)}: {e}"
                            )

        except Exception as e:
            logger.error(f"Error al limpiar screenshots de error: {str(e)}")

    def generar_mapas(self, df_final):
        crear_mapa(
            df_final, f"{self.output_folder}/mapa_jurisdicciones_{self.cliente}.png"
        )
        crear_mapa_argentina(
            df_final, f"{self.output_folder}/mapa_nacional_{self.cliente}.png"
        )

    def crear_zip(self) -> tuple[str, str]:
        """
        Crea un archivo ZIP que contiene todas las imágenes PNG y el PDF generado.

        Returns:
            tuple[str, str]: Ruta y nombre del archivo ZIP generado
        """
        try:
            now = datetime.now()
            fecha_actual = now.strftime("%Y%m%d")
            hora_actual = now.strftime("%H%M")
            zip_name = f"{self.cliente}_{fecha_actual}_{hora_actual}.zip"
            zip_path = os.path.join(self.output_folder, zip_name)

            # Obtener archivos PNG
            png_files = glob.glob(os.path.join(self.output_folder, "*.png"))

            # Obtener archivos PDF (también están en self.output_folder)
            pdf_files = glob.glob(os.path.join(self.output_folder, "*.pdf"))

            # Combinar todos los archivos a comprimir
            all_files = png_files + pdf_files

            pass_zip = self.zip_password
            # Comprimir todos los archivos
            pyminizip.compress_multiple(
                all_files,
                [],
                zip_path,
                pass_zip,
                5,  # Nivel de compresión: 1-9 (1 = fastest, 9 = best)
            )

            if not os.path.exists(zip_path):
                logger.error(f"Error al crear el archivo ZIP: {zip_path}")
                self.socio_responsable = CORREO_NOTIFICACION_ERROR
                self.correo_output = []
            else:
                logger.info(f"Archivo ZIP creado correctamente: {zip_path}")
                logger.info(
                    f"Archivos incluidos en el ZIP: {len(all_files)} - {len(png_files)} PNG y {len(pdf_files)} PDF"
                )

            self.zip_path = zip_path
            self.zip_name = zip_name
            return zip_path, zip_name
        except Exception as e:
            logger.error(f"Error al crear el archivo ZIP: {e}")
            self.socio_responsable = CORREO_NOTIFICACION_ERROR
            self.correo_output = []
            return "", ""

    def generar_pdf(self) -> str:
        """
        Genera un PDF con todas las imágenes PNG del directorio de salida.
        Las imágenes se ordenan con prioridad para los mapas.

        Returns:
            str: Ruta al archivo PDF generado
        """
        try:
            fecha_actual = datetime.now().strftime("%d_%m_%Y")
            nombre_pdf = f"NFE_alert_resume_{self.cliente}_{fecha_actual}.pdf"
            archivo_salida = os.path.join(self.output_folder, nombre_pdf)

            # Obtener imágenes PNG ordenadas con prioridad
            imagenes = sorted(
                [
                    archivo
                    for archivo in os.listdir(self.output_folder)
                    if archivo.lower().endswith(".png")
                ],
                key=lambda x: (
                    not x.startswith("mapa_nacional"),  # Prioridad 1: mapa_nacional%
                    not x.startswith(
                        "mapa_jurisdicciones"
                    ),  # Prioridad 2: mapa_jurisdicciones%
                    x,  # Orden alfabético para el resto
                ),
            )

            if not imagenes:
                logger.warning(
                    f"No se encontraron imágenes PNG para generar el PDF en {self.output_folder}"
                )
                return ""

            # Crear PDF con orientación horizontal A4
            pdf = canvas.Canvas(archivo_salida, pagesize=landscape(A4))
            ancho_pagina, alto_pagina = landscape(A4)

            # Texto para el título y subtítulo
            titulo = f"NFE Alert - {self.cliente}"
            subtitulo = f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            pagina_actual = 0  # Contador de páginas

            for nombre in imagenes:
                ruta_imagen = os.path.join(self.output_folder, nombre)
                with Image.open(ruta_imagen) as img:
                    img_ancho, img_alto = img.size

                    # Escala proporcional para ajustar a la página (dejando margen para el título)
                    escala = min(
                        (ancho_pagina - 40) / img_ancho, (alto_pagina - 80) / img_alto
                    )
                    nuevo_ancho = img_ancho * escala
                    nuevo_alto = img_alto * escala

                    # Posición centrada
                    x = (ancho_pagina - nuevo_ancho) / 2
                    y = (alto_pagina - nuevo_alto - 60) / 2  # Ajustar por el título

                    # Agregar título en la parte superior
                    pdf.setFont("Helvetica-Bold", 16)
                    pdf.drawCentredString(ancho_pagina / 2, alto_pagina - 30, titulo)

                    # Agregar nombre de la imagen como subtítulo de la imagen
                    pdf.setFont("Helvetica", 10)
                    nombre_limpio = os.path.splitext(nombre)[0].replace("_", " ")
                    pdf.drawCentredString(
                        ancho_pagina / 2, y + nuevo_alto + 15, nombre_limpio
                    )

                    # Dibujar la imagen
                    pdf.drawImage(ruta_imagen, x, y, nuevo_ancho, nuevo_alto)

                    # Agregar subtítulo con la fecha en el pie de página
                    pdf.setFont("Helvetica", 10)
                    pdf.drawCentredString(ancho_pagina / 2, 20, subtitulo)

                    # Finalizar la página
                    pdf.showPage()

                    pagina_actual += 1

            # Agregar página en blanco si no se ha agregado ninguna página
            if pagina_actual == 0:
                logger.warning(
                    f"No se agregaron páginas al PDF, se generará una página en blanco como placeholder."
                )
                pdf.showPage()

            pdf.save()
            logger.info(f"PDF generado correctamente: {archivo_salida}")
            return archivo_salida
        except Exception as e:
            logger.error(f"Error al generar PDF: {e}")
            return ""

    def evaluar_estado_por_destinatario(self, df_final: pd.DataFrame) -> str:
        """
        Método público para determinar el estado basándose en el destinatario.

        Args:
            df_final: DataFrame con los resultados del procesamiento

        Returns:
            str: Estado del procesamiento ('Correcto' o 'Proceso terminado con errores')
        """
        try:
            # Obtener información sobre el procesamiento
            hay_errores_original = self._hay_errores_en_resultados(df_final)
            es_ultimo_procesamiento = self._es_ultimo_procesamiento()

            # Evaluar errores para la lógica de destinatario
            hay_errores_para_destinatario = self._evaluar_errores_para_destinatario(
                hay_errores_original
            )

            # Determinar destinatario usando la misma lógica que enviar_email
            receptor, _ = self.determinar_destinatario(
                hay_errores_para_destinatario, es_ultimo_procesamiento
            )

            # Si el receptor es el correo de error, marcar como erróneo
            correo_error = os.getenv(
                "CORREO_NOTIFICACION_ERROR", CORREO_NOTIFICACION_ERROR
            )

            if receptor == correo_error:
                return "Proceso terminado con errores"
            else:
                return "Correcto"

        except Exception as e:
            logger.error(f"Error al evaluar estado por destinatario: {e}")
            return "Erróneo"

    def _hay_errores_en_resultados(self, df_final: pd.DataFrame) -> bool:
        """
        Verifica si hay errores técnicos en los resultados del procesamiento.

        Excluye errores de credenciales (LoginError, LoginErrorAfip) y delegación (DelegacionError)
        ya que estos no representan problemas técnicos del sistema sino configuraciones pendientes.

        Args:
            df_final: DataFrame con los resultados del procesamiento.

        Returns:
            bool: True si hay errores técnicos, False en caso contrario.
        """
        # Filtrar las jurisdicciones que están deshabilitadas desde el entorno virtual
        jurisdicciones_deshabilitadas: str = os.getenv(
            "JURISDICCIONES_DESHABILITADAS", ""
        )

        if jurisdicciones_deshabilitadas:
            lista_jurisdicciones_deshabilitadas = jurisdicciones_deshabilitadas.split(
                ","
            )
            df_filtrado = df_final[
                ~df_final["Nombre"].isin(lista_jurisdicciones_deshabilitadas)
            ].copy()
        else:
            df_filtrado = df_final.copy()

        # Tipos de error que NO se consideran como errores técnicos
        errores_excluidos = ["LoginError", "LoginErrorAfip", "DelegacionError"]

        # Filtrar errores que no sean de credenciales/delegación
        errores_tecnicos = df_filtrado[
            df_filtrado["Error"].notna() & ~df_filtrado["Error"].isin(errores_excluidos)
        ]

        # Evaluar si hay errores técnicos
        tiene_errores_tecnicos = len(errores_tecnicos) > 0

        # Log informativo para debugging
        if tiene_errores_tecnicos:
            logger.debug(
                f"Cliente {self.cliente}: Se detectaron {len(errores_tecnicos)} errores técnicos"
            )
        else:
            logger.debug(f"Cliente {self.cliente}: No se detectaron errores técnicos")

        return tiene_errores_tecnicos

    def _es_ultimo_procesamiento(self) -> bool:
        """
        Determina si el procesamiento actual es el último del día.

        Returns:
            bool: True si es el último procesamiento, False en caso contrario.
        """
        ultimo_procesamiento_diario = int(os.getenv("PROCESAMIENTOS_DIARIOS", 5))
        numero_procesamiento = self._obtener_numero_procesamiento()

        # Si no se puede obtener el número por problemas de DB, asumir que es el último
        # Esto es más conservador y asegura que el correo llegue al cliente
        if numero_procesamiento is None:
            logger.warning(
                "No se pudo determinar el número de procesamiento. "
                "Asumiendo que es el último procesamiento para asegurar entrega al cliente."
            )
            return True

        return numero_procesamiento >= ultimo_procesamiento_diario

    def _preparar_dataframe_correo(self, df_final: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara el DataFrame para incluirlo en el correo electrónico.

        Args:
            df_final: DataFrame con los resultados del procesamiento.

        Returns:
            pd.DataFrame: DataFrame formateado para el correo.
        """
        return df_final[["Nombre", "Notificacion", "Screenshot"]].rename(
            columns={
                "Nombre": "Jurisdicción",
                "Notificacion": "Notificaciones",
                "Screenshot": "Screenshot",
            }
        )

    def determinar_destinatario(
        self, hay_errores: bool, es_ultimo_procesamiento: bool
    ) -> tuple[
        Optional[str], Optional[str]
    ]:  # Modificado para que receptor pueda ser Optional[str]
        """
        Determina el destinatario y CC del correo según la lógica de negocio.

        Args:
            hay_errores (bool): Si hubieron errores registrados en df_final
            es_ultimo_procesamiento (bool): Si es el último procesamiento para el cliente

        Returns:
            Tupla con (receptor_email, cc_email)
        """
        # Si hay errores y no es el último procesamiento, enviar al correo de notificación
        if hay_errores and not es_ultimo_procesamiento:
            receptor = os.getenv("CORREO_NOTIFICACION_ERROR", CORREO_NOTIFICACION_ERROR)
            cc = None
            logger.info(
                f"Cliente {self.cliente}: Redirigiendo correo con errores (no es último procesamiento) a {receptor}"
            )
            return receptor, cc

        # Mantener los destinatarios normales
        if not self.correo_output and not self.socio_responsable:
            # Si no hay correos configurados, y no estamos en el caso de error anterior,
            # podría ser un problema de configuración o un caso donde no se deba enviar.
            # Por seguridad, si se llega aquí sin destinatario, se podría enviar a error o loggear severamente.
            # Opcionalmente, devolver None para que enviar_email lo maneje.
            logger.warning(
                f"Cliente {self.cliente}: No se encontró Correo Output ni Socio Responsable. "
                f"Se intentará enviar a CORREO_NOTIFICACION_ERROR como fallback."
            )
            receptor = os.getenv("CORREO_NOTIFICACION_ERROR", CORREO_NOTIFICACION_ERROR)
            cc = None
            # Considerar si este es el comportamiento deseado o si debería lanzar un error.
            # raise ValueError(f"Cliente {self.cliente}: No se encontraron direcciones de correo válidas (Output o Socio).")
        elif self.correo_output:
            receptor = self.correo_output
            cc = self.socio_responsable if self.socio_responsable else None
        elif self.socio_responsable:  # Solo socio, sin correo_output
            receptor = self.socio_responsable
            cc = None
        else:
            # Este caso teóricamente no debería alcanzarse si la lógica anterior es exhaustiva.
            # Pero por si acaso, para asegurar que receptor siempre tenga un valor o se maneje el error.
            logger.error(
                f"Cliente {self.cliente}: Condición inesperada en la determinación de destinatarios."
            )
            receptor = os.getenv("CORREO_NOTIFICACION_ERROR", CORREO_NOTIFICACION_ERROR)
            cc = None

        if receptor:
            logger.info(
                f"Cliente {self.cliente}: Destinatario determinado: {receptor}, CC: {cc}"
            )
        return receptor, cc

    def enviar_email(self, df_final: pd.DataFrame) -> bool:
        """
        Envía un email con los resultados del procesamiento.
        El archivo ZIP contiene tanto las imágenes PNG como el PDF.

        Args:
            df_final: DataFrame con los resultados del procesamiento.

        Returns:
            bool: True si el correo fue enviado correctamente, False en caso contrario.
        """
        try:
            # Obtener información sobre el procesamiento
            hay_errores_original = self._hay_errores_en_resultados(df_final)
            es_ultimo_procesamiento = self._es_ultimo_procesamiento()
            numero_procesamiento = self._obtener_numero_procesamiento()

            # Evaluar errores para la lógica de destinatario
            hay_errores_para_destinatario = self._evaluar_errores_para_destinatario(
                hay_errores_original
            )

            # Preparar el DataFrame para el correo
            df_correo = self._preparar_dataframe_correo(df_final)

            # Determinar destinatario usando la lógica encapsulada
            es_ultimo_procesamiento = True #!!! TODO : SACAR HARDCODEO
            receptor, cc = self.determinar_destinatario(
                hay_errores_para_destinatario, es_ultimo_procesamiento
            )

            if receptor is None:
                logger.error(
                    f"Cliente {self.cliente}: El destinatario del correo es None. "
                    "No se puede enviar el correo."
                )
                return False

            # Log informativo sobre el estado original de errores
            if hay_errores_original:
                logger.info(
                    f"Cliente {self.cliente}: Procesamiento #{numero_procesamiento} "
                    "finalizado con errores."
                )
            else:
                logger.info(
                    f"Cliente {self.cliente}: Procesamiento #{numero_procesamiento} "
                    "finalizado sin errores."
                )

            if not self.zip_path or not os.path.exists(self.zip_path):
                logger.warning(
                    f"Cliente {self.cliente}: Archivo ZIP no encontrado en {self.zip_path} "
                    "o no generado. El correo se intentará enviar sin el adjunto ZIP."
                )

            enviar_correo(
                receptor=receptor,
                cliente=self.cliente,
                cuit=self.cuit_cliente,
                inicio=self.inicio,
                ruta_archivo_adjunto=self.zip_path,
                nombre_archivo_adjunto=self.zip_name,
                df=df_correo,
                ruta_imagen_png=f"{self.output_folder}/mapa_nacional_{self.cliente}.png",
                ruta_imagen_png_2=f"{self.output_folder}/mapa_jurisdicciones_{self.cliente}.png",
                cuerpo_html_plantilla="html/mail_plantilla.html",
                cc=cc,
            )
            logger.info(
                f"Correo enviado para el cliente {self.cliente} a {receptor} (CC: {cc})"
            )
            return True

        except Exception as e:
            logger.error(f"Error al enviar correo: cliente: {self.cliente}, error: {e}")
            return False

    def sort_df_final(self, df_final: pd.DataFrame) -> pd.DataFrame:
        """
        Ordena el DataFrame utilizando los códigos del diccionario jurisdiccion_clases:
        1. Primero Nacional y SICNEA
        2. Luego el resto de jurisdicciones por su código numérico (ej. "901 CABA")

        Args:
            df_final: DataFrame con los resultados a ordenar

        Returns:
            DataFrame ordenado con índice reseteado
        """
        from config import jurisdiccion_clases

        # Crear diccionario inverso: de nombre de clase a código de jurisdicción
        inv_jurisdiccion = {v: k for k, v in jurisdiccion_clases.items()}

        # Crear columna de orden con el código numérico de la jurisdicción
        df_final["orden_codigo"] = df_final["Nombre"].map(inv_jurisdiccion)

        # Crear columna de prioridad (1: Nacional/SICNEA, 2: resto)
        df_final["prioridad"] = 2
        prioridad_1 = ["Nacional", "SICNEA", "Sicnea"]
        df_final.loc[df_final["Nombre"].isin(prioridad_1), "prioridad"] = 1

        # Ordenar primero por prioridad, luego por código de jurisdicción
        df_final = df_final.sort_values(by=["prioridad", "orden_codigo"])

        # Eliminar columnas auxiliares
        df_final = df_final.drop(["orden_codigo", "prioridad"], axis=1).reset_index(
            drop=True
        )

        return df_final

    def obtener_username(self):
        if self.correo_output:
            return self.correo_output
        elif self.socio_responsable:
            return self.socio_responsable
        else:
            return "No definido"

    def registrar_ejecucion(self, proceso, inicio, estado):
        # Verificar si estamos en modo desarrollo
        if os.getenv("GRABAR_EJECUCIONES", "false").lower() == "false":
            logger.info(
                f"Modo desarrollo: Omitiendo registro de ejecución para {self.cliente}"
            )
            return

        # En modo producción, registrar normalmente
        conectar_db(
            proceso=proceso,
            cliente=self.client_folder,
            username=self.obtener_username(),
            inicio_value=inicio,
            estado_value=estado,
            cliente_id=self.cliente_id,
            procesamiento_id=self.procesamiento_id,
        )

    def _obtener_numero_procesamiento(self) -> Optional[int]:
        """
        Obtiene el número de procesamiento a partir del ID.

        Returns:
            int o None: Número de procesamiento o None si no se puede determinar.
        """
        if not self.procesamiento_id:
            return None

        try:
            with SessionLocal() as db:
                procesamiento = (
                    db.query(ProcesamientosDiariosGlobal)
                    .filter(ProcesamientosDiariosGlobal.id == self.procesamiento_id)
                    .first()
                )
                return procesamiento.numero_procesamiento if procesamiento else None
        except Exception as e:
            logger.warning(
                f"Error al obtener número de procesamiento desde DB: {e}. "
                f"Retornando None para usar lógica fallback."
            )
            return None

    def _evaluar_errores_para_destinatario(self, hay_errores_original: bool) -> bool:
        """
        Evalúa si se deben tratar los errores como tal para la determinación del destinatario.

        Para ciertos clientes en la lista CLIENTES_ENVIAR_AUNQUE_ERROR, si hay errores
        pero no es el último procesamiento, se tratará como si no hubiera errores
        para efectos del destinatario del correo.

        Args:
            hay_errores_original: Resultado original de la detección de errores

        Returns:
            bool: True si se deben tratar como errores para destinatario, False en caso contrario
        """
        if (
            hay_errores_original
            and self.client_folder in CLIENTES_ENVIAR_AUNQUE_ERROR_LIST
        ):
            es_ultimo_procesamiento = self._es_ultimo_procesamiento()
            if not es_ultimo_procesamiento:
                logger.info(
                    f"Cliente {self.client_folder} está en la lista CLIENTES_ENVIAR_AUNQUE_ERROR. "
                    f"Como no es el último procesamiento, se tratará como si no hubiera errores para la determinación del destinatario."
                )
                return False

        return hay_errores_original
