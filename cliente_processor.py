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
    PATH_ESTRUCTURA_ROBOT,
    jurisdiccion_clases,
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
    ):
        self.cliente: str = cliente
        self.client_folder = client_folder
        self.group: pd.DataFrame = group
        self.cuit_cliente: str = cuit_cliente
        self.inicio: datetime = inicio
        self.client_folder: str = client_folder
        self.output_folder, self.backup_folder = self.preparar_directorios()
        self.correo_output: str = self.obtener_correo()
        self.socio_responsable: str = self.obtener_socio()
        self.zip_path: str = None
        self.zip_name: str = None

        # Extraer la contraseña del grupo
        if "ZIP_Password" in group.columns:
            self.zip_password = group["ZIP_Password"].iloc[0]
        else:
            # Valor por defecto si no existe en el Excel
            self.zip_password = client_folder[:8].replace(" ", "") + "Tax"

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
        instances = {}
        encontradas = []
        no_encontradas = []

        for _, row in self.group.iterrows():
            jurisdiction = row["Jurisdiccion"]
            if not hasattr(jurisdicciones, jurisdiction):
                no_encontradas.append(jurisdiction)
                continue
            encontradas.append(jurisdiction)
            instance = await self.crear_instancia_jurisdiccion(
                playwright, row, jurisdiction, retry=False
            )
            instances[jurisdiction] = instance
        return instances, encontradas, no_encontradas

    async def crear_instancia_jurisdiccion(
        self, playwright, row, jurisdiction, retry=False
    ):
        JurisdictionClass = getattr(jurisdicciones, jurisdiction)
        create_args = {
            "playwright": playwright,
            "cliente": row["Cliente"],
            "client_folder": row["client_folder"],
            "cuit": int(row["Usuario"]),
            "clave_fiscal": row["Password"],
            "fecha_desde": row["fecha_desde"],
            "fecha_hasta": row["fecha_hasta"],
            "cuit_cliente_input": int(row["cuit_cliente"]),
            "headless": not retry,  #! TODO colocar True para producción
        }
        return await JurisdictionClass.create(**create_args)

    async def ejecutar_jurisdicciones(self, instances):
        tareas = [instance.procesar_jurisdiccion() for instance in instances.values()]
        resultados = await asyncio.gather(*tareas)
        resultados = [list(res) for res in resultados]
        return pd.DataFrame(
            resultados, columns=["Nombre", "Notificacion", "Screenshot", "Error"]
        )

    async def reintentar_errores(self, playwright, df_final):
        errores = df_final[
            (df_final["Error"].notna())
            | (df_final["Screenshot"] == "No se realizó Screenshot")
        ]
        for _, error_row in errores.iterrows():
            jurisdiction = error_row["Nombre"]
            # ToDo no reintentar LoginError + identificar los de ARCA
            # error = error_row["Error"]

            # if isinstance(error, jurisdicciones.LoginError):
            #     print(f"Skipping retry for {jurisdiction} due to LoginError")
            #     continue

            row = self.group[self.group["Jurisdiccion"] == jurisdiction].iloc[0]
            for _ in range(LIMITES_REINTENTO):
                instance = await self.crear_instancia_jurisdiccion(
                    playwright, row, jurisdiction, retry=True
                )
                resultado = await instance.procesar_jurisdiccion()
                df_final.loc[df_final["Nombre"] == jurisdiction] = list(resultado)
                if pd.isna(
                    df_final.loc[df_final["Nombre"] == jurisdiction, "Error"]
                ).all():
                    break
                if _ == LIMITES_REINTENTO - 1:
                    # Error por default luego de reintentar 5 veces
                    df_final.loc[df_final["Nombre"] == jurisdiction, "Notificacion"] = (
                        "La página se encuentra caída"
                    )
        return df_final

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

    def obtener_username(self):
        if self.correo_output:
            return self.correo_output
        elif self.socio_responsable:
            return self.socio_responsable
        else:
            return "No definido"

    def registrar_ejecucion(self, proceso, inicio, estado):
        conectar_db(
            proceso=proceso,
            cliente=self.client_folder,
            username=self.obtener_username(),
            inicio_value=inicio,
            estado_value=estado,
        )
