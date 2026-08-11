# Cobertura "timeout vs. credenciales" — las 24 jurisdicciones

Mapeo completo de cómo cada jurisdicción maneja el caso "no hay indicador de
éxito ni de error explícito" (la ambigüedad real que causa el síntoma
reportado: un timeout de portal se informa como "credenciales inválidas").
No se modificó ningún archivo de `jurisdicciones/`.

## Resultado del mapeo

| Categoría | Jurisdicciones | Test |
|---|---|---|
| 🔴 **Riesgo confirmado** (timeout/excepción genérica → `LoginError` por diseño) | Agip, Salta, Sicnea, Neuquen | Test dedicado por archivo (`test_<clase>_timeout_vs_credenciales.py` / `test_e2e_agip_known_issue.py`), reproduce el escenario exacto y confirma el bug |
| 🟢 **Patrón seguro** (chequeo inmediato `is_visible`/`count`, no bloquea ni convierte timeouts en `LoginError`) | Arba, Chaco, Chubut, Formosa, Jujuy, LaPampa, LaRioja, Misiones, SanJuan, SanLuis | Cubiertas por el test genérico parametrizado |
| 🟢 **Delegan en `AFIP_login` de la clase base** (no agregan su propio riesgo) | Corrientes, EntreRios, RioNegro, Catamarca, SantiagoDelEstero, Tucuman, Cordoba, Nacional | Cubiertas por el test genérico parametrizado |
| ⭐ **Referencia / ya usa el mecanismo correcto** | Mendoza (`clasificar_fallo_login`) | Cubierta por el test genérico + tests previos de `clasificar_fallo_login` |
| ⚪ **Sin implementar** | SantaFe, TierraDelFuego | N/A |

**24/24 jurisdicciones implementadas quedaron cubiertas.** Las 4 riesgosas
con un test específico y quirúrgico (como el que ya tenías de AGIP); las 20
restantes con un test genérico parametrizado que simula "ningún indicador
de error visible" para cada una y audita que el resultado nunca sea
`LoginError`/`LoginErrorAfip`.

## Archivos nuevos

```
tests/unit/test_todas_jurisdicciones_no_falsos_positivos_credenciales.py   (20 jurisdicciones, parametrizado)
tests/unit/test_salta_timeout_vs_credenciales.py                          (2 tests)
tests/unit/test_sicnea_timeout_vs_credenciales.py                         (2 tests)
tests/unit/test_neuquen_timeout_vs_credenciales.py                        (2 tests)
```
(`tests/e2e/test_e2e_agip_known_issue.py` ya existía de antes.)

Los 4 archivos ya están corridos y validados: **27 passed** en conjunto.

## Hallazgos nuevos que aparecieron al armar esto (no pedidos, pero relacionados)

1. **`neuquen.py::login_neuquen_afip`** tiene el mismo patrón que agip/salta/sicnea:
   `except Exception: ... raise LoginError(self.cliente, LoginError.SERVICIO_NO_DISPONIBLE)`
   sobre CUALQUIER excepción no clasificada previamente (confirmado con test, no en vivo).

2. **`sicnea.py::_select_cuit_from_dropdown`** tiene un bug adicional, distinto al de timeout:
   `DelegacionError` no hereda de `LoginError`, así que el
   `except LoginError: raise` de ese método NO la atrapa — cae al
   `except Exception` genérico y **un `DelegacionError` legítimo también
   termina reempaquetado como `LoginError`**. Se pierde la distinción entre
   "no está delegado" y "credenciales inválidas" en SICNEA específicamente.

## Qué NO cubre esto (por si se sigue iterando)

- No se testeó cada rama de código de las 20 jurisdicciones "seguras" en profundidad — el test genérico confirma que el patrón de chequeo inmediato no fuerza un `LoginError`, pero no ejercita cada selector particular de cada una.
- No se tocó el bug de timezone en `filtrar_jurisdicciones_por_login_error` (ya documentado en `tests/integration/test_login_error_persistence.py` de una entrega anterior) — sigue vigente y sigue siendo el motivo por el que, aunque se claseifique bien un `LoginError`, el "saltear 24hs" no funciona en la práctica.
- Como pediste, **no se tocó ningún archivo de `jurisdicciones/`** — todo lo de arriba son tests que documentan el estado actual, marcados `@pytest.mark.known_issue` donde corresponde.
