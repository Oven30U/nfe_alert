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


async def main():
    async with async_playwright() as playwright:
        # Crear instancias
        agip = await Agip.create(
            playwright,
            "FACEBOOK ARGENTINA S.R.L",
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

        # Crear tareas para cada método procesar_jurisdiccion
        tareas = [
            asyncio.create_task(instancia.procesar_jurisdiccion())
            for instancia in [
                nacional,
                agip,
                arba,
                mendoza,
                cordoba,
                neuquen,
                rio_negro,
            ]
        ]

        # Utilizar la lista en asyncio.gather
        resultados = await asyncio.gather(*tareas)

        # Convertir resultados de tulpa a lista y en DataFrame
        resultados = [list(res) for res in resultados]
        df = pd.DataFrame(
            resultados, columns=["Nombre", "Notificacion", "Screenshot", "Error"]
        )
        print(df)


if __name__ == "__main__":
    asyncio.run(main())
