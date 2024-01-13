from rclone import execute


packs = ["rar", "unrar", "p7zip-full"]


with open("/etc/apt/sources.list", "r") as f:
    sources = f.read()

# 为每个source添加contrib non-free
print("adding contrib non-free")
sources = sources.split("\n")
for i in range(len(sources)):
    if sources[i].strip().startswith("#"):
        continue
    sources[i] = sources[i].strip()
    if "main" in sources[i] and "contrib" not in sources[i] and "non-free" not in sources[i]:
        sources[i] = sources[i] + " contrib non-free"

sources = "\n".join(sources)
with open("/etc/apt/sources.list", "w") as f:
    f.write(sources)

return_code = execute("apt update")
if return_code != 0:
    print("apt update failed")
    exit(1)

return_code = execute("apt install -y " + " ".join(packs))
if return_code != 0:
    print("apt install failed")
    exit(1)

print("install success")

