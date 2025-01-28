##################################################################################
# ...existing code...
class Jurisdiccion(ABC):
    is_afip_enabled = False
    # ...existing code...    # ...existing code...
class Chaco(Jurisdiccion):
    is_afip_enabled = True
    # ...existing code...        # ...existing code...
async def reintentar_errores(self, playwright, df_final):
    errores = df_final[
        (df_final["Error"].notna())
        | (df_final["Screenshot"] == "No se realizó Screenshot")
    ]
    for _, error_row in errores.iterrows():
        jurisdiction = error_row["Nombre"]
        instance = instances.get(jurisdiction)
        if instance and not instance.is_afip_enabled:
            # solo reintentas si no es AFIP
            # ...existing retry logic...
    return df_final


##################################################################################
import asyncio
import pandas as pd
import jurisdicciones

class ClienteProcessor:
    # ...existing code...

    async def ejecutar_jurisdicciones(self, instances):
        tareas = [instance.procesar_jurisdiccion() for instance in instances.values()]
        resultados = await asyncio.gather(*tareas, return_exceptions=True)
        procesados = []
        for instance, result in zip(instances.values(), resultados):
            if isinstance(result, Exception):
                # manejo de LoginError
                if isinstance(result, jurisdicciones.LoginError):
                    procesados.append([instance.nombre, None, None, result])
                else:
                    procesados.append([instance.nombre, None, None, result])
            else:
                # result viene como tuple: (nombre, notificacion, screenshot, error)
                procesados.append(list(result))
        return pd.DataFrame(procesados, columns=["Nombre", "Notificacion", "Screenshot", "Error"])

    async def reintentar_errores(self, playwright, df_final):
        errores = df_final[
            (df_final["Error"].notna())
            | (df_final["Screenshot"] == "No se realizó Screenshot")
        ]
        for _, error_row in errores.iterrows():
            jurisdiction = error_row["Nombre"]
            error = error_row["Error"]
            if isinstance(error, jurisdicciones.LoginError):
                print(f"Skipping retry for {jurisdiction} due to LoginError")
                continue
            # ...existing retry logic...
        return df_final
# ...existing code...


##################################################################################
import asyncio
from is_afip_enabled import is_afip_enabled
from jurisdicciones import LoginError

class ClienteProcessor:
    # ...
    async def ejecutar_jurisdicciones(self, instances):
        # ...existing code...

        # Separate instances based on is_afip_enabled
        afip_instances = [inst for inst in instances.values() if not is_afip_enabled]
        non_afip_instances = [inst for inst in instances.values() if is_afip_enabled]

        # Execute AFIP-dependent group first with a single instance
        if afip_instances:
            try:
                await afip_instances[0].procesar_jurisdiccion()
            except LoginError:
                print("AFIP LoginError encountered. Aborting AFIP-dependent executions.")
                # Optionally handle the error (e.g., log it, notify, etc.)
        
        # Execute the non-AFIP-dependent instances
        if non_afip_instances:
            await asyncio.gather(*(inst.procesar_jurisdiccion() for inst in non_afip_instances))

        # ...existing code...


#################################################################################
afip_instances = [inst for inst in instances.values() if not is_afip_enabled]

afip_instances = [inst for inst in instances.values() if not inst.is_afip_enabled]
non_afip_instances = [inst for inst in instances.values() if inst.is_afip_enabled]

async def ejecutar_jurisdicciones(self, instances):
    # Separar las instancias según is_afip_enabled
    afip_instances = [inst for inst in instances.values() if not inst.is_afip_enabled]
    non_afip_instances = [inst for inst in instances.values() if inst.is_afip_enabled]

    procesados = []

    # Ejecutar el grupo AFIP primero con una única instancia
    if afip_instances:
        try:
            resultado = await afip_instances[0].procesar_jurisdiccion()
            procesados.append(resultado)
        except LoginError as e:
            print("AFIP LoginError encontrado. Abortando ejecuciones dependientes de AFIP.")
            # Manejar el error según sea necesario

    # Si no hubo LoginError, proceder con las demás instancias
    if non_afip_instances:
        resultados = await asyncio.gather(*(inst.procesar_jurisdiccion() for inst in non_afip_instances), return_exceptions=True)
        for inst, result in zip(non_afip_instances, resultados):
            if isinstance(result, Exception):
                if isinstance(result, jurisdicciones.LoginError):
                    procesados.append([inst.nombre, None, None, result])
                else:
                    procesados.append([inst.nombre, None, None, result])
            else:
                procesados.append(list(result))

    return pd.DataFrame(procesados, columns=["Nombre", "Notificacion", "Screenshot", "Error"])