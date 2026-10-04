"""为每套皮肤生成设置面板用的缩略图（壁纸 + 角落立绘 + 金属描边）。

用法：
    python tools/make_thumbs.py [输出目录]

产出：thumb-<skin>.webp（320x200），由宿主静态路由提供给设置面板的皮肤选择器。
"""

from __future__ import annotations

import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(os.path.dirname(HERE), "dsh-whale-atelier")
ASSETS = os.path.join(PLUGIN, "assets")

W, H = 320, 200

METALS = {
    "gold": (214, 178, 110),
    "silver": (150, 168, 204),
}

# 与 lib/client.js 的 SKINS 表对应（缩略图专用）
SKINS = {
    "atelier": {"scene": "interior", "metal": "gold", "decor": True, "mascot": "notebook", "corner": "left"},
    "garden": {"scene": "interior", "metal": "silver", "decor": True, "mascot": "pointer", "corner": "right"},
    "abyss": {"scene": "abyss", "metal": "silver", "decor": False, "mascot": "curious", "corner": "right"},
    "snow": {"scene": "snow", "metal": "silver", "decor": True, "mascot": "pointer", "corner": "right"},
    "moonfest": {"scene": "moonfest", "metal": "gold", "decor": True, "mascot": "curious", "corner": "left"},
}


def cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """等比缩放并居中裁剪到目标尺寸（等价 CSS background-size: cover）。"""
    scale = max(size[0] / image.width, size[1] / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    left = (resized.width - size[0]) // 2
    top = (resized.height - size[1]) // 2
    return resized.crop((left, top, left + size[0], top + size[1]))


def build(skin_id: str, skin: dict, source_dir: str = ASSETS) -> Image.Image:
    wallpaper = Image.open(os.path.join(source_dir, f"ww-{skin['scene']}-companion-dark.webp")).convert("RGBA")
    canvas = cover(wallpaper, (W, H))
    # 左侧压一层暗角，模仿真实使用时的遮罩
    shade = Image.new("RGBA", (W, H), (8, 11, 20, 96))
    canvas.alpha_composite(shade)

    mascot_path = os.path.join(source_dir, f"mascot-{skin['mascot']}.webp")
    if not os.path.exists(mascot_path):
        mascot_path = os.path.join(ASSETS, f"mascot-{skin['mascot']}.webp")
    mascot = Image.open(mascot_path).convert("RGBA")
    target_h = int(H * 0.52)
    mascot = mascot.resize((round(mascot.width * target_h / mascot.height), target_h), Image.LANCZOS)
    margin = 8
    if skin["corner"] == "left":
        position = (margin, H - mascot.height + 6)
    else:
        position = (W - mascot.width - margin, H - mascot.height + 6)
    canvas.alpha_composite(mascot, position)

    if skin["decor"]:
        metal = METALS[skin["metal"]]
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([3, 3, W - 4, H - 4], outline=(*metal, 190), width=2)
        corner_path = os.path.join(source_dir, f"orn-corner-{skin['metal']}.png")
        if not os.path.exists(corner_path):
            corner_path = os.path.join(ASSETS, f"orn-corner-{skin['metal']}.png")
        corner = Image.open(corner_path).convert("RGBA")
        corner = corner.resize((46, 46), Image.LANCZOS)
        canvas.alpha_composite(corner, (2, 2))
        canvas.alpha_composite(corner.transpose(Image.ROTATE_180), (W - 48, H - 48))
    return canvas.convert("RGB")


def build_pack_thumb(pack_dir: str) -> str:
    """给一个皮肤包目录生成 thumb.webp（读它的 skin.json，壁纸与立绘优先用包内文件）。"""
    manifest_path = os.path.join(pack_dir, "skin.json")
    with open(manifest_path, encoding="utf-8") as handle:
        manifest = json.load(handle)
    skin = {
        "scene": manifest.get("scene") or manifest.get("id") or "abyss",
        "metal": manifest.get("metal", "gold"),
        "decor": manifest.get("decor", manifest.get("metal", "gold") != "none"),
        "mascot": manifest.get("mascot", "curious"),
        "corner": manifest.get("mascotCorner", "right"),
    }
    out = os.path.join(pack_dir, "thumb.webp")
    source = os.path.join(pack_dir, "assets")
    if not os.path.exists(os.path.join(source, f"ww-{skin['scene']}-companion-dark.webp")):
        source = pack_dir
    build(manifest.get("id", "pack"), skin, source).save(out, "WEBP", quality=88, method=6)
    return out


def main() -> None:
    if len(sys.argv) > 2 and sys.argv[1] == "--pack":
        print(build_pack_thumb(sys.argv[2]))
        return
    out_dir = sys.argv[1] if len(sys.argv) > 1 else ASSETS
    os.makedirs(out_dir, exist_ok=True)
    for skin_id, skin in SKINS.items():
        path = os.path.join(out_dir, f"thumb-{skin_id}.webp")
        build(skin_id, skin).save(path, "WEBP", quality=88, method=6)
        print(f"{path}  {os.path.getsize(path) // 1024} KB")


if __name__ == "__main__":
    main()
