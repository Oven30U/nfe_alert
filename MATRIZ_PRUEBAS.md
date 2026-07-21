# Matriz resumida de pruebas

| ID | Nivel | Escenario | Resultado esperado |
|---|---|---|---|
| SMK-001 | Smoke | Importar módulos críticos | Sin error de colección |
| SMK-002 | Smoke | Contrato mínimo de AGIP | Métodos críticos disponibles |
| UNI-001 | Unit | LoginError por defecto | Mensaje de credenciales inválidas |
| UNI-002 | Unit | LoginError explícito | Conserva mensaje específico |
| UNI-003 | Unit | Error visible Clave Ciudad | Lanza LoginError |
| UNI-004 | Unit | Indicadores MIBA | Lanza LoginError solo si son visibles |
| REG-001 | Unit | Timeout esperando éxito AGIP | No debe decir credenciales inválidas |
| INT-001 | Integración | Fallback Clave Ciudad → MIBA | Segundo método ejecutado |
| INT-002 | Integración | Timeout inicial y fallback | Segundo método ejecutado |
| INT-003 | Integración | Ambos métodos fallan | LoginError final |
| INT-004 | Integración | LoginError en reintentos | No reintenta |
| INT-005 | Integración | Timeout técnico | Sí reintenta |
| REG-002 | Integración | Timeout mal clasificado | No debe bloquear reintento |
| E2E-001 | E2E | Credenciales QA inválidas | Error de credenciales comprobable |
| E2E-002 | E2E | Timeout inducido con credenciales válidas | No marcar credenciales inválidas |
