import asyncio
import os
import time
from datetime import datetime
from typing import Optional, List, Dict

import pandas as pd
from playwright.async_api import async_playwright

from cliente_processor import ClienteProcessor
from config import jurisdiccion_clases
from functions.delete_backs import delete_zip_files_in_backup
from inputs import obtener_clientes
from logger import Logger
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
        self.sin_clientes = False  # Flag para controlar el bucle
        self.intervalo_espera = (
            int(os.getenv("INTERVALO_ESPERA_MINUTOS", 30)) * 60
        )  # segundos

    async def run(self) -> None:
        """Ejecuta el procesamiento principal."""
        self.procesamiento_global = ProcesamientoGlobalManager.registrar_procesamiento()
        self.procesamiento_id = (
            self.procesamiento_global.id if self.procesamiento_global else None
        )

        async with async_playwright() as playwright:
            df_input = self.obtener_datos_clientes()
            if df_input is None or df_input.empty:
                logger.info("No se encontraron clientes para procesar.")
                # Solo establecer sin_clientes si es un DataFrame vacío, no si hay error de DB
                if df_input is not None and df_input.empty:
                    self.sin_clientes = True
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

    def obtener_datos_clientes(self) -> Optional[pd.DataFrame]:
        """Obtiene los datos de clientes desde la base de datos o archivo de configuración."""
        try:
            if os.getenv("INPUT_DATA_FROM_DB", "false").lower() == "true":
                obtener_datos = ObtenerDatosClientes()
                obtener_datos.run()
                return obtener_datos.data
            else:
                return obtener_clientes(jurisdiccion_clases=jurisdiccion_clases)
        except Exception as e:
            logger.error(f"Error al obtener datos de clientes: {e}")
            return None

    async def procesar_cliente(
        self, cliente_tuple: tuple, group: pd.DataFrame, playwright
    ) -> None:
        """Procesa un cliente específico."""
        cliente = cliente_tuple[0]
        logger.info(f"Procesando cliente {cliente}")
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
            # Generar PDF después de mapas y antes de ZIP
            pdf_path = processor.generar_pdf()
            if pdf_path:
                processor.pdf_path = pdf_path  # Guardar la ruta para usar en el correo

            processor.crear_zip()

            # Determinar estado basado en el destinatario del correo
            estado = self._determinar_estado_por_destinatario(processor, df_final)

        except Exception as e:
            logger.error(
                f"Error general en el procesamiento del cliente {cliente}: {e}"
            )
        finally:
            self.finalizar_cliente(processor, df_final, estado, inicio)

    def obtener_cliente_id(self, client_folder: str) -> Optional[int]:
        """Obtiene el ID del cliente desde la base de datos."""
        try:
            if os.getenv("INPUT_DATA_FROM_DB", "false").lower() == "true":
                with SessionLocal() as db:
                    cliente_record = (
                        db.query(Cliente)
                        .filter(Cliente.client_folder == client_folder)
                        .first()
                    )
                    return cliente_record.id if cliente_record else None
            return None
        except Exception as e:
            logger.error(f"Error al obtener cliente_id para {client_folder}: {e}")
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

    def _determinar_estado_por_destinatario(
        self, processor: ClienteProcessor, df_final: pd.DataFrame
    ) -> str:
        """
        Determina el estado del procesamiento basándose en el destinatario del correo.

        Args:
            processor: Instancia del procesador del cliente
            df_final: DataFrame con los resultados del procesamiento

        Returns:
            str: Estado del procesamiento ('Correcto' o 'Proceso terminado con errores')
        """
        try:
            return processor.evaluar_estado_por_destinatario(df_final)
        except Exception as e:
            logger.error(f"Error al determinar estado por destinatario: {e}")
            return "Erróneo"

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
        """Registra que no hay clientes para procesar y establece el flag para detener el bucle."""
        # NO establecer sin_clientes = True aquí para errores de DB
        # Solo establecer el flag cuando realmente no hay clientes para procesar

        try:
            if self.procesamiento_id:
                ProcesamientoGlobalManager.finalizar_procesamiento_sin_clientes(
                    self.procesamiento_id
                )
                logger.info(
                    f"Procesamiento global {self.procesamiento_id} | diario {self.procesamientos_diarios} finalizado sin clientes."
                )
        except Exception as e:
            logger.error(f"Error al registrar procesamiento sin clientes: {e}")
            # No propagar la excepción para que el bucle continuo no se detenga

    def verificar_fin_procesamiento(self) -> bool:
        """
        Verifica si se debe finalizar el procesamiento continuo.

        Returns:
            bool: True si se debe detener el procesamiento continuo
        """
        try:
            # Aquí puedes agregar lógica específica para determinar
            # cuándo realmente no hay más clientes para procesar
            # Por ejemplo, consultar directamente la DB o verificar condiciones específicas

            if os.getenv("INPUT_DATA_FROM_DB", "false").lower() == "true":
                # Lógica específica para base de datos
                with SessionLocal() as db:
                    # Verificar si hay clientes pendientes
                    clientes_pendientes = (
                        db.query(Cliente)
                        .filter(
                            # Agregar aquí las condiciones específicas para clientes pendientes
                            Cliente.id.isnot(None)  # Ejemplo básico
                        )
                        .count()
                    )
                    return clientes_pendientes == 0
            else:
                # Para archivos de configuración, verificar si hay datos
                df_clientes = obtener_clientes(jurisdiccion_clases=jurisdiccion_clases)
                return df_clientes is None or df_clientes.empty

        except Exception as e:
            logger.error(f"Error al verificar fin de procesamiento: {e}")
            # En caso de error, continuar procesando (no detener)
            return False

    async def run_continuous(self) -> None:
        """Ejecuta el procesamiento de forma continua hasta que no haya clientes."""
        logger.info("Iniciando procesamiento continuo...")

        while not self.sin_clientes:
            try:
                logger.info("Iniciando nueva iteración de procesamiento...")
                await self.run()

                if not self.sin_clientes:
                    logger.info(
                        f"Esperando {self.intervalo_espera // 60} minutos antes de la siguiente iteración..."
                    )
                    await asyncio.sleep(self.intervalo_espera)
                else:
                    logger.info(
                        "No hay más clientes para procesar. Finalizando procesamiento continuo."
                    )

            except Exception as e:
                logger.error(f"Error en el procesamiento continuo: {e}")
                logger.info(
                    f"Esperando {self.intervalo_espera // 60} minutos antes de reintentar..."
                )
                await asyncio.sleep(self.intervalo_espera)


async def main() -> None:
    """Función principal que ejecuta el procesamiento continuo."""
    modo_continuo = os.getenv("MODO_CONTINUO", "false").lower() == "true"

    manager = ProcesamientoManager()

    if modo_continuo:
        await manager.run_continuous()
    else:
        await manager.run()


if __name__ == "__main__":
    asyncio.run(main())
