from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "mssql+pyodbc://TaxTech:T&LTechnologies@ARBAS0228/RPA/Tecnologia?driver=SQL+Server"

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Función para obtener una nueva sesión
def get_session():
    return Session()