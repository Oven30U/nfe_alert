"""
Script para crear todas las tablas definidas en los modelos.

Este módulo garantiza que todas las tablas necesarias existan en la base de datos
antes de ejecutar la aplicación principal.
"""

# Importaciones de bibliotecas estándar
import logging
from typing import List, Optional

# Importaciones de bibliotecas de terceros
from sqlalchemy.exc import SQLAlchemyError

# Importaciones locales
from obtener_datos_clientes.db import engine, Base
# Es crucial importar todos los modelos para que SQLAlchemy los conozca
from obtener_datos_clientes.models import (
    Cliente,
    Jurisdiccion,
    ClienteJurisdiccion,
    UsuariosAutorizados,
    UsuarioCliente,
    MonitoreoBots,
    ProcesamientosDiariosGlobal
)

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def verify_models() -> List[str]:
    """
    Verifica que todos los modelos necesarios estén importados.
    
    Returns:
        List[str]: Lista de nombres de los modelos registrados.
    """
    model_names = [table.name for table in Base.metadata.sorted_tables]
    logger.info(f"Modelos encontrados: {model_names}")
    return model_names


def create_tables() -> bool:
    """
    Crea todas las tablas definidas en los modelos si no existen.
    
    Returns:
        bool: True si las tablas se crearon exitosamente, False en caso contrario.
    """
    try:
        logger.info("Iniciando creación de tablas...")
        verify_models()
        
        # Crear todas las tablas definidas en los modelos
        Base.metadata.create_all(bind=engine)
        
        # Verificar que las tablas se crearon correctamente
        tables_created = len(Base.metadata.tables)
        logger.info(f"{tables_created} tablas creadas o verificadas exitosamente!")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error de SQLAlchemy al crear tablas: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error inesperado al crear tablas: {str(e)}")
        return False


def main() -> None:
    """Función principal para ejecutar la creación de tablas."""
    success = create_tables()
    if success:
        logger.info("Estructura de base de datos lista para uso.")
    else:
        logger.critical("No se pudo crear la estructura de base de datos.")


if __name__ == "__main__":
    main()