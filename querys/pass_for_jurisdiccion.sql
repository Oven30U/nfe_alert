-- Obtener todas los clientes de jurisdicciones especificas
SELECT c.cuit, c.nombre , j.clase, cj.usuario, cj.password
FROM cliente_jurisdiccion AS cj
    INNER JOIN clientes as c ON c.id = cj.cliente_id
    INNER JOIN jurisdicciones as j ON j.id = cj.jurisdiccion_id
WHERE j.clase = 'Catamarca' AND cj.consultar = 1