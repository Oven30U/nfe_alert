from obtener_datos_clientes.query_data import query_data
from obtener_datos_clientes.db import SessionLocal
from obtener_datos_clientes.models import ProcesamientosDiariosGlobal, Cliente
import datetime
from datetime import timezone
from sqlalchemy.sql import func


class ProcesamientoGlobalManager:
    """Clase para gestionar los procesamientos globales."""

    @staticmethod
    def registrar_procesamiento():
        """Registra un nuevo procesamiento global al comenzar."""
        with SessionLocal() as db:
            # Obtener la fecha actual (solo fecha, sin hora)
            fecha_hoy = datetime.datetime.now().date()

            # SQL Server: comparar año, mes y día individualmente
            max_numero_procesamiento = (
                db.query(ProcesamientosDiariosGlobal.numero_procesamiento)
                .filter(
                    func.year(ProcesamientosDiariosGlobal.fecha) == fecha_hoy.year,
                    func.month(ProcesamientosDiariosGlobal.fecha) == fecha_hoy.month,
                    func.day(ProcesamientosDiariosGlobal.fecha) == fecha_hoy.day,
                )
                .order_by(ProcesamientosDiariosGlobal.numero_procesamiento.desc())
                .first()
            )

            # Incrementar el número de procesamiento o iniciar en 1 si no hay registros
            numero_procesamiento = (
                max_numero_procesamiento[0] + 1 if max_numero_procesamiento else 1
            )

            nuevo_procesamiento = ProcesamientosDiariosGlobal(
                fecha=datetime.datetime.now(timezone.utc),
                numero_procesamiento=numero_procesamiento,
                iniciado=datetime.datetime.now(
                    timezone.utc
                ),  # Aseguramos que sea timezone-aware
                finalizado=None,
                procesamiento_correcto=True,
            )
            db.add(nuevo_procesamiento)
            db.commit()
            db.refresh(
                nuevo_procesamiento
            )  # Refrescar para obtener el ID y otros datos actualizados

            # Incrementar el número de procesamiento para futuras iteraciones
            return nuevo_procesamiento

    @staticmethod
    def finalizar_procesamiento(procesamiento, procesamiento_correcto=True):
        """Marca un procesamiento global como finalizado.

        Args:
            procesamiento: El objeto procesamiento a finalizar
            procesamiento_correcto: True si el procesamiento fue exitoso, False en caso de error (default: True)
        """
        with SessionLocal() as db:
            procesamiento.finalizado = datetime.datetime.now(
                timezone.utc
            )  # Use timezone-aware datetime
            procesamiento.procesamiento_correcto = procesamiento_correcto
            db.merge(
                procesamiento
            )  # Aseguramos que el objeto esté sincronizado con la sesión
            db.commit()
            estado = (
                "finalizado" if procesamiento_correcto else "finalizado con errores"
            )
            print(f"Procesamiento {procesamiento.numero_procesamiento} {estado}.")

    @staticmethod
    def finalizar_procesamiento_sin_clientes(procesamiento_id):
        """
        Marca un procesamiento global como finalizado cuando no hay clientes para procesar.
        
        Args:
            procesamiento_id: ID del procesamiento global a finalizar
        """
        with SessionLocal() as db:
            procesamiento = db.query(ProcesamientosDiariosGlobal).filter(
                ProcesamientosDiariosGlobal.id == procesamiento_id
            ).first()
            
            if procesamiento:
                procesamiento.finalizado = datetime.now()
                procesamiento.procesamiento_correcto = True
                db.commit()
                return True
            else:
                return False


class CorreoManager:
    """Clase para gestionar el envío de correos."""

    @staticmethod
    def enviar_correos(procesamiento):
        """Envía correos a los clientes según el número de procesamiento."""
        with SessionLocal() as db:
            if procesamiento.numero_procesamiento == 3:
                print(
                    "Enviando correos a todos los clientes debido al tercer procesamiento del día."
                )
                clientes = db.query(Cliente).all()
                for cliente in clientes:
                    print(
                        f"Enviando correo a: {cliente.correo_output} para el cliente {cliente.nombre}"
                    )
            else:
                print(
                    f"Procesamiento {procesamiento.numero_procesamiento} del día. No se enviarán correos masivos."
                )


class ObtenerDatosClientes:
    """Clase principal para gestionar el flujo de datos y correos."""

    def __init__(self):
        self.data = None
        self.procesamiento = None

    def run(self):
        """Ejecuta la consulta de datos."""
        try:
            self.data = query_data()
            print(f"Datos obtenidos correctamente: {len(self.data)} registros")
            self.display_data()
        except Exception as e:
            print(f"Error al obtener datos: {str(e)}")
            # En caso de error, inicializar con DataFrame vacío
            import pandas as pd
            self.data = pd.DataFrame()
            print("Se continuará con un DataFrame vacío")

    def display_data(self):
        """Muestra los datos obtenidos."""
        if self.data is not None and not self.data.empty:
            print(self.data)
        else:
            print("No hay datos para mostrar")

    def gestionar_envio_correos(self):
        """Gestiona el envío de correos y el registro de procesamientos."""
        try:
            # Registrar un nuevo procesamiento global
            self.procesamiento = ProcesamientoGlobalManager.registrar_procesamiento()

            # Enviar correos según el número de procesamiento
            CorreoManager.enviar_correos(self.procesamiento)

            # Finalizar el procesamiento global
            ProcesamientoGlobalManager.finalizar_procesamiento(self.procesamiento)
        except Exception as e:
            print(f"Error en gestión de correos: {str(e)}")
            print("Se continuará con la ejecución principal")


if __name__ == "__main__":
    main_instance = ObtenerDatosClientes()
    main_instance.run()
    main_instance.gestionar_envio_correos()
