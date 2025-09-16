import os
import requests
import zipfile
import shutil
import logging


def setup_logging():
    logging.basicConfig(
        filename="update_log.txt",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def get_github_release(owner: str, repo: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def download_file(url: str, output_path: str):
    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        with open(output_path, "wb") as file:
            shutil.copyfileobj(response.raw, file)


def extract_zip(zip_path: str, extract_to: str):
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        # Detecta si todo el contenido está dentro de una sola carpeta raíz
        all_names = [
            member.filename
            for member in zip_ref.infolist()
            if member.filename and not member.is_dir()
        ]
        if not all_names:
            return
        common_prefix = os.path.commonprefix(all_names)
        # Ajusta el prefijo para que sea una carpeta completa
        if common_prefix and not common_prefix.endswith("/"):
            common_prefix = os.path.dirname(common_prefix) + "/"

        for member in zip_ref.infolist():
            # Si hay una carpeta raíz común, quítala del path de destino
            rel_path = (
                member.filename[len(common_prefix) :]
                if common_prefix and member.filename.startswith(common_prefix)
                else member.filename
            )
            if not rel_path or rel_path.endswith("/"):
                # Es una carpeta
                dir_path = os.path.join(extract_to, rel_path)
                os.makedirs(dir_path, exist_ok=True)
                continue
            extracted_path = os.path.join(extract_to, rel_path)
            os.makedirs(os.path.dirname(extracted_path), exist_ok=True)
            with zip_ref.open(member) as source, open(extracted_path, "wb") as target:
                shutil.copyfileobj(source, target)


def main():
    setup_logging()

    owner = os.getenv("GITHUB_OWNER", "AR-BPS-TaxTech")
    repo = os.getenv("GITHUB_REPO", "nfe_alert")

    try:
        release = get_github_release(owner, repo)
        assets = release.get("assets", [])
        asset_names = [asset.get("name", "") for asset in assets]
        logging.info(f"Assets found in latest release: {asset_names}")

        if not assets:
            logging.error("No assets found in the latest release.")
            return

        zip_asset = next(
            (asset for asset in assets if asset.get("name", "").endswith(".zip")), None
        )

        if not zip_asset:
            logging.error("No ZIP file found in the latest release assets.")
            return

        zip_url = zip_asset.get("browser_download_url")
        zip_name = zip_asset.get("name")
        if not zip_url or not zip_name:
            logging.error("ZIP asset is missing download URL or name.")
            return

        zip_path = os.path.join(os.getcwd(), zip_name)

        logging.info(f"Downloading {zip_name} from {zip_url} ...")
        try:
            download_file(zip_url, zip_path)
        except Exception as e:
            logging.error(f"Failed to download ZIP file: {e}")
            return

        logging.info(f"Extracting {zip_name}...")
        try:
            extract_zip(zip_path, os.getcwd())
        except zipfile.BadZipFile:
            logging.error("Failed to extract ZIP file. The file may be corrupted.")
            return
        except Exception as e:
            logging.error(f"Unexpected error extracting ZIP: {e}")
            return

        logging.info("Update completed successfully.")
    except requests.RequestException as e:
        logging.error(f"HTTP error occurred: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
