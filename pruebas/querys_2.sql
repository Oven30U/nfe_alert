select *
from usuarios_autorizados
-- where id in (1064, 1063, 1054, 1041)

select *
from usuario_cliente

select *
from clientes


-- update clientes set fecha_actualizacion_pass = '01-09-2022'

-- delete from usuario_cliente where id_usuario = 1041
-- delete from usuario_cliente

-- SELECT COLUMN_NAME, DATA_TYPE
-- FROM INFORMATION_SCHEMA.COLUMNS
-- WHERE TABLE_NAME = 'clientes'
SELECT TOP (1000) [id]
      ,[nombre]
      ,[pass]
      ,[fecha_actualizacion_pass]
      ,[id_username]
  FROM [Tecnologia].[dbo].[clientes]


BEGIN TRANSACTION
ALTER TABLE clientes
DROP COLUMN id_username;
COMMIT TRANSACTION

BEGIN TRANSACTION
ALTER TABLE clientes
ALTER COLUMN fecha_actualizacion_pass DATETIME
COMMIT TRANSACTION


ALTER TABLE clientes
ADD fecha_vencimiento_pass DATETIME;

SELECT COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'clientes';

SELECT COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'usuarios_autorizados';

SELECT c.*
FROM clientes c
INNER JOIN (
    SELECT nombre, MAX(fecha_actualizacion_pass) AS max_fecha_actualizacion_pass
    FROM clientes
    GROUP BY nombre
) subquery
ON c.nombre = subquery.nombre AND c.fecha_actualizacion_pass = subquery.max_fecha_actualizacion_pass;