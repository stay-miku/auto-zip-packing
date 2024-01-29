import os

from rclone import execute
from config import repack_type


async def packing(source: str, destination: str, segment_size=-1, password=""):
    if not source.endswith("/") or not source.endswith("\\"):
        source += "/"
    if repack_type == "7z":
        return_code = await execute(f'7z a {"-v" + str(segment_size) if segment_size > 0 else ""} {"-p" + password if password != "" else ""} -t7z -mx=0 -r "{destination}" "{source}"*')
    elif repack_type == "rar":
        return_code = await execute(f'rar a -rr3 -scfc -r -k -ed -ms -htb -m0 {"-v" + str(segment_size) if segment_size > 0 else ""} -s -oi:65536 -qo+ -tk {"-p" + password if password != "" else ""} "{destination}" "{source}"*')
    else:
        raise Exception(f"unknown repack type: {repack_type}")
    if return_code != 0:
        return False
    return True


async def unpacking(source: str, destination: str, password=""):
    out, code = await execute(f"file {source}", get_output=True)
    if "rar" in out.lower():
        return_code = await execute(f'rar x {"-p" + password if password != "" else ""} "{source}" "{destination}"')
    else:
        return_code = await execute(f'7z x -y {"-p" + password if password != "" else ""} -o"{destination}" "{source}"')
    if return_code != 0:
        return False
    return True
