import asyncio
import glob
import os
import shutil
from datetime import datetime
from typing import Optional

import pandas as pd
import pyminizip

import jurisdicciones
from conectar_db import conectar_db
from config import (
    CORREO_NOTIFICACION_ERROR,
    CORREO_TEST,
    ENVIAR_CORREO_TEST,
    LIMITES_REINTENTO,
)
from logger import Logger
from mail import enviar_correo
from mapa_plot import crear_mapa, crear_mapa_argentina
from obtener_datos_clientes.db import SessionLocal
from obtener_datos_clientes.models import ProcesamientosDiariosGlobal

logger = Logger.get_logger()


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
            Cliente,
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

                    # Si hay error de login pero se han actualizado las credenciales después, procesar y resetear error
                    if (
                        cliente_jurisdiccion.fecha_actualizacion
                        and cliente_jurisdiccion.fecha_login_error
                        < cliente_jurisdiccion.fecha_actualizacion
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

                    # Si el error es más reciente que la actualización, marcar para saltar
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

                # Verificar si hubo error de login
                error_type = result[3]
                if error_type == "LoginError" or error_type == "LoginErrorAfip":
                    logger.warning(
                        "Error de login en Nacional. Filtrando jurisdicciones dependientes."
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
                    f"Saltando {instance.nombre} debido a error de login en Nacional"
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
        return await JurisdictionClass.create(**create_args)

    async def ejecutar_jurisdicciones(
        self,
        instances: list,
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

        async def procesar_con_limite(instance):
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
                *[procesar_con_limite(instance) for instance in instancias_a_procesar]
            )
            resultados.extend(list(resultados_paralelos))

        # Añadir jurisdicciones saltadas por dependencia
        if saltadas_por_dependencia:
            for instance, error_type in saltadas_por_dependencia:
                resultados.append(
                    (
                        instance.nombre,
                        "Credenciales ARCA inválidas",
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
        from obtener_datos_clientes.models import ClienteJurisdiccion, Jurisdiccion

        # Verificar si hay errores de login
        login_errors = df_final[
            df_final["Error"].isin(["LoginError", "LoginErrorAfip"])
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

    async def reintentar_errores(self, playwright, df_final):
        errores = df_final[
            (df_final["Error"].notna())
            | (df_final["Screenshot"] != "Se realizó Screenshot")
            | (df_final["Notificacion"] == "La página se encuentra caída")
        ]
        for _, error_row in errores.iterrows():
            jurisdiction = error_row["Nombre"]
            error_type = error_row["Error"]  # Error ahora contiene el tipo de error

            # Evitar reintento para ciertos tipos de error
            if error_type == "LoginError":
                logger.info(
                    f"Saltando reintento de {jurisdiction} porque es un LoginError"
                )
                continue

            self.renombrar_screenshots_error(jurisdiction)
            row = self.group[self.group["Jurisdiccion"] == jurisdiction].iloc[0]
            for _ in range(LIMITES_REINTENTO):
                instance = await self.crear_instancia_jurisdiccion(
                    playwright, row, jurisdiction, retry=True
                )
                resultado = await instance.procesar_jurisdiccion()
                logger.debug(
                    f"Resultado del reintento para la jurisdicción '{jurisdiction}': {resultado}"
                )
                df_final.loc[df_final["Nombre"] == jurisdiction] = list(resultado)

                # Verificar si se resolvió el error
                if pd.isna(
                    df_final.loc[df_final["Nombre"] == jurisdiction, "Error"]
                ).all():
                    self.eliminar_screenshots_errores(jurisdiction)
                    break

                # Verificar ciertos tipos de error que no deberían reintentarse
                nuevo_error_type = resultado[
                    3
                ]  # El tipo de error después del reintento
                if nuevo_error_type in ["LoginError", "LoginErrorAfip"]:
                    logger.info(
                        f"Deteniendo reintentos de {jurisdiction} por error de credenciales"
                    )
                    break
                if _ == LIMITES_REINTENTO - 1:
                    # Error por default luego de reintentar 5 veces
                    df_final.loc[df_final["Nombre"] == jurisdiction, "Notificacion"] = (
                        "La página se encuentra caída"
                    )
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
        Elimina screenshots de error filtrando por jurisdicción

        Args:
            jurisdiction (str): Solo elimina screenshots de esta jurisdicción
        """
        try:
            archivos_a_eliminar = glob.glob(
                os.path.join(self.output_folder, f"*{jurisdiction}*_error.png")
            )
            logger.info(
                f"Eliminando {len(archivos_a_eliminar)} screenshots de {jurisdiction}"
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

    def generar_mapas(self, df_final):
        crear_mapa(
            df_final, f"{self.output_folder}/mapa_jurisdicciones_{self.cliente}.png"
        )
        crear_mapa_argentina(
            df_final, f"{self.output_folder}/mapa_nacional_{self.cliente}.png"
        )

    def crear_zip(self):
        now = datetime.now()
        fecha_actual = now.strftime("%Y%m%d")
        hora_actual = now.strftime("%H%M")
        zip_name = f"{self.cliente}_{fecha_actual}_{hora_actual}.zip"
        zip_path = os.path.join(self.output_folder, zip_name)
        png_files = glob.glob(os.path.join(self.output_folder, "*.png"))

        pass_zip = self.zip_password
        # Comprime todos los .png en un solo zip
        pyminizip.compress_multiple(
            png_files,
            [],
            zip_path,
            pass_zip,
            5,  # Nivel de compresión: 1-9 (1 = fastest, 9 = best)
        )

        if not os.path.exists(zip_path):
            self.socio_responsable = CORREO_NOTIFICACION_ERROR
            self.correo_output = []

        self.zip_path = zip_path
        self.zip_name = zip_name

    def _hay_errores_en_resultados(self, df_final: pd.DataFrame) -> bool:
        """
        Verifica si hay errores en los resultados del procesamiento.
        
        Args:
            df_final: DataFrame con los resultados del procesamiento.
            
        Returns:
            bool: True si hay errores, False en caso contrario.
        """
        return not df_final["Error"].isna().all()

    def _es_ultimo_procesamiento(self) -> bool:
        """
        Determina si el procesamiento actual es el último del día.
        
        Returns:
            bool: True si es el último procesamiento, False en caso contrario.
        """
        ultimo_procesamiento_diario = int(os.getenv("PROCESAMIENTOS_DIARIOS", 5))
        numero_procesamiento = self._obtener_numero_procesamiento()
        
        return (numero_procesamiento is not None and 
                numero_procesamiento >= ultimo_procesamiento_diario)

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

    def determinar_destinatario(self, df_final: pd.DataFrame) -> tuple[str, Optional[str]]:
        """
        Determina el destinatario y CC del correo según la lógica de negocio.
        
        Args:
            df_final: DataFrame con los resultados del procesamiento.
            
        Returns:
            Tupla con (receptor_email, cc_email)
        """
        hay_errores = self._hay_errores_en_resultados(df_final)
        es_ultimo_procesamiento = self._es_ultimo_procesamiento()
        
        # Si hay errores y no es el último procesamiento, enviar al correo de notificación
        if hay_errores and not es_ultimo_procesamiento:
            receptor = os.getenv("CORREO_NOTIFICACION_ERROR", CORREO_NOTIFICACION_ERROR)
            cc = None
            logger.info(f"Redirigiendo correo con errores a {receptor}")
            return receptor, cc
        
        # Mantener los destinatarios normales
        if not self.correo_output and not self.socio_responsable:
            receptor = os.getenv("CORREO_NOTIFICACION_ERROR", CORREO_NOTIFICACION_ERROR)
            cc = None
        elif self.correo_output:
            receptor = self.correo_output
            cc = self.socio_responsable if self.socio_responsable else None
        elif self.socio_responsable:
            receptor = self.socio_responsable
            cc = None
        else:
            raise ValueError("No valid email address found for sending the zip email.")
            
        return receptor, cc

    def enviar_email(self, df_final: pd.DataFrame) -> bool:
        """
        Envía un email con los resultados del procesamiento.
        
        Args:
            df_final: DataFrame con los resultados del procesamiento.
            
        Returns:
            bool: True si el correo fue enviado correctamente, False en caso contrario.
        """
        try:
            # Obtener información sobre el procesamiento
            hay_errores = self._hay_errores_en_resultados(df_final)
            es_ultimo_procesamiento = self._es_ultimo_procesamiento()
            numero_procesamiento = self._obtener_numero_procesamiento()
            
            # Preparar el DataFrame para el correo
            df_correo = self._preparar_dataframe_correo(df_final)
            
            # Determinar destinatario usando la lógica encapsulada
            receptor, cc = self.determinar_destinatario(df_final)
            
            if receptor is None:
                raise ValueError("Receptor email address is None. Cannot send zip email.")
                
            if hay_errores and not es_ultimo_procesamiento:
                logger.info(f"(Hubo errores en el procesamiento #{numero_procesamiento}) de {self.cliente} \n cambio a receptor a: {receptor}")

            # Enviar correo
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
            
        with SessionLocal() as db:
            procesamiento = (
                db.query(ProcesamientosDiariosGlobal)
                .filter(ProcesamientosDiariosGlobal.id == self.procesamiento_id)
                .first()
            )
            return procesamiento.numero_procesamiento if procesamiento else None
