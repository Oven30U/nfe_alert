from repositories.cliente_service import ClienteService


def obtener_datos_clientes():
    """Obtener los clientes y jurisdicciones para procesar hoy."""
    df_clientes = ClienteService.get_clientes_jurisdicciones_hoy()
    
    # Aplicar transformaciones adicionales si son necesarias
    
    return df_clientes

if __name__ == '__main__':
    # Ejecutar la función para obtener los datos
    df_clientes = obtener_datos_clientes()
    print(df_clientes)