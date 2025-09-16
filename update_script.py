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


def get_github_release(owner: str, repo: str, token: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def download_file(url: str, output_path: str):
    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        with open(output_path, "wb") as file:
            shutil.copyfileobj(response.raw, file)


def extract_zip(zip_path: str, extract_to: str):
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)


def main():
    setup_logging()

    owner = os.getenv("GITHUB_OWNER", "AR-BPS-TaxTech")
    repo = os.getenv("GITHUB_REPO", "nfe_alert")
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        logging.error("GITHUB_TOKEN environment variable not set.")
        return

    try:
        release = get_github_release(owner, repo, token)
        zip_asset = next(
            (asset for asset in release["assets"] if asset["name"].endswith(".zip")),
            None,
        )

        if not zip_asset:
            logging.info("No ZIP file found in the latest release.")
            return

        zip_url = zip_asset["browser_download_url"]
        zip_name = zip_asset["name"]
        zip_path = os.path.join(os.getcwd(), zip_name)

        logging.info(f"Downloading {zip_name}...")
        download_file(zip_url, zip_path)

        logging.info(f"Extracting {zip_name}...")
        extract_zip(zip_path, os.getcwd())

        logging.info("Update completed successfully.")
    except requests.RequestException as e:
        logging.error(f"HTTP error occurred: {e}")
    except zipfile.BadZipFile:
        logging.error("Failed to extract ZIP file. The file may be corrupted.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
