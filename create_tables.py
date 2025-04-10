from sqlalchemy import create_engine
from models import Base, ClienteNFE, JurisdiccionNFE, ClienteJurisdiccionNFE
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


def create_nfe_tables():
    """
    Crea las tablas necesarias en la base de datos NFEAlert.
    """
    # Obtener variables de entorno
    SQLSERVER_DRIVER = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server")
    SQLSERVER_SERVER = os.getenv("SQLSERVER_SERVER")
    SQLSERVER_USERNAME = os.getenv("SQLSERVER_USERNAME")
    SQLSERVER_PASSWORD = os.getenv("SQLSERVER_PASSWORD")
    SQLSERVER_DATABASE = os.getenv("SQLSERVER_DATABASE")

    # Crear cadena de conexión específica para NFEAlert
    connection_string = (
        f"mssql+pyodbc://{SQLSERVER_USERNAME}:{SQLSERVER_PASSWORD}@{SQLSERVER_SERVER}/{SQLSERVER_DATABASE}"
        f"?driver={SQLSERVER_DRIVER}"
    )

    print(f"Conectando a NFEAlert en {SQLSERVER_SERVER}...")
    engine = create_engine(connection_string, fast_executemany=True)

    # Crear solo las tablas específicas
    tables = [
        ClienteNFE.__table__,
        JurisdiccionNFE.__table__,
        ClienteJurisdiccionNFE.__table__,
    ]

    Base.metadata.create_all(engine, tables=tables)
    print("Tablas creadas exitosamente en NFEAlert.")


if __name__ == "__main__":
    create_nfe_tables()
