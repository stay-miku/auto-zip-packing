import os

from rclone import execute


def packing(source: str, destination: str, segment_size=-1, password=""):
    if not source.endswith("/") or not source.endswith("\\"):
        source += "/"
    return_code = execute(f'7z a {"-v" + str(segment_size) if segment_size > 0 else ""} {"-p" + password if password != "" else ""} -t7z -mx=0 -r "{destination}" "{source}"*')
    if return_code != 0:
        return False
    return True


def unpacking(source: str, destination: str, password=""):

    return_code = execute(f'7z x -y {"-p" + password if password != "" else ""} -o"{destination}" "{source}"')
    if return_code != 0:
        return False
    return True
