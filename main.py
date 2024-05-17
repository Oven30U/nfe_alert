import asyncio
import pandas as pd
from playwright.async_api import async_playwright
from nacional import Nacional
from agip import Agip
from arba import Arba
from mendoza import Mendoza
from cordoba import Cordoba
from neuquen import Neuquen
from rio_negro import RioNegro
from tucuman import Tucuman
from misiones import Misiones
from entre_rios import EntreRios
from jujuy import Jujuy
from chubut import Chubut


async def main():
    async with async_playwright() as playwright:
        # Crear instancias
        agip = await Agip.create(
            playwright,
            "EDGE ARGENTINA S.R.L",
            "20236063586",
            "Bart41051",
            "01052024",
            "30052024",
            "30712132554",
        )
        nacional = await Nacional.create(
            playwright,
            "EDGE ARGENTINA S.R.L",
            "20386165476",
            "Gabriel1994",
            "01/05/2024",
            "30/05/2024",
            "30714604356",
        )
        arba = await Arba.create(
            playwright,
            "EDGE ARGENTINA S.R.L",
            "30714604356",
            "Edge2018",
            "01052024",
            "30052024",
            "30714604356",
        )
        mendoza = await Mendoza.create(
            playwright,
            "EDGE ARGENTINA S.R.L",
            "30714604356",
            "Edge2023",
            "01052024",
            "30052024",
            "30714604356",
        )
        cordoba = await Cordoba.create(
            playwright,
            "EDGE ARGENTINA S.R.L",
            "20386165476",
            "Gabriel1994",
            "01052024",
            "30052024",
            "30714604356",
        )
        neuquen = await Neuquen.create(
            playwright,
            "EDGE ARGENTINA S.R.L",
            "30714604356",
            "Edge2021",
            "01052024",
            "30052024",
            "30714604356",
        )
        rio_negro = await RioNegro.create(
            playwright,
            "EDGE ARGENTINA S.R.L",
            "20386165476",
            "Gabriel1994",
            "01052024",
            "30052024",
            "30714604356",
        )
        tucuman = await Tucuman.create(
            playwright,
            "EDGE ARGENTINA S.R.L",
            "20386165476",
            "Gabriel1994",
            "01052024",
            "30052024",
            "30714604356",
        )
        misiones = await Misiones.create(
            playwright,
            "EDGE ARGENTINA S.R.L",
            "30714604356",
            "Edge2021",
            "01052024",
            "30052024",
            "30714604356",
        )
        entre_rios = await EntreRios.create(
            playwright,
            "EDGE ARGENTINA S.R.L",
            "20386165476",
            "Gabriel1994",
            "01052024",
            "30052024",
            "30714604356",
        )
        jujuy = await Jujuy.create(
            playwright,
            "EDGE ARGENTINA S.R.L",
            "30714604356",
            "Edge2021!",
            "01052024",
            "30052024",
            "30714604356",
        )
        chubut = await Chubut.create(
            playwright,
            "EDGE ARGENTINA S.R.L",
            "30714604356",
            "Edge2023",
            "01052024",
            "30052024",
            "30714604356",
        )

        # Create a dictionary to map names to instances
        instances = {
            "Nacional": nacional,
            "Agip": agip,
            "Arba": arba,
            "Mendoza": mendoza,
            "Cordoba": cordoba,
            "Neuquen": neuquen,
            "RioNegro": rio_negro,
            "Tucuman": tucuman,
            "Misiones": misiones,
            "EntreRios": entre_rios,
            "Jujuy": jujuy,
            "Chubut": chubut,
        }

        # Crear una lista de tareas
        tareas = [instance.procesar_jurisdiccion() for instance in instances.values()]

        # Ejecutar todas las tareas de manera concurrente
        resultados = await asyncio.gather(*tareas)

        # Convertir resultados de tupla a lista y en DataFrame
        resultados = [list(res) for res in resultados]
        df = pd.DataFrame(
            resultados, columns=["Nombre", "Notificacion", "Screenshot", "Error"]
        )

        # Verificar errores y volver a ejecutar si es necesario
        for index, row in df.iterrows():
            if row["Error"] is not None:
                # Obtener la instancia por nombre
                instance = instances[row["Nombre"]]
                # Volver a ejecutar el método
                result = await instance.procesar_jurisdiccion()
                # Actualizar el DataFrame
                df.loc[index] = list(result)

        print(df)


if __name__ == "__main__":
    asyncio.run(main())
