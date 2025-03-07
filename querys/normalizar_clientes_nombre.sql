-- Actualizar nombres de clientes para limpiar datos con posibilidad de rollback
BEGIN TRANSACTION;

-- Guarda la cantidad de filas que serán afectadas para verificación
DECLARE @FilasAfectadas INT;
SELECT @FilasAfectadas = COUNT(*)
FROM monitoreo_bots
WHERE cliente IN ('ABBVIE S.A.', 'PFIZER S.R.L.', 
                 'JANSSEN CILAG FARMACEUTICA SOCIEDAD ANONIMA',
                 'JOHNSON & JOHNSON MEDICAL SOCIEDAD ANONIMA');

PRINT 'Filas que serán afectadas: ' + CAST(@FilasAfectadas AS VARCHAR);

-- Ejecuta la actualización
UPDATE monitoreo_bots
SET cliente = CASE 
    WHEN cliente = 'ABBVIE S.A.' THEN 'ABBVIE S.A'
    WHEN cliente = 'PFIZER S.R.L.' THEN 'PFIZER S.R.L - ARCA'
    WHEN cliente = 'JANSSEN CILAG FARMACEUTICA SOCIEDAD ANONIMA' THEN 'JANSSEN CILAG FARMACEUTICA S.A'
    WHEN cliente = 'JOHNSON & JOHNSON MEDICAL SOCIEDAD ANONIMA' THEN 'JOHNSON & JOHNSON MEDICAL S.A'
    ELSE cliente
END
WHERE cliente IN ('ABBVIE S.A.', 'PFIZER S.R.L.', 
                 'JANSSEN CILAG FARMACEUTICA SOCIEDAD ANONIMA',
                 'JOHNSON & JOHNSON MEDICAL SOCIEDAD ANONIMA');

-- Verifica los resultados antes de confirmar
SELECT 'Registros actualizados:', @@ROWCOUNT;


-- Seleccionar el mes con clientes desnormalizados para comparar contra uno normalizado
    SELECT DISTINCT cliente
    FROM monitoreo_bots
    WHERE proceso = 'NFE Alert'
        AND MONTH(iniciado) = 1 AND YEAR(iniciado) = 2025
EXCEPT
    SELECT DISTINCT cliente
    FROM monitoreo_bots
    WHERE proceso = 'NFE Alert'
        AND MONTH(iniciado) = 2 AND YEAR(iniciado) = 2025
ORDER BY cliente;


-- Para confirmar los cambios, descomenta la siguiente línea:
-- COMMIT TRANSACTION;

-- Para deshacer los cambios, descomenta la siguiente línea:
-- ROLLBACK TRANSACTION;

-- IMPORTANTE: Asegúrate de ejecutar COMMIT o ROLLBACK para finalizar la transacción