import logging
import subprocess
from typing import List


def execute(command: str, get_output=False):
    if get_output:
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE)
        return result.stdout.decode('utf-8'), result.returncode
    else:
        result = subprocess.run(command, shell=True)
        return result.returncode


def copy_file(source: str or List[str], destination: str):
    if isinstance(source, str):
        return_code = execute(f'rclone copy "{source}" "{destination}" -P')
        if return_code != 0:
            logging.error(f"rclone copy {source} {destination} failed with return code {return_code}")
            return False
        return True
    # 需要为同一drive的同一文件夹内的文件
    else:
        with open("list.txt", "w") as f:
            for i in source:
                f.write(i.rsplit("/", 1)[-1] + "\n")
        drive = source[0].rsplit("/", 1)[0] + "/"
        return_code = execute(f'rclone copy "{drive}" "{destination}" --include-from=list.txt -P')
        if return_code != 0:
            logging.error(f"rclone copy {drive} {destination} failed with return code {return_code}")
            return False
        return True


def ls(path: str, max_depth=20):
    if not path.endswith("/") and not path.endswith("\\"):
        path += "/"
    output, return_code = execute(f'rclone ls "{path}" --max-depth={max_depth}', get_output=True)
    if return_code != 0:
        logging.error(f"rclone ls {path} failed with return code {return_code}")
        return []
    files_path = output.split('\n')
    file_and_size = [[int(i.strip().split(" ", 1)[0]), path + i.strip().split(" ", 1)[-1]] for i in files_path if i != '']
    return file_and_size
