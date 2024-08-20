"""
cliente_system.py

Este módulo define la clase ClienteSystem, que representa a un cliente en el sistema.
Cada cliente tiene atributos como nombre, correo electrónico, personas autorizadas, horario, días de ejecución, hora de inicio y la última verificación.

La clase ClienteSystem tiene los siguientes métodos:
- verificar_ejecucion: Verifica si se debe ejecutar la verificación del cliente.
- actualizar_fecha_verificacion: Actualiza la fecha de la última verificación del cliente en el archivo Excel.
- quitar_input_ejecucion_manual: Mueve los archivos de la carpeta de entrada a la carpeta de destino si el horario del cliente es "Manual".

Este módulo también incluye un bloque de código de prueba que crea un objeto ClienteSystem y verifica si se debe ejecutar la verificación del cliente.
"""

from datetime import datetime, time
import shutil
import os

# from genericpath import isdir
import pandas as pd
import unidecode
import math
import numpy as np

from config import  link_clientes

class ClienteSystem:
    """
    Por cada cliente de System/System-Clientes.xlsx (fila del dataframe) se crea un objeto de esta clase \n
    """

    # link_clientes = "Estructura-robot/System/System-Clientes.xlsx"
    @staticmethod
    def parse_time(time_input):
        if isinstance(time_input, time):
            time_input = time_input.strftime("%H:%M:%S")
        elif not isinstance(time_input, str):
            raise ValueError("Unsupported time input type")

        return datetime.strptime(time_input, "%H:%M:%S").time()

    def __init__(
        self,
        nombre,
        correo_output,
        personas_autorizadas,
        schedule,
        dias_de_ejecucion,
        hora_de_inicio,
        ultima_verificacion,
    ):
        """
        Inicializa un objeto de la clase ClienteSystem.

        Args:
            nombre (str): Nombre del cliente.
            correo_output (str): Correo electrónico para la salida de datos.
            personas_autorizadas (list): Lista de personas autorizadas para acceder a la información del cliente.
            schedule (str): Horario de trabajo del cliente.
            dias_de_ejecucion (list): Días de la semana en los que se ejecutan las tareas.
            hora_de_inicio (str): Hora de inicio de las tareas.
            ultima_verificacion (datetime): Fecha y hora de la última verificación.

        """
        self.nombre = nombre
        self.correo_output = correo_output
        self.personas_autorizadas = personas_autorizadas
        self.schedule = schedule
        self.dias_de_ejecucion = dias_de_ejecucion
        self.hora_de_inicio = self.parse_time(hora_de_inicio)
        self.ultima_verificacion = ultima_verificacion

    def __str__(self):
        """
        Devuelve una representación en cadena de caracteres del objeto ClienteSystem.

        Returns:
            str: Representación en cadena de caracteres del objeto ClienteSystem.
        """
        return f"{self.nombre} - {self.schedule} - {self.dias_de_ejecucion} - {self.hora_de_inicio} - {self.ultima_verificacion}"

    def verificar_ejecucion(self, archivo_input):
        """
        Verifica si se debe ejecutar la verificación del cliente \n
        Si el schedule es Manual, siempre se debe verificar \n\n

        Si el schedule es Automático, se debe verificar sólo si:\n
          El día de la semana actual está en la lista de días de ejecución \n
          La hora actual es mayor a la hora de inicio \n
          La última verificación fue antes de hoy
        """
        try:
            if os.path.exists(archivo_input) and os.listdir(archivo_input):
                if self.schedule == "Manual" or self.ultima_verificacion is None or (
                        isinstance(self.ultima_verificacion, str) and self.ultima_verificacion == '') or (
                        isinstance(self.ultima_verificacion, float) and math.isnan(self.ultima_verificacion)):
                    return True
                elif self.schedule == "Automático":
                    dias_semana = {
                        "monday": "lunes",
                        "tuesday": "martes",
                        "wednesday": "miercoles",
                        "thursday": "jueves",
                        "friday": "viernes",
                        "saturday": "sabado",
                        "sunday": "domingo",
                    }
                    day = datetime.now().strftime("%A").lower()
                    dia = dias_semana.get(day, "dia no encontrado")
                    hora_actual = datetime.strptime(
                        datetime.now().strftime("%H:%M"), "%H:%M"
                    ).time()
                    # hora_de_inicio = datetime.strptime(
                    #     self.hora_de_inicio, "%H:%M:%S"
                    # ).time()
                    hora_de_inicio = self.hora_de_inicio
                    if self.ultima_verificacion is not None and self.ultima_verificacion != '':
                        if isinstance(self.ultima_verificacion, pd.Timestamp):
                            ultima_verificacion = self.ultima_verificacion.to_pydatetime()
                        elif isinstance(self.ultima_verificacion, str):
                            ultima_verificacion = datetime.strptime(self.ultima_verificacion, "%d/%m/%Y %H:%M:%S")
                        else:
                            ultima_verificacion = self.ultima_verificacion

                        if (
                                dia
                                in unidecode.unidecode(self.dias_de_ejecucion.replace(" ", ""))
                                .lower()
                                .split(";")
                                and hora_de_inicio < hora_actual
                                and pd.Timestamp(ultima_verificacion).date()
                                < datetime.strptime(
                            datetime.now().strftime("%d/%m/%Y"), "%d/%m/%Y"
                        ).date()
                        ):
                            return True
                    else:
                        return False
        except Exception as e:
            print(e)
            return False

    def actualizar_fecha_verificacion(self):
        """
        Actualiza la fecha de la última verificación del cliente en el archivo Excel.

        Args:
            link_clientes (str): Ruta del archivo Excel que contiene la información de los clientes.
        """
        # Leer el archivo Excel en un DataFrame
        df_clientes = pd.read_excel(self.link_clientes, sheet_name="System-Clientes")

        # Encontrar la fila donde la columna "Cliente" coincide con self.nombre
        index = df_clientes[df_clientes["Cliente"] == self.nombre].index

        # Actualizar la columna "Última verificación" con la fecha actual
        df_clientes.loc[index, "Última verificación"] = datetime.now().strftime(
            "%d/%m/%Y  %H:%M:%S"
        )

        # Guardar el DataFrame de nuevo en el archivo Excel
        df_clientes.to_excel(self.link_clientes, sheet_name="System-Clientes", index=False)

    def quitar_input_ejecucion_manual(self, path_carpeta_input, path_carpeta_destino):
        """
        Mueve los archivos de la carpeta input dentro de la carpeta del cliente, a la carpeta de destino, si el schedule del cliente es "Manual".

        Args:
            path_carpeta_input (str): Ruta de la carpeta de entrada.
            path_carpeta_destino (str): Ruta de la carpeta de destino.
        """
        if self.schedule == "Manual":
            archivos = os.listdir(path_carpeta_input)
            for archivo in archivos:
                path_archivo_input = os.path.join(path_carpeta_input, archivo)
                nuevo_path_archivo_input = os.path.join(path_carpeta_destino, archivo)
                shutil.move(path_archivo_input, nuevo_path_archivo_input)


