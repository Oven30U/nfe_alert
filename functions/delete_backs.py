import os
import glob
from functions.config import PATH_ESTRUCTURA_ROBOT

def delete_zip_files_in_backup(directory):
    for root, dirs, files in os.walk(directory):
        if os.path.basename(root) == "Backup":
            zip_files = glob.glob(os.path.join(root, "*.zip"))
            for zip_file in zip_files:
                try:
                    os.remove(zip_file)
                    # print(f"Deleted: {zip_file}")
                except Exception as e:
                    print(f"Error deleting {zip_file}: {e}")

if __name__ == '__main__':
    directory_path = r"C:\Users\lmarinaro\OneDrive - Deloitte (O365D)\Documents\Proyectos\test_robot_framework\dfe\Estructura-robot"
    delete_zip_files_in_backup(directory_path)