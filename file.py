import os
from typing import List, Dict
import rclone
import logging
import pack

from config import keep_relative_path


def get_files_size(path: str):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            total_size += os.path.getsize(file_path)
    return total_size


# 会去除分卷拓展名
def get_file_name(file: List[str]):
    file_full_path = file[1]
    file_name = file_full_path.split("/")[-1]

    division = file_name.rsplit(".", 2)
    if len(division) < 2:
        return file_name

    if len(division) == 2:
        if division[1].startswith("r") and division[1][1:].isdigit():
            return division[0] + ".rar"
        else:
            return file_name

    if division[2].isdigit():
        return division[0] + "." + division[1]

    if division[1].startswith("part"):
        return division[0] + "." + division[2]

    if division[2].startswith("r") and division[2][1:].isdigit():
        return division[0] + ".rar"

    if division[2].lower() in ["zip", "7z", "rar"]:
        return file_name

    logging.warning(f"can not get file type from {file_full_path}")
    return file_name


def get_file_path(file: List[str]):
    file_full_path = file[1]
    file_path = file_full_path.rsplit("/", 1)[0]
    return file_path


def group_file(file_list: List[List[str]]):
    grouped_file = {}
    for file in file_list:
        file_name = get_file_path(file) + "/" + get_file_name(file)
        if file_name not in grouped_file:
            grouped_file[file_name] = []
        grouped_file[file_name].append(file)

    return grouped_file


class File:
    remote_path: str
    remote_root_path: str
    relative_path: str
    local_path: str
    repacked_path: str  # 重新打包后的文件路径
    repacked_post_path: str  # 重新打包后的文件上传路径
    file_format: str  # rar zip 7z     由拓展名识别
    unpacking_tmp_path: str  # 解压缩临时文件夹
    size: int  # 文件大小
    name: str  # 文件名 不包含拓展名
    segments: List[Dict[str, str]]  # 分段文件, 包含大小

    def __init__(self):
        pass

    def first_segment(self):
        path = [i["path"] for i in self.segments]
        path = sorted(path)
        if path[-1].lower().endswith("rar"):
            return path[-1]
        return path[0]

    # 重命名part01.rar以及更新segment路径
    def rename(self):
        logging.info(f"rename {self.name} files")
        for i in range(len(self.segments)):
            path = self.segments[i]["path"]
            name = path.rsplit("/", 1)[-1]
            division = name.rsplit(".", 2)
            if len(division) <= 2:
                self.segments[i]["path"] = os.path.join(self.local_path, name)
                continue

            if division[1].startswith("part"):
                old_name = name
                new_name = division[0] + "." + division[2] + "." + "{:03d}".format(int(division[1][4:]))
                os.rename(os.path.join(self.local_path, old_name), os.path.join(self.local_path, new_name))
                self.segments[i]["path"] = os.path.join(self.local_path, new_name)

            else:
                name = path.rsplit("/", 1)[-1]
                self.segments[i]["path"] = os.path.join(self.local_path, name)

    async def copy_to_local(self, local_path: str, thread_name: str):
        self.local_path = local_path
        logging.info(f"copying {self.name} to local")
        logging.info(f"current file have {len(self.segments)} segments")
        path = [i["path"] for i in self.segments]
        if not await rclone.copy_file(path, local_path, thread_name):
            return False
        self.rename()
        return True

    async def post_to_remote(self, thread_name: str):
        logging.info(f"post {self.name} to remote")
        # segments = os.listdir(self.repacked_path)
        # for i in segments:
        #     result = rclone.copy_file(os.path.join(self.repacked_path, i), self.repacked_post_path)
        #     if result != 0:
        #         logging.error(f"post {self.name} failed")
        #         return False
        if keep_relative_path:
            if not self.repacked_post_path.endswith("/") and not self.repacked_post_path.endswith("\\"):
                self.repacked_post_path += "/"
            if not await rclone.copy_file(self.repacked_path, self.repacked_post_path + self.relative_path, thread_name):
                return False
        else:
            if not await rclone.copy_file(self.repacked_path, self.repacked_post_path, thread_name):
                return False
        return True

    async def post_to_remote_without_repack(self, thread_name: str):
        logging.info(f"post {self.name} to remote")
        if keep_relative_path:
            if not self.repacked_post_path.endswith("/") and not self.repacked_post_path.endswith("\\"):
                self.repacked_post_path += "/"
            if not await rclone.copy_file(self.unpacking_tmp_path, os.path.join(self.repacked_post_path + os.path.dirname(self.relative_path), self.name), thread_name):
                return False
        else:
            if not await rclone.copy_file(self.unpacking_tmp_path, os.path.join(self.repacked_post_path, self.name), thread_name):
                return False
        return True

    async def unpacking(self, destination: str, password=[]):
        self.unpacking_tmp_path = destination
        first_segment = self.first_segment()
        if first_segment is None:
            logging.error(f"can not find first segment of {self.name}")
            return None
        logging.info(f"unpacking {self.name} to {destination}")
        if not await pack.unpacking(first_segment, destination, password):
            return None
        return get_files_size(self.unpacking_tmp_path)

    async def packing(self, destination: str):
        if not destination.endswith("/") and not destination.endswith("\\"):
            destination += "/"
        self.repacked_path = destination
        logging.info(f"packing {self.name} to {destination}")
        if not await pack.packing(self.unpacking_tmp_path, destination + self.name, password="", segment_size=(0 if len(self.segments) <= 1 else max([i["size"] for i in self.segments]))):
            return None
        return get_files_size(self.repacked_path)

    @classmethod
    def from_list(cls, path_list: List[List[str]], repacked_post_path: str):
        file_list = group_file(path_list)

        files = []

        for i in list(file_list.keys()):
            f = file_list[i]

            if len(f) < 1:
                raise Exception(f"file list is empty: {i}")
            elif len(f) == 1:
                i = i.rsplit("/", 1)[-1]
                file = File()
                f = f[0]
                file.remote_path = f[1].rsplit("/", 1)[0]
                file.relative_path = f[2].rsplit("/", 1)[0]
                file.remote_root_path = f[4]
                file.local_path = ""
                file.file_format = i.rsplit(".", 1)[-1]
                file.size = f[0]
                file.name = i.split(".", 1)[0]
                # file.name = i
                file.segments = [{"size": f[0], "path": f[1]}]
                file.repacked_path = ""
                file.repacked_post_path = repacked_post_path
                files.append(file)
            else:
                i = i.rsplit("/", 1)[-1]
                file = File()
                file.remote_path = f[0][1].rsplit("/", 1)[0]
                file.relative_path = f[0][2].rsplit("/", 1)[0]
                file.remote_root_path = f[0][4]
                file.local_path = ""
                file.file_format = i.rsplit(".", 1)[-1]
                file.size = sum([j[0] for j in f])
                file.name = i.split(".", 1)[0]
                # file.name = i
                file.segments = []
                for j in f:
                    file.segments.append({"size": j[0], "path": j[1]})
                file.repacked_path = ""
                file.repacked_post_path = repacked_post_path
                files.append(file)

        return files
