SELECT DISTINCT cliente
FROM monitoreo_bots
WHERE proceso = 'NFE Alert'
    AND CAST(finalizado AS DATE) = CAST(GETDATE() AS DATE)

----------------------------------------------------------

SELECT cliente, cast(iniciado as date) as fecha
FROM monitoreo_bots
WHERE proceso = 'NFE Alert'
    AND cliente LIKE'%SPOTIFY%'
group by cliente, cast(iniciado as date)
order by fecha desc