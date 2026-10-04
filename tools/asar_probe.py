"""Probe app.asar: list entries matching a substring and optionally dump/save one file.

用法：
    python tools/asar_probe.py --asar "<DSH>/resources/app.asar" <路径片段> [list|dump|save] [输出]
"""
import json
import os
import sys

def resolve_asar(argv):
    """asar 路径：--asar <路径> > 环境变量 DSH_ASAR > 报错提示（不写死任何本机路径）。"""
    if "--asar" in argv:
        index = argv.index("--asar")
        if index + 1 >= len(argv):
            raise SystemExit("--asar 后面要跟 app.asar 的路径")
        return argv[index + 1], argv[:index] + argv[index + 2:]
    env = os.environ.get("DSH_ASAR")
    if env:
        return env, argv
    raise SystemExit(
        "请指定 app.asar 路径：--asar \"<DSH 安装目录>/resources/app.asar\"，或设置环境变量 DSH_ASAR。"
    )


def load_header(f):
    f.seek(0)
    head = f.read(16)
    # pickle: uint32 4, then header size pickle, then header size, json size
    (a,) = (int.from_bytes(head[0:4], "little"),)
    (b,) = (int.from_bytes(head[4:8], "little"),)
    (c,) = (int.from_bytes(head[8:12], "little"),)
    (jlen,) = (int.from_bytes(head[12:16], "little"),)
    f.seek(16)
    header = json.loads(f.read(jlen).decode("utf-8"))
    return header, 8 + b


def walk(node, prefix, out):
    for name, meta in node.get("files", {}).items():
        p = prefix + "/" + name
        if "files" in meta:
            walk(meta, p, out)
        else:
            out.append((p, int(meta.get("offset", -1)), int(meta.get("size", 0))))


def main():
    asar, argv = resolve_asar(sys.argv[1:])
    if not argv:
        raise SystemExit("用法：asar_probe.py --asar <app.asar> <路径片段> [list|dump|save] [输出文件]")
    needle = argv[0]
    mode = argv[1] if len(argv) > 1 else "list"
    with open(asar, "rb") as f:
        header, data_start = load_header(f)
        entries = []
        walk(header, "", entries)
        hits = [e for e in entries if needle in e[0]]
        print("total entries:", len(entries), "hits:", len(hits))
        for p, off, size in hits[:200]:
            print(f"{size:>9}  {p}")
        if mode == "dump" and hits:
            p, off, size = hits[0]
            f.seek(data_start + off)
            sys.stdout.write(f.read(size).decode("utf-8", "replace"))
        if mode == "save" and hits:
            p, off, size = hits[0]
            f.seek(data_start + off)
            out = argv[2]
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "wb") as g:
                g.write(f.read(size))
            print("saved", out, size)


main()
