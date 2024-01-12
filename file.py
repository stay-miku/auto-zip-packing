from typing import List


class File:
    remote_path: str
    local_path: str
    file_format: str            # rar zip 7z     由拓展名识别
    size: int                   # 文件大小
    name: str                   # 文件名(去除分卷拓展名)
    segments: List[str]         # 分段文件
    segments_size: List[int]    # 分段文件大小

    def __init__(self, remote_path: List[str]):
        pass

    def copy_to_local(self):
        pass

    @classmethod
    def from_list(cls, path_list: List[str]):
        pass
