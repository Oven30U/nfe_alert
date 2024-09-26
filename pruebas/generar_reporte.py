from database import get_session
from sqlalchemy.sql import text
import pandas as pd

def obtener_datos() -> pd.DataFrame:
    try:
        with get_session() as session:
            query = text("SELECT * FROM monitoreo_bots WHERE proceso = 'Revision de Domicilios Fiscales Electronicos'")
            result = session.execute(query).fetchall()
            if result:
                columns = result[0].keys() if hasattr(result[0], 'keys') else [col for col in result[0]._fields]
                return pd.DataFrame(result, columns=columns)
            else:
                return pd.DataFrame()
    except Exception as e:
        print(f"Error al obtener los datos: {e}")
        return pd.DataFrame()

def generar_excel() -> None:
    try:
        reporte_monitoreo = obtener_datos()
        if not reporte_monitoreo.empty:
            reporte_monitoreo.to_excel("reporte_monitoreo_nfe.xlsx", index=False)
        else:
            print("No se encontraron datos para generar el reporte.")
    except Exception as e:
        print(f"Error al generar el archivo Excel: {e}")

if __name__ == "__main__":
    generar_excel()