if __name__ == "__main__":
    clientesito = ClienteSystem(
        "nombre",
        "correo_output",
        "personas_autorizadas",
        "Automático",
        "lunes; viernes",
        "16:00",
        "18/04/2024",
    )
    if clientesito.verificar_ejecucion():
        print("Se debe verificar")
    else:
        print("No se debe verificar")

    # link_system = "Estructura-robot/System/"
    #
    # link_clientes = f"{link_system}System-Clientes.xlsx"

    df_clientes = pd.read_excel(link_clientes, sheet_name="System-Clientes")

    clientes_si_verificar = []
    clientes_no_verificar = []

    for cliente in df_clientes.iterrows():
        cliente = ClienteSystem(
            cliente[1]["Cliente"],
            cliente[1]["Correo Output"],
            cliente[1]["Personas autorizadas"],
            cliente[1]["Schedule"],
            cliente[1]["Dia/s de ejecución"],
            cliente[1]["Hora de inicio"],
            cliente[1]["Última verificación"],
        )

    # Falta colocar un argumento
        if cliente.verificar_ejecucion():
            clientes_si_verificar.append(cliente.nombre)
            cliente.actualizar_fecha_verificacion(link_clientes)
            print(f"Se actualizó la fecha de verificación de {cliente.nombre}")
        else:
            clientes_no_verificar.append(cliente.nombre)

    print("Clientes a verificar")
    for cliente in clientes_si_verificar:
        print(cliente)

    print("\nClientes no verificar")
    for cliente in clientes_no_verificar:
        print(cliente)
