import json, sys, os, shutil, random, string, datetime, concurrent.futures, zipfile, subprocess, itertools, time
from PIL import Image
from glob import glob

def findJsonFile(path):
    """ Find the first JSON file in the given directory. """
    jsonFiles = glob(os.path.join(path, '*.json'))
    return jsonFiles[0] if jsonFiles else None

def copy_image(image_info, dataset_path, output_path):
    image_path = os.path.join(dataset_path, image_info['file_name'])
    if os.path.exists(image_path):
        shutil.copy(image_path, os.path.join(output_path, image_info['file_name']))


def mergeCocoDatasets(dataset_paths, output_path):
    merged_data = {
        'images': [],
        'annotations': [],
        'categories': [{"name": "objects", "supercategory": "none", "id": 0}]
    }

    max_image_id = 0
    max_annotation_id = 0

    updated_dataset_paths = []

    for dataset_path in dataset_paths:
        json_file = findJsonFile(dataset_path)
        if not json_file:
            print(f"No JSON file found in {dataset_path}. Skipping this dataset.")
            continue
        else:
            updated_dataset_paths.append(dataset_path)

        # Load JSON data
        with open(json_file) as file:
            data = json.load(file)

        # Set categories from the first dataset (assuming all datasets have the same categories)
        for category in data['categories']:
            if category["name"] not in [cat["name"] for cat in merged_data['categories']] and category["supercategory"] != "none":
                merged_data['categories'].append({ "name": category["name"], "supercategory": "objects", "id": len(merged_data['categories']) })

    for dataset_path in updated_dataset_paths:
        json_file = findJsonFile(dataset_path)
        if not json_file:
            print(f"No JSON file found in {dataset_path}. Skipping this dataset.")
            continue

        with open(json_file) as file:
            data = json.load(file)

        # Update IDs in the dataset
        id_mapping = {}
        for image in data['images']:
            old_id = image['id']
            new_id = old_id + max_image_id
            id_mapping[old_id] = new_id
            image['id'] = new_id
            merged_data['images'].append(image)

        for annotation in data['annotations']:
            category_name = None
            for category in data['categories']:
                if category['id'] == annotation['category_id']:
                    category_name = category['name']
                    break

            if category_name is not None:
                for category in merged_data['categories']:
                    if category['name'] == category_name:
                        annotation['category_id'] = category['id']
                        break
                else:
                    print(f"Category '{category_name}' not found in merged data.")
            else:
                print("Category name is None.")

            annotation['id'] += max_annotation_id
            annotation['image_id'] = id_mapping[annotation['image_id']]
            merged_data['annotations'].append(annotation)

        # Remove images without annotations
        merged_data['images'] = [image for image in merged_data['images'] if any(annotation['image_id'] == image['id'] for annotation in merged_data['annotations'])]

        # Update max ID values for the next dataset
        max_image_id = max([img['id'] for img in merged_data['images']], default=max_image_id)
        max_annotation_id = max([ann['id'] for ann in merged_data['annotations']], default=max_annotation_id)

        # Copy images to output folder
        os.makedirs(output_path, exist_ok=True)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for image_info in merged_data['images']:
                future = executor.submit(copy_image, image_info, dataset_path, output_path)
                futures.append(future)

            # Wait for all tasks to complete
            concurrent.futures.wait(futures)

    # Save merged JSON
    with open(os.path.join(output_path, '_annotations.coco.json'), 'w') as file:
        json.dump(merged_data, file)

def findMetadataFolders(directoryPath, year, classcombo):
    matchingMetadataFolders = []

    for root, dirs, files in os.walk(directoryPath):
        if 'metadata.json' in files:
            metadataFilePath = os.path.join(root, 'metadata.json')
            with open(metadataFilePath, 'r') as f:
                metadata = json.load(f)

            # Assuming 'targetDataset' is a key in metadata.json
            targetDatasetValue = metadata.get('targetDataset')
            classes = metadata.get('classes')
            status = metadata.get('status')

            if targetDatasetValue == year and status == 'merged' and set(classcombo).issubset(set(classes)):
                matchingMetadataFolders.append(root)
            
    return matchingMetadataFolders


