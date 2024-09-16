SELECT cliente, MAX(finalizado) AS finalizado
FROM monitoreo_bots
WHERE CAST(finalizado AS DATE) = CAST(GETDATE() AS DATE)
    AND proceso = 'Revision de Domicilios Fiscales Electronicos'
    AND cliente IN ('EDGE ARGENTINA S.R.L')
GROUP BY cliente

-- AND cliente IN ('EDGE ARGENTINA S.R.L', 'valor2', 'valor3')
-- AND cliente = 'EDGE ARGENTINA S.R.L' 
-- AND estado = 'Correcto'
