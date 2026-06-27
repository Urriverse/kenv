"""
Download and extract archives (tar.gz, zip).
"""
import os
import shutil
import requests
import tarfile
import zipfile


def download_and_extract(url: str, target_dir: str, config_env: dict[str, str]):
    """
    Download archive from URL and extract into target_dir.
    Supports .tar.gz and .zip.
    """
    os.makedirs(target_dir, exist_ok=True)
    # Substitute env variables in url
    try:
        url = url.format(**config_env)
    except KeyError:
        pass

    # Download to temporary file
    response = requests.get(url, stream=True)
    response.raise_for_status()
    temp_file = os.path.join(target_dir, "download_temp")
    with open(temp_file, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    # Extract based on extension
    if url.endswith('.tar.gz') or url.endswith('.tgz'):
        with tarfile.open(temp_file, 'r:gz') as tar:
            tar.extractall(path=target_dir)
    elif url.endswith('.zip'):
        with zipfile.ZipFile(temp_file, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
    else:
        raise ValueError(f"Unsupported archive format: {url}")
    
    # safety from situations when archive consist of only one directory (nested archive) with all content.
    if len(os.listdir(target_dir)) == 1 and os.path.isdir(os.path.join(target_dir, os.listdir(target_dir)[0])):
        shutil.copytree(os.path.join(target_dir, os.listdir(target_dir)[0], "*"), target_dir)
        shutil.rmtree(os.path.join(target_dir, os.listdir(target_dir)[0]))

    os.remove(temp_file)