def zipDataset(dataset_path, output_path):
    with zipfile.ZipFile(output_path, 'w') as zipf:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for root, dirs, files in os.walk(dataset_path):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), dataset_path))

def countImages(folder_path):
    image_count = 0
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(('.jpg', '.jpeg', '.png')):
                image_count += 1
    return image_count

def countAnnotations(folder_path):
    annotation_count = 0
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.json'):
                with open(os.path.join(root, file), 'r') as f:
                    data = json.load(f)
                    annotation_count += len(data['annotations'])
    return annotation_count

def powerset(iterable):
    s = list(iterable)
    return [list(combo) for r in range(len(s)+1) for combo in itertools.combinations(s, r) if combo]

years = ["FRC2024"] # "FRC2023", 
classes = {"FRC2023": ["cone", "cube", "robot"], "FRC2024": ["note", "robot"]}
tempNamesCOCO = {"FRC2023": [], "FRC2024": []}
tempNamesYOLO = {"FRC2023": [], "FRC2024": []}
tempNamesTFRecord = {"FRC2023": [], "FRC2024": []}

for year in years:
    print(powerset(classes[year]))
    for classcombo in powerset(classes[year]):
        print(year, classcombo)
        tempNamesCOCO[year].append(''.join(random.choices(string.ascii_lowercase + string.digits, k=4)))
        tempNamesYOLO[year].append(''.join(random.choices(string.ascii_lowercase + string.digits, k=4)))
        tempNamesTFRecord[year].append(''.join(random.choices(string.ascii_lowercase + string.digits, k=4)))

        # Combine COCO
        print("Combining COCO (" + tempNamesCOCO[year][-1] + ")")
        directoryPath = '/home/team4169/datasetcolab/app/upload'
        metadataFolders = findMetadataFolders(directoryPath, year, classcombo)
        testFolders = [s + "/test" for s in metadataFolders]
        trainFolders = [s + "/train" for s in metadataFolders]
        validFolders = [s + "/valid" for s in metadataFolders]

        outputPathCOCO = '/home/team4169/datasetcolab/app/download/' + tempNamesCOCO[year][-1]
        mergeCocoDatasets(testFolders, outputPathCOCO + "/test")
        mergeCocoDatasets(trainFolders, outputPathCOCO + "/train")
        mergeCocoDatasets(validFolders, outputPathCOCO + "/valid")

        test_image_count = countImages(outputPathCOCO + "/test")
        train_image_count = countImages(outputPathCOCO + "/train")
        valid_image_count = countImages(outputPathCOCO + "/valid")
        test_annotation_count = countAnnotations(outputPathCOCO + "/test")
        train_annotation_count = countAnnotations(outputPathCOCO + "/train")
        valid_annotation_count = countAnnotations(outputPathCOCO + "/valid")

        metadata = {
            "folderName": tempNamesCOCO[year][-1],
            "classes": classcombo,
            "testImageCount": test_image_count,
            "trainImageCount": train_image_count,
            "validImageCount": valid_image_count,
            "totalImageCount": test_image_count + train_image_count + valid_image_count,
            "testAnnotationCount": test_annotation_count,
            "trainAnnotationCount": train_annotation_count,
            "validAnnotationCount": valid_annotation_count,
            "totalAnnotationCount": test_annotation_count + train_annotation_count + valid_annotation_count,
        }

        metadataFilePath = outputPathCOCO + '/metadata.json'
        with open(metadataFilePath, 'w') as f:
            json.dump(metadata, f)

        zipDataset(outputPathCOCO, outputPathCOCO + '.zip')

        coco_zip_size = os.path.getsize(outputPathCOCO + '.zip')
        metadata["zipSize"] = coco_zip_size
        metadata["datasetType"] = "COCO"
        metadata["uploadName"] = year + "COCO" + ''.join([class_name[:2].upper() for class_name in classcombo])

        metadataFilePathCOCO = outputPathCOCO + '/metadata.json'
        with open(metadataFilePathCOCO, 'w') as f:
            json.dump(metadata, f)

        # Convert to YOLO
        print("Converting to YOLO (" + tempNamesYOLO[year][-1] + ")")
        outputPathYOLO = '/home/team4169/datasetcolab/app/download/' + tempNamesYOLO[year][-1]
        shutil.copytree(outputPathCOCO, outputPathYOLO)
        command = ['python3', 'COCOtoYOLO.py', outputPathYOLO, year]
        command.extend(classcombo)
        subprocess.run(command)
        
        zipDataset(outputPathYOLO, outputPathYOLO + '.zip')
        metadata["zipSize"] = os.path.getsize(outputPathYOLO + '.zip')
        metadata["datasetType"] = "YOLO"
        metadata["uploadName"] = year + "YOLO" + ''.join([class_name[:2].upper() for class_name in classcombo])

        metadataFilePathYOLO = outputPathYOLO + '/metadata.json'
        with open(metadataFilePathYOLO, 'w') as f:
            json.dump(metadata, f)

        # Convert to TFRecord
        print("Converting to TFRecord (" + tempNamesTFRecord[year][-1] + ")")
        outputPathTFRecord = '/home/team4169/datasetcolab/app/download/' + tempNamesTFRecord[year][-1]
        subprocess.run(['python3', 'COCOtoTFRecord.py', "--annotation_info_file=" + outputPathCOCO + "/train/_annotations.coco.json", "--image_dir=" + outputPathCOCO + "/train", "--output_dir=" + outputPathTFRecord + "/train", "--shards=800"])
        subprocess.run(['python3', 'COCOtoTFRecord.py', "--annotation_info_file=" + outputPathCOCO + "/test/_annotations.coco.json", "--image_dir=" + outputPathCOCO + "/test", "--output_dir=" + outputPathTFRecord + "/test", "--shards=800"])
        subprocess.run(['python3', 'COCOtoTFRecord.py', "--annotation_info_file=" + outputPathCOCO + "/valid/_annotations.coco.json", "--image_dir=" + outputPathCOCO + "/valid", "--output_dir=" + outputPathTFRecord + "/valid", "--shards=800"])

        zipDataset(outputPathTFRecord, outputPathTFRecord + '.zip')
        metadata["zipSize"] = os.path.getsize(outputPathTFRecord + '.zip')
        metadata["datasetType"] = "TFRecord"
        metadata["uploadName"] = year + "TFRecord" + ''.join([class_name[:2].upper() for class_name in classcombo])

        metadataFilePathTFRecord = outputPathTFRecord + '/metadata.json'
        with open(metadataFilePathTFRecord, 'w') as f:
            json.dump(metadata, f)

currentDatasetPath = '/home/team4169/datasetcolab/app/important.json'
with open(currentDatasetPath, 'r') as f:
    currentDataset = json.load(f)

for i, year in enumerate(years):
    for j, classes in enumerate(powerset(classes[year])):
        classcombo = ''.join([class_name[:2].upper() for class_name in classes])
        for dataset in ["COCO", "YOLO", "TFRecord"]:
            oldDatasetPath = None
            try:
                oldDatasetPath = '/home/team4169/datasetcolab/app/download/' + currentDataset[year + dataset + classcombo]
            except:
                pass

            if dataset == "COCO":
                currentDataset[year + dataset + classcombo] = tempNamesCOCO[year][j]
            elif dataset == "YOLO":
                currentDataset[year + dataset + classcombo] = tempNamesYOLO[year][j]
            elif dataset == "TFRecord":
                currentDataset[year + dataset + classcombo] = tempNamesTFRecord[year][j]

            with open(currentDatasetPath, 'w') as f:
                json.dump(currentDataset, f)

            try:
                os.system('rm -fr ' + oldDatasetPath)
                if os.path.exists(oldDatasetPath + '.zip'):
                    os.remove(oldDatasetPath + '.zip')
            except:
                pass
