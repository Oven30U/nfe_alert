#!/usr/bin/env python3
"""
Update script for NFE Alert - Python version
Reimplementation of update.ps1 with improved portability and flexibility
"""

import argparse
import hashlib
import json
import logging
import os
import shutil
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urljoin

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UpdateManager:
    """Manages the update process for NFE Alert from GitHub releases."""
    
    def __init__(
        self,
        owner: str,
        repo: str,
        channel_tag: str = "latest",
        target: Optional[str] = None,
        zip_name_pattern: str = "nfe_alert*.zip",
        sha_name_pattern: str = "nfe_alert*.zip.sha256",
        temp_root: Optional[str] = None,
        cleanup: bool = True,
        force: bool = False,
        verbose: bool = False
    ):
        """
        Initialize the UpdateManager.
        
        Args:
            owner: GitHub repository owner
            repo: GitHub repository name
            channel_tag: Release tag to install (default: "latest")
            target: Target directory for installation
            zip_name_pattern: Pattern to match ZIP asset names
            sha_name_pattern: Pattern to match SHA256 asset names
            temp_root: Root directory for temporary files
            cleanup: Whether to clean up temporary files
            force: Force reinstallation even if already up to date
            verbose: Enable verbose logging
        """
        self.owner = owner
        self.repo = repo
        self.channel_tag = channel_tag
        self.target = Path(target) if target else Path.home() / "NFE_Alert"
        self.zip_name_pattern = zip_name_pattern
        self.sha_name_pattern = sha_name_pattern
        self.temp_root = temp_root or tempfile.gettempdir()
        self.cleanup = cleanup
        self.force = force
        self.verbose = verbose
        
        if self.verbose:
            logger.setLevel(logging.DEBUG)
        
        # GitHub API configuration
        self.api_base = f"https://api.github.com/repos/{owner}/{repo}/releases"
        self.headers = {
            "User-Agent": f"nfe-alert-updater/{os.environ.get('COMPUTERNAME', 'python-client')}"
        }
        
        # Setup GitHub token
        self._setup_github_token()
    
    def _setup_github_token(self) -> None:
        """Setup GitHub authentication token from .env file or environment variables."""
        token = None
        
        # Try to read token from .env files
        script_dir = Path(__file__).parent
        env_paths = [
            script_dir / '.env',
            Path.cwd() / '.env'
        ]
        
        for env_path in env_paths:
            if env_path.exists():
                logger.debug(f"Reading .env from: {env_path}")
                try:
                    with open(env_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('GITHUB_TOKEN='):
                                token_value = line.split('=', 1)[1].strip()
                                # Remove quotes if present
                                if (token_value.startswith('"') and token_value.endswith('"')) or \
                                   (token_value.startswith("'") and token_value.endswith("'")):
                                    token_value = token_value[1:-1]
                                token = token_value
                                break
                    if token:
                        break
                except Exception as e:
                    logger.debug(f"Error reading .env file {env_path}: {e}")
        
        # Fallback to environment variables
        if not token:
            token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GITHUB_PAT_NFE_UY')
            if token:
                logger.debug("Using GitHub token from environment variables (fallback)")
        
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
            logger.debug("Authorization header prepared (token detected)")
        else:
            logger.debug("No GitHub token detected; attempting public download")
    
    def _match_pattern(self, name: str, pattern: str) -> bool:
        """Simple glob-like pattern matching for asset names."""
        import fnmatch
        return fnmatch.fnmatch(name, pattern)
    
    def _get_release(self) -> Dict[str, Any]:
        """
        Get release information from GitHub API.
        
        Returns:
            Release information dictionary
            
        Raises:
            Exception: If release cannot be found
        """
        # Try specific endpoint first
        if self.channel_tag.lower() == "latest":
            url = f"{self.api_base}/latest"
        else:
            url = f"{self.api_base}/tags/{self.channel_tag}"
        
        logger.debug(f"Getting release from: {url}")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Fallback to listing all releases
            if self.channel_tag.lower() == "latest":
                logger.debug(f"Failed to get latest release: {e}. Trying to list releases...")
                try:
                    response = requests.get(self.api_base, headers=self.headers)
                    response.raise_for_status()
                    releases = response.json()
                    if releases:
                        release = releases[0]
                        logger.debug(f"Using fallback release: {release['tag_name']}")
                        return release
                    else:
                        raise Exception("No releases available in the repository")
                except requests.exceptions.RequestException as list_error:
                    raise Exception(f"Could not get latest release or list releases: {list_error}")
            else:
                logger.debug(f"Failed to get release by tag ({self.channel_tag}). Trying to list releases...")
                try:
                    response = requests.get(self.api_base, headers=self.headers)
                    response.raise_for_status()
                    releases = response.json()
                    for release in releases:
                        if release['tag_name'] == self.channel_tag:
                            return release
                    raise Exception(f"No release found with tag '{self.channel_tag}'")
                except requests.exceptions.RequestException as list_error:
                    raise Exception(f"Could not find release with tag '{self.channel_tag}': {list_error}")
    
    def _check_local_version(self, remote_tag: str) -> bool:
        """
        Check if local version matches remote version.
        
        Args:
            remote_tag: Remote release tag
            
        Returns:
            True if update is needed, False if already up to date
        """
        local_version_file = self.target / '.nfe_release_tag'
        
        if not self.force and local_version_file.exists():
            try:
                local_tag = local_version_file.read_text(encoding='utf-8').strip()
                if local_tag == remote_tag:
                    logger.info(f"Already up to date: {remote_tag}. Use --force to reinstall.")
                    return False
            except Exception as e:
                logger.debug(f"Error reading local version file: {e}")
        
        return True
    
    def _find_assets(self, release: Dict[str, Any]) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Find ZIP and SHA assets in the release.
        
        Args:
            release: Release information dictionary
            
        Returns:
            Tuple of (zip_asset, sha_asset) or (None, None) if not found
        """
        zip_asset = None
        sha_asset = None
        
        for asset in release.get('assets', []):
            asset_name = asset['name']
            if self._match_pattern(asset_name, self.zip_name_pattern):
                zip_asset = asset
            elif self._match_pattern(asset_name, self.sha_name_pattern):
                sha_asset = asset
        
        if not zip_asset:
            raise Exception(f"No ZIP asset found matching pattern: {self.zip_name_pattern}")
        
        return zip_asset, sha_asset
    
    def _download_file(self, asset: Dict[str, Any], output_path: Path) -> None:
        """
        Download an asset file.
        
        Args:
            asset: Asset information dictionary
            output_path: Path where to save the file
        """
        if "Authorization" in self.headers:
            # Use API download for authenticated requests
            headers = self.headers.copy()
            headers["Accept"] = "application/octet-stream"
            url = asset['url']
            logger.debug(f"Downloading (API) {asset['name']} -> {output_path}")
        else:
            # Use browser download URL for public assets
            url = asset['browser_download_url']
            headers = {}
            logger.debug(f"Downloading (public) {asset['name']} -> {output_path}")
        
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    
    def _verify_sha256(self, zip_path: Path, sha_path: Path) -> None:
        """
        Verify ZIP file SHA256 checksum.
        
        Args:
            zip_path: Path to ZIP file
            sha_path: Path to SHA256 file
            
        Raises:
            Exception: If SHA256 verification fails
        """
        if not sha_path.exists():
            logger.debug("No SHA256 file found, skipping verification")
            return
        
        # Read expected SHA256
        sha_content = sha_path.read_text(encoding='utf-8').strip()
        lines = sha_content.replace('\r', '').split('\n')
        first_line = lines[0].strip()
        
        # Try to extract 64-character hex string
        import re
        hex_match = re.search(r'([a-fA-F0-9]{64})', first_line)
        if hex_match:
            expected_sha = hex_match.group(1).upper()
        else:
            expected_sha = first_line.split(' ')[0].upper()
        
        logger.debug(f"Expected SHA256: {expected_sha}")
        
        # Calculate actual SHA256
        sha256_hash = hashlib.sha256()
        with open(zip_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        actual_sha = sha256_hash.hexdigest().upper()
        logger.debug(f"Actual SHA256:   {actual_sha}")
        
        if expected_sha != actual_sha:
            raise Exception("SHA256 checksum mismatch. Download may be corrupted.")
    
    def _extract_and_copy(self, zip_path: Path, temp_dir: Path) -> None:
        """
        Extract ZIP file and copy contents to target directory.
        
        Args:
            zip_path: Path to ZIP file
            temp_dir: Temporary directory for extraction
        """
        extract_dir = temp_dir / "extract"
        extract_dir.mkdir(exist_ok=True)
        
        # Extract ZIP file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Determine source directory
        contents = list(extract_dir.iterdir())
        if len(contents) == 1 and contents[0].is_dir():
            # ZIP contains single root directory
            src_dir = contents[0]
        else:
            # ZIP contains multiple items at root
            src_dir = extract_dir
        
        if not src_dir.exists():
            raise Exception(f"Source directory does not exist: {src_dir}")
        
        # Create target directory
        self.target.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"Copying from {src_dir} -> {self.target} (mirror)")
        
        # Copy files (mirror operation)
        if self.target.exists():
            # Remove existing files but keep the directory
            for item in self.target.iterdir():
                if item.name != '.nfe_release_tag':  # Preserve version file during copy
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
        
        # Copy new files
        for item in src_dir.iterdir():
            dest = self.target / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
    
    def _save_version_tag(self, tag: str) -> None:
        """
        Save the installed version tag to local file.
        
        Args:
            tag: Version tag to save
        """
        version_file = self.target / '.nfe_release_tag'
        try:
            logger.debug(f"Writing installed tag to: {version_file}")
            self.target.mkdir(parents=True, exist_ok=True)
            version_file.write_text(tag, encoding='utf-8')
        except Exception as e:
            logger.warning(f"Could not write version file {version_file}: {e}")
    
    def update(self) -> None:
        """
        Perform the update process.
        
        Raises:
            Exception: If update process fails
        """
        logger.info("Starting NFE Alert update process...")
        
        # 1. Get release information
        release = self._get_release()
        remote_tag = release['tag_name']
        logger.info(f"Found release: {remote_tag}")
        
        # 2. Check if update is needed
        if not self._check_local_version(remote_tag):
            return
        
        # 3. Find assets
        zip_asset, sha_asset = self._find_assets(release)
        logger.debug(f"Found ZIP asset: {zip_asset['name']}")
        if sha_asset:
            logger.debug(f"Found SHA256 asset: {sha_asset['name']}")
        
        # 4. Create temporary directory
        temp_dir = Path(self.temp_root) / f"app_update_{uuid.uuid4()}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created temporary directory: {temp_dir}")
        
        try:
            # 5. Download files
            zip_path = temp_dir / zip_asset['name']
            self._download_file(zip_asset, zip_path)
            
            sha_path = None
            if sha_asset:
                sha_path = temp_dir / sha_asset['name']
                self._download_file(sha_asset, sha_path)
            
            # 6. Verify SHA256 if available
            if sha_path:
                self._verify_sha256(zip_path, sha_path)
            
            # 7. Extract and copy files
            self._extract_and_copy(zip_path, temp_dir)
            
            # 8. Save version tag
            self._save_version_tag(remote_tag)
            
            logger.info(f"Update completed: {remote_tag} → {self.target}")
            
        finally:
            # 9. Cleanup temporary files
            if self.cleanup and temp_dir.exists():
                logger.debug(f"Cleaning up temporary files: {temp_dir}")
                shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> None:
    """Main entry point for the update script."""
    parser = argparse.ArgumentParser(
        description="Update NFE Alert from GitHub releases",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--owner",
        required=True,
        help="GitHub repository owner"
    )
    
    parser.add_argument(
        "--repo", 
        required=True,
        help="GitHub repository name"
    )
    
    parser.add_argument(
        "--channel-tag",
        default="latest",
        help="Release tag to install"
    )
    
    parser.add_argument(
        "--target",
        help="Target directory for installation (default: ~/NFE_Alert)"
    )
    
    parser.add_argument(
        "--zip-name-pattern",
        default="nfe_alert*.zip",
        help="Pattern to match ZIP asset names"
    )
    
    parser.add_argument(
        "--sha-name-pattern", 
        default="nfe_alert*.zip.sha256",
        help="Pattern to match SHA256 asset names"
    )
    
    parser.add_argument(
        "--temp-root",
        help="Root directory for temporary files"
    )
    
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Do not clean up temporary files"
    )
    
    parser.add_argument(
        "--force",
        action="store_true", 
        help="Force reinstallation even if already up to date"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    try:
        updater = UpdateManager(
            owner=args.owner,
            repo=args.repo,
            channel_tag=args.channel_tag,
            target=args.target,
            zip_name_pattern=args.zip_name_pattern,
            sha_name_pattern=args.sha_name_pattern,
            temp_root=args.temp_root,
            cleanup=not args.no_cleanup,
            force=args.force,
            verbose=args.verbose
        )
        
        updater.update()
        
    except KeyboardInterrupt:
        logger.error("Update cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Update failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()