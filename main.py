import asyncio
import pandas as pd
from playwright.async_api import async_playwright
from inputs import obtener_clientes
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
        df_input = obtener_clientes()
        df_input_por_cliente = df_input.groupby("Cliente")

        # Mapea nombre de las instancias
        jurisdiccion_clases = {
            "Nacional": Nacional,
            "AGIP": Agip,
            "ARBA": Arba,
            "Mendoza": Mendoza,
            "Cordoba": Cordoba,
            "Neuquen": Neuquen,
            "Rio Negro": RioNegro,
            "Tucuman": Tucuman,
            "Misiones": Misiones,
            "Entre Rios": EntreRios,
            "Jujuy": Jujuy,
            "Chubut": Chubut,
        }
        for cliente, group in df_input_por_cliente:
            instances = {}
            for index, row in group.iterrows():
                jurisdiction = row["Jurisdiccion"]
                cliente = row["Cliente"]
                usuario = int(row["Usuario"])
                password = row["Password"]
                fecha_desde = row["fecha_desde"].replace("/", "")
                fecha_hasta = row["fecha_hasta"].replace("/", "")
                cuit_cliente = int(row["cuit_cliente"])

                JurisdictionClass = jurisdiccion_clases[jurisdiction]

                # Use the globals() function to get the class by name
                # JurisdictionClass = globals()[jurisdiction]
                instance = await JurisdictionClass.create(
                    playwright,
                    cliente,
                    usuario,
                    password,
                    fecha_desde,
                    fecha_hasta,
                    cuit_cliente,
                )
                instances[jurisdiction] = instance

            # agip = await Agip.create(
            #     playwright,
            #     "EDGE ARGENTINA S.R.L",
            #     "20236063586",
            #     "Bart41051",
            #     "01052024",
            #     "30052024",
            #     "30714604356",
            # )
            # nacional = await Nacional.create(
            #     playwright,
            #     "EDGE ARGENTINA S.R.L",
            #     "20386165476",
            #     "Gabriel1994",
            #     "01/05/2024",
            #     "30/05/2024",
            #     "30714604356",
            # )
            # arba = await Arba.create(
            #     playwright,
            #     "EDGE ARGENTINA S.R.L",
            #     "30714604356",
            #     "Edge2018",
            #     "01052024",
            #     "30052024",
            #     "30714604356",
            # )
            # mendoza = await Mendoza.create(
            #     playwright,
            #     "EDGE ARGENTINA S.R.L",
            #     "30714604356",
            #     "Edge2023",
            #     "01052024",
            #     "30052024",
            #     "30714604356",
            # )
            # cordoba = await Cordoba.create(
            #     playwright,
            #     "EDGE ARGENTINA S.R.L",
            #     "20386165476",
            #     "Gabriel1994",
            #     "01052024",
            #     "30052024",
            #     "30714604356",
            # )
            # neuquen = await Neuquen.create(
            #     playwright,
            #     "EDGE ARGENTINA S.R.L",
            #     "30714604356",
            #     "Edge2021",
            #     "01052024",
            #     "30052024",
            #     "30714604356",
            # )
            # rio_negro = await RioNegro.create(
            #     playwright,
            #     "EDGE ARGENTINA S.R.L",
            #     "20386165476",
            #     "Gabriel1994",
            #     "01052024",
            #     "30052024",
            #     "30714604356",
            # )
            # tucuman = await Tucuman.create(
            #     playwright,
            #     "EDGE ARGENTINA S.R.L",
            #     "20386165476",
            #     "Gabriel1994",
            #     "01052024",
            #     "30052024",
            #     "30714604356",
            # )
            # misiones = await Misiones.create(
            #     playwright,
            #     "EDGE ARGENTINA S.R.L",
            #     "30714604356",
            #     "Edge2021",
            #     "01052024",
            #     "30052024",
            #     "30714604356",
            # )
            # entre_rios = await EntreRios.create(
            #     playwright,
            #     "EDGE ARGENTINA S.R.L",
            #     "20386165476",
            #     "Gabriel1994",
            #     "01052024",
            #     "30052024",
            #     "30714604356",
            # )
            # jujuy = await Jujuy.create(
            #     playwright,
            #     "EDGE ARGENTINA S.R.L",
            #     "30714604356",
            #     "Edge2021!",
            #     "01052024",
            #     "30052024",
            #     "30714604356",
            # )
            # chubut = await Chubut.create(
            #     playwright,
            #     "EDGE ARGENTINA S.R.L",
            #     "30714604356",
            #     "Edge2023",
            #     "01052024",
            #     "30052024",
            #     "30714604356",
            # )

            # # Create a dictionary to map names to instances
            # instances = {
            #     "Nacional": nacional,
            #     "Agip": agip,
            #     "Arba": arba,
            #     "Mendoza": mendoza,
            #     "Cordoba": cordoba,
            #     "Neuquen": neuquen,
            #     "RioNegro": rio_negro,
            #     "Tucuman": tucuman,
            #     "Misiones": misiones,
            #     "EntreRios": entre_rios,
            #     "Jujuy": jujuy,
            #     "Chubut": chubut,
            # }

            # Crear una lista de tareas
            tareas = [
                instance.procesar_jurisdiccion() for instance in instances.values()
            ]

            # Ejecutar todas las tareas de manera concurrente
            resultados = await asyncio.gather(*tareas)

            # Cerrar todas las instancias de navegador
            for instance in instances.values():
                await instance.browser.close()

            # Convertir resultados de tupla a lista y en DataFrame
            resultados = [list(res) for res in resultados]
            df_final_cliente = pd.DataFrame(
                resultados, columns=["Nombre", "Notificacion", "Screenshot", "Error"]
            )

            # Verificar errores y volver a ejecutar si es necesario, hasta 5 veces
            for _ in range(5):
                for index, row in df_final_cliente.iterrows():
                    if row["Error"] is not None:
                        instance = instances[row["Nombre"]]
                        result = await instance.procesar_jurisdiccion()
                        df_final_cliente.loc[index] = list(result)
                if not df_final_cliente["Error"].any():
                    break

            print(f"{cliente} \n {df_final_cliente}")
            # return df


if __name__ == "__main__":
    asyncio.run(main())
