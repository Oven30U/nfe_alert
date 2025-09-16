#!/usr/bin/env python3
"""
Script de actualización en Python que replica la lógica del script PowerShell update.ps1.
Utiliza GITHUB_TOKEN para autenticación y descarga releases desde GitHub.
"""

import argparse
import hashlib
import logging
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import requests


class GitHubReleaseUpdater:
    """Maneja la descarga e instalación de releases desde GitHub."""
    
    def __init__(
        self,
        owner: str,
        repo: str,
        channel_tag: str = "latest",
        target: Optional[str] = None,
        zip_name_pattern: str = "nfe_alert*.zip",
        sha_name_pattern: str = "nfe_alert*.zip.sha256",
        force: bool = False,
        verbose: bool = False
    ):
        """
        Inicializa el actualizador de releases.
        
        Args:
            owner: Propietario del repositorio en GitHub
            repo: Nombre del repositorio
            channel_tag: Tag del release a instalar (por defecto "latest")
            target: Directorio destino (por defecto ~/NFE_Alert)
            zip_name_pattern: Patrón para localizar el archivo ZIP
            sha_name_pattern: Patrón para localizar el archivo SHA256
            force: Forzar reinstalación aunque la versión ya esté instalada
            verbose: Habilitar mensajes verbosos
        """
        self.owner = owner
        self.repo = repo
        self.channel_tag = channel_tag
        self.target = Path(target) if target else Path.home() / "NFE_Alert"
        self.zip_name_pattern = zip_name_pattern
        self.sha_name_pattern = sha_name_pattern
        self.force = force
        self.verbose = verbose
        
        # Configurar logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
        # Configurar headers HTTP
        self.headers = {
            "User-Agent": f"NFE-Alert-Updater/{os.environ.get('COMPUTERNAME', 'Python')}"
        }
        
        # Obtener token de GitHub
        self.token = self._get_github_token()
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
            self.logger.info("Token de GitHub detectado, usando autenticación")
        else:
            self.logger.info("No se detectó token de GitHub, usando descarga pública")
    
    def _get_github_token(self) -> Optional[str]:
        """
        Obtiene el token de GitHub desde variables de entorno o archivo .env.
        
        Returns:
            Token de GitHub o None si no se encuentra
        """
        # Buscar en archivos .env
        env_paths = [
            Path(__file__).parent / '.env',
            Path.cwd() / '.env'
        ]
        
        for env_path in env_paths:
            if env_path.exists():
                self.logger.debug(f"Leyendo .env desde: {env_path}")
                try:
                    with open(env_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('GITHUB_TOKEN='):
                                token = line.split('=', 1)[1].strip()
                                # Quitar comillas si existen
                                if (token.startswith('"') and token.endswith('"')) or \
                                   (token.startswith("'") and token.endswith("'")):
                                    token = token[1:-1]
                                return token
                except Exception as e:
                    self.logger.debug(f"Error leyendo {env_path}: {e}")
        
        # Fallback a variables de entorno del sistema
        return os.environ.get('GITHUB_TOKEN') or os.environ.get('GITHUB_PAT_NFE_UY')
    
    def _get_release_info(self) -> Dict[str, Any]:
        """
        Obtiene información del release desde la API de GitHub.
        
        Returns:
            Información del release
            
        Raises:
            RuntimeError: Si no se puede obtener el release
        """
        api_base = f"https://api.github.com/repos/{self.owner}/{self.repo}/releases"
        
        if self.channel_tag.lower() == "latest":
            rel_url = f"{api_base}/latest"
        else:
            rel_url = f"{api_base}/tags/{self.channel_tag}"
        
        self.logger.info(f"Obteniendo release desde: {rel_url}")
        
        try:
            response = requests.get(rel_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Intentar listar releases como fallback
                self.logger.info("Release específico no encontrado, listando releases...")
                try:
                    response = requests.get(api_base, headers=self.headers, timeout=30)
                    response.raise_for_status()
                    releases = response.json()
                    
                    if not releases:
                        raise RuntimeError("No hay releases disponibles en el repositorio")
                    
                    if self.channel_tag.lower() == "latest":
                        release = releases[0]
                        self.logger.info(f"Usando release fallback: {release['tag_name']}")
                        return release
                    else:
                        # Buscar por tag específico
                        for release in releases:
                            if release['tag_name'] == self.channel_tag:
                                return release
                        raise RuntimeError(f"No se encontró release con tag '{self.channel_tag}'")
                        
                except requests.exceptions.RequestException as inner_e:
                    raise RuntimeError(f"No se pudo obtener releases: {inner_e}")
            else:
                raise RuntimeError(f"Error obteniendo release: {e}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error de conexión: {e}")
    
    def _check_local_version(self, remote_tag: str) -> bool:
        """
        Verifica si ya tenemos la versión remota instalada.
        
        Args:
            remote_tag: Tag del release remoto
            
        Returns:
            True si ya está instalada y no se debe reinstalar
        """
        if self.force:
            return False
            
        local_version_file = self.target / '.nfe_release_tag'
        
        if local_version_file.exists():
            try:
                local_tag = local_version_file.read_text(encoding='utf-8').strip()
                if local_tag == remote_tag:
                    self.logger.info(f"Ya estás en la versión más reciente: {remote_tag}")
                    return True
            except Exception as e:
                self.logger.debug(f"Error leyendo versión local: {e}")
        
        return False
    
    def _find_assets(self, release: Dict[str, Any]) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Encuentra los assets ZIP y SHA en el release.
        
        Args:
            release: Información del release
            
        Returns:
            Tupla con (asset_zip, asset_sha)
        """
        zip_asset = None
        sha_asset = None
        
        for asset in release.get('assets', []):
            name = asset['name']
            if self._matches_pattern(name, self.zip_name_pattern) and not zip_asset:
                zip_asset = asset
            elif self._matches_pattern(name, self.sha_name_pattern) and not sha_asset:
                sha_asset = asset
        
        return zip_asset, sha_asset
    
    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """
        Verifica si un nombre de archivo coincide con un patrón.
        Convierte patrón estilo PowerShell (*) a Python.
        
        Args:
            filename: Nombre del archivo
            pattern: Patrón con wildcards
            
        Returns:
            True si coincide
        """
        import fnmatch
        return fnmatch.fnmatch(filename, pattern)
    
    def _download_asset(self, asset: Dict[str, Any], target_path: Path) -> None:
        """
        Descarga un asset desde GitHub.
        
        Args:
            asset: Información del asset
            target_path: Ruta donde guardar el archivo
        """
        if self.token:
            # Descarga autenticada vía API
            headers = self.headers.copy()
            headers["Accept"] = "application/octet-stream"
            url = asset['url']
            self.logger.info(f"Descargando (API) {asset['name']} -> {target_path}")
        else:
            # Descarga pública
            url = asset['browser_download_url']
            headers = self.headers
            self.logger.info(f"Descargando (público) {asset['name']} -> {target_path}")
        
        try:
            response = requests.get(url, headers=headers, timeout=300, stream=True)
            response.raise_for_status()
            
            with open(target_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error descargando {asset['name']}: {e}")
    
    def _verify_sha256(self, zip_path: Path, sha_path: Path) -> None:
        """
        Verifica el checksum SHA256 del archivo ZIP.
        
        Args:
            zip_path: Ruta del archivo ZIP
            sha_path: Ruta del archivo SHA256
            
        Raises:
            RuntimeError: Si el checksum no coincide
        """
        try:
            sha_content = sha_path.read_text(encoding='utf-8').strip()
            # Extraer el hash (primer token de 64 caracteres hex)
            lines = sha_content.split('\n')
            first_line = lines[0].strip()
            
            expected_hash = None
            # Buscar patrón de 64 caracteres hexadecimales
            import re
            match = re.search(r'([a-fA-F0-9]{64})', first_line)
            if match:
                expected_hash = match.group(1).lower()
            else:
                # Tomar el primer token si no hay patrón
                expected_hash = first_line.split()[0].lower()
            
            # Calcular hash actual
            sha256_hash = hashlib.sha256()
            with open(zip_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            actual_hash = sha256_hash.hexdigest().lower()
            
            self.logger.info(f"SHA256 esperado: {expected_hash}")
            self.logger.info(f"SHA256 actual:   {actual_hash}")
            
            if expected_hash != actual_hash:
                raise RuntimeError("SHA256 no coincide. Descarga corrupta.")
                
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Error verificando SHA256: {e}")
    
    def _extract_and_copy(self, zip_path: Path, temp_dir: Path) -> None:
        """
        Extrae el ZIP y copia el contenido al directorio destino.
        
        Args:
            zip_path: Ruta del archivo ZIP
            temp_dir: Directorio temporal
        """
        extract_dir = temp_dir / "extract"
        extract_dir.mkdir(exist_ok=True)
        
        # Extraer ZIP
        self.logger.info(f"Extrayendo {zip_path} -> {extract_dir}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Detectar si el ZIP contiene una sola carpeta raíz
        children = list(extract_dir.iterdir())
        dirs = [child for child in children if child.is_dir()]
        
        if len(dirs) == 1 and len(children) == 1:
            # ZIP contiene una sola carpeta
            src_dir = dirs[0]
        else:
            # ZIP contiene múltiples elementos en la raíz
            src_dir = extract_dir
        
        if not src_dir.exists():
            raise RuntimeError(f"Directorio de origen no existe: {src_dir}")
        
        # Crear directorio destino
        self.target.mkdir(parents=True, exist_ok=True)
        
        # Copiar archivos (mirror)
        self.logger.info(f"Copiando desde {src_dir} -> {self.target} (mirror)")
        self._copy_directory_contents(src_dir, self.target)
    
    def _copy_directory_contents(self, src: Path, dst: Path) -> None:
        """
        Copia el contenido de un directorio a otro, reemplazando archivos existentes.
        
        Args:
            src: Directorio origen
            dst: Directorio destino
        """
        for item in src.rglob('*'):
            if item.is_file():
                # Calcular ruta relativa y ruta destino
                rel_path = item.relative_to(src)
                dst_path = dst / rel_path
                
                # Crear directorios padre si es necesario
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copiar archivo
                shutil.copy2(item, dst_path)
                self.logger.debug(f"Copiado: {rel_path}")
    
    def _save_version_tag(self, tag: str) -> None:
        """
        Guarda el tag de la versión instalada.
        
        Args:
            tag: Tag de la versión
        """
        version_file = self.target / '.nfe_release_tag'
        try:
            version_file.write_text(tag, encoding='utf-8')
            self.logger.info(f"Tag instalado guardado: {tag}")
        except Exception as e:
            self.logger.warning(f"No se pudo guardar el tag de versión: {e}")
    
    def update(self) -> None:
        """
        Ejecuta el proceso completo de actualización.
        """
        try:
            # 1. Obtener información del release
            release = self._get_release_info()
            remote_tag = release['tag_name']
            
            # 2. Verificar si ya tenemos esta versión
            if self._check_local_version(remote_tag):
                self.logger.info("No es necesario actualizar")
                return
            
            # 3. Encontrar assets
            zip_asset, sha_asset = self._find_assets(release)
            if not zip_asset:
                raise RuntimeError(f"No se encontró archivo ZIP en el release (patrón: {self.zip_name_pattern})")
            
            # 4. Crear directorio temporal
            with tempfile.TemporaryDirectory(prefix="nfe_update_") as temp_dir:
                temp_path = Path(temp_dir)
                
                # 5. Descargar assets
                zip_path = temp_path / zip_asset['name']
                self._download_asset(zip_asset, zip_path)
                
                sha_path = None
                if sha_asset:
                    sha_path = temp_path / sha_asset['name']
                    self._download_asset(sha_asset, sha_path)
                
                # 6. Verificar SHA256 si está disponible
                if sha_path and sha_path.exists():
                    self._verify_sha256(zip_path, sha_path)
                else:
                    self.logger.info("No hay archivo SHA256 disponible, omitiendo verificación")
                
                # 7. Extraer y copiar
                self._extract_and_copy(zip_path, temp_path)
                
                # 8. Guardar tag de versión
                self._save_version_tag(remote_tag)
                
                self.logger.info(f"Actualizado desde {remote_tag} → {self.target}")
                
        except Exception as e:
            self.logger.error(f"Error durante la actualización: {e}")
            raise


def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(
        description="Script de actualización para NFE Alert desde GitHub releases"
    )
    parser.add_argument(
        "--owner", "-o",
        required=True,
        help="Propietario del repositorio en GitHub"
    )
    parser.add_argument(
        "--repo", "-r", 
        required=True,
        help="Nombre del repositorio"
    )
    parser.add_argument(
        "--tag", "-t",
        default="latest",
        help="Tag del release a instalar (por defecto: latest)"
    )
    parser.add_argument(
        "--target",
        help="Directorio destino (por defecto: ~/NFE_Alert)"
    )
    parser.add_argument(
        "--zip-pattern",
        default="nfe_alert*.zip",
        help="Patrón para localizar el archivo ZIP"
    )
    parser.add_argument(
        "--sha-pattern", 
        default="nfe_alert*.zip.sha256",
        help="Patrón para localizar el archivo SHA256"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Forzar reinstalación aunque la versión ya esté instalada"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Habilitar salida verbosa"
    )
    
    args = parser.parse_args()
    
    # Configurar logging para el log file
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"update-{timestamp}.log"
    
    # Configurar logging dual (consola + archivo)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Obtener el logger root y agregar el handler de archivo
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    
    try:
        updater = GitHubReleaseUpdater(
            owner=args.owner,
            repo=args.repo,
            channel_tag=args.tag,
            target=args.target,
            zip_name_pattern=args.zip_pattern,
            sha_name_pattern=args.sha_pattern,
            force=args.force,
            verbose=args.verbose
        )
        
        updater.update()
        
        # Log de finalización exitosa
        root_logger.info("Actualización completada exitosamente")
        print(f"Log guardado en: {log_file}")
        
    except Exception as e:
        root_logger.error(f"Error en la actualización: {e}")
        print(f"Error: {e}")
        print(f"Log guardado en: {log_file}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())