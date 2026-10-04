"""从客户端 bundle 里抽出 CSS-module 类名，按关键词归类，用于确定装饰层挂点。

用法：
    python tools/scan_classes.py [关键词...]
只给关键词时打印匹配的类名；不给关键词时打印全部类名计数最高的若干组。
"""

from __future__ import annotations

import collections
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(os.path.dirname(HERE), "_probe")

CLASS = re.compile(r"\.([A-Za-z0-9][\w-]*_[A-Za-z][\w]*)")


def main() -> None:
    keywords = [k.lower() for k in sys.argv[1:]]
    per_file: dict[str, collections.Counter[str]] = {}
    for path in sorted(glob.glob(os.path.join(PROBE, "*.client.js"))):
        text = open(path, encoding="utf-8", errors="replace").read()
        per_file[os.path.basename(path)] = collections.Counter(CLASS.findall(text))

    if not keywords:
        merged: collections.Counter[str] = collections.Counter()
        for counter in per_file.values():
            merged.update(counter)
        for name, count in merged.most_common(120):
            print(f"{count:5}  {name}")
        return

    for filename, counter in per_file.items():
        hits = [name for name in counter if any(k in name.lower() for k in keywords)]
        if not hits:
            continue
        print(f"### {filename}")
        for name in sorted(set(hits)):
            print(f"   {name}")
        print()


if __name__ == "__main__":
    main()
