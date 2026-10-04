"""Probe app.asar: list entries matching a substring and optionally dump one file."""
import json
import os
import sys

ASAR = r"F:\DeepSeek Harness\resources\app.asar"


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
    needle = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "list"
    with open(ASAR, "rb") as f:
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
            out = sys.argv[3]
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "wb") as g:
                g.write(f.read(size))
            print("saved", out, size)


main()
