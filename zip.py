import logging
import subprocess
from rclone import execute


def zip_file(source: str, destination: str):
    return_code = execute(f'7z a "{destination}" "{source}" -mx=0 -mmt=8 -r')
    if return_code != 0:
        logging.error(f"7z a {destination} {source} failed with return code {return_code}")
        return False
    return True


