--- Reemplazador de formato de dias_ejecucion ---
-- Lunes a 0
UPDATE clientes
SET dias_ejecucion = REPLACE(dias_ejecucion, 'Lunes', '0')
WHERE CHARINDEX('Lunes', dias_ejecucion) > 0;

-- Martes a 1
UPDATE clientes
SET dias_ejecucion = REPLACE(dias_ejecucion, 'Martes', '1')
WHERE CHARINDEX('Martes', dias_ejecucion) > 0;

-- Miércoles a 2
UPDATE clientes
SET dias_ejecucion = REPLACE(dias_ejecucion, 'Miércoles', '2')
WHERE CHARINDEX('Miércoles', dias_ejecucion) > 0;

-- Jueves a 3
UPDATE clientes
SET dias_ejecucion = REPLACE(dias_ejecucion, 'Jueves', '3')
WHERE CHARINDEX('Jueves', dias_ejecucion) > 0;

-- Viernes a 4
UPDATE clientes
SET dias_ejecucion = REPLACE(dias_ejecucion, 'Viernes', '4')
WHERE CHARINDEX('Viernes', dias_ejecucion) > 0;

-- Sábado a 5
UPDATE clientes
SET dias_ejecucion = REPLACE(dias_ejecucion, 'Sábado', '5')
WHERE CHARINDEX('Sábado', dias_ejecucion) > 0;

-- Domingo a 6
UPDATE clientes
SET dias_ejecucion = REPLACE(dias_ejecucion, 'Domingo', '6')
WHERE CHARINDEX('Domingo', dias_ejecucion) > 0;