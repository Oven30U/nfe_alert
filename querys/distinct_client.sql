SELECT DISTINCT cliente
FROM monitoreo_bots
WHERE proceso = 'NFE Alert'
    AND CAST(finalizado AS DATE) = CAST(GETDATE() AS DATE)

