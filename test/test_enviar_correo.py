import os
import shutil
from datetime import datetime

import pandas as pd
import pytest
from bs4 import BeautifulSoup

from mail import enviar_correo


@pytest.fixture
def carpeta_cliente():
    folder_path = r"C:\Users\lmarinaro\OneDrive - Deloitte (O365D)\Documents\Proyectos\test_robot_framework\dfe\Estructura-robot\Cliente Test"
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    yield folder_path
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)


@pytest.fixture
def verificar_html():
    def _check(file_path, textos):
        assert os.path.isfile(file_path), f"No se encontró el archivo: {file_path}"
        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        for t in textos:
            assert t in soup.get_text(), f"No se encontró '{t}' en el HTML"

    return _check


def test_enviar_correo(carpeta_cliente, verificar_html):
    receptor = "lmarinaro@deloitte.com"
    cc = "lmarinaro@deloitte.com;lmarinaro@deloitte.com"
    cuit_cliente = '30123456789'
    inicio = datetime.now()
    cliente = "Cliente Test"
    data = {
        "Jurisdicción": [
            "924 TUCUMAN",
            "907 CHUBUT",
            "916 RIO NEGRO",
            "915 NEUQUEN",
            "913 MENDOZA",
            "919 SAN LIUS",
            "902 BUENOS AIRES",
            "904 CORDOBA",
            "908 ENTRE RIOS",
            "905 CORRIENTES",
            "914 MISIONES",
            "906 CHACO",
            "909 FORMOSA",
            "910 JUJUY",
            "917 SALTA",
            "922 SANTIAGO DEL ESTERO",
            "903 CATAMARCA",
            "901 CABA",
        ],
        "Notificaciones": [
            "No hay notificaciones",
            "No hay notificaciones",
            "No hay notificaciones",
            "No hay notificaciones",
            "No hay notificaciones",
            "No hay notificaciones",
            "No hay notificaciones",
            "No hay notificaciones",
            "No hay notificaciones",
            "No hay notificaciones",
            "No hay notificaciones",
            "No hay notificaciones",
            "No hay notificaciones",
            "No hay notificaciones",
            "No hay notificaciones",
            "Error al buscar notificación",
            "Error al buscar notificación",
            "Error al buscar notificación",
        ],
        "Screenshot": [
            "Se realizó Screenshot",
            "Se realizó Screenshot",
            "Se realizó Screenshot",
            "Se realizó Screenshot",
            "Se realizó Screenshot",
            "Se realizó Screenshot",
            "Se realizó Screenshot",
            "Se realizó Screenshot",
            "Se realizó Screenshot",
            "Se realizó Screenshot",
            "Se realizó Screenshot",
            "Se realizó Screenshot",
            "Se realizó Screenshot",
            "Se realizó Screenshot",
            "Se realizó Screenshot",
            "Error al buscar tomar screenshot",
            "Error al buscar tomar screenshot",
            "Error al buscar tomar screenshot",
        ],
    }
    df = pd.DataFrame(data)
    enviar_correo(
        receptor=receptor,
        cliente=cliente,
        cuit=cuit_cliente,
        inicio=inicio,
        ruta_archivo_adjunto="test/assets/EDGE ARGENTINA S.R.L_20250103_1309.zip",
        nombre_archivo_adjunto="EDGE ARGENTINA S.R.L_20250103_1309.zip",
        df=df,
        ruta_imagen_png="test/assets/mapa_nacional_EDGE ARGENTINA S.R.L.png",
        ruta_imagen_png_2="test/assets/mapa_jurisdicciones_EDGE ARGENTINA S.R.L.png",
        cuerpo_html_plantilla="html/mail_plantilla.html",
        cc=cc,
    )
    
    cuit_formateado = f"{cuit_cliente[:2]}-{cuit_cliente[2:10]}-{cuit_cliente[10:]}"
    textos_a_buscar = [f"{cliente}", f"{cuit_formateado}"]
    fecha_actual = datetime.now().strftime("%Y%m%d")
    archivo_html = os.path.join(carpeta_cliente, f"output\{cliente}_{fecha_actual}.html")
    verificar_html(archivo_html, textos_a_buscar)

    # Verificar que exista la carpeta después de enviar el correo
    assert os.path.isdir(
        carpeta_cliente
    ), f"No se encontró la carpeta {carpeta_cliente}"
