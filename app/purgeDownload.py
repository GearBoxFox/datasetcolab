import os
import json
import subprocess

json_file_path = "/home/team4169/datasetcolab/app/important.json"
download_folder_path = "/home/team4169/datasetcolab/app/download"

with open(json_file_path, "r") as json_file:
    important_data = json.load(json_file)

values = [value for value in important_data.values() if isinstance(value, str)]
valueszip = [value + ".zip" for value in values]

for folder in os.listdir(download_folder_path):
    folder_path = os.path.join(download_folder_path, folder)
    if os.path.isdir(folder_path) and folder not in values:
        subprocess.run(["rm", "-fr", folder_path])
    elif os.path.isfile(folder_path) and folder not in valueszip:
        subprocess.run(["rm", "-fr", folder_path])