import sqlite3
import os
from database import get_session


def create_database():
    # Conectar a la base de datos (se creará si no existe)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Crear la tabla 'clientes'
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY,
        nombre NVARCHAR(255),
        pass NVARCHAR(12),
        fecha_actualizacion_pass DATETIME,
        fecha_vencimiento_pass DATETIME
    )
    ''')



    # Crear la tabla 'usuarios_autorizados'
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios_autorizados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        fecha_autorizacion DATETIME,
    )
    ''')

    # Crear la tabla 'usuario_cliente'
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuario_cliente (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario INTEGER,
        id_cliente INTEGER,
        FOREIGN KEY (id_usuario) REFERENCES usuarios_autorizados(id),
        FOREIGN KEY (id_cliente) REFERENCES clientes(id)
    )
    ''')

    # Confirmar los cambios
    conn.commit()
    conn.close()


def fetch_records_from_sql_server():
    # Conectar a la base de datos SQL Server usando get_session()
    session = get_session()
    conn = session.connection().connection
    cursor = conn.cursor()

    # Obtener registros de la tabla 'clientes'
    cursor.execute('SELECT nombre, pass, fecha_actualizacion_pass FROM clientes')
    clientes = cursor.fetchall()

    # Obtener registros de la tabla 'usuarios_autorizados'
    cursor.execute('SELECT username FROM usuarios_autorizados')
    usuarios_autorizados = cursor.fetchall()

    # Obtener registros de la tabla 'usuario_cliente'
    cursor.execute('SELECT id_cliente, id_usuario  FROM usuario_cliente')
    usuario_cliente = cursor.fetchall()

    conn.close()
    return clientes, usuarios_autorizados, usuario_cliente


def insert_records_into_sqlite(clientes, usuarios_autorizados, usuario_cliente):
    # Conectar a la base de datos SQLite
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Insertar registros en la tabla 'clientes'
    cursor.executemany('INSERT INTO clientes (nombre, pass, fecha_actualizacion_pass) VALUES (?, ?, ?)', clientes)

    # Insertar registros en la tabla 'usuarios_autorizados'
    cursor.executemany('INSERT INTO usuarios_autorizados (username) VALUES (?)', usuarios_autorizados)

    # Insertar registros en la tabla 'usuario_cliente'
    cursor.executemany('INSERT INTO usuario_cliente (id_usuario, id_cliente) VALUES (?, ?)', usuario_cliente)

    # Confirmar los cambios
    conn.commit()
    conn.close()


if __name__ == "__main__":
    # Verificar si la base de datos SQLite existe
    if not os.path.exists('database.db'):
        create_database()
    # create_database()

    clientes, usuarios_autorizados, usuario_cliente = fetch_records_from_sql_server()
    insert_records_into_sqlite(clientes, usuarios_autorizados, usuario_cliente)
