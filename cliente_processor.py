import asyncio
import glob
import os
import shutil
from datetime import datetime

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

    async def procesar_jurisdicciones(self, playwright):
        """
        Procesa todas las jurisdicciones del cliente con un orden específico.

        Returns:
            Tuple con (instancias, encontradas, no_encontradas)
        """
        jurisdicciones_dependientes = os.getenv(
            "JURISDICCIONES_DEPENDIENTES_NACIONAL", ""
        ).split(",")
        instances = []
        encontradas = []
        no_encontradas = []
        saltadas_por_dependencia = []  # ← Nueva lista para jurisdicciones saltadas
        login_error_nacional = None  # ← Guardar el tipo de error específico

        # 1. Clasificar las jurisdicciones en 3 grupos: Nacional, dependientes, y otras
        nacional_instance = None
        jurisdicciones_dependientes_instances = []
        otras_jurisdicciones_instances = []

        for _, row in self.group.iterrows():
            try:
                jurisdiction = row["Jurisdiccion"]
                # Intentar crear la instancia
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
                error_type = result[3]  # El tipo de error está en la posición 3
                if error_type == "LoginError" or error_type == "LoginErrorAfip":
                    logger.warning(
                        "Error de login en Nacional. Filtrando jurisdicciones dependientes."
                    )
                    error_nacional = True
                    login_error_nacional = (
                        error_type  # ← Guardar el tipo exacto de error
                    )

            except Exception as e:
                logger.error(f"Error procesando Nacional: {e}")
                error_nacional = True

        # 3. Si hubo error en Nacional, registrar las jurisdicciones dependientes como saltadas
        if error_nacional:
            for instance in jurisdicciones_dependientes_instances:
                encontradas.remove(instance.nombre)
                saltadas_por_dependencia.append(
                    (instance, login_error_nacional)
                )  # ← Guardar la instancia y el tipo
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
        self, instances, saltadas_por_dependencia=None, login_error_nacional=None
    ):
        """Ejecuta todas las instancias en paralelo y devuelve los resultados en un DataFrame."""
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
                        login_error_nacional,  # Usar el error real de login si existe
                    )
                )
            else:
                instancias_a_procesar.append(instance)

        cantidad_jurisdicciones_concurrentes = int(os.getenv("JURISDICCIONES_CONCURRENTES", 5))
        semaforo = asyncio.Semaphore(
            cantidad_jurisdicciones_concurrentes
        )

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

        df = pd.DataFrame(
            resultados, columns=["Nombre", "Notificacion", "Screenshot", "Error"]
        )
        return df

    async def reintentar_errores(self, playwright, df_final):
        errores = df_final[
            (df_final["Error"].notna())
            | (df_final["Screenshot"] != "Se realizó Screenshot")
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

    def enviar_email(self, df_final):
        try:
            df_correo = df_final[["Nombre", "Notificacion", "Screenshot"]].rename(
                columns={
                    "Nombre": "Jurisdicción",
                    "Notificacion": "Notificaciones",
                    "Screenshot": "Screenshot",
                }
            )

            if not self.correo_output and not self.socio_responsable:
                receptor = CORREO_NOTIFICACION_ERROR
                cc = None
            elif self.correo_output:
                receptor = self.correo_output
                cc = self.socio_responsable if self.socio_responsable else None
            elif self.socio_responsable:
                receptor = self.socio_responsable
                cc = None
            else:
                raise ValueError(
                    "No valid email address found for sending the zip email."
                )

            if receptor is None:
                raise ValueError(
                    "Receptor email address is None. Cannot send zip email."
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
            return True
        except Exception as e:
            logger.error(
                f"Error al enviar correo: receptor:{receptor} cliente: {self.cliente}"
            )
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
        if os.getenv("DEV_MODE", "False").lower() == "true":
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
            procesamiento_id=self.procesamiento_id
        )
