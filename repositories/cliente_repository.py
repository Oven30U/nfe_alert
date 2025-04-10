from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from repositories.base_repository import BaseRepository
from models import ClienteNFE, JurisdiccionNFE, ClienteJurisdiccionNFE

class ClienteRepository(BaseRepository[ClienteNFE]):
    """Repositorio para operaciones con clientes."""
    
    def __init__(self, session: Session):
        super().__init__(session, ClienteNFE)
    
    def get_by_client_folder(self, client_folder: str) -> Optional[ClienteNFE]:
        """Obtiene un cliente por su carpeta de cliente."""
        return self.session.query(self.model_class).filter_by(client_folder=client_folder).first()
    
    def get_clientes_by_dia_ejecucion(self, dia: str) -> List[ClienteNFE]:
        """Obtiene clientes cuyo día de ejecución coincide con el día especificado."""
        return self.session.query(self.model_class).filter(
            self.model_class.dias_ejecucion.ilike(f"%{dia}%")
        ).all()
    
    def get_all_with_jurisdicciones(self) -> List[ClienteNFE]:
        """Obtiene todos los clientes con sus jurisdicciones."""
        return self.session.query(self.model_class).all()


class JurisdiccionRepository(BaseRepository[JurisdiccionNFE]):
    """Repositorio para operaciones con jurisdicciones."""
    
    def __init__(self, session: Session):
        super().__init__(session, JurisdiccionNFE)
    
    def get_by_codigo(self, codigo: str) -> Optional[JurisdiccionNFE]:
        """Obtiene una jurisdicción por su código."""
        return self.session.query(self.model_class).filter_by(codigo=codigo).first()


class ClienteJurisdiccionRepository(BaseRepository[ClienteJurisdiccionNFE]):
    """Repositorio para operaciones con relaciones cliente-jurisdicción."""
    
    def __init__(self, session: Session):
        super().__init__(session, ClienteJurisdiccionNFE)
    
    def get_jurisdicciones_by_cliente_id(self, cliente_id: int, consultar: bool = True) -> List[ClienteJurisdiccionNFE]:
        """Obtiene las jurisdicciones de un cliente filtradas por consultar."""
        return self.session.query(self.model_class).filter(
            and_(
                self.model_class.cliente_id == cliente_id,
                self.model_class.consultar == consultar
            )
        ).all()