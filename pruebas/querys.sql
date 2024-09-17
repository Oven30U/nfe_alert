SELECT cliente, MAX(finalizado) AS finalizado
FROM monitoreo_bots
WHERE CAST(finalizado AS DATE) = CAST(GETDATE() AS DATE)
  AND proceso = 'Revision de Domicilios Fiscales Electronicos'
  AND cliente IN ('EDGE ARGENTINA S.R.L', 'NATURA COSMETICOS S.A', 'FACEBOOK ARGENTINA S.R.L')
GROUP BY cliente

-- AND cliente IN ('EDGE ARGENTINA S.R.L', 'valor2', 'valor3')
-- AND cliente = 'EDGE ARGENTINA S.R.L' 
-- AND estado = 'Correcto'

SELECT cliente, count(id), estado
--  MAX(finalizado) AS finalizado
FROM monitoreo_bots
WHERE 
    -- CAST(finalizado AS DATE) = CAST(GETDATE() AS DATE)
    -- AND 
    proceso = 'Revision de Domicilios Fiscales Electronicos'
-- AND cliente IN ('EDGE ARGENTINA S.R.L', 'NATURA COSMETICOS S.A', 'FACEBOOK ARGENTINA S.R.L')
GROUP BY cliente, estado

select cliente, username, count(*) as q_ejecuciones
from monitoreo_bots
where proceso = 'Revision de Domicilios Fiscales Electronicos'
  and username = 'lmarinaro'
group by cliente, username

----------------------------------------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------------------------------------

CREATE TABLE gui_configuracion_botones
(
  id smallint PRIMARY KEY,
  nombre_boton nvarchar,
  funcion_boton nvarchar,
  tooltip_boton nvarchar,
  active_boton bit
);


CREATE TABLE gui_lineas_servicios_botones
(
  id smallint PRIMARY KEY,
  id_linea_servicio smallint,
  id_boton smallint
);


CREATE TABLE gui_versiones
(
  id int PRIMARY KEY,
  version_app varchar,
  release_date date,
  active tinyint DEFAULT ((0)),
  download_path varchar
);


CREATE TABLE lineas_servicios
(
  id smallint PRIMARY KEY,
  nombre_linea_servicio nvarchar,
  sub_linea_servicio nvarchar
);


CREATE TABLE monitoreo_bots
(
  id smallint PRIMARY KEY,
  username nvarchar,
  proceso nvarchar,
  estado nvarchar,
  iniciado datetime,
  finalizado datetime,
  cliente nvarchar
);


CREATE TABLE sysdiagrams
(
  name nvarchar,
  principal_id int,
  diagram_id int PRIMARY KEY,
  version int,
  definition varbinary
);


CREATE TABLE usuarios
(
  id smallint PRIMARY KEY,
  nombre_usuario nvarchar,
  id_linea_servicio smallint
);


CREATE TABLE usuarios_autorizados
(
  id int PRIMARY KEY,
  username nvarchar,
  fecha_autorizacion datetime DEFAULT (getdate())
);


CREATE TABLE usuarios_lineas_servicios
(
  id int PRIMARY KEY,
  id_usuario int,
  id_linea_servicio smallint,
  fecha_asignacion datetime2
);


CREATE TABLE clientes
(
  id int NOT NULL PRIMARY KEY,
  nombre nvarchar,
  pass nvarchar,
  fecha_actualizacion_pass datetime,
  id_username int
);


CREATE TABLE usuario_cliente
(
  id int NOT NULL PRIMARY KEY,
  id_cliente int,
  id_usuario int
);


-- ALTER TABLE usuarios_lineas_servicios ADD CONSTRAINT FK__usuarios___id_li__03F0984C FOREIGN KEY (id_linea_servicio) REFERENCES lineas_servicios (id);
-- ALTER TABLE usuarios_lineas_servicios ADD CONSTRAINT FK__usuarios___id_us__04E4BC85 FOREIGN KEY (id_usuario) REFERENCES usuarios_autorizados (id);
-- ALTER TABLE gui_lineas_servicios_botones ADD CONSTRAINT fk_boton FOREIGN KEY (id_boton) REFERENCES gui_configuracion_botones (id);
-- ALTER TABLE gui_lineas_servicios_botones ADD CONSTRAINT fk_linea_servicio FOREIGN KEY (id_linea_servicio) REFERENCES lineas_servicios (id);
-- ALTER TABLE usuarios ADD CONSTRAINT fk_linea_servicio_usuario FOREIGN KEY (id_linea_servicio) REFERENCES lineas_servicios (id);
-- ALTER TABLE usuarios_autorizados ADD CONSTRAINT usuarios_autorizados_id_fk FOREIGN KEY (id) REFERENCES usuario_cliente (id_usuario);
-- ALTER TABLE clientes ADD CONSTRAINT clientes_id_fk FOREIGN KEY (id) REFERENCES usuario_cliente (id_cliente);

-- Verificar y agregar constraints solo si no existen
IF NOT EXISTS (
    SELECT *
FROM sys.foreign_keys
WHERE name = 'FK__usuarios___id_li__03F0984C'
)
BEGIN
  ALTER TABLE usuarios_lineas_servicios 
    ADD CONSTRAINT FK__usuarios___id_li__03F0984C 
    FOREIGN KEY (id_linea_servicio) 
    REFERENCES lineas_servicios (id);
END;

IF NOT EXISTS (
    SELECT *
FROM sys.foreign_keys
WHERE name = 'FK__usuarios___id_us__04E4BC85'
)
BEGIN
  ALTER TABLE usuarios_lineas_servicios 
    ADD CONSTRAINT FK__usuarios___id_us__04E4BC85 
    FOREIGN KEY (id_usuario) 
    REFERENCES usuarios_autorizados (id);
