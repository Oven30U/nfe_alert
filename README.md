# Introducción

Proyecto para realizar la revisión de los DFE de las jurisdicciones de la República Argentina.

# Ejecución

El archivo principal es **[main.py](main.py)** para correrlo en modo productivo

Desde **[config.py](config.py)** puede setearse el modo Debug con sus respectivas variables.

Si debemos correr desde main.py entonces colocar DEBUG = False en config.py.
Por el momento el headless se configura unicamente desde config.py

# Estructura

Pasos para utilizar:

1. Crear el virtual enviroment (en caso de no existir utilizando requirements.txt)
2. Ejecutar main.py y verificar el funcionamiento con el archivo de prueba
3. Tener configurado git
4. Crear el archivo bat:

   ***Precaución con git reset hard*** y actualizar path del proyecto
   ```bat
   @echo off
   cd "C:\Users\lmarinaro\OneDrive - Deloitte (O365D)\Documents\Proyectos\test_robot_framework\dfe"
   call .venv\Scripts\activate
   git reset --hard
   git pull DFEPW main
   start /min "" python main.py
   call .venv\Scripts\deactivate.bat
   ```
5. Configurar la tarea programada para que se ejecute el archivo bat

# Testing

Archivo de [test unitarios](test_unit.py)

Activar entorno virtual con el siguiente comando:

```bash
# Activar entorno virtual
.venv\Scripts\activate


Para realizar los test unitarios de cada jurisdiccion se debe ejecutar el siguiente comando:

# Ejecutar todos los tests
pytest

# Ejecutar tests de una clase específica
pytest test_unit.py::TestJujuy

# Ejecutar tests de un método específico en una clase
pytest test_unit.py::TestJujuy::test_jujuy
pytest test_unit.py::TestJujuy::test_jujuy_error

# Ejecutar tests con un marcador específico
pytest -m base
pytest -m error

# Ejecutar tests múltiples veces
pytest --count=4 test_unit.py::TestLaPampa

# Detener al primer fallo y reintentar test fallido hasta 3 veces
pytest --maxfail=1 --reruns 3

# Definir la cantidad de veces a ejecutar el test
pytest --count=10 test_unit.py::TestJujuy
```
