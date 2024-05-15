import asyncio
import pandas as pd
from abc import ABC, abstractmethod

class TareaAbstracta(ABC):
    @abstractmethod
    async def orquestador(self):
        pass

class Tarea1(TareaAbstracta):
    async def orquestador(self):
        try:
            print("Tarea 1 en proceso...")
            await asyncio.sleep(2)
            print("Tarea 1 completada.")
        except Exception as e:
            print(f"Error en Tarea 1: {e}")

class Tarea2(TareaAbstracta):
    async def orquestador(self):
        try:
            print("Tarea 2 en proceso...")
            await asyncio.sleep(2)
            print("Tarea 2 completada.")
        except Exception as e:
            print(f"Error en Tarea 2: {e}")

# Mapeo de nombres de tareas a clases
tareas_map = {
    'tarea_1': Tarea1,
    'tarea_2': Tarea2,
}

async def main():
    # Leer el archivo Excel
    df = pd.read_excel('tareas.xlsx')

    # Obtener la lista de tareas desde el DataFrame
    tareas_nombres = df['Tareas'].tolist()

    # Mapear los nombres de las tareas a las instancias de las clases correspondientes
    # y crear tareas con asyncio.create_task()
    tareas = [asyncio.create_task(tareas_map[nombre]().orquestador()) for nombre in tareas_nombres]

    # Utilizar la lista en asyncio.gather
    await asyncio.gather(*tareas)

if __name__ == '__main__':
    asyncio.run(main())