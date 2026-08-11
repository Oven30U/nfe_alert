import importlib

import pytest


@pytest.mark.smoke
def test_modulos_criticos_importan_sin_error():
    for module_name in (
        "jurisdicciones.jurisdiccion",
        "jurisdicciones.agip",
        "cliente_processor",
    ):
        importlib.import_module(module_name)


@pytest.mark.smoke
def test_agip_expone_metodos_criticos():
    from jurisdicciones.agip import Agip

    for method_name in (
        "_login",
        "_login_clave_ciudad",
        "_login_miba",
        "consultar_notificaciones",
        "buscar_notificacion",
    ):
        assert callable(getattr(Agip, method_name, None))
