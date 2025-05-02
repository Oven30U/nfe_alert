import os
import sys
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, ANY
import shutil

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PIL import Image
from reportlab.pdfgen import canvas
from cliente_processor import ClienteProcessor


class TestGenerarPDF:
    """
    Pruebas unitarias para el método generar_pdf de la clase ClienteProcessor.
    """

    @pytest.fixture
    def setup_temp_folder(self, tmp_path):
        """
        Crea una estructura temporal de carpetas y archivos para las pruebas.
        
        Args:
            tmp_path: Fixture de pytest que proporciona una ruta temporal
            
        Returns:
            tuple: (client_folder, output_folder)
        """
        # Usar tmp_path de pytest en lugar de crear directorios manualmente
        client_folder = tmp_path / "TEST_CLIENT"
        output_folder = client_folder / "Output"
        
        # Crear directorios
        output_folder.mkdir(parents=True, exist_ok=True)
        
        # Devolver rutas
        return str(client_folder), str(output_folder)

    @pytest.fixture
    def mock_processor(self, setup_temp_folder):
        """
        Crea una instancia mock del ClienteProcessor.
        
        Args:
            setup_temp_folder: Fixture que proporciona las carpetas temporales
            
        Returns:
            MagicMock: Mock de ClienteProcessor
        """
        client_folder, output_folder = setup_temp_folder
        
        # Crear mock del procesador
        processor = MagicMock()
        processor.cliente = "TEST_CLIENT"
        processor.output_folder = output_folder
        processor.logger = MagicMock()
        
        return processor

    @pytest.fixture
    def create_test_images(self, setup_temp_folder):
        """
        Crea imágenes PNG de prueba en la carpeta temporal.
        
        Args:
            setup_temp_folder: Fixture que proporciona las carpetas temporales
            
        Returns:
            list: Lista de rutas de imágenes creadas
        """
        _, output_folder = setup_temp_folder
        
        # Lista para almacenar las rutas de las imágenes
        image_paths = []
        
        # Crear imágenes de prueba
        test_images = [
            "mapa_nacional_TEST_CLIENT.png",
            "mapa_jurisdicciones_TEST_CLIENT.png",
            "screenshot_nacional_TEST_CLIENT.png",
            "screenshot_agip_TEST_CLIENT.png"
        ]
        
        for img_name in test_images:
            img_path = os.path.join(output_folder, img_name)
            # Crear imagen simple
            img = Image.new('RGB', (100, 100), color='white')
            img.save(img_path)
            image_paths.append(img_path)
        
        return image_paths

    def test_generar_pdf_exitoso(self, mock_processor, create_test_images, setup_temp_folder):
        """
        Prueba la generación exitosa de un PDF con las imágenes ordenadas correctamente.
        """
        _, output_folder = setup_temp_folder
        
        # Patchar el método de ClienteProcessor
        with patch('cliente_processor.ClienteProcessor.generar_pdf', autospec=True) as mock_method:
            # Configurar el mock para llamar a la implementación real
            mock_method.side_effect = ClienteProcessor.generar_pdf
            
            # Configurar fecha simulada para pruebas deterministas
            with patch('cliente_processor.datetime') as mock_datetime:
                mock_datetime.now.return_value = datetime(2023, 1, 15)
                mock_datetime.strftime = datetime.strftime
                
                # Ejecutar el método
                resultado = ClienteProcessor.generar_pdf(mock_processor)
                
                # Verificar el resultado
                expected_pdf_path = os.path.join(output_folder, f"NFE_alert_resume_TEST_CLIENT_15_01_2023.pdf")
                assert resultado == expected_pdf_path
                
                # Verificar que se llamó al logger con el mensaje correcto
                mock_processor.logger.info.assert_called_with(f"PDF generado correctamente: {expected_pdf_path}")

    def test_generar_pdf_sin_imagenes(self, mock_processor, setup_temp_folder):
        """
        Prueba el comportamiento cuando no hay imágenes PNG disponibles.
        """
        # Patchar el método de ClienteProcessor
        with patch('cliente_processor.ClienteProcessor.generar_pdf', autospec=True) as mock_method:
            # Configurar el mock para llamar a la implementación real
            mock_method.side_effect = ClienteProcessor.generar_pdf
            
            # Ejecutar el método
            resultado = ClienteProcessor.generar_pdf(mock_processor)
            
            # Verificar que se devuelve una cadena vacía cuando no hay imágenes
            assert resultado == ""
            
            # Verificar que se llamó al logger con el mensaje de advertencia
            mock_processor.logger.warning.assert_called_with(
                f"No se encontraron imágenes PNG para generar el PDF en {mock_processor.output_folder}"
            )

    def test_generar_pdf_error(self, mock_processor, create_test_images):
        """
        Prueba el manejo de errores durante la generación del PDF.
        """
        # Patchar canvas.Canvas para simular un error
        with patch('cliente_processor.canvas.Canvas', side_effect=Exception("Error al crear PDF")):
            # Patchar el método de ClienteProcessor
            with patch('cliente_processor.ClienteProcessor.generar_pdf', autospec=True) as mock_method:
                # Configurar el mock para llamar a la implementación real
                mock_method.side_effect = ClienteProcessor.generar_pdf
                
                # Ejecutar el método
                resultado = ClienteProcessor.generar_pdf(mock_processor)
                
                # Verificar que se devuelve una cadena vacía en caso de error
                assert resultado == ""
                
                # Verificar que se llamó al logger con el mensaje de error
                mock_processor.logger.error.assert_called_with(ANY)


if __name__ == "__main__":
    # Ejecutar desde la ruta del archivo
    file_dir = os.path.dirname(os.path.abspath(__file__))
    pytest.main(["-xvs", os.path.abspath(__file__)])