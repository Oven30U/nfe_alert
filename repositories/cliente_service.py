from datetime import datetime
import pandas as pd
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from repositories.cliente_repository import ClienteRepository, JurisdiccionRepository, ClienteJurisdiccionRepository
from database import get_session

class ClienteService:
    """Servicio para operaciones de negocio relacionadas con clientes y jurisdicciones."""
    
    @staticmethod
    def get_clientes_jurisdicciones_hoy() -> pd.DataFrame:
        """
        Obtiene los clientes que deben ejecutarse hoy y sus jurisdicciones activas.
        
        Returns:
            DataFrame: DataFrame con clientes y jurisdicciones a procesar.
        """
        # Mapeo de días de la semana en inglés a español
        dias = {
            0: "Lunes", 
            1: "Martes", 
            2: "Miércoles", 
            3: "Jueves", 
            4: "Viernes", 
            5: "Sábado", 
            6: "Domingo"
        }
        
        dia_actual = dias[datetime.today().weekday()]
        
        session = get_session()
        try:
            # Inicializar repositorios
            cliente_repo = ClienteRepository(session)
            jurisdiccion_repo = JurisdiccionRepository(session)
            cliente_jurisdiccion_repo = ClienteJurisdiccionRepository(session)
            
            # Obtener clientes para el día actual
            clientes = cliente_repo.get_clientes_by_dia_ejecucion(dia_actual)
            
            # Crear lista para almacenar los datos
            data = []
            
            # Para cada cliente, obtener sus jurisdicciones activas
            for cliente in clientes:
                # Obtener jurisdicciones con consultar=True
                relaciones = cliente_jurisdiccion_repo.get_jurisdicciones_by_cliente_id(cliente.id, True)
                
                for relacion in relaciones:
                    jurisdiccion = jurisdiccion_repo.get_by_id(relacion.jurisdiccion_id)
                    
                    # Calcular fechas desde y hasta
                    fecha_hasta = datetime.now().strftime("%d%m%Y")
                    fecha_desde_obj = datetime.now() - pd.Timedelta(days=cliente.rango_consulta_dias or 10)
                    fecha_desde = fecha_desde_obj.strftime("%d%m%Y")
                    
                    # Añadir a la lista de datos
                    data.append({
                        'Cliente': cliente.nombre,
                        'client_folder': cliente.client_folder,
                        'Jurisdiccion': jurisdiccion.codigo,
                        'cuit_cliente': relacion.usuario,  # Utilizamos el campo usuario para el CUIT
                        'Usuario': relacion.usuario,
                        'Password': relacion.password,
                        'fecha_desde': relacion.fecha_desde or fecha_desde,
                        'fecha_hasta': relacion.fecha_hasta or fecha_hasta,
                        'Correo Output': cliente.correo_output,
                        'CC: Equipo Deloitte': cliente.socio_responsable,
                        'Rango de consulta dias anteriores': cliente.rango_consulta_dias,
                        'Schedule': cliente.schedule,
                        'Dia/s de ejecución': cliente.dias_ejecucion,
                        'Consultar': 'Si'  # Ya filtramos solo las relaciones con consultar=True
                    })
            
            # Convertir a DataFrame
            df = pd.DataFrame(data)
            return df
            
        finally:
            session.close()