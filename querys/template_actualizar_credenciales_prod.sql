-- Plantilla para llamar al stored procedure ActualizarCredenciales
-- Reemplaza los valores debajo antes de ejecutar. Evita commitear contraseñas en el repo.

SET NOCOUNT ON;
-- Batch 1: Ejecutar procedimiento para un cliente / jurisdicción
BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @RC INT;
    DECLARE @ClienteID INT = 6;              -- <- reemplazar
    DECLARE @JurisdiccionID INT = 20;        -- <- reemplazar
    DECLARE @Usuario VARCHAR(255) = '30709724912'; -- <- reemplazar
    DECLARE @Password VARCHAR(255) = 'REEMPLAZAR_CON_PASSWORD_SEGURA'; -- <- reemplazar

    EXECUTE @RC = dbo.ActualizarCredenciales
        @ClienteID,
        @JurisdiccionID,
        @Usuario,
        @Password;

    -- Puedes comprobar @RC si tu SP lo devuelve
    IF @RC IS NOT NULL AND @RC <> 0
    BEGIN
    RAISERROR('Stored procedure returned non-zero return code: %d', 16, 1, @RC);
END

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    -- Re-lanzar el error para que el runner Python lo capture y haga rollback global
    DECLARE @Msg NVARCHAR(4000) = ERROR_MESSAGE();
    DECLARE @Line INT = ERROR_LINE();
    RAISERROR('Error ejecutando ActualizarCredenciales: %s (linea %d)', 16, 1, @Msg, @Line);
END CATCH
GO