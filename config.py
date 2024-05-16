import json


with open("config.json", "r") as f:
    config = json.load(f)

source_dir = config["source"]
destination_dir = config["target"]
password = config["password"]
max_depth = config["max_depth"]
tmp_dir = config["tmp_dir"]
do_not_repack = config["do_not_repack"]
task_num = config["tasks"]
repack_type = config["repack_type"]
keep_relative_path = config["keep_relative_path"]

password += ""  # 空密码

if repack_type == "rar":
    raise TypeError("rar is not supported yet")
