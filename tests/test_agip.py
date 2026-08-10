import asyncio
import os
import sys

# Ensure project root is on sys.path so we can import test_manuales reliably
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from test_manuales import agip_test

# Lista de clientes para pruebas en lote. Cada entrada es una tupla con:
# (nombre_cliente, carpeta_cliente, cuit_cliente, usuario_afip, clave_fiscal)
# Completar esta lista con los clientes que se deseen probar.
USERS: list[tuple[str, str, str, str, str]] = [
    ("ABBVIE S.A.", "ABBVIE S.A", "30712399623", "27258767115", "Abbvie2020"),
    ("ADIDAS ARGENTINA S.A.", "ADIDAS ARGENTINA S.A - PROVINCIALES", "30685140221", "27181301126", "Junin1557"),
    ("BIOGEN ARGENTINA S.R.L.", "BIOGEN ARGENTINA S.R.L", "30709724912", "27202819759", "mitre231"),
    ("BIOMARIN ARGENTINA SRL", "BIOMARIN ARGENTINA S.R.L", "30710215800", "20373757676", "Homero1994!"),
    ("EDGE ARGENTINA S.R.L", "EDGE ARGENTINA S.R.L", "30714604356", "20236063586", "Bart41051"),
    ("EUROP ASSISTANCE ARGENTINA S.A", "EUROP ASSISTANCE ARGENTINA S.A", "30691216361", "20353617770", "DeloittE123,"),
    ("FACEBOOK ARGENTINA S.R.L", "FACEBOOK ARGENTINA S.R.L", "30712132554", "20236063586", "Bart41051"),
    ("Gas Link S.A.", "GAS LINK S.A", "30707567607", "23381628124", "Bchaves-2025"),
    ("JANSSEN CILAG FARMACEUTICA SOCIEDAD ANONIMA", "JANSSEN CILAG FARMACEUTICA S.A", "30598129246", "27338956091", "JNJ.2023"),
    ("JOHNSON & JOHNSON MEDICAL SOCIEDAD ANONIMA", "JOHNSON & JOHNSON MEDICAL S.A", "30598498500", "27338956091", "JNJ.2023"),
    ("MAGNETI MARELLI CONJ.DE ESCAPE S.A", "MAGNETI MARELLI CONJ.DE ESCAPE S.A", "30707570144", "20041476142", "bach2018"),
    ("MAGNETI MARELLI REPUESTOS S.A", "MAGNETI MARELLI REPUESTOS S.A", "30707570136", "20041476142", "bach2018"),
    ("PFIZER S.R.L.", "PFIZER S.R.L - PROVINCIALES", "30503518518", "27314236365", "Italia2024."),
    ("Spotify Argentina S.A.", "SPOTIFY ARGENTINA S.A", "30717579360", "20350715801", "Estudio000."),
    ("TELCOSUR S.A.", "TELCOSUR S.A", "30698406344", "23381628124", "Bchaves-2025"),
    ("THE BRITISH COUNCIL", "THE BRITISH COUNCIL", "30714349135", "27236083271", "maru0231"),
    ("Transportadora de Gas del Sur S.A.", "TRANSPORTADORA DE GAS DEL SUR S.A", "30657862068", "23381628124", "Bchaves-2025"),
    ("ULTRAGENYX ARGENTINA S.R.L", "ULTRAGENYX ARGENTINA S.R.L", "30715629611", "23206361859", "julio950"),
    ("VERIZON ARGENTINA S.R.L.", "VERIZON ARGENTINA S.R.L", "30702022165", "20350715801", "Estudio000."),
    ("GARPA S.A.", "GARPA S.A", "30716589575", "20408964823", "Vader66."),
    ("WeWork Argentina S.R.L.", "WeWork Argentina S.R.L", "30715334255", "20373757676", "Homero1994!"),
    ("DÓLAR APP MEXICO S.E.", "Dolar App Mexico S.E.", "30719102758", "20408964823", "Vader66."),
    ("DA INV SA", "DA INV SA", "30719237785", "20408964823", "Vader66."),
    ("Lear de Argentina S.R.L", "Lear Argentina S.R.L", "30680622317", "27314236365", "Italia2024."),
    ("Akamai Technologies Argentina SRL", "Akamai Technologies Argentina SRL", "30716198355", "20408964823", "Vader66."),
    ("Qualtrics de Argentina SRL", "Qualtrics de Argentina SRL", "33717582689", "20408964823", "Vader66."),
    ("INLAND SERVICES ARGENTINA S.A.", "INLAND SERVICES ARGENTINA S.A", "30677737545", "27237030163", "bauti2007"),
    ("MAERSK LINE ARGENTINA S.A.", "MAERSK LINE ARGENTINA S.A", "30688415531", "27237030163", "bauti2007"),
    ("HP INC ARGENTINA SRL", "HP INC ARGENTINA SRL", "30714809373", "20353617770", "DeloittE123,"),
]


async def agip_batch_test(
    headless: bool = False,
    iterations: int = 1,
    enable_tracing: bool = True,
    trace_dir: str = "traces",
):
    """
    Ejecuta `agip_test` para una lista explícita de clientes.

    Para cada entrada establece las variables de entorno que usa
    `generic_test` (TEST_AGIP_*) y llama a `agip_test`.

    Esta función permite probar en lote los clientes proporcionados por el
    equipo sin depender de la base de datos.
    """
    for nombre, client_folder, cuit, usuario, clave in USERS:
        # Configurar variables de entorno utilizadas por generic_test
        os.environ["TEST_AGIP_CLIENT"] = nombre 
        os.environ["TEST_AGIP_CLIENT_FOLDER"] = client_folder
        os.environ["TEST_AGIP_CUIT"] = usuario
        os.environ["TEST_AGIP_CLAVE_FISCAL"] = clave
        os.environ["TEST_AGIP_CUIT_CLIENTE_INPUT"] = cuit

        print("Ejecutando test para cliente: ", client_folder)
        # Ejecutar el test para este cliente
        await agip_test(
            headless=headless, iterations=iterations, enable_tracing=enable_tracing, trace_dir=trace_dir
        )


if __name__ == "__main__":
    asyncio.run(agip_batch_test(headless=False, iterations=1))
