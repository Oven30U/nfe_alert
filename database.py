import os
from time import sleep
import pyodbc
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import sqlite3
from sqlite3 import Error

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Leer las variables de entorno para SQL Server
SERVER = os.getenv("SERVER")
DATABASE = os.getenv("DATABASE")
USERNAME = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
DRIVER = os.getenv("DRIVER")

# Leer las variables de entorno para SQLite
DATABASE_SQLITE = os.getenv("SQLITE_DATABASE")


# Función para obtener una nueva sesión con lógica de reintento para SQL Server
def get_session(max_reintentos=25, delay=3):
    connection_string = (
        f"Driver={DRIVER};"
        f"Server={SERVER};"
        f"Database={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD};"
    )

    for i in range(max_reintentos):
        try:
            conn = pyodbc.connect(connection_string)
            engine = create_engine('mssql+pyodbc://', creator=lambda: conn)
            Session = sessionmaker(bind=engine)
            session = Session()
            return session
        except OperationalError as e:
            print(f"Connection error num {i + 1}: {e}")
            if i < max_reintentos - 1:
                sleep(delay)
            else:
                print("Error: Could not connect to the database after several attempts.")
                return None


# Función para obtener una nueva sesión con lógica de reintento para SQLite
def get_sqlite_session(db_file=DATABASE_SQLITE, max_retries=25, delay=3):
    """Create a database connection to an SQLite database with retry logic."""
    conn = None
    for i in range(max_retries):
        try:
            conn = sqlite3.connect(db_file)
            print(f"Connected to SQLite database: {db_file}")
            return conn
        except Error as e:
            print(f"Connection error num {i + 1}: {e}")
            if i < max_retries - 1:
                sleep(delay)
            else:
                raise Exception("Error: Could not connect to the SQLite database after several attempts.")
    return conn


if __name__ == "__main__":
    # try:
    #     # Test SQL Server connection
    #     session = get_session()
    #     print("SQL Server session created successfully!")
    #
    #     # Crear un cursor desde la conexión
    #     cursor = session.connection().connection.cursor()
    #
    #     # Ejecutar la consulta
    #     cursor.execute("SELECT TOP 1 * FROM usuarios_autorizados")
    #
    #     # Obtener y mostrar los resultados
    #     results = cursor.fetchall()
    #     for row in results:
    #         print(row)
    # except Exception as e:
    #     print(f"Error creating SQL Server session: {e}")
    # finally:
    #     if session:
    #         session.close()

    try:
        # Test SQLite connection
        connection = get_sqlite_session()
        print("SQLite session created successfully!")

        # Create a cursor from the connection
        cursor = connection.cursor()

        # Execute a query
        cursor.execute("SELECT * FROM usuarios_autorizados LIMIT 1")

        # Fetch and display the results
        results = cursor.fetchall()
        for row in results:
            print(row)
    except Exception as e:
        print(f"Error creating SQLite session: {e}")
    finally:
        if connection:
            connection.close()
