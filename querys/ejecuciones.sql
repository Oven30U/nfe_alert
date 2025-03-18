SELECT *
FROM vw_ejecuciones_mensuales_nfe;

SELECT *
FROM vw_inicio_clientes_nfe
ORDER BY primera_ejecucion, cliente;

-- Primera fecha de ejecución para cada cliente (fecha de incorporación)
SELECT
    cliente,
    MIN(CAST(iniciado AS DATE)) AS primera_ejecucion
FROM monitoreo_bots
WHERE proceso = 'NFE Alert'
    AND cliente != 'TaxTech'
GROUP BY cliente
ORDER BY primera_ejecucion, cliente;



-- Cantidad de ejecuciones por mes
SELECT
    CAST(iniciado as DATE) AS fecha,
    COUNT(id) AS cantidad_ejecuciones
FROM monitoreo_bots
WHERE proceso = 'NFE Alert'
    AND cliente != 'TaxTech'
GROUP BY CAST(iniciado AS DATE)
ORDER BY fecha;



-- Cantidad de ejecuciones por mes, con diferencia nominal y porcentual de clientes respecto al mes anterior
SELECT
    YEAR(iniciado) AS año,
    MONTH(iniciado) AS mes,
    COUNT(id) AS ejecuciones,
    COUNT(DISTINCT cliente) AS clientes,
    CASE
        WHEN LAG(COUNT(DISTINCT cliente), 1, 0) OVER (ORDER BY YEAR(iniciado), MONTH(iniciado)) = 0 THEN 0
        ELSE ROUND((COUNT(DISTINCT cliente) - LAG(COUNT(DISTINCT cliente), 1, 0) OVER (ORDER BY YEAR(iniciado), MONTH(iniciado))), 2)
    END AS diferencia_clientes,
    CASE 
        WHEN LAG(COUNT(DISTINCT cliente), 1, 0) OVER (ORDER BY YEAR(iniciado), MONTH(iniciado)) = 0 THEN 0
        ELSE CAST((COUNT(DISTINCT cliente) - LAG(COUNT(DISTINCT cliente), 1, 0) OVER (ORDER BY YEAR(iniciado), MONTH(iniciado))) AS FLOAT) / 
             LAG(COUNT(DISTINCT cliente), 1, 0) OVER (ORDER BY YEAR(iniciado), MONTH(iniciado))
    END AS porcentaje_cambio,
    CASE
        WHEN FIRST_VALUE(COUNT(DISTINCT cliente)) OVER (ORDER BY YEAR(iniciado), MONTH(iniciado) ROWS UNBOUNDED PRECEDING) = 0 THEN 0
        ELSE CAST((COUNT(DISTINCT cliente) - FIRST_VALUE(COUNT(DISTINCT cliente)) OVER (ORDER BY YEAR(iniciado), MONTH(iniciado) ROWS UNBOUNDED PRECEDING)) AS FLOAT) / 
             FIRST_VALUE(COUNT(DISTINCT cliente)) OVER (ORDER BY YEAR(iniciado), MONTH(iniciado) ROWS UNBOUNDED PRECEDING)
    END AS porcentaje_cambio_historico
FROM monitoreo_bots
WHERE proceso = 'NFE Alert'
    AND cliente != 'TaxTech'
GROUP BY YEAR(iniciado), MONTH(iniciado)
ORDER BY año, mes;


-- Lista de todos los clientes que ejecutaron el proceso NFE Alert
SELECT DISTINCT cliente
FROM monitoreo_bots
WHERE proceso = 'NFE Alert'
    AND cliente != 'TaxTech'
ORDER BY cliente;


-- CREATE VIEW vw_ejecuciones_mensuales_nfe
-- AS
--     SELECT
--         YEAR(iniciado) AS año,
--         MONTH(iniciado) AS mes,
--         COUNT(id) AS ejecuciones,
--         COUNT(DISTINCT cliente) AS clientes,
--         CASE
--         WHEN LAG(COUNT(DISTINCT cliente), 1, 0) OVER (ORDER BY YEAR(iniciado), MONTH(iniciado)) = 0 THEN 0
--         ELSE ROUND((COUNT(DISTINCT cliente) - LAG(COUNT(DISTINCT cliente), 1, 0) OVER (ORDER BY YEAR(iniciado), MONTH(iniciado))), 2)
--     END AS diferencia_clientes,
--         CASE 
--         WHEN LAG(COUNT(DISTINCT cliente), 1, 0) OVER (ORDER BY YEAR(iniciado), MONTH(iniciado)) = 0 THEN 0
--         ELSE CAST((COUNT(DISTINCT cliente) - LAG(COUNT(DISTINCT cliente), 1, 0) OVER (ORDER BY YEAR(iniciado), MONTH(iniciado))) AS FLOAT) / 
--              LAG(COUNT(DISTINCT cliente), 1, 0) OVER (ORDER BY YEAR(iniciado), MONTH(iniciado))
--     END AS porcentaje_cambio,
--         CASE
--         WHEN FIRST_VALUE(COUNT(DISTINCT cliente)) OVER (ORDER BY YEAR(iniciado), MONTH(iniciado) ROWS UNBOUNDED PRECEDING) = 0 THEN 0
--         ELSE CAST((COUNT(DISTINCT cliente) - FIRST_VALUE(COUNT(DISTINCT cliente)) OVER (ORDER BY YEAR(iniciado), MONTH(iniciado) ROWS UNBOUNDED PRECEDING)) AS FLOAT) / 
--              FIRST_VALUE(COUNT(DISTINCT cliente)) OVER (ORDER BY YEAR(iniciado), MONTH(iniciado) ROWS UNBOUNDED PRECEDING)
--     END AS porcentaje_cambio_historico
--     FROM monitoreo_bots
--     WHERE proceso = 'NFE Alert'
--         AND cliente != 'TaxTech'
--     GROUP BY YEAR(iniciado), MONTH(iniciado);


-- CREATE VIEW vw_inicio_clientes_nfe AS
--     SELECT
--         cliente,
--         MIN(CAST(iniciado AS DATE)) AS primera_ejecucion
--     FROM monitoreo_bots
--     WHERE proceso = 'NFE Alert'
--         AND cliente != 'TaxTech'
--     GROUP BY cliente
    
