import os
from time import sleep
import pyodbc
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Leer las variables de entorno
SERVER = os.getenv("SERVER")
DATABASE = os.getenv("DATABASE")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
DRIVER = os.getenv("DRIVER")

# Función para obtener una nueva sesión con lógica de reintento
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
                raise Exception("Error: Could not connect to the database after several attempts.")

if __name__ == "__main__":
    try:
        session = get_session()
        print("Session created successfully!")

        # Crear un cursor desde la conexión
        cursor = session.connection().connection.cursor()

        # Ejecutar la consulta
        cursor.execute("SELECT TOP 1 * FROM usuarios_autorizados")

        # Obtener y mostrar los resultados
        results = cursor.fetchall()
        for row in results:
            print(row)
    except Exception as e:
        print(f"Error creating session: {e}")
    finally:
        session.close()