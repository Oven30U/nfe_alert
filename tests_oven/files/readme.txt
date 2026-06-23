# Unitarios (rápido, sin nada externo)
pytest tests/test_unitarios.py -v

# Integración (mocks de browser)
pytest tests/test_integracion.py -v

# Mutación (boundaries diseñados para matar mutantes)
pytest tests/test_mutacion.py -v

# E2E solo conectividad DB (sin browser, ~10 segundos)
pytest tests/test_e2e.py::TestE2EConectividadDB -v

# E2E una jurisdicción completa
pytest tests/test_e2e.py::TestE2ENacional -v -s

# Mutation testing con mutmut
mutmut run