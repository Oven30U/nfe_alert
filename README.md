# Introducción 
Proyecto para realizar la revisión de los DFE de las jurisdicciones de la República Argentina. 

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
