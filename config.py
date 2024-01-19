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
