import os
from time import sleep
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# SQL Server configuration
SQLSERVER_DRIVER = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server")  # Default driver
SQLSERVER_SERVER = os.getenv("SQLSERVER_SERVER")
SQLSERVER_DATABASE = os.getenv("SQLSERVER_DATABASE")
SQLSERVER_USERNAME = os.getenv("SQLSERVER_USERNAME")
SQLSERVER_PASSWORD = os.getenv("SQLSERVER_PASSWORD")

# SQLite configuration
SQLITE_DATABASE_FILE = os.getenv("SQLITE_DATABASE_FILE", "database.db")

# Function to create SQL Server session
def get_session(max_retries=5, delay=3):
    """
    Create and return a SQLAlchemy Session connected to SQL Server with retry logic.
    """
    connection_string = (
        f"mssql+pyodbc://{SQLSERVER_USERNAME}:{SQLSERVER_PASSWORD}@{SQLSERVER_SERVER}/{SQLSERVER_DATABASE}"
        f"?driver={SQLSERVER_DRIVER}"
    )
    engine = create_engine(connection_string, fast_executemany=True, echo=False)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    for attempt in range(1, max_retries + 1):
        try:
            session = SessionLocal()
            print(f"Connected to SQL Server database: {SQLSERVER_DATABASE}")
            return session
        except OperationalError as e:
            print(f"SQL Server connection error #{attempt}: {e}")
            if attempt < max_retries:
                sleep(delay)
            else:
                raise Exception("Failed to connect to SQL Server after multiple attempts.") from e

# Function to create SQLite session
def get_sqlite_session(max_retries=5, delay=3):
    """
    Create and return a SQLAlchemy Session connected to SQLite with retry logic.
    """
    connection_string = f"sqlite:///{SQLITE_DATABASE_FILE}"
    engine = create_engine(connection_string, connect_args={"check_same_thread": False})

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    for attempt in range(1, max_retries + 1):
        try:
            session = SessionLocal()
            print(f"Connected to SQLite database: {SQLITE_DATABASE_FILE}")
            return session
        except OperationalError as e:
            print(f"SQLite connection error #{attempt}: {e}")
            if attempt < max_retries:
                sleep(delay)
            else:
                raise Exception("Failed to connect to SQLite after multiple attempts.") from e

if __name__ == "__main__":
    try:
        # Test SQL Server connection
        session = get_session()
        print("SQL Server session created successfully!")
    
        # Crear un cursor desde la conexión
        cursor = session.connection().connection.cursor()
    
        # Ejecutar la consulta
        cursor.execute("SELECT TOP 1 * FROM usuarios_autorizados")
    
        # Obtener y mostrar los resultados
        results = cursor.fetchall()
        for row in results:
            print(row)
    except Exception as e:
        print(f"Error creating SQL Server session: {e}")
    finally:
        if session:
            session.close()

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