END;

IF NOT EXISTS (
    SELECT *
FROM sys.foreign_keys
WHERE name = 'fk_boton'
)
BEGIN
  ALTER TABLE gui_lineas_servicios_botones 
    ADD CONSTRAINT fk_boton 
    FOREIGN KEY (id_boton) 
    REFERENCES gui_configuracion_botones (id);
END;

IF NOT EXISTS (
    SELECT *
FROM sys.foreign_keys
WHERE name = 'fk_linea_servicio'
)
BEGIN
  ALTER TABLE gui_lineas_servicios_botones 
    ADD CONSTRAINT fk_linea_servicio 
    FOREIGN KEY (id_linea_servicio) 
    REFERENCES lineas_servicios (id);
END;

IF NOT EXISTS (
    SELECT *
FROM sys.foreign_keys
WHERE name = 'fk_linea_servicio_usuario'
)
BEGIN
  ALTER TABLE usuarios 
    ADD CONSTRAINT fk_linea_servicio_usuario 
    FOREIGN KEY (id_linea_servicio) 
    REFERENCES lineas_servicios (id);
END;

IF NOT EXISTS (
    SELECT *
FROM sys.foreign_keys
WHERE name = 'usuarios_autorizados_id_fk'
)
BEGIN
  ALTER TABLE usuarios_autorizados 
    ADD CONSTRAINT usuarios_autorizados_id_fk 
    FOREIGN KEY (id) 
    REFERENCES usuario_cliente (id_usuario);
END;

IF NOT EXISTS (
    SELECT *
FROM sys.foreign_keys
WHERE name = 'clientes_id_fk'
)
BEGIN
  ALTER TABLE clientes 
    ADD CONSTRAINT clientes_id_fk 
    FOREIGN KEY (id) 
    REFERENCES usuario_cliente (id_cliente);
END;


SELECT *
FROM sys.foreign_keys


SELECT TOP 1
  [pass], [fecha_actualizacion_pass]
FROM clientes
WHERE nombre = 'FACEBOOK ARGENTINA S.R.L'
ORDER BY id DESC
select *
from clientes



-- Alterar la columna 'nombre' a nvarchar(255)
ALTER TABLE clientes
ALTER COLUMN nombre nvarchar(255);

-- Alterar la columna 'pass' a nvarchar(255)
ALTER TABLE clientes
ALTER COLUMN pass nvarchar(255);

-- Alterar la columna 'fecha_actualizacion_pass' a datetime
ALTER TABLE clientes
ALTER COLUMN fecha_actualizacion_pass datetime;

-- Alterar la columna 'id_username' a int
ALTER TABLE clientes
ALTER COLUMN id_username int;


'\n                INSERT INTO clientes (nombre, pass, fecha_actualizacion_pass)\n                VALUES (?, ?, ?)\n            '
'FACEBOOK ARGENTINA S.R.L'
'cThcP506Y8lr'
datetime.datetime
(2024, 9, 16, 17, 55, 11, 754580)

-- Alterar la columna 'fecha_actualizacion_pass' a nvarchar(10)
ALTER TABLE clientes
ALTER COLUMN fecha_actualizacion_pass nvarchar(10);

-- Crear una nueva tabla temporal con la columna 'id' autoincremental
CREATE TABLE clientes_temp
(
  id int IDENTITY(1,1) PRIMARY KEY,
  nombre nvarchar(255),
  pass nvarchar(255),
  fecha_actualizacion_pass nvarchar(10),
  id_username int
);

-- Copiar los datos de la tabla original a la tabla temporal
INSERT INTO clientes_temp
  (nombre, pass, fecha_actualizacion_pass, id_username)
SELECT nombre, pass, fecha_actualizacion_pass, id_username
FROM clientes;

-- Eliminar la tabla original
DROP TABLE clientes;

-- Renombrar la tabla temporal a la tabla original
EXEC sp_rename 'clientes_temp', 'clientes';


select DISTINCT ua.username
from usuarios_autorizados ua
  inner join usuario_cliente uc on ua.id = uc.id_usuario
  inner join clientes cli on uc.id_cliente = cli.id
  WHERE uc.id_cliente = 1

select * from usuarios_autorizados where username in ('lmarinaro', 'rtolaba')
select * from usuario_cliente
select * from clientes
-- delete from usuario_cliente where id = 7

update clientes
set fecha_actualizacion_pass = '01-01-2020' where nombre = 'FACEBOOK ARGENTINA S.R.L' 

-- obtenemos los id de los usuarios autorizados y de los clientes
SELECT id 
FROM usuarios_autorizados 
WHERE username IN ('lmarinaro', 'usuario2', 'usuario3');

-- obtenemos el id del cliente
select id
from clientes
where nombre = 'FACEBOOK ARGENTINA S.R.L'

INSERT INTO usuario_cliente (id_cliente, id_usuario) VALUES (1, 1041);

-- EXEC sp_help 'usuario_cliente';

-- -- Eliminar la restricción de clave primaria
-- ALTER TABLE usuario_cliente
-- DROP CONSTRAINT PK__usuario___3213E83F953DE32D;

-- -- Eliminar la columna id
-- ALTER TABLE usuario_cliente
-- DROP COLUMN id;

-- -- Agregar la columna id como autoincremental y establecerla como clave primaria
-- ALTER TABLE usuario_cliente
-- ADD id INT IDENTITY(1,1) PRIMARY KEY;

select * from monitoreo_bots where proceso like ('Revisi%') order by id desc

-- delete from usuario_cliente