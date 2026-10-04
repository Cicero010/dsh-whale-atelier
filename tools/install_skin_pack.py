"""把一个皮肤包安装/卸载到插件的 assets/packs/ 下（不需要重启宿主，刷新页面即生效）。

用法：
    python tools/install_skin_pack.py packs/sakura
    python tools/install_skin_pack.py packs/sakura --plugin-dir dsh-whale-wallpaper
    python tools/install_skin_pack.py --uninstall sakura
    python tools/install_skin_pack.py --list

原理：皮肤包目录（skin.json + 壁纸）被复制成
    <plugin>/assets/packs/<id>/{skin.json,assets/*.webp,thumb.webp}
并登记进 <plugin>/assets/packs/index.json。客户端启动时先读这个索引，
所以走的是插件已有的 /assets 只读路由 —— 不需要重启宿主进程。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLUGIN = os.path.join(os.path.dirname(HERE), "dsh-whale-wallpaper")


def index_path(plugin_dir: str) -> str:
    return os.path.join(plugin_dir, "assets", "packs", "index.json")


def read_index(plugin_dir: str) -> dict:
    path = index_path(plugin_dir)
    if not os.path.exists(path):
        return {"version": 1, "packs": []}
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("packs"), list):
        return {"version": 1, "packs": []}
    return data


def write_index(plugin_dir: str, data: dict) -> str:
    path = index_path(plugin_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data["packs"] = sorted(data["packs"], key=lambda item: str(item.get("id", "")))
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


def load_manifest(pack_dir: str) -> dict:
    manifest_path = os.path.join(pack_dir, "skin.json")
    if not os.path.exists(manifest_path):
        sys.exit(f"{pack_dir} 里没有 skin.json")
    with open(manifest_path, encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("id"), str) or not manifest["id"]:
        sys.exit("skin.json 缺少合法的 id")
    return manifest


def install(pack_dir: str, plugin_dir: str) -> None:
    manifest = load_manifest(pack_dir)
    pack_id = manifest["id"]
    target = os.path.join(plugin_dir, "assets", "packs", pack_id)
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(pack_dir, target)

    entry = dict(manifest)
    entry["base"] = f"packs/{pack_id}/"
    # 资源在包内 assets/ 子目录时，把 base 指向它，客户端拼 URL 更直接
    if os.path.exists(os.path.join(target, "assets", f"ww-{manifest.get('scene', pack_id)}-companion-dark.webp")):
        entry["base"] = f"packs/{pack_id}/assets/"
    entry["wallpapers"] = [
        f"{pose}-{theme}"
        for pose in ("companion", "debug", "slack")
        for theme in ("dark", "light")
        if os.path.exists(os.path.join(target, "assets", f"ww-{manifest.get('scene', pack_id)}-{pose}-{theme}.webp"))
    ]
    entry["thumb"] = os.path.exists(os.path.join(target, "thumb.webp"))
    entry["local"] = True

    data = read_index(plugin_dir)
    data["packs"] = [item for item in data["packs"] if item.get("id") != pack_id]
    data["packs"].append(entry)
    path = write_index(plugin_dir, data)
    print(f"已安装皮肤包 {pack_id} → {target}")
    print(f"索引已更新: {path}（现有 {len(data['packs'])} 个包，刷新页面即生效）")


def uninstall(pack_id: str, plugin_dir: str) -> None:
    target = os.path.join(plugin_dir, "assets", "packs", pack_id)
    shutil.rmtree(target, ignore_errors=True)
    data = read_index(plugin_dir)
    before = len(data["packs"])
    data["packs"] = [item for item in data["packs"] if item.get("id") != pack_id]
    write_index(plugin_dir, data)
    print(f"已卸载皮肤包 {pack_id}（索引条目 {before} → {len(data['packs'])}），刷新页面即生效")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pack_dir", nargs="?", help="皮肤包目录（含 skin.json）")
    parser.add_argument("--plugin-dir", default=DEFAULT_PLUGIN)
    parser.add_argument("--uninstall", metavar="ID")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        data = read_index(args.plugin_dir)
        if not data["packs"]:
            print("索引里没有皮肤包")
        for item in data["packs"]:
            print(f"{item.get('id'):14} {item.get('name', ''):10} base={item.get('base')} 壁纸 {len(item.get('wallpapers', []))} 张")
        return
    if args.uninstall:
        uninstall(args.uninstall, args.plugin_dir)
        return
    if not args.pack_dir:
        sys.exit("用法：install_skin_pack.py <pack_dir> | --uninstall <id> | --list")
    install(os.path.abspath(args.pack_dir), os.path.abspath(args.plugin_dir))


if __name__ == "__main__":
    main()
