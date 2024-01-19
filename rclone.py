import json
import logging
import subprocess
from typing import List
import asyncio


async def execute(command: str, get_output=False):
    logging.info(f"executing: {command}, get_output: {get_output}")
    if get_output:
        # result = subprocess.run(command, shell=True, stdout=subprocess.PIPE)
        process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, shell=True)
        stdout, stderr = await process.communicate()
        logging.debug(stdout.decode('utf-8') + stderr.decode('utf-8'))
        return stdout.decode('utf-8') + stderr.decode('utf-8'), process.returncode
    else:
        # process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # last_output = ""
        # while True:
        #     output = process.stdout.readline()
        #     if output == '' and process.poll() is not None:
        #         break
        #     if output:
        #         last_output = output.strip()
        #         print(output.strip(), end="")
        # process.wait()
        # if process.returncode != 0:
        #     logging.error(last_output)
        # logging.info(last_output)
        # return process.returncode
        # result = subprocess.run(command, shell=True)
        process = await asyncio.create_subprocess_shell(command, shell=True)
        stdout, stderr = await process.communicate()
        return process.returncode


async def copy_file(source: str or List[str], destination: str, thread_name: str):
    if isinstance(source, str):
        return_code = await execute(f'rclone copy "{source}" "{destination}" -P')
        if return_code != 0:
            logging.error(f"rclone copy {source} {destination} failed with return code {return_code}")
            return False
        return True
    # 需要为同一drive的同一文件夹内的文件
    else:
        with open(f"list-{thread_name}.txt", "w") as f:
            for i in source:
                f.write(i.rsplit("/", 1)[-1] + "\n")
        drive = source[0].rsplit("/", 1)[0] + "/"
        return_code = await execute(f'rclone copy "{drive}" "{destination}" --include-from=list-{thread_name}.txt -P')
        if return_code != 0:
            logging.error(f"rclone copy {drive} {destination} failed with return code {return_code}")
            return False
        return True


async def ls(path: str, max_depth=20):
    if not path.endswith("/") and not path.endswith("\\"):
        path += "/"
    output, return_code = await execute(f'rclone ls "{path}" --max-depth={max_depth}', get_output=True)
    if return_code != 0:
        logging.error(f"rclone ls {path} failed with return code {return_code}")
        return []
    files_path = output.split('\n')
    file_and_size = [[int(i.strip().split(" ", 1)[0]), path + i.strip().split(" ", 1)[-1]] for i in files_path if i != '']
    return file_and_size


async def remaining_space(path: str):
    if not path.endswith("/") and not path.endswith("\\"):
        path += "/"
    output, return_code = await execute(f'rclone about "{path}" --json', get_output=True)
    if return_code != 0:
        logging.error(f"rclone about {path} failed with return code {return_code}")
        return 0
    output = json.loads(output)
    logging.info(f"remaining space of {path}: {output['free']}")
    return output["free"]
