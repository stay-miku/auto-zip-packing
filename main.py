import json
import logging
import os
import shutil
import time

from file import File
import rclone
from typing import List


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler(f"log-{time.strftime('%Y-%m-%d-%H-%M-%S')}.log")
file_handler.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logging.getLogger().addHandler(file_handler)
# logging.getLogger().addHandler(console_handler)


def complete(file: File, completed_file: List[File]):
    for i in completed_file:
        if i.name == file.name:
            return True
    return False


def clear_dir(path: str):
    if os.path.exists(path):
        for i in os.listdir(path):
            if os.path.isdir(os.path.join(path, i)):
                shutil.rmtree(os.path.join(path, i))
            else:
                os.remove(os.path.join(path, i))


def error_log(log: str, file_name: str = "error.log"):
    with open(file_name, "a") as file:
        file.write(log + "\n")


def error_file(file: File):
    error_log(f"name: {file.name}, size: {file.size}, remote_path: {file.remote_path}, format: {file.file_format}"
              , "error_file.log")


if __name__ == '__main__':

    with open("config.json", "r") as f:
        config = json.load(f)

    source_dir = config["source"]
    destination_dir = config["target"]
    password = config["password"]
    max_depth = config["max_depth"]
    tmp_dir = config["tmp_dir"]
    do_not_repack = config["do_not_repack"]

    target_index = 0

    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    # echo all config
    logging.info("start. config:")
    logging.info(f"source_dir: {source_dir}")
    logging.info(f"destination_dir: {'|'.join(destination_dir)}")
    logging.info(f"password: {password}")
    logging.info(f"max_depth: {max_depth}")
    logging.info(f"tmp_dir: {tmp_dir}")

    tmp_local_dir = os.path.join(tmp_dir, "local")
    tmp_unpacking_dir = os.path.join(tmp_dir, "unpacking")
    tmp_repacked_dir = os.path.join(tmp_dir, "repacked")
    if not os.path.exists(tmp_local_dir):
        os.mkdir(tmp_local_dir)
    if not os.path.exists(tmp_unpacking_dir):
        os.mkdir(tmp_unpacking_dir)
    if not os.path.exists(tmp_repacked_dir):
        os.mkdir(tmp_repacked_dir)

    clear_dir(tmp_local_dir)
    clear_dir(tmp_unpacking_dir)
    clear_dir(tmp_repacked_dir)

    # get all files
    logging.info("get remote file list")
    source_files = rclone.ls(source_dir, max_depth)
    destination_files = []
    for i in destination_dir:
        destination_files += rclone.ls(i, max_depth)

    source_files = File.from_list(source_files, destination_dir[0])
    destination_files = File.from_list(destination_files, "")

    logging.info(f"get {len(source_files)} single files from remote, start repack")
    for need_repack_file in source_files:
        try:
            if complete(need_repack_file, destination_files):
                logging.info(f"{need_repack_file.name} is already complete, skip")
                error_file(need_repack_file)
                continue
            logging.info(f"start repack {need_repack_file.name}")
            if not need_repack_file.copy_to_local(tmp_local_dir):
                logging.error(f"{need_repack_file.name} copy to local failed, skip")
                error_file(need_repack_file)
                continue
            size = need_repack_file.unpacking(tmp_unpacking_dir, password)
            if size is None:
                logging.error(f"{need_repack_file.name} unpacking failed, skip")
                error_file(need_repack_file)
                continue
            clear_dir(tmp_local_dir)

            if do_not_repack:
                while rclone.remaining_space(destination_dir[target_index]) < size:
                    logging.info(f"{destination_dir[target_index]} no enough space, change to next")
                    target_index += 1
                    if target_index >= len(destination_dir):
                        logging.error(f"{need_repack_file.name} no enough space, stop")
                        error_file(need_repack_file)
                        exit(1)
                need_repack_file.repacked_post_path = destination_dir[target_index]
                if not need_repack_file.post_to_remote_without_repack():
                    logging.error(f"{need_repack_file.name} post to remote failed, skip")
                    error_file(need_repack_file)
                    continue
                clear_dir(tmp_unpacking_dir)
                logging.info(f"{need_repack_file.name} post complete")
            else:
                size = need_repack_file.packing(tmp_repacked_dir)
                if size is None:
                    logging.error(f"{need_repack_file.name} repacking failed, skip")
                    error_file(need_repack_file)
                    continue
                while rclone.remaining_space(destination_dir[target_index]) < size:
                    logging.info(f"{destination_dir[target_index]} no enough space, change to next")
                    target_index += 1
                    if target_index >= len(destination_dir):
                        logging.error(f"{need_repack_file.name} no enough space, stop")
                        error_file(need_repack_file)
                        exit(1)
                clear_dir(tmp_unpacking_dir)
                need_repack_file.repacked_post_path = destination_dir[target_index]
                if not need_repack_file.post_to_remote():
                    logging.error(f"{need_repack_file.name} post to remote failed, skip")
                    error_file(need_repack_file)
                    continue
                clear_dir(tmp_repacked_dir)
                logging.info(f"{need_repack_file.name} post complete")
        except Exception as e:
            logging.error(e)
            error_file(need_repack_file)
            logging.error(f"{need_repack_file.name} repack failed, skip")
            continue

    logging.info("all file repack complete")

    


