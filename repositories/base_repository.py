from typing import Generic, TypeVar, Type, List, Optional, Any, Dict
from sqlalchemy.orm import Session

# Tipo genérico para modelos
T = TypeVar('T')

class BaseRepository(Generic[T]):
    """Repositorio base genérico para operaciones CRUD."""
    
    def __init__(self, session: Session, model_class: Type[T]):
        self.session = session
        self.model_class = model_class
    
    def get_by_id(self, id: int) -> Optional[T]:
        """Obtiene una entidad por su ID."""
        return self.session.query(self.model_class).get(id)
    
    def get_all(self) -> List[T]:
        """Obtiene todas las entidades."""
        return self.session.query(self.model_class).all()
    
    def find_by(self, **kwargs) -> List[T]:
        """Encuentra entidades por criterios específicos."""
        return self.session.query(self.model_class).filter_by(**kwargs).all()
    
    def create(self, **kwargs) -> T:
        """Crea una nueva entidad."""
        entity = self.model_class(**kwargs)
        self.session.add(entity)
        return entity
    
    def update(self, entity: T, **kwargs) -> T:
        """Actualiza una entidad existente."""
        for key, value in kwargs.items():
            setattr(entity, key, value)
        return entity
    
    def delete(self, entity: T) -> None:
        """Elimina una entidad."""
        self.session.delete(entity)