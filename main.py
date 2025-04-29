import asyncio
import os
from contextlib import contextmanager
from datetime import date, datetime
from typing import Optional, List, Dict

import pandas as pd
from playwright.async_api import async_playwright

from cliente_processor import ClienteProcessor
from conectar_db import conectar_db
from config import jurisdiccion_clases
from database import get_session, get_sqlite_session
from functions.delete_backs import delete_zip_files_in_backup
from inputs import obtener_clientes
from logger import Logger
from models import MonitoreoBots, MonitoreoBotsBackup
from obtener_datos_clientes.db import SessionLocal
from obtener_datos_clientes.obtener_datos_clientes import (
    Cliente,
    ObtenerDatosClientes,
    ProcesamientoGlobalManager,
)

logger = Logger.get_logger()


class ProcesamientoManager:
    """Clase principal para gestionar el procesamiento de clientes."""

    def __init__(self, procesamiento_id: Optional[int] = None):
        self.procesamiento_id = procesamiento_id
        self.procesamiento_global = None
        self.procesamientos_diarios = int(os.getenv("PROCESAMIENTOS_DIARIOS", 3))

    async def run(self) -> None:
        """Ejecuta el procesamiento principal."""
        self.procesamiento_global = ProcesamientoGlobalManager.registrar_procesamiento()
        self.procesamiento_id = (
            self.procesamiento_global.id if self.procesamiento_global else None
        )

        async with async_playwright() as playwright:
            df_input = self.obtener_datos_clientes()
            if df_input.empty:
                logger.info("No se encontraron clientes para procesar.")
                self.registrar_sin_clientes()
                return

            df_por_cliente = df_input.groupby(["client_folder", "Cliente"])
            for cliente_tuple, group in df_por_cliente:
                await self.procesar_cliente(cliente_tuple, group, playwright)

        if self.procesamiento_global:
            ProcesamientoGlobalManager.finalizar_procesamiento(
                self.procesamiento_global, True
            )

        delete_zip_files_in_backup(os.getenv("PATH_ESTRUCTURA_ROBOT"))

    def obtener_datos_clientes(self) -> pd.DataFrame:
        """Obtiene los datos de clientes desde la base de datos o archivo de configuración."""
        if os.getenv("INPUT_DATA_FROM_DB", "false").lower() == "true":
            obtener_datos = ObtenerDatosClientes()
            obtener_datos.run()
            return obtener_datos.data
        else:
            return obtener_clientes(jurisdiccion_clases=jurisdiccion_clases)

    async def procesar_cliente(
        self, cliente_tuple: tuple, group: pd.DataFrame, playwright
    ) -> None:
        """Procesa un cliente específico."""
        cliente = cliente_tuple[0]
        estado = "Erróneo"
        inicio = datetime.now()
        df_final = None

        try:
            cuit_cliente = group["cuit_cliente"].values[0]
            client_folder = group["client_folder"].values[0]
            cliente_id = self.obtener_cliente_id(client_folder)

            processor = ClienteProcessor(
                cliente=cliente,
                group=group,
                cuit_cliente=cuit_cliente,
                inicio=inicio,
                client_folder=client_folder,
                cliente_id=cliente_id,
                procesamiento_id=self.procesamiento_id,
            )
            processor.respaldar_archivos()

            (
                instances,
                encontradas,
                no_encontradas,
                saltadas_por_dependencia,
                login_error_nacional,
                jurisdicciones_con_error_login,
            ) = await self.procesar_jurisdicciones(processor, playwright)
            logger.debug(
                f"Jurisdicciones encontradas: {encontradas}, no encontradas: {no_encontradas}"
            )

            df_final = await self.ejecutar_y_reintentar(
                processor,
                instances,
                saltadas_por_dependencia,
                login_error_nacional,
                playwright,
            )

            if jurisdicciones_con_error_login:
                df_final = self.agregar_errores_login(
                    df_final, jurisdicciones_con_error_login
                )

            df_final = processor.sort_df_final(df_final)

            processor.generar_mapas(df_final)
            processor.crear_zip()

            estado = (
                "Correcto"
                if (
                    df_final["Error"].isna().all()
                    and not df_final["Screenshot"]
                    .str.contains("No se realizó Screenshot")
                    .any()
                )
                else "Proceso terminado con errores"
            )
        except Exception as e:
            logger.error(
                f"Error general en el procesamiento del cliente {cliente}: {e}"
            )
        finally:
            self.finalizar_cliente(processor, df_final, estado, inicio)

    def obtener_cliente_id(self, client_folder: str) -> Optional[int]:
        """Obtiene el ID del cliente desde la base de datos."""
        if os.getenv("INPUT_DATA_FROM_DB", "false").lower() == "true":
            with SessionLocal() as db:
                cliente_record = (
                    db.query(Cliente)
                    .filter(Cliente.client_folder == client_folder)
                    .first()
                )
                return cliente_record.id if cliente_record else None
        return None

    async def procesar_jurisdicciones(
        self, processor: ClienteProcessor, playwright
    ) -> tuple:
        """Procesa las jurisdicciones de un cliente."""
        try:
            return await processor.procesar_jurisdicciones(playwright)
        except Exception as e:
            logger.error(f"Error al procesar jurisdicciones: {e}")
            raise

    async def ejecutar_y_reintentar(
        self,
        processor: ClienteProcessor,
        instances: list,
        saltadas_por_dependencia: list,
        login_error_nacional: Optional[str],
        playwright,
    ) -> pd.DataFrame:
        """Ejecuta las jurisdicciones y realiza reintentos si es necesario."""
        try:
            df_final = await processor.ejecutar_jurisdicciones(
                instances, saltadas_por_dependencia, login_error_nacional
            )
            return await processor.reintentar_errores(playwright, df_final)
        except Exception as e:
            logger.error(f"Error al ejecutar jurisdicciones: {e}")
            raise

    def agregar_errores_login(
        self, df_final: pd.DataFrame, jurisdicciones_con_error_login: List[Dict]
    ) -> pd.DataFrame:
        """Agrega jurisdicciones con errores de login al DataFrame final."""
        df_error_login = pd.DataFrame(jurisdicciones_con_error_login)
        df_error_login.rename(
            columns={
                "nombre": "Nombre",
                "notificacion": "Notificacion",
                "screenshot": "Screenshot",
                "error": "Error",
            },
            inplace=True,
        )
        return pd.concat([df_final, df_error_login], ignore_index=True)

    def finalizar_cliente(
        self,
        processor: ClienteProcessor,
        df_final: Optional[pd.DataFrame],
        estado: str,
        inicio: datetime,
    ) -> None:
        """Finaliza el procesamiento de un cliente."""
        try:
            if df_final is not None:
                processor.enviar_email(df_final)
            processor.registrar_ejecucion(
                proceso=os.getenv("PROYECTO"), inicio=inicio, estado=estado
            )
        except Exception as e:
            logger.error(f"Error al finalizar cliente: {e}")

    def registrar_sin_clientes(self) -> None:
        """Registra que no hay clientes para procesar."""
        if self.procesamiento_id:
            ProcesamientoGlobalManager.finalizar_procesamiento_sin_clientes(
                self.procesamiento_id
            )
            logger.info(
                f"Procesamiento global {self.procesamiento_id} finalizado sin clientes."
            )


if __name__ == "__main__":
    asyncio.run(ProcesamientoManager().run())
