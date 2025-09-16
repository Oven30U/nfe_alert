#!/usr/bin/env python3
"""
Ejemplo de uso del script update.py para NFE Alert.

Este script demuestra cómo usar el actualizador de GitHub para descargar
e instalar automáticamente la última versión de NFE Alert.
"""

import os
import subprocess
import sys
from pathlib import Path


def setup_environment():
    """Configura el entorno necesario para la actualización."""
    print("=== Configuración del entorno ===")
    
    # Verificar si GITHUB_TOKEN está configurado
    github_token = os.environ.get('GITHUB_TOKEN')
    if github_token:
        print("✓ GITHUB_TOKEN encontrado en variables de entorno")
    else:
        print("⚠ GITHUB_TOKEN no encontrado en variables de entorno")
        
        # Verificar si hay archivo .env
        env_file = Path('.env')
        if env_file.exists():
            print("✓ Archivo .env encontrado")
            with open(env_file, 'r') as f:
                content = f.read()
                if 'GITHUB_TOKEN=' in content:
                    print("✓ GITHUB_TOKEN encontrado en archivo .env")
                else:
                    print("⚠ GITHUB_TOKEN no encontrado en archivo .env")
        else:
            print("⚠ Archivo .env no encontrado")
            print("\nPara usar el actualizador, necesitas configurar GITHUB_TOKEN:")
            print("1. Variable de entorno: export GITHUB_TOKEN=tu_token")
            print("2. Archivo .env: echo 'GITHUB_TOKEN=tu_token' > .env")


def run_update():
    """Ejecuta la actualización de NFE Alert."""
    print("\n=== Ejecutando actualización ===")
    
    # Parámetros de actualización
    owner = "AR-BPS-TaxTech"
    repo = "nfe_alert"
    target_dir = Path.home() / "NFE_Alert"
    
    print(f"Repositorio: {owner}/{repo}")
    print(f"Directorio destino: {target_dir}")
    
    # Construir comando
    cmd = [
        sys.executable, "update.py",
        "--owner", owner,
        "--repo", repo,
        "--target", str(target_dir),
        "--verbose"
    ]
    
    print(f"Comando: {' '.join(cmd)}")
    
    try:
        # Ejecutar actualización
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Actualización completada exitosamente")
            print("\nSalida del script:")
            print(result.stdout)
        else:
            print("❌ Error durante la actualización")
            print(f"Código de salida: {result.returncode}")
            print("\nError:")
            print(result.stderr)
            
        return result.returncode
        
    except Exception as e:
        print(f"❌ Error ejecutando el script: {e}")
        return 1


def main():
    """Función principal del ejemplo."""
    print("Ejemplo de actualización de NFE Alert")
    print("=" * 40)
    
    # Configurar entorno
    setup_environment()
    
    # Preguntar al usuario si desea continuar
    print("\n¿Desea ejecutar la actualización? (y/N): ", end="")
    try:
        respuesta = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nOperación cancelada por el usuario")
        return 0
    
    if respuesta in ('y', 'yes', 'sí', 's'):
        return run_update()
    else:
        print("Actualización cancelada por el usuario")
        print("\nPara ejecutar manualmente:")
        print("python update.py --owner AR-BPS-TaxTech --repo nfe_alert --verbose")
        return 0


if __name__ == "__main__":
    exit(main())