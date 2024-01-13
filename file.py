import os
from typing import List, Dict
import rclone
import logging
import pack


# 会去除分卷拓展名
def get_file_name(file: List[str]):
    file_full_path = file[1]
    file_name = file_full_path.split("/")[-1]
    if "." in file_name:
        extension = file_name.rsplit(".", 1)[-1]
        if extension.isdigit():
            file_name = file_name.rsplit(".", 1)[0]
            return file_name

    return file_name


def group_file(file_list: List[List[str]]):
    grouped_file = {}
    for file in file_list:
        file_name = get_file_name(file)
        if file_name not in grouped_file:
            grouped_file[file_name] = []
        grouped_file[file_name].append(file)

    return grouped_file


class File:
    remote_path: str
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
        for i in self.segments:
            if i["path"].endswith(".001"):
                return i
        return None

    def copy_to_local(self, local_path: str):
        self.local_path = local_path
        logging.info(f"copying {self.name} to local")
        logging.info(f"current file have {len(self.segments)} segments")
        for i in self.segments:
            logging.info(f"copying {i['path']} to {self.local_path}")
            if not rclone.copy_file(i["path"], self.local_path):
                return False
        return True

    def post_to_remote(self):
        logging.info(f"post {self.name} to remote")
        segments = os.listdir(self.repacked_path)
        for i in segments:
            result = rclone.copy_file(os.path.join(self.repacked_path, i), self.repacked_post_path)
            if result != 0:
                logging.error(f"post {self.name} failed")
                return False
        return True

    def unpacking(self, destination: str, password=""):
        self.unpacking_tmp_path = destination
        first_segment = self.first_segment()
        if first_segment is None:
            logging.error(f"can not find first segment of {self.name}")
            return False
        first_segment = first_segment["path"]
        logging.info(f"unpacking {self.name} to {destination}")
        if not pack.unpacking(first_segment, destination, password):
            return False
        return True

    def packing(self, destination: str):
        if not destination.endswith("/") or not destination.endswith("\\"):
            destination += "/"
        self.repacked_path = destination
        logging.info(f"packing {self.name} to {destination}")
        if not pack.packing(self.unpacking_tmp_path, destination + self.name + ".7z", password="", segment_size=(0 if self.first_segment() is None else self.first_segment()["size"])):
            return False
        return True

    @classmethod
    def from_list(cls, path_list: List[List[str]], repacked_post_path: str):
        file_list = group_file(path_list)

        files = []

        for i in list(file_list.keys()):
            f = file_list[i]

            if len(f) < 1:
                raise Exception(f"file list is empty: {i}")
            elif len(f) == 1:
                file = File()
                f = f[0]
                file.remote_path = f[1].rsplit("/", 1)[0]
                file.local_path = ""
                file.file_format = i.rsplit(".", 1)[-1]
                file.size = f[0]
                file.name = i.split(".", 1)[0]
                file.segments = [{"size": f[0], "path": f[1]}]
                file.repacked_path = ""
                file.repacked_post_path = repacked_post_path
                files.append(file)
            else:
                file = File()
                file.remote_path = f[0][1].rsplit("/", 1)[0]
                file.local_path = ""
                file.file_format = i.rsplit(".", 1)[-1]
                file.size = sum([j[0] for j in f])
                file.name = i.split(".", 1)[0]
                file.segments = []
                for j in f:
                    file.segments.append({"size": j[0], "path": j[1]})
                file.repacked_path = ""
                file.repacked_post_path = repacked_post_path
                files.append(file)

        return files
