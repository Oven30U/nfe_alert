-- Reemplazar nombres de días por sus índices (0 = Lunes … 6 = Domingo)
-- y poner NULL en dias_ejecucion si contiene caracteres distintos de 0–6 y comas
BEGIN TRY
    BEGIN TRANSACTION;

    -- 1) Reemplazar nombres de días por sus índices (0 = Lunes … 6 = Domingo)
    UPDATE [clientes]
    SET [dias_ejecucion] = REPLACE(
                             REPLACE(
                               REPLACE(
                                 REPLACE(
                                   REPLACE(
                                     REPLACE(
                                       REPLACE(
                                         [dias_ejecucion],
                                         'Lunes',     '0'
                                       ),
                                       'Martes',    '1'
                                     ),
                                     'Miércoles', '2'
                                   ),
                                   'Jueves',    '3'
                                 ),
                                 'Viernes',   '4'
                               ),
                               'Sábado',    '5'
                             ),
                             'Domingo',   '6'
                           )
    WHERE [dias_ejecucion] LIKE '%Lunes%'
    OR [dias_ejecucion] LIKE '%Martes%'
    OR [dias_ejecucion] LIKE '%Miércoles%'
    OR [dias_ejecucion] LIKE '%Jueves%'
    OR [dias_ejecucion] LIKE '%Viernes%'
    OR [dias_ejecucion] LIKE '%Sábado%'
    OR [dias_ejecucion] LIKE '%Domingo%';

    -- 2) Poner NULL en dias_ejecucion si contiene caracteres distintos de 0–6 y comas
    UPDATE [clientes]
    SET [dias_ejecucion] = NULL
    WHERE [dias_ejecucion] LIKE '%[^0-6,]%';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    ROLLBACK TRANSACTION;
    THROW;
END CATCH;