import asyncio
import logging
import os
import shutil
import time

from file import File
import rclone
from typing import List
from config import source_dir, destination_dir, password, max_depth, tmp_dir, do_not_repack, task_num


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


source_files: List[File] = []
source_files_lock = False
destination_files: List[File] = []


async def get_task_file():
    global source_files_lock
    global source_files
    if source_files_lock:
        await asyncio.sleep(0.1)
    source_files_lock = True
    while True:
        if len(source_files) == 0:
            source_files_lock = False
            return None
        file = source_files[0]
        source_files = source_files[1:]
        if complete(file, destination_files):
            logging.info(f"{file.name} is already complete, skip")
            continue
        source_files_lock = False
        return file


async def process_file(need_repack_file: File, tmp_local_dir, tmp_unpacking_dir, tmp_repacked_dir):
    try:
        target_index = 0
        clear_dir(tmp_local_dir)
        clear_dir(tmp_unpacking_dir)
        clear_dir(tmp_repacked_dir)
        # if complete(need_repack_file, destination_files):
        #     logging.info(f"{need_repack_file.name} is already complete, skip")
        #     error_file(need_repack_file)
        #     return
        logging.info(f"start repack {need_repack_file.name}")
        if not await need_repack_file.copy_to_local(tmp_local_dir):
            logging.error(f"{need_repack_file.name} copy to local failed, skip")
            error_file(need_repack_file)
            return
        size = await need_repack_file.unpacking(tmp_unpacking_dir, password)
        if size is None:
            logging.error(f"{need_repack_file.name} unpacking failed, skip")
            error_file(need_repack_file)
            return
        clear_dir(tmp_local_dir)

        if do_not_repack:
            while await rclone.remaining_space(destination_dir[target_index]) < size:
                logging.info(f"{destination_dir[target_index]} no enough space, change to next")
                target_index += 1
                if target_index >= len(destination_dir):
                    logging.error(f"{need_repack_file.name} no enough space, stop")
                    error_file(need_repack_file)
                    exit(1)
            need_repack_file.repacked_post_path = destination_dir[target_index]
            if not await need_repack_file.post_to_remote_without_repack():
                logging.error(f"{need_repack_file.name} post to remote failed, skip")
                error_file(need_repack_file)
                return
            clear_dir(tmp_unpacking_dir)
            logging.info(f"{need_repack_file.name} post complete")
        else:
            size = await need_repack_file.packing(tmp_repacked_dir)
            if size is None:
                logging.error(f"{need_repack_file.name} repacking failed, skip")
                error_file(need_repack_file)
                return
            while await rclone.remaining_space(destination_dir[target_index]) < size:
                logging.info(f"{destination_dir[target_index]} no enough space, change to next")
                target_index += 1
                if target_index >= len(destination_dir):
                    logging.error(f"{need_repack_file.name} no enough space, stop")
                    error_file(need_repack_file)
                    exit(1)
            clear_dir(tmp_unpacking_dir)
            need_repack_file.repacked_post_path = destination_dir[target_index]
            if not await need_repack_file.post_to_remote():
                logging.error(f"{need_repack_file.name} post to remote failed, skip")
                error_file(need_repack_file)
                return
            clear_dir(tmp_repacked_dir)
            logging.info(f"{need_repack_file.name} post complete")
    except Exception as e:
        logging.error(e)
        error_file(need_repack_file)
        logging.error(f"{need_repack_file.name} repack failed, skip")
        return


async def task_thread(uuid: str):
    task_tmp_dir = os.path.join(tmp_dir, uuid)

    tmp_local_dir = os.path.join(task_tmp_dir, "local")
    tmp_unpacking_dir = os.path.join(task_tmp_dir, "unpacking")
    tmp_repacked_dir = os.path.join(task_tmp_dir, "repacked")
    if not os.path.exists(tmp_local_dir):
        os.makedirs(tmp_local_dir)
    if not os.path.exists(tmp_unpacking_dir):
        os.makedirs(tmp_unpacking_dir)
    if not os.path.exists(tmp_repacked_dir):
        os.makedirs(tmp_repacked_dir)

    clear_dir(tmp_local_dir)
    clear_dir(tmp_unpacking_dir)
    clear_dir(tmp_repacked_dir)

    i = 0

    while True:
        file = await get_task_file()
        if file is None:
            break
        logging.info(f"repacking file {file.name} by thread {uuid}")
        await process_file(file, tmp_local_dir, tmp_unpacking_dir, tmp_repacked_dir)
        i += 1

    logging.info(f"thread {uuid} complete, repack {i} files")


async def main():

    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    # echo all config
    logging.info("start. config:")
    logging.info(f"source_dir: {source_dir}")
    logging.info(f"destination_dir: {'|'.join(destination_dir)}")
    logging.info(f"password: {password}")
    logging.info(f"max_depth: {max_depth}")
    logging.info(f"tmp_dir: {tmp_dir}")
    logging.info(f"do_not_repack: {do_not_repack}")
    logging.info(f"task_num: {task_num}")

    # tmp_local_dir = os.path.join(tmp_dir, "local")
    # tmp_unpacking_dir = os.path.join(tmp_dir, "unpacking")
    # tmp_repacked_dir = os.path.join(tmp_dir, "repacked")
    # if not os.path.exists(tmp_local_dir):
    #     os.mkdir(tmp_local_dir)
    # if not os.path.exists(tmp_unpacking_dir):
    #     os.mkdir(tmp_unpacking_dir)
    # if not os.path.exists(tmp_repacked_dir):
    #     os.mkdir(tmp_repacked_dir)

    # clear_dir(tmp_local_dir)
    # clear_dir(tmp_unpacking_dir)
    # clear_dir(tmp_repacked_dir)

    # get all files
    logging.info("get remote file list")
    global source_files, destination_files
    source_files = await rclone.ls(source_dir, max_depth)
    destination_files = []
    for i in destination_dir:
        destination_files += await rclone.ls(i, max_depth)

    source_files = File.from_list(source_files, destination_dir[0])
    destination_files = File.from_list(destination_files, "")

    logging.info(f"get {len(source_files)} single files from remote, start repack")
    tasks = []
    for i in range(task_num):
        tasks.append(asyncio.create_task(task_thread(str(i))))
        logging.info(f"create task {i}")
    await asyncio.gather(*tasks)

    logging.info("all file repack complete")


if __name__ == '__main__':
    asyncio.run(main())


    


