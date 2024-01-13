import json
import logging
import os
import shutil

from file import File
import rclone
from typing import List


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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


if __name__ == '__main__':

    with open("config.json", "r") as f:
        config = json.load(f)

    source_dir = config["source"]
    destination_dir = config["target"]
    password = config["password"]
    max_depth = config["max_depth"]
    tmp_dir = config["tmp_dir"]

    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    # echo all config
    logging.info("start. config:")
    logging.info(f"source_dir: {source_dir}")
    logging.info(f"destination_dir: {destination_dir}")
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
    destination_files = rclone.ls(destination_dir, max_depth)

    source_files = File.from_list(source_files, destination_files)
    destination_files = File.from_list(destination_files, "")

    logging.info(f"get {len(source_files)} single files from remote, start repack")
    for need_repack_file in source_files:
        if complete(need_repack_file, destination_files):
            logging.info(f"{need_repack_file.name} is already complete, skip")
            continue
        logging.info(f"start repack {need_repack_file.name}")
        if not need_repack_file.copy_to_local(tmp_local_dir):
            logging.error(f"{need_repack_file.name} copy to local failed, stop")
            exit(1)
        if not need_repack_file.unpacking(tmp_unpacking_dir, password):
            logging.error(f"{need_repack_file.name} unpacking failed, stop")
            exit(1)
        clear_dir(tmp_local_dir)
        if not need_repack_file.repacking(tmp_repacked_dir):
            logging.error(f"{need_repack_file.name} repacking failed, stop")
            exit(1)
        clear_dir(tmp_unpacking_dir)
        if not need_repack_file.post_to_remote():
            logging.error(f"{need_repack_file.name} post to remote failed, stop")
            exit(1)
        clear_dir(tmp_repacked_dir)
        logging.info(f"{need_repack_file.name} repack complete")

    logging.info("all file repack complete")

    


