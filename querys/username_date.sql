select
    username, proceso, iniciado, cliente, estado
from
    monitoreo_bots
where
    proceso = 'NFE Alert'
    and username = 'julia.gonzalo'--username correspondiente
order by
    finalizado desc