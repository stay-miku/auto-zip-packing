import logging
import subprocess


def execute(command: str, get_output=False):
    if get_output:
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE)
        return result.stdout.decode('utf-8'), result.returncode
    else:
        result = subprocess.run(command, shell=True)
        return result.returncode


def copy_file(source: str, destination: str):
    return_code = execute(f'rclone copy "{source}" "{destination}" -P')
    if return_code != 0:
        logging.error(f"rclone copy {source} {destination} failed with return code {return_code}")
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
