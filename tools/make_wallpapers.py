"""生成「鲸鱼工作区壁纸」的场景底图。

用法：
    python tools/make_wallpapers.py --set all [输出目录]
    python tools/make_wallpapers.py --set interior
    python tools/make_wallpapers.py --set snow
    python tools/make_wallpapers.py --set moonfest
    python tools/make_wallpapers.py --set sakura --out packs/sakura/assets

场景（1920x1080 webp，运行时命名 ww-<set>-<pose>-<theme>.webp）：
    abyss     深海：水下渐变 + 气泡 + 水面波纹（最初那版）
    interior  夜庭室内：高窗 + 窗帘 + 吊灯 + 地脚线（对应参考图的室内观感；浅色为白天版）
    snow      雪夜庭（冬）：室内同构，窗外落雪 + 窗框/窗台积雪 + 玻璃霜花，冷蓝白与室内暖烛光对比
    moonfest  桂月夜庭（中秋）：室内同构，窗外暖色满月（柔光）+ 室内 2-3 盏纸灯笼 + 飘落桂花，整体暖金

    sakura    樱吹雪（春夜庭）：室内同构，窗外紫粉春夜 + 更小更柔的月亮 + 樱花枝（深色枝干、
              远层小簇与近层大簇两层花团），室内飘落带旋转的樱花瓣，吊灯那一片仍是暖烛光。
              这是示例皮肤包「樱吹雪」专用的第 5 套，不在 --set all 里，需要显式 --set sakura；
              配合 --out packs/sakura/assets 输出 ww-sakura-<pose>-<theme>.webp。

    --set all 依次产出内置 4 套场景：每套 3 立绘 × 深/浅两版，共 24 张（不含 sakura）。
    snow / moonfest / sakura 各自 3 立绘 × 深/浅两版，单独跑一次即 6 张。

立绘来自已安装的 dsh-whale-musume（512x512 RGBA，背景透明）。
所有画面都把左侧压暗（text_safe），保证正文与侧栏文字始终压得住。
四季场景全部复用同一套室内构件（沿用 scene_interior 的构图与落点常量 ART_CENTER / ART_HEIGHT），
只替换调色板与季节细节。
"""

from __future__ import annotations

import argparse
import math
import os
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter

W, H = 1920, 1080

def resolve_src_dir() -> str:
    """立绘素材目录（dsh-whale-musume 的 generated/）：

    解析顺序：环境变量 DSH_WHALE_MUSUME_ASSETS > ~/.dsh/plugins/dsh-whale-musume/assets/generated
    """
    env = os.environ.get("DSH_WHALE_MUSUME_ASSETS")
    if env:
        return os.path.expanduser(env)
    return os.path.join(os.path.expanduser("~"), ".dsh", "plugins", "dsh-whale-musume", "assets", "generated")


SRC_DIR = resolve_src_dir()

POSES = {
    "companion": "dsh-whale-state-idle-cute.webp",   # 陪伴
    "debug": "dsh-whale-state-work-debug.webp",      # 查 bug
    "slack": "dsh-whale-state-sleep.webp",           # 摸鱼
}

# 立绘在画面里的落点（相对画布）与高度
ART_CENTER = (0.775, 0.56)
ART_HEIGHT = 0.58

ABYSS = {
    "dark": {
        "top": (10, 14, 26), "bottom": (22, 34, 58),
        "glow": (86, 134, 254), "bubble": (150, 196, 255),
        "vignette": (0, 0, 0), "shadow": (0, 0, 0),
    },
    "light": {
        "top": (224, 235, 252), "bottom": (168, 194, 234),
        "glow": (255, 255, 255), "bubble": (255, 255, 255),
        "vignette": (108, 140, 196), "shadow": (66, 96, 148),
    },
}

INTERIOR = {
    "dark": {
        "wall_top": (11, 13, 26), "wall_bottom": (24, 27, 52),
        "floor": (9, 10, 20), "wainscot": (16, 19, 38),
        "sky_top": (30, 46, 92), "sky_bottom": (78, 106, 164),
        "curtain": (30, 36, 68), "curtain_light": (46, 55, 96),
        "gold": (206, 168, 98), "gold_dim": (128, 102, 58),
        "candle": (255, 206, 132),
        "glow": (120, 150, 255), "vignette": (0, 0, 0), "shadow": (0, 0, 0),
    },
    "light": {
        "wall_top": (222, 230, 244), "wall_bottom": (194, 206, 228),
        "floor": (172, 184, 208), "wainscot": (206, 216, 236),
        "sky_top": (172, 206, 248), "sky_bottom": (224, 238, 255),
        "curtain": (184, 202, 234), "curtain_light": (210, 222, 244),
        "gold": (162, 126, 68), "gold_dim": (196, 172, 126),
        "candle": (255, 232, 190),
        "glow": (255, 255, 255), "vignette": (110, 140, 196), "shadow": (66, 96, 148),
    },
}

# 雪夜庭：墙面/地板比 interior 更冷（蓝白），天空压暗成落雪夜空；
# 金色与烛光刻意保留 INTERIOR 的暖色，形成「窗外冷 / 室内暖」的对比。
SNOW = {
    "dark": {
        "wall_top": (10, 15, 30), "wall_bottom": (22, 31, 56),
        "floor": (9, 13, 25), "wainscot": (17, 23, 44),
        "sky_top": (16, 27, 56), "sky_bottom": (62, 85, 136),
        "curtain": (32, 43, 78), "curtain_light": (52, 66, 110),
        "gold": (204, 170, 106), "gold_dim": (124, 104, 66),
        "candle": (255, 203, 130),
        "snow": (240, 248, 255), "snow_dim": (206, 224, 244), "frost": (194, 220, 245),
        "glow": (126, 158, 255), "vignette": (0, 2, 8), "shadow": (0, 0, 0),
    },
    "light": {
        "wall_top": (218, 228, 244), "wall_bottom": (188, 202, 228),
        "floor": (166, 180, 208), "wainscot": (208, 218, 238),
        "sky_top": (162, 190, 240), "sky_bottom": (214, 230, 250),
        "curtain": (178, 198, 232), "curtain_light": (206, 220, 244),
        "gold": (162, 126, 68), "gold_dim": (196, 174, 132),
        "candle": (255, 230, 188),
        "snow": (255, 255, 255), "snow_dim": (216, 232, 248), "frost": (208, 232, 252),
        "glow": (255, 255, 255), "vignette": (98, 128, 184), "shadow": (60, 90, 142),
    },
}

# 桂月夜庭：整体暖金，夜空偏暖褐紫，月亮更大更暖。
MOONFEST = {
    "dark": {
        "wall_top": (20, 14, 24), "wall_bottom": (44, 31, 40),
        "floor": (16, 11, 18), "wainscot": (32, 23, 34),
        "sky_top": (46, 38, 74), "sky_bottom": (108, 75, 84),
        "curtain": (50, 35, 58), "curtain_light": (74, 52, 78),
        "gold": (224, 180, 104), "gold_dim": (146, 110, 58),
        "candle": (255, 200, 118),
        "moon": (255, 234, 190), "moon_glow": (255, 200, 128),
        "lantern": (255, 196, 120), "lantern_paper": (255, 172, 104),
        "petal": (255, 214, 128), "petal_light": (255, 244, 200),
        "glow": (255, 196, 132), "vignette": (10, 4, 6), "shadow": (0, 0, 0),
    },
    "light": {
        "wall_top": (243, 229, 208), "wall_bottom": (226, 204, 178),
        "floor": (206, 184, 162), "wainscot": (238, 222, 198),
        "sky_top": (238, 198, 148), "sky_bottom": (255, 232, 190),
        "curtain": (232, 206, 176), "curtain_light": (246, 226, 200),
        "gold": (168, 124, 60), "gold_dim": (206, 178, 124),
        "candle": (255, 228, 178),
        "moon": (255, 246, 216), "moon_glow": (255, 214, 150),
        "lantern": (255, 202, 138), "lantern_paper": (255, 186, 124),
        "petal": (234, 168, 66), "petal_light": (252, 212, 128),
        "glow": (255, 236, 196), "vignette": (124, 96, 60), "shadow": (86, 62, 40),
    },
}


# 樱吹雪：春夜庭（第 5 套，不参与 --set all）。室内沿用 interior 的构件与落点，
# 窗外换成樱花枝（深色枝干 + 远/近两层粉花团），天空是偏紫粉的春夜，月亮更小更柔；
# 室内保留吊灯那一片暖烛光，与窗外偏冷的紫粉夜色对比。
SAKURA = {
    "dark": {
        "wall_top": (18, 13, 30), "wall_bottom": (38, 26, 48),
        "floor": (15, 11, 24), "wainscot": (27, 20, 41),
        "sky_top": (50, 32, 80), "sky_bottom": (126, 82, 124),
        "curtain": (46, 30, 62), "curtain_light": (70, 47, 84),
        "gold": (214, 172, 106), "gold_dim": (134, 104, 60),
        "candle": (255, 204, 128),
        "moon": (255, 236, 230), "moon_glow": (255, 196, 190), "moon_radius": 19, "moon_alpha": 232,
        "branch": (30, 18, 32), "branch_light": (56, 35, 50),
        "blossom": (238, 158, 190), "blossom_deep": (201, 108, 154),
        "blossom_light": (255, 218, 232), "blossom_core": (255, 176, 170),
        "petal": (255, 196, 216), "petal_light": (255, 238, 246),
        "glow": (188, 148, 255), "vignette": (8, 2, 10), "shadow": (0, 0, 0),
    },
    "light": {
        "wall_top": (242, 233, 244), "wall_bottom": (224, 208, 228),
        "floor": (204, 188, 208), "wainscot": (236, 224, 240),
        "sky_top": (186, 178, 246), "sky_bottom": (245, 210, 236),
        "curtain": (216, 196, 224), "curtain_light": (238, 222, 240),
        "gold": (166, 124, 70), "gold_dim": (200, 172, 134),
        "candle": (255, 230, 186),
        "moon": (255, 250, 252), "moon_glow": (255, 218, 226), "moon_radius": 17, "moon_alpha": 244,
        "branch": (104, 76, 86), "branch_light": (140, 106, 116),
        "blossom": (242, 158, 192), "blossom_deep": (214, 120, 166),
        "blossom_light": (255, 226, 238), "blossom_core": (255, 196, 190),
        "petal": (244, 156, 196), "petal_light": (255, 214, 234),
        "glow": (255, 255, 255), "vignette": (120, 92, 124), "shadow": (86, 62, 92),
    },
}


# ---------------------------------------------------------------- 通用绘制工具


def vertical_gradient(top, bottom) -> Image.Image:
    strip = Image.new("RGB", (1, H))
    px = strip.load()
    for y in range(H):
        t = y / (H - 1)
        px[0, y] = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return strip.resize((W, H), Image.BILINEAR).convert("RGBA")


def radial_glow(center, radius, color, strength, squash: float = 0.82) -> Image.Image:
    mask = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(mask)
    steps = 48
    for i in range(steps, 0, -1):
        r = radius * i / steps
        alpha = round(255 * strength * (1 - i / steps) ** 2.2)
        draw.ellipse(
            [center[0] - r, center[1] - r * squash, center[0] + r, center[1] + r * squash],
            fill=alpha,
        )
    mask = mask.filter(ImageFilter.GaussianBlur(radius * 0.15))
    return Image.merge("RGBA", (*Image.new("RGB", (W, H), color).split(), mask))


def apply_vignette(canvas: Image.Image, color, strength: float = 0.42) -> None:
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).ellipse([-W * 0.30, -H * 0.40, W * 1.30, H * 1.40], fill=255)
    mask = ImageChops.invert(mask.filter(ImageFilter.GaussianBlur(170)))
    mask = mask.point(lambda v: round(v * strength))
    canvas.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (W, H), color).split(), mask)))


def text_safe(canvas: Image.Image, theme: str) -> None:
    """左侧压一层横向渐变：正文与侧栏那一侧更沉，立绘那侧保持通透。"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    color = (7, 10, 18) if theme == "dark" else (255, 255, 255)
    start = 0.55 if theme == "dark" else 0.62
    peak = 0.62 if theme == "dark" else 0.72
    for x in range(W):
        t = x / (W - 1)
        if t >= start:
            break
        alpha = round(255 * (start - t) / start * peak)
        draw.line([(x, 0), (x, H)], fill=color + (alpha,))
    canvas.alpha_composite(layer)


def place_character(canvas: Image.Image, theme: str, filename: str, glow_color, shadow_color, glow_strength: float) -> None:
    art = Image.open(os.path.join(SRC_DIR, filename)).convert("RGBA")
    target_h = int(H * ART_HEIGHT)
    scale = target_h / art.height
    art = art.resize((max(1, round(art.width * scale)), target_h), Image.LANCZOS)

    cx = int(W * ART_CENTER[0])
    cy = int(H * ART_CENTER[1])
    x = cx - art.width // 2
    y = cy - art.height // 2

    canvas.alpha_composite(radial_glow((cx, cy + art.height * 0.03), art.width * 0.66, glow_color, glow_strength))

    shadow = Image.new("L", (W, H), 0)
    shadow.paste(art.getchannel("A"), (x + 16, y + 22))
    shadow = shadow.filter(ImageFilter.GaussianBlur(30)).point(lambda v: round(v * 0.5))
    canvas.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (W, H), shadow_color).split(), shadow)))

    canvas.alpha_composite(art, (x, y))


# ---------------------------------------------------------------- 场景一：深海


def draw_bubbles(canvas: Image.Image, theme: str, rng: random.Random) -> None:
    pal = ABYSS[theme]
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for _ in range(60):
        r = rng.uniform(5, 32)
        x = rng.uniform(-40, W + 40)
        y = rng.uniform(-40, H + 40)
        if 0.14 * W < x < 0.74 * W and 0.10 * H < y < 0.90 * H and rng.random() < 0.75:
            continue
        alpha = rng.randint(14, 40) if theme == "dark" else rng.randint(30, 70)
        draw.ellipse([x - r, y - r, x + r, y + r], outline=pal["bubble"] + (alpha,), width=max(1, round(r * 0.12)))
        if r > 16:
            draw.ellipse([x - r * 0.5, y - r * 0.6, x - r * 0.1, y - r * 0.2], fill=pal["bubble"] + (alpha // 2,))
    canvas.alpha_composite(layer)


def draw_waves(canvas: Image.Image, theme: str) -> None:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    colors = [(120, 170, 255, 30), (86, 134, 254, 22)] if theme == "dark" else [(255, 255, 255, 150), (150, 190, 255, 110)]
    for index, color in enumerate(colors):
        base = H * (0.80 + 0.07 * index)
        amp = 22 - index * 7
        points = [(x, base + amp * math.sin(x / (240 + index * 90) + index)) for x in range(0, W + 1, 8)]
        draw.line(points, fill=color, width=3 - index)
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(1.2)))


def scene_abyss(theme: str, pose_key: str, filename: str) -> Image.Image:
    pal = ABYSS[theme]
    rng = random.Random(f"abyss:{pose_key}:{theme}")
    canvas = vertical_gradient(pal["top"], pal["bottom"])
    draw_bubbles(canvas, theme, rng)
    draw_waves(canvas, theme)
    place_character(canvas, theme, filename, pal["glow"], pal["shadow"], 0.34 if theme == "dark" else 0.55)
    text_safe(canvas, theme)
    apply_vignette(canvas, pal["vignette"])
    return canvas.convert("RGB")


# ---------------------------------------------------------------- 室内构件（interior / snow / moonfest 共用）


def draw_wall_panels(canvas: Image.Image, pal) -> None:
    """墙板：竖向镶板缝 + 腰线 + 地脚线。"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    dark = (0, 0, 0, 26) if sum(pal["wall_top"]) < 240 else (120, 140, 180, 26)
    for x in range(0, W + 1, 160):
        draw.line([(x, 0), (x, int(H * 0.78))], fill=dark, width=1)
    waist = int(H * 0.62)
    draw.line([(0, waist), (W, waist)], fill=pal["gold_dim"] + (60,), width=2)
    draw.line([(0, waist + 4), (W, waist + 4)], fill=dark, width=1)
    floor = int(H * 0.80)
    draw.rectangle([0, floor, W, H], fill=pal["floor"] + (235,))
    draw.line([(0, floor), (W, floor)], fill=pal["gold_dim"] + (70,), width=2)
    canvas.alpha_composite(layer)


def window_box() -> tuple[int, int, int, int]:
    """高窗的内框矩形（所有室内场景共用同一构图）。"""
    return int(W * 0.245), int(H * 0.075), int(W * 0.525), int(H * 0.745)


def draw_window_frame(canvas: Image.Image, pal, box: tuple[int, int, int, int]) -> None:
    """窗框：金色内框 + 厚外框 + 窗台。"""
    left, top, right, bottom = box
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rectangle([left - 10, top - 10, right + 10, bottom + 10], outline=pal["gold"] + (230,), width=7)
    draw.rectangle([left - 22, top - 22, right + 22, bottom + 22], outline=pal["gold_dim"] + (150,), width=3)
    draw.rectangle([left + 6, bottom + 12, right - 6, bottom + 30], fill=pal["wainscot"] + (255,))  # 窗台
    canvas.alpha_composite(layer)


def draw_window(canvas: Image.Image, pal, rng: random.Random, theme: str) -> tuple[int, int, int, int]:
    """高窗：夜空 + 月亮 + 星 + 庭园剪影 + 窗棂 + 窗框；返回窗框矩形。"""
    left, right = int(W * 0.245), int(W * 0.525)
    top, bottom = int(H * 0.075), int(H * 0.745)

    strip = Image.new("RGB", (1, bottom - top))
    px = strip.load()
    for y in range(bottom - top):
        t = y / max(1, bottom - top - 1)
        px[0, y] = tuple(round(pal["sky_top"][i] + (pal["sky_bottom"][i] - pal["sky_top"][i]) * t) for i in range(3))
    sky = strip.resize((right - left, bottom - top), Image.BILINEAR).convert("RGBA")

    draw = ImageDraw.Draw(sky)
    # 月亮（半径/透明度可被调色板覆盖；樱吹雪用更小更柔的春夜月）
    moon = (int((right - left) * 0.72), int((bottom - top) * 0.20))
    moon_r = pal.get("moon_radius", 30)
    moon_a = pal.get("moon_alpha", 255 if theme == "light" else 235)
    if moon_r > 0:
        draw.ellipse([moon[0] - moon_r, moon[1] - moon_r, moon[0] + moon_r, moon[1] + moon_r], fill=pal.get("moon", (246, 244, 226)) + (moon_a,))
    # 星
    for _ in range(70 if theme == "dark" else 26):
        sx = rng.uniform(0, right - left)
        sy = rng.uniform(0, (bottom - top) * 0.7)
        r = rng.uniform(0.8, 2.1)
        a = rng.randint(90, 220) if theme == "dark" else rng.randint(60, 140)
        draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(255, 255, 255, a))
    # 庭园剪影（树丛 + 围栏）
    horizon = int((bottom - top) * 0.76)
    bush = (10, 16, 30, 255) if theme == "dark" else (120, 146, 186, 190)
    for i in range(-1, 9):
        bx = i * ((right - left) / 8)
        br = rng.uniform(26, 60)
        draw.ellipse([bx - br, horizon - br * 0.75, bx + br, horizon + br * 0.9], fill=bush)
    draw.rectangle([0, horizon + 18, right - left, bottom - top], fill=(8, 12, 24, 255) if theme == "dark" else (150, 172, 206, 210))
    for i in range(0, right - left, 22):
        draw.line([(i, horizon + 18), (i, bottom - top)], fill=(0, 0, 0, 60), width=1)

    # 窗棂
    for i in range(1, 3):
        x = (right - left) * i / 3
        draw.line([(x, 0), (x, bottom - top)], fill=pal["wainscot"] + (255,), width=9)
    for i in range(1, 4):
        y = (bottom - top) * i / 4
        draw.line([(0, y), (right - left, y)], fill=pal["wainscot"] + (255,), width=9)

    canvas.alpha_composite(sky, (left, top))
    draw_window_frame(canvas, pal, (left, top, right, bottom))
    return left - 22, top - 22, right + 22, bottom + 30


def draw_curtains(canvas: Image.Image, pal, box: tuple[int, int, int, int]) -> None:
    """窗帘：两侧垂褶 + 金色束带。"""
    left, top, right, bottom = box
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    spans = [
        (int(W * 0.155), left + 6),
        (right - 6, int(W * 0.615)),
    ]
    for index, (x0, x1) in enumerate(spans):
        width = x1 - x0
        draw.rectangle([x0, top - 26, x1, bottom + 52], fill=pal["curtain"] + (255,))
        # 垂褶：竖向明暗条
        folds = max(6, width // 26)
        for f in range(folds):
            fx = x0 + width * (f + 0.5) / folds
            shade = pal["curtain_light"] if f % 2 == 0 else pal["curtain"]
            half = width / folds * 0.5
            draw.rectangle([fx - half, top - 26, fx + half, bottom + 52], fill=shade + (255,))
        # 顶褶
        for f in range(folds):
            fx = x0 + width * (f + 0.5) / folds
            draw.ellipse([fx - width / folds * 0.6, top - 34, fx + width / folds * 0.6, top + 4], fill=pal["curtain_light"] + (255,))
        # 束带
        band_y = int(H * 0.40)
        draw.rectangle([x0 - 6, band_y, x1 + 6, band_y + 16], fill=pal["gold"] + (235,))
        draw.ellipse([x1 - 6, band_y + 20, x1 + 26, band_y + 86], fill=pal["curtain_light"] + (255,))
    canvas.alpha_composite(layer)


def draw_cornice(canvas: Image.Image, pal) -> None:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    y = int(H * 0.035)
    draw.rectangle([0, 0, W, y], fill=pal["wainscot"] + (255,))
    draw.line([(0, y), (W, y)], fill=pal["gold"] + (200,), width=3)
    draw.line([(0, y + 6), (W, y + 6)], fill=pal["gold_dim"] + (110,), width=1)
    for x in range(18, W, 74):
        draw.rectangle([x, y + 8, x + 30, y + 16], fill=pal["gold_dim"] + (90,))
    canvas.alpha_composite(layer)


def draw_wall_decor(canvas: Image.Image, pal) -> None:
    """右侧墙面装饰：壁灯 + 挂画（让立绘那一侧也有结构，不至于空成一片）。"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # 挂画：金色画框 + 内部深海色块
    fx0, fy0 = int(W * 0.795), int(H * 0.175)
    fx1, fy1 = int(W * 0.975), int(H * 0.475)
    draw.rectangle([fx0, fy0, fx1, fy1], fill=pal["wainscot"] + (255,))
    draw.rectangle([fx0 + 12, fy0 + 12, fx1 - 12, fy1 - 12], fill=pal["sky_top"] + (255,))
    for i in range(6):
        wy = fy0 + 30 + i * 18
        draw.line([(fx0 + 22, wy), (fx1 - 22, wy + 8)], fill=pal["curtain_light"] + (150,), width=3)
    draw.rectangle([fx0, fy0, fx1, fy1], outline=pal["gold"] + (225,), width=6)
    draw.rectangle([fx0 - 8, fy0 - 8, fx1 + 8, fy1 + 8], outline=pal["gold_dim"] + (140,), width=2)

    # 壁灯：托架 + 灯罩 + 烛光
    for sx in (int(W * 0.745),):
        sy = int(H * 0.335)
        draw.line([(sx, sy), (sx, sy + 46)], fill=pal["gold"] + (215,), width=4)
        draw.ellipse([sx - 22, sy - 14, sx + 22, sy + 16], fill=pal["gold"] + (225,))
        draw.polygon([(sx - 26, sy - 14), (sx + 26, sy - 14), (sx + 16, sy - 58), (sx - 16, sy - 58)], fill=(250, 246, 236, 225))
        draw.ellipse([sx - 7, sy - 74, sx + 7, sy - 56], fill=pal["candle"] + (255,))
    canvas.alpha_composite(layer)

    for sx in (int(W * 0.745),):
        canvas.alpha_composite(radial_glow((sx, int(H * 0.30)), 250, pal["candle"], 0.34 if sum(pal["wall_top"]) < 240 else 0.2))

    # 地面反光
    canvas.alpha_composite(radial_glow((int(W * 0.46), int(H * 0.95)), 620, pal["candle"], 0.14 if sum(pal["wall_top"]) < 240 else 0.08, squash=0.22))


def draw_chandelier(canvas: Image.Image, pal, center_x: int) -> None:
    """吊灯：吊链 + 五臂 + 烛光。"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    hang_top = int(H * 0.05)
    body_y = int(H * 0.265)
    draw.line([(center_x, hang_top), (center_x, body_y)], fill=pal["gold"] + (210,), width=3)
    for step in range(7):
        y = hang_top + (body_y - hang_top) * step / 7
        draw.ellipse([center_x - 6, y - 6, center_x + 6, y + 6], outline=pal["gold"] + (200,), width=2)
    draw.ellipse([center_x - 20, body_y - 20, center_x + 20, body_y + 20], fill=pal["gold"] + (235,))

    arm_gap = 104
    for arm in range(-2, 3):
        ax = center_x + arm * arm_gap
        ay = body_y + 74 + abs(arm) * 12
        draw.line([(center_x, body_y), (ax, ay)], fill=pal["gold"] + (215,), width=5)
        draw.ellipse([ax - 16, ay - 11, ax + 16, ay + 11], fill=pal["gold"] + (235,))
        draw.rectangle([ax - 6, ay - 62, ax + 6, ay - 12], fill=(250, 246, 236, 240))
        draw.ellipse([ax - 6, ay - 80, ax + 6, ay - 62], fill=pal["candle"] + (255,))
    canvas.alpha_composite(layer)

    for arm in range(-2, 3):
        ax = center_x + arm * arm_gap
        ay = body_y + 58 + abs(arm) * 12
        canvas.alpha_composite(radial_glow((ax, ay), 190, pal["candle"], 0.55 if sum(pal["wall_top"]) < 240 else 0.3))
    canvas.alpha_composite(radial_glow((center_x, body_y + 50), 560, pal["candle"], 0.24 if sum(pal["wall_top"]) < 240 else 0.14))


def scene_interior(theme: str, pose_key: str, filename: str) -> Image.Image:
    pal = INTERIOR[theme]
    rng = random.Random(f"interior:{pose_key}:{theme}")
    canvas = vertical_gradient(pal["wall_top"], pal["wall_bottom"])
    draw_wall_panels(canvas, pal)
    draw_cornice(canvas, pal)
    box = draw_window(canvas, pal, rng, theme)
    draw_curtains(canvas, pal, box)
    draw_chandelier(canvas, pal, int(W * 0.385))
    draw_wall_decor(canvas, pal)
    place_character(canvas, theme, filename, pal["glow"], pal["shadow"], 0.32 if theme == "dark" else 0.5)
    text_safe(canvas, theme)
    apply_vignette(canvas, pal["vignette"], 0.5 if theme == "dark" else 0.36)
    return canvas.convert("RGB")


# ---------------------------------------------------------------- 季节细节：雪


def draw_snowfall(canvas: Image.Image, pal, rng: random.Random, theme: str) -> None:
    """两层落雪：远层细密小点（轻微虚化）+ 近层略大亮点，随机斜落。

    左侧文字栏附近刻意减稀、减淡，避免雪点把正文压花。
    """
    far_n = 470 if theme == "dark" else 400
    near_n = 190

    def keep(x: float) -> bool:
        """0.45W 以左按距离降概率，越靠左越稀。"""
        edge = W * 0.45
        if x >= edge:
            return True
        return rng.random() < 0.18 + 0.82 * (x / edge)

    # 远层
    far_mask = Image.new("L", (W, H), 0)
    fdraw = ImageDraw.Draw(far_mask)
    for _ in range(far_n):
        x = rng.uniform(-30, W + 30)
        y = rng.uniform(-30, H + 30)
        if not keep(x):
            continue
        r = rng.uniform(0.6, 1.35)
        a = rng.randint(60, 140) if theme == "dark" else rng.randint(55, 125)
        fdraw.ellipse([x - r, y - r, x + r, y + r], fill=a)
    far_mask = far_mask.filter(ImageFilter.GaussianBlur(0.7))
    canvas.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (W, H), pal["snow_dim"]).split(), far_mask)))

    # 近层：稍大 + 拖尾，带一点下落动势
    near_mask = Image.new("L", (W, H), 0)
    ndraw = ImageDraw.Draw(near_mask)
    for _ in range(near_n):
        x = rng.uniform(-20, W + 20)
        y = rng.uniform(-20, H + 20)
        if not keep(x):
            continue
        r = rng.uniform(1.1, 2.4)
        drift = rng.uniform(-2.5, -0.6) * r
        a = rng.randint(115, 220) if theme == "dark" else rng.randint(115, 205)
        ndraw.ellipse([x - r, y - r, x + r, y + r], fill=a)
        ndraw.line([(x, y), (x + drift, y - r * rng.uniform(1.6, 2.6))], fill=max(40, a - 90), width=1)
    near_mask = near_mask.filter(ImageFilter.GaussianBlur(0.35))
    canvas.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (W, H), pal["snow"]).split(), near_mask)))


def draw_snow_on_frame(canvas: Image.Image, pal, box: tuple[int, int, int, int], rng: random.Random) -> None:
    """窗框/窗棂/窗台积雪：下缘压实发暗，上缘留白高光。"""
    left, top, right, bottom = box
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    snow, dim, frost = pal["snow"], pal["snow_dim"], pal["frost"]

    def cap(y: float, x0: float, x1: float, h: float, alpha: int = 240, seed: int = 0) -> None:
        """一条带起伏的积雪：上面留白、下面一条压暗的阴影。"""
        pts = []
        for x in range(int(x0), int(x1) + 1, 9):
            bump = math.sin(x / 47 + seed) * 1.6 + math.sin(x / 13 + seed * 2) * 1.1
            pts.append((x, y + bump))
        top_pts = [(x, yy - h) for x, yy in pts]
        draw.polygon(top_pts + pts[::-1], fill=snow + (alpha,))
        draw.line(pts, fill=dim + (200,), width=2)

    # 窗台积雪：最厚的一处，用两层软椭圆堆成雪堆而不是一条硬带
    cap(bottom + 13, left - 4, right + 4, 13, 200, 0.7)
    for ex, ew in ((left + 74, 86), (right - 96, 70), (left + 190, 54)):
        draw.ellipse([ex - ew, bottom + 2, ex + ew * 0.6, bottom + 22], fill=snow + (215,))
    draw.ellipse([left - 2, bottom + 6, left + 34, bottom + 24], fill=dim + (170,))

    # 上框 + 两侧外框的薄雪（窗台上方更少，避免形成白框）
    cap(top - 15, left - 20, right + 20, 8, 150, 2.3)
    for y0 in (int(H * 0.30), int(H * 0.58)):
        draw.ellipse([left - 21, y0, left - 12, y0 + 20], fill=snow + (105,))
        draw.ellipse([right + 12, y0 + 26, right + 21, y0 + 46], fill=snow + (105,))

    # 窗棂横档上的挂雪（只在竖棂顶头留一点，横档很淡）
    for i in range(1, 3):
        x = left + (right - left) * i / 3
        cap(top + 10, x - 4, x + 4, 4, 120, i * 1.7)
    for i in range(1, 4):
        y = top + (bottom - top) * i / 4
        cap(y - 3, left + 6, right - 6, 4, 90, i * 2.1)
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.6)))

    # 聚集在窗台与窗框上的冷光
    canvas.alpha_composite(radial_glow(((left + right) // 2, bottom + 30), 340, frost, 0.16 if sum(pal["wall_top"]) < 240 else 0.10, squash=0.3))


def draw_frost(canvas: Image.Image, pal, box: tuple[int, int, int, int], rng: random.Random) -> None:
    """窗玻璃四角的霜花：细密的结晶弧，靠玻璃角、越往里越淡（不是裂纹那种直射线）。"""
    left, top, right, bottom = box
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    frost = pal["frost"]

    corners = (
        (left + 14, top + 14, 46.0, 24),
        (right - 14, top + 14, 134.0, 20),
        (left + 14, bottom - 14, -46.0, 18),
        (right - 14, bottom - 14, -134.0, 14),
    )
    for cx, cy, base_deg, branches in corners:
        for b in range(branches):
            deg = base_deg + rng.uniform(-62, 62)
            length = rng.uniform(26, 92)
            alpha = int(105 * (1 - length / 115)) + 34
            # 弯折的两段折线，比一条直线更像霜晶
            mid_deg = deg + rng.uniform(-16, 16)
            mx = cx + length * 0.55 * math.cos(math.radians(mid_deg))
            my = cy - length * 0.55 * math.sin(math.radians(mid_deg))
            ex = mx + length * 0.45 * math.cos(math.radians(deg + rng.uniform(-22, 22)))
            ey = my - length * 0.45 * math.sin(math.radians(deg + rng.uniform(-22, 22)))
            draw.line([(cx, cy), (mx, my), (ex, ey)], fill=frost + (alpha,), width=1)
            # 侧枝（更短更淡）
            if rng.random() < 0.75:
                blen = length * rng.uniform(0.16, 0.3)
                bdeg = deg + rng.choice((-1, 1)) * rng.uniform(30, 58)
                draw.line(
                    [(mx, my), (mx + blen * math.cos(math.radians(bdeg)), my - blen * math.sin(math.radians(bdeg)))],
                    fill=frost + (max(22, alpha - 34),),
                    width=1,
                )
        # 角上一小块实心冰晶
        draw.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=frost + (60,))
    layer = layer.filter(ImageFilter.GaussianBlur(0.8))
    canvas.alpha_composite(layer)

    # 玻璃整体的一层薄霜雾（边角更重）
    veil = Image.new("L", (W, H), 0)
    vdraw = ImageDraw.Draw(veil)
    for _ in range(7):
        vx = rng.uniform(left, right)
        vy = rng.uniform(top, bottom)
        vr = rng.uniform(120, 260)
        vdraw.ellipse([vx - vr, vy - vr, vx + vr, vy + vr], fill=rng.randint(8, 18))
    veil = veil.filter(ImageFilter.GaussianBlur(40))
    canvas.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (W, H), frost).split(), veil)))


def draw_garden_snow(canvas: Image.Image, pal, rng: random.Random) -> None:
    """庭园剪影上的积雪：树冠顶 + 围墙压顶。"""
    left, right = int(W * 0.245), int(W * 0.525)
    top, bottom = int(H * 0.075), int(H * 0.745)
    horizon = top + int((bottom - top) * 0.76)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for i in range(-1, 9):
        bx = left + i * ((right - left) / 8)
        br = rng.uniform(26, 60)
        # 每丛树只挂 1-2 段短弧，留缺口，免得连成一条白线
        for _ in range(rng.randint(1, 2)):
            start = rng.uniform(205, 265)
            span = rng.uniform(34, 62)
            draw.arc(
                [bx - br, horizon - br * 0.75, bx + br, horizon + br * 0.9],
                start,
                min(340.0, start + span),
                fill=pal["snow"] + (rng.randint(95, 150),),
                width=max(1, int(br * 0.10)),
            )
        if rng.random() < 0.5:
            draw.ellipse([bx - 7, horizon - br * 0.72, bx + 7, horizon - br * 0.54], fill=pal["snow"] + (105,))
    for x0 in range(left + 20, right - 20, 74):
        draw.line(
            [(x0, horizon + 15), (x0 + rng.randint(30, 52), horizon + 15)],
            fill=pal["snow"] + (rng.randint(80, 125),),
            width=2,
        )
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(1.0)))


def scene_snow(theme: str, pose_key: str, filename: str) -> Image.Image:
    """雪夜庭：与 interior 同一间房、同一构图，换成落雪的冬夜。"""
    pal = SNOW[theme]
    dark = theme == "dark"
    rng = random.Random(f"snow:{pose_key}:{theme}")
    canvas = vertical_gradient(pal["wall_top"], pal["wall_bottom"])
    draw_wall_panels(canvas, pal)
    draw_cornice(canvas, pal)
    left, top, right, bottom = window_box()
    draw_window(canvas, pal, rng, theme)
    draw_garden_snow(canvas, pal, rng)
    draw_frost(canvas, pal, (left, top, right, bottom), rng)
    draw_snowfall(canvas, pal, rng, theme)
    draw_curtains(canvas, pal, (left - 22, top - 22, right + 22, bottom + 30))
    draw_chandelier(canvas, pal, int(W * 0.385))
    # 冷暖对比：吊灯那一片再补一层暖烛光，和窗外的冷蓝拉开
    canvas.alpha_composite(radial_glow((int(W * 0.385), int(H * 0.34)), 900, pal["candle"], 0.22 if dark else 0.13, squash=0.75))
    draw_wall_decor(canvas, pal)
    draw_snow_on_frame(canvas, pal, (left - 22, top - 22, right + 22, bottom + 30), rng)
    place_character(canvas, theme, filename, pal["glow"], pal["shadow"], 0.30 if dark else 0.5)
    text_safe(canvas, theme)
    apply_vignette(canvas, pal["vignette"], 0.5 if dark else 0.36)
    return canvas.convert("RGB")


# ---------------------------------------------------------------- 季节细节：中秋


def draw_big_moon(canvas: Image.Image, pal, rng: random.Random, theme: str) -> None:
    """窗外的大满月：暖色实心 + 环形光晕 + 月面纹理 + 几缕云。"""
    left, right = int(W * 0.245), int(W * 0.525)
    top, bottom = int(H * 0.075), int(H * 0.745)
    cx = left + int((right - left) * 0.60)
    cy = top + int((bottom - top) * 0.235)
    r = 100 if theme == "dark" else 92

    # 柔和光晕：外层大而淡，内层小而亮
    for radius, strength in ((640, 0.26), (380, 0.30), (200, 0.26)):
        canvas.alpha_composite(radial_glow((cx, cy), radius, pal["moon_glow"], strength if theme == "dark" else strength * 0.68))

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=pal["moon"] + (250,))
    # 月面纹理：低对比的环形山斑（小而淡，避免变成大块斑点）
    for _ in range(22):
        ang = rng.uniform(0, math.tau)
        dist = rng.uniform(0, r * 0.72)
        mx = cx + dist * math.cos(ang)
        my = cy + dist * math.sin(ang)
        mr = rng.uniform(4, 13) * (1 - dist / (r * 1.5))
        if mr < 3:
            continue
        shade = 238 if theme == "dark" else 240
        draw.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(shade, shade - 12, shade - 40, 34))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(1.0)))

    # 云：横向淡带，压过月亮下缘
    cloud = Image.new("L", (W, H), 0)
    cdraw = ImageDraw.Draw(cloud)
    for i in range(5):
        cxx = cx + rng.uniform(-r * 2.2, r * 2.2)
        cyy = cy + rng.uniform(-r * 0.2, r * 1.5)
        cw = rng.uniform(r * 1.1, r * 2.6)
        ch = rng.uniform(7, 18)
        cdraw.ellipse([cxx - cw, cyy - ch, cxx + cw, cyy + ch], fill=rng.randint(30, 70))
    cloud = cloud.filter(ImageFilter.GaussianBlur(9))
    canvas.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (W, H), pal["moon_glow"]).split(), cloud)))


def draw_lanterns(canvas: Image.Image, pal, theme: str, z: int) -> None:
    """室内纸灯笼：吊绳 + 上下木盖 + 暖纸身 + 竖骨 + 流苏 + 暖光。

    z=0 是立在立绘之后的（更远），z=1 是垂在立绘之前的（更近）；
    两批分开画，才能让近处那盏自然压住立绘。
    """
    dark = theme == "dark"
    specs = (
        (0.585, 0.255, 68),
        (0.638, 0.115, 54),
        (0.618, 0.435, 60),
    )
    if z == 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        for index, (rx, ry, rad) in enumerate(specs):
            cx, cy = int(W * rx), int(H * ry)
            # 只为「更远」的那批画吊绳，近处那盏的绳子会压住立绘头顶
            if index >= 1:
                draw.line([(cx, int(H * 0.035)), (cx, cy - rad)], fill=pal["gold_dim"] + (215,), width=2)
            draw.ellipse([cx - 11, cy - rad - 7, cx + 11, cy - rad + 7], fill=pal["gold"] + (225,))
            draw.ellipse([cx - 13, cy + rad - 8, cx + 13, cy + rad + 8], fill=pal["gold"] + (225,))
            # 纸身
            draw.ellipse([cx - rad, cy - rad * 0.94, cx + rad, cy + rad * 0.94], fill=pal["lantern_paper"] + (215,))
            draw.ellipse([cx - rad * 0.72, cy - rad * 0.78, cx + rad * 0.72, cy + rad * 0.78], fill=pal["lantern"] + (160,))
            # 竖骨
            for k in range(-2, 3):
                ox = cx + k * rad * 0.36
                half = rad * 0.94 * math.sqrt(max(0.0, 1 - (k * 0.36) ** 2))
                draw.line([(ox, cy - half), (ox, cy + half)], fill=pal["gold_dim"] + (95,), width=1)
            # 流苏
            draw.line([(cx, cy + rad + 8), (cx, cy + rad + 44)], fill=pal["gold"] + (210,), width=3)
            draw.ellipse([cx - 7, cy + rad + 44, cx + 7, cy + rad + 58], fill=pal["gold"] + (215,))
        canvas.alpha_composite(layer)

    # 灯笼的暖光统一最后补，这样前后两批的光都不会压在其他元素上
    for rx, ry, rad in specs:
        cx, cy = int(W * rx), int(H * ry)
        canvas.alpha_composite(radial_glow((cx, cy), 250, pal["lantern"], 0.40 if dark else 0.23))
        canvas.alpha_composite(radial_glow((cx, cy), 600, pal["lantern"], 0.15 if dark else 0.09))


def draw_osmanthus(canvas: Image.Image, pal, rng: random.Random, theme: str) -> None:
    """室内飘落的桂花花瓣：小椭圆 + 明暗两层，散而不糊。"""
    dark = theme == "dark"
    canvas.alpha_composite(radial_glow((int(W * 0.50), int(H * 0.46)), 980, pal["moon_glow"], 0.11 if dark else 0.07, squash=0.95))

    for depth in range(2):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        count = 112 if depth == 0 else 34
        size = 2.9 if depth == 0 else 4.6
        color = pal["petal"] if depth == 0 else pal["petal_light"]
        for _ in range(count):
            x = rng.uniform(-20, W + 20)
            y = rng.uniform(-20, H + 20)
            rw = size * rng.uniform(0.7, 1.4)
            rh = rw * rng.uniform(0.42, 0.68)
            ang = rng.uniform(0, 180)
            box = Image.new("RGBA", (int(rw * 2) + 6, int(rh * 2) + 6), (0, 0, 0, 0))
            bd = ImageDraw.Draw(box)
            bd.ellipse(
                [2, 2, rw * 2 + 2, rh * 2 + 2],
                fill=color + (rng.randint(70, 150) if depth == 0 else rng.randint(90, 175),),
            )
            box = box.rotate(ang, resample=Image.BICUBIC, expand=True)
            layer.alpha_composite(box, (int(x), int(y)))
        canvas.alpha_composite(layer)


def scene_moonfest(theme: str, pose_key: str, filename: str) -> Image.Image:
    """桂月夜庭：与 interior 同一间房、同一构图，换成中秋暖金版本。"""
    pal = MOONFEST[theme]
    dark = theme == "dark"
    rng = random.Random(f"moonfest:{pose_key}:{theme}")
    canvas = vertical_gradient(pal["wall_top"], pal["wall_bottom"])
    draw_wall_panels(canvas, pal)
    draw_cornice(canvas, pal)
    left, top, right, bottom = window_box()
    draw_window(canvas, pal, rng, theme)
    draw_big_moon(canvas, pal, rng, theme)
    draw_curtains(canvas, pal, (left - 22, top - 22, right + 22, bottom + 30))
    draw_chandelier(canvas, pal, int(W * 0.385))
    draw_wall_decor(canvas, pal)
    draw_lanterns(canvas, pal, theme, 0)                      # 远层：立绘之后
    place_character(canvas, theme, filename, pal["glow"], pal["shadow"], 0.36 if dark else 0.48)
    draw_lanterns(canvas, pal, theme, 1)                      # 近层：垂在立绘之前
    draw_osmanthus(canvas, pal, rng, theme)
    text_safe(canvas, theme)
    apply_vignette(canvas, pal["vignette"], 0.48 if dark else 0.36)
    return canvas.convert("RGB")


# ---------------------------------------------------------------- 季节细节：樱吹雪


def edge_falloff(x: float, edge: float, floor: float, rng: random.Random) -> bool:
    """左侧文字栏那一片按距离降概率留白（越靠左越稀），右侧不动。"""
    if x >= edge:
        return True
    return rng.random() < floor + (1.0 - floor) * (x / edge)


def draw_branch(draw: ImageDraw.ImageDraw, pts, width: float, pal) -> None:
    """一段枝干：深色粗线打底做剪影，亮色细线提受光面，枝条才有圆柱感。"""
    draw.line(pts, fill=pal["branch"] + (250,), width=max(2, round(width)), joint="curve")
    if width > 3.2:
        draw.line(pts, fill=pal["branch_light"] + (170,), width=max(1, round(width * 0.32)), joint="curve")


def branch_paths(left: float, top: float, right: float, bottom: float) -> tuple:
    """樱枝骨架：右上角最密（自窗框外垂入），左沿一枝斜插，中下部只留细梢。

    坐标按窗玻璃的比例给，中间一带（约 0.25–0.62 宽 / 0.30–0.72 高）刻意留空，
    既不挡住月亮与庭园剪影，也不会和前面的吊灯抢地方。
    """
    lx, ly = left, top
    ww, wh = right - left, bottom - top

    def pt(u: float, v: float) -> tuple[float, float]:
        return lx + ww * u, ly + wh * v

    return (
        ([pt(-0.04, 0.02), pt(0.07, 0.12), pt(0.17, 0.21)], 9.0),
        ([pt(0.07, 0.12), pt(0.13, 0.12), pt(0.18, 0.13), pt(0.24, 0.14), pt(0.30, 0.15)], 5.6),
        ([pt(0.13, 0.12), pt(0.16, 0.12), pt(0.19, 0.10), pt(0.22, 0.10), pt(0.26, 0.08)], 3.5),
        ([pt(0.19, 0.10), pt(0.21, 0.09), pt(0.22, 0.08), pt(0.24, 0.06), pt(0.25, 0.05)], 2.1),
        ([pt(0.13, 0.12), pt(0.17, 0.17), pt(0.20, 0.21)], 3.5),
        ([pt(0.17, 0.17), pt(0.19, 0.17), pt(0.21, 0.18), pt(0.23, 0.18), pt(0.24, 0.18)], 2.1),
        ([pt(0.07, 0.12), pt(0.07, 0.17), pt(0.06, 0.22), pt(0.06, 0.27), pt(0.06, 0.32)], 5.6),
        ([pt(0.07, 0.17), pt(0.09, 0.19), pt(0.10, 0.22), pt(0.12, 0.24), pt(0.13, 0.26)], 3.5),
        ([pt(0.09, 0.19), pt(0.11, 0.20), pt(0.12, 0.20), pt(0.14, 0.20), pt(0.16, 0.20)], 2.1),
        ([pt(0.09, 0.19), pt(0.09, 0.21), pt(0.09, 0.23), pt(0.09, 0.24), pt(0.09, 0.26)], 2.1),
        ([pt(0.07, 0.17), pt(0.03, 0.20), pt(-0.01, 0.24)], 3.5),
        ([pt(0.03, 0.20), pt(0.02, 0.22), pt(0.02, 0.24), pt(0.01, 0.26)], 2.1),
        ([pt(1.04, 0.04), pt(0.97, 0.13), pt(0.92, 0.20), pt(0.87, 0.30)], 9.5),
        ([pt(0.97, 0.13), pt(0.99, 0.23), pt(1.00, 0.32)], 5.9),
        ([pt(0.97, 0.13), pt(0.92, 0.14), pt(0.86, 0.16), pt(0.81, 0.18)], 5.9),
        ([pt(0.86, 0.16), pt(0.83, 0.20), pt(0.80, 0.26)], 3.7),
        ([pt(0.83, 0.20), pt(0.84, 0.22), pt(0.84, 0.25), pt(0.85, 0.27)], 2.3),
        ([pt(0.83, 0.20), pt(0.80, 0.21), pt(0.78, 0.21), pt(0.76, 0.20)], 2.3),
        ([pt(0.86, 0.16), pt(0.81, 0.16), pt(0.75, 0.16)], 3.7),
        ([pt(0.81, 0.16), pt(0.79, 0.18), pt(0.76, 0.20)], 2.3),
        ([pt(0.81, 0.16), pt(0.80, 0.15), pt(0.78, 0.13), pt(0.77, 0.12)], 2.3),
        ([pt(-0.02, 0.36), pt(0.08, 0.38), pt(0.20, 0.39)], 6.0),
        ([pt(0.08, 0.38), pt(0.11, 0.37), pt(0.14, 0.36), pt(0.17, 0.34), pt(0.21, 0.33)], 3.7),
        ([pt(0.17, 0.34), pt(0.18, 0.31), pt(0.21, 0.28), pt(0.23, 0.26)], 2.3),
        ([pt(0.18, 0.31), pt(0.18, 0.29), pt(0.18, 0.26)], 1.4),
        ([pt(0.18, 0.31), pt(0.20, 0.31), pt(0.21, 0.30), pt(0.22, 0.30), pt(0.24, 0.29)], 1.4),
        ([pt(1.03, 0.24), pt(0.96, 0.23), pt(0.88, 0.22), pt(0.81, 0.22)], 7.0),
        ([pt(0.96, 0.23), pt(0.93, 0.26), pt(0.91, 0.28), pt(0.89, 0.32), pt(0.87, 0.35)], 4.3),
        ([pt(0.91, 0.28), pt(0.92, 0.31), pt(0.92, 0.34), pt(0.92, 0.37), pt(0.92, 0.40)], 2.7),
        ([pt(0.92, 0.37), pt(0.94, 0.39), pt(0.95, 0.42)], 1.7),
        ([pt(0.92, 0.37), pt(0.90, 0.38), pt(0.89, 0.39), pt(0.88, 0.40)], 1.7),
        ([pt(0.91, 0.28), pt(0.90, 0.28), pt(0.87, 0.28), pt(0.85, 0.29), pt(0.82, 0.29)], 2.7),
        ([pt(0.90, 0.28), pt(0.88, 0.29), pt(0.87, 0.30), pt(0.86, 0.30), pt(0.84, 0.31)], 1.7),
        ([pt(0.90, 0.28), pt(0.88, 0.27), pt(0.85, 0.25)], 1.7),
        ([pt(0.96, 0.23), pt(0.93, 0.21), pt(0.90, 0.19), pt(0.88, 0.17), pt(0.85, 0.16)], 4.3),
        ([pt(0.93, 0.21), pt(0.91, 0.22), pt(0.89, 0.23), pt(0.87, 0.24), pt(0.85, 0.25)], 2.7),
        ([pt(0.89, 0.23), pt(0.88, 0.24), pt(0.86, 0.26), pt(0.84, 0.27)], 1.7),
        ([pt(0.89, 0.23), pt(0.88, 0.23), pt(0.87, 0.23), pt(0.85, 0.22), pt(0.84, 0.23)], 1.7),
        ([pt(0.66, -0.03), pt(0.65, 0.09), pt(0.65, 0.24)], 6.5),
        ([pt(0.65, 0.09), pt(0.68, 0.12), pt(0.70, 0.13), pt(0.73, 0.15), pt(0.77, 0.17)], 4.0),
        ([pt(0.73, 0.15), pt(0.77, 0.13), pt(0.80, 0.12), pt(0.83, 0.11)], 2.5),
        ([pt(0.80, 0.12), pt(0.83, 0.09), pt(0.85, 0.06)], 1.5),
        ([pt(0.80, 0.12), pt(0.83, 0.13), pt(0.85, 0.14)], 1.5),
        ([pt(0.73, 0.15), pt(0.75, 0.17), pt(0.77, 0.18), pt(0.79, 0.20), pt(0.81, 0.21)], 2.5),
        ([pt(0.79, 0.20), pt(0.82, 0.20), pt(0.85, 0.21)], 1.5),
        ([pt(0.79, 0.20), pt(0.79, 0.21), pt(0.79, 0.23), pt(0.80, 0.25)], 1.5),
        ([pt(0.65, 0.09), pt(0.59, 0.15), pt(0.54, 0.20)], 4.0),
        ([pt(0.59, 0.15), pt(0.59, 0.19), pt(0.59, 0.22), pt(0.58, 0.25)], 2.5),
        ([pt(0.59, 0.22), pt(0.59, 0.25), pt(0.60, 0.28)], 1.5),
        ([pt(0.59, 0.22), pt(0.57, 0.23), pt(0.56, 0.23), pt(0.55, 0.24), pt(0.54, 0.25)], 1.5),
        ([pt(0.59, 0.15), pt(0.55, 0.14), pt(0.50, 0.14)], 2.5),
        ([pt(0.55, 0.14), pt(0.53, 0.15), pt(0.51, 0.16), pt(0.50, 0.17)], 1.5),
        ([pt(0.55, 0.14), pt(0.53, 0.13), pt(0.52, 0.12), pt(0.51, 0.11)], 1.5),
        ([pt(0.30, -0.03), pt(0.31, 0.02), pt(0.33, 0.08), pt(0.34, 0.14), pt(0.34, 0.21)], 5.5),
        ([pt(0.33, 0.08), pt(0.37, 0.14), pt(0.40, 0.23)], 3.4),
        ([pt(0.37, 0.14), pt(0.39, 0.15), pt(0.42, 0.16), pt(0.44, 0.16), pt(0.47, 0.18)], 2.1),
        ([pt(0.42, 0.16), pt(0.46, 0.15), pt(0.49, 0.16)], 1.3),
        ([pt(0.42, 0.16), pt(0.43, 0.18), pt(0.44, 0.20), pt(0.45, 0.22)], 1.3),
        ([pt(0.37, 0.14), pt(0.36, 0.17), pt(0.35, 0.19), pt(0.33, 0.23)], 2.1),
        ([pt(0.35, 0.19), pt(0.35, 0.23), pt(0.36, 0.26)], 1.3),
        ([pt(0.35, 0.19), pt(0.32, 0.20), pt(0.30, 0.21)], 1.3),
        ([pt(0.33, 0.08), pt(0.28, 0.13), pt(0.24, 0.19)], 3.4),
        ([pt(0.28, 0.13), pt(0.29, 0.18), pt(0.29, 0.22)], 2.1),
        ([pt(0.29, 0.18), pt(0.31, 0.20), pt(0.34, 0.22)], 1.3),
        ([pt(0.29, 0.18), pt(0.27, 0.20), pt(0.25, 0.22)], 1.3),
        ([pt(0.28, 0.13), pt(0.24, 0.15), pt(0.21, 0.18)], 2.1),
        ([pt(0.24, 0.15), pt(0.24, 0.17), pt(0.23, 0.20)], 1.3),
        ([pt(0.24, 0.15), pt(0.23, 0.15), pt(0.22, 0.15), pt(0.21, 0.15), pt(0.20, 0.15)], 1.3),
        ([pt(0.42, 1.03), pt(0.43, 0.99), pt(0.44, 0.95), pt(0.45, 0.90), pt(0.47, 0.86)], 5.0),
        ([pt(0.45, 0.90), pt(0.45, 0.87), pt(0.44, 0.85), pt(0.44, 0.82), pt(0.43, 0.79)], 3.1),
        ([pt(0.44, 0.82), pt(0.43, 0.81), pt(0.42, 0.79), pt(0.40, 0.77), pt(0.40, 0.76)], 1.9),
        ([pt(0.43, 0.81), pt(0.41, 0.80), pt(0.39, 0.79), pt(0.37, 0.78)], 1.2),
        ([pt(0.43, 0.81), pt(0.43, 0.79), pt(0.43, 0.78), pt(0.43, 0.76)], 1.2),
    )



def sample_branches(paths) -> list:
    """沿枝干按固定步长取点：花团只长在枝上，画面才像「一棵开花的树」。"""
    pts = []
    for path, _w in paths:
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            seg = math.hypot(x1 - x0, y1 - y0)
            steps = max(2, int(seg / 15) + 1)
            for k in range(steps + 1):
                t = k / steps
                pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return pts


def blossom_specs(paths, rng: random.Random, theme: str) -> tuple[list, list]:
    """两层花簇落点。

    每个落点都以枝上取样点为基准做二维散布（垂直于枝条的偏移更大），
    远层（小块、密、偏深粉）与近层（大朵、稀、带暖芯）各自独立取样 → 疏密不同。
    取样点会按粗细过滤：1.3px 的末梢不挂花，免得糊成一片。
    """
    dark = theme == "dark"
    base = sample_branches([(p, w) for p, w in paths if w >= 2.0])

    def cluster(points: int, spread: float, along: float, size: tuple, dark_ratio: float) -> list:
        out = []
        for _ in range(points):
            bx, by = base[rng.randrange(len(base))]
            out.append((bx + rng.gauss(0, along), by + rng.gauss(0, spread), rng.uniform(*size), dark_ratio))
        return out

    # 远层：每个取样点上挂 1-3 朵，二维散开 → 花团成簇而不是串珠
    far = cluster(74 if dark else 66, 14.0, 11.0, (4.4, 7.6) if dark else (5.2, 8.6), 0.0)
    far += cluster(54, 7.5, 6.0, (3.8, 6.0) if dark else (4.4, 6.8), 0.0)
    # 近层：十来个大花团（每团 3-8 朵大花贴在一起），另加若干散朵
    near = []
    for _ in range(12):
        bx, by = base[rng.randrange(len(base))]
        for _ in range(rng.randint(3, 8)):
            near.append((bx + rng.gauss(0, 19.0), by + rng.gauss(0, 15.0), rng.uniform(8.6, 13.6) if dark else rng.uniform(9.4, 14.6), 0.0))
    near += cluster(14, 22.0, 16.0, (7.8, 11.0) if dark else (8.6, 12.0), 0.0)
    return far, near


def draw_blossom(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color, core_color, alpha: int) -> None:
    """单朵樱花：五枚花瓣绕心排布（小朵用四枚），中间一点暖芯 → 远看是花不是噪点。"""
    petals = 5 if r > 6.0 else 4
    start = 90.0 / petals
    for k in range(petals):
        ang = math.radians(start + 360.0 * k / petals)
        px = cx + r * 0.58 * math.cos(ang)
        py = cy + r * 0.58 * math.sin(ang)
        box = [px - r * 0.52, py - r * 0.40, px + r * 0.52, py + r * 0.40]
        if r > 7.0:
            # 大朵留一道向外的凹口，轮廓更像樱花瓣而不是圆点
            deg = math.degrees(ang)
            draw.pieslice(box, deg - 148.0, deg + 148.0, fill=color + (alpha,))
        else:
            draw.ellipse(box, fill=color + (alpha,))
    if core_color is not None:
        draw.ellipse([cx - r * 0.19, cy - r * 0.19, cx + r * 0.19, cy + r * 0.19], fill=core_color + (min(255, alpha),))


def draw_sakura_branches(canvas: Image.Image, pal, theme: str) -> tuple:
    """窗玻璃上的樱花枝：先画枝干，再在枝上点花团（远层虚、近层实）。"""
    left, top = int(W * 0.245), int(H * 0.075)
    right, bottom = int(W * 0.525), int(H * 0.745)
    paths = branch_paths(left, top, right, bottom)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for path, width in paths:
        draw_branch(draw, path, width, pal)

    # 枝干外沿一层薄粉（花光染在枝上），深枝才不至于生硬
    halo = layer.filter(ImageFilter.GaussianBlur(5))
    canvas.alpha_composite(
        Image.merge("RGBA", (*Image.new("RGB", (W, H), pal["blossom_deep"]).split(), halo.getchannel("A").point(lambda v: round(v * 0.30))))
    )
    canvas.alpha_composite(layer)
    return paths


def draw_blossoms(canvas: Image.Image, pal, paths, rng: random.Random, theme: str) -> None:
    """在枝上成簇开花：远层小簇（虚化、深粉、稠密）+ 近层大朵（清晰、亮粉、暖芯）。"""
    dark = theme == "dark"
    far, near = blossom_specs(paths, rng, theme)

    # 花团整体的柔光：夜里一片开花的树，先铺一层粉雾再点花
    left, right = int(W * 0.245), int(W * 0.525)
    top, bottom = int(H * 0.075), int(H * 0.745)
    canvas.alpha_composite(radial_glow(((left + right) // 2, top + int((bottom - top) * 0.26)), 660, pal["blossom"], 0.17 if dark else 0.12))

    far_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fdraw = ImageDraw.Draw(far_layer)
    for x, y, r, _ in far:
        c = pal["blossom_deep"] if r > 5.9 else pal["blossom"]
        draw_blossom(fdraw, x, y, r, c, None, rng.randint(120, 190))
    canvas.alpha_composite(far_layer.filter(ImageFilter.GaussianBlur(0.8)))

    near_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ndraw = ImageDraw.Draw(near_layer)
    for x, y, r, _ in near:
        c = pal["blossom_light"] if rng.random() < 0.32 else pal["blossom"]
        draw_blossom(ndraw, x, y, r, c, pal["blossom_core"], rng.randint(215, 255))
    canvas.alpha_composite(near_layer)


def draw_glass_reflection(canvas: Image.Image, pal, theme: str) -> None:
    """玻璃下缘的月光倒影：按窗棂分格，只在横档下方留一抹更淡的亮斑。"""
    left, right = int(W * 0.245), int(W * 0.525)
    top, bottom = int(H * 0.075), int(H * 0.745)
    cx = left + int((right - left) * 0.70)
    cy = top + int((bottom - top) * 0.20)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for i in range(1, 4):
        y = top + (bottom - top) * i / 4
        dy = (bottom - cy) + (y - top) * 0.42
        r = 26 * max(0.4, 1 - i * 0.18)
        a = int((78 if theme == "dark" else 66) * (1 - i * 0.16))
        draw.ellipse([cx - r, y + dy - r * 0.34, cx + r, y + dy + r * 0.34], fill=pal["moon"] + (max(10, a),))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(7)))


def petal_sprite(rw: float, rh: float, ang: float, color, alpha: int, face) -> Image.Image:
    """烘一枚旋转好的花瓣：低透明度直接画到图层上会被 blur 冲淡，必须先烘再贴。"""
    box = Image.new("RGBA", (int(rw * 2) + 10, int(rh * 2.8) + 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(box)
    top, bot = 5, 5 + rh * 2
    d.ellipse([5, top, 5 + rw * 2, top + rh * 1.9], fill=color + (alpha,))
    d.polygon([(5 + rw * 0.62, bot - rh * 0.4), (5 + rw * 1.38, bot - rh * 0.4), (5 + rw, bot + rh * 0.9)], fill=color + (alpha,))
    # 花瓣根部的亮条：有它才看得出旋转与朝向
    d.ellipse([5 + rw * 0.78, top + rh * 0.25, 5 + rw * 1.22, top + rh * 1.15], fill=face + (min(255, alpha + 45),))
    return box.rotate(ang, resample=Image.BICUBIC, expand=True)


def draw_falling_petals(canvas: Image.Image, pal, rng: random.Random, theme: str) -> None:
    """室内飘落的樱花瓣：比桂花大得多，带随机旋转与明暗两面；左侧文字栏依旧减稀。"""
    dark = theme == "dark"
    canvas.alpha_composite(radial_glow((int(W * 0.50), int(H * 0.44)), 940, pal["blossom"], 0.11 if dark else 0.07, squash=0.95))

    edge = W * 0.66

    def layer_of(count: int, size: float, color, face, alo: int, ahi: int, blur: float) -> None:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for _ in range(count):
            x = rng.uniform(-30, W + 30)
            y = rng.uniform(-30, H + 30)
            if not edge_falloff(x, edge, 0.10, rng):
                continue
            rw = size * rng.uniform(0.75, 1.35)
            rh = rw * rng.uniform(0.52, 0.80)
            sprite = petal_sprite(rw, rh, rng.uniform(-180.0, 180.0), color, rng.randint(alo, ahi), face)
            layer.alpha_composite(sprite, (int(x - sprite.width / 2), int(y - sprite.height / 2)))
        if blur > 0:
            layer = layer.filter(ImageFilter.GaussianBlur(blur))
        canvas.alpha_composite(layer)

    # 远层：小、淡、密（带一点虚化）；近层：大、实、稀，能看清花瓣形状
    layer_of(210 if dark else 186, 3.6, pal["petal"], pal["petal_light"], 46, 96, 1.0)
    layer_of(74, 7.6, pal["petal_light"], pal["petal_light"], 110, 185, 0.0)
    layer_of(22, 12.0, pal["petal_light"] if dark else pal["petal"], pal["blossom_light"], 140, 215, 0.0)


def draw_sill_petals(canvas: Image.Image, pal, rng: random.Random) -> None:
    """窗台上落了一层花瓣，另有一根细梢从窗框右下探进室内，把樱花带进屋。"""
    left, right = int(W * 0.245), int(W * 0.525)
    bottom = int(H * 0.745)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for _ in range(52):
        x = rng.uniform(left - 30, right + 34)
        y = bottom + 15 + abs(rng.gauss(0, 8))
        rw = rng.uniform(3.2, 7.4)
        rh = rw * rng.uniform(0.45, 0.75)
        a = rng.randint(120, 205)
        c = pal["petal_light"] if rng.random() < 0.45 else pal["petal"]
        draw.ellipse([x - rw, y - rh, x + rw, y + rh], fill=c + (a,))
    # 探进室内的细梢（越过窗框一点，往左下挑，不碰立绘）
    draw_branch(draw, [(right - 18, bottom - 2), (right - 76, bottom + 46), (right - 138, bottom + 60), (right - 186, bottom + 104)], 3.4, pal)
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.5)))


def scene_sakura(theme: str, pose_key: str, filename: str) -> Image.Image:
    """樱吹雪：与 interior 同一间房、同一构图，窗外换成春夜樱花枝。"""
    pal = SAKURA[theme]
    dark = theme == "dark"
    rng = random.Random(f"sakura:{pose_key}:{theme}")
    canvas = vertical_gradient(pal["wall_top"], pal["wall_bottom"])
    draw_wall_panels(canvas, pal)
    draw_cornice(canvas, pal)
    left, top, right, bottom = window_box()
    draw_window(canvas, pal, rng, theme)          # 春夜月色（更小更柔）+ 藤紫天空 + 庭园剪影
    draw_glass_reflection(canvas, pal, theme)
    paths = draw_sakura_branches(canvas, pal, theme)
    draw_blossoms(canvas, pal, paths, rng, theme)
    draw_curtains(canvas, pal, (left - 22, top - 22, right + 22, bottom + 30))
    draw_chandelier(canvas, pal, int(W * 0.385))
    # 冷暖对比：吊灯那一片补一层暖烛光，和窗外偏冷的紫粉夜色拉开
    canvas.alpha_composite(radial_glow((int(W * 0.385), int(H * 0.34)), 900, pal["candle"], 0.22 if dark else 0.13, squash=0.75))
    draw_wall_decor(canvas, pal)
    place_character(canvas, theme, filename, pal["glow"], pal["shadow"], 0.30 if dark else 0.5)
    draw_sill_petals(canvas, pal, rng)
    draw_falling_petals(canvas, pal, rng, theme)
    text_safe(canvas, theme)
    apply_vignette(canvas, pal["vignette"], 0.5 if dark else 0.36)
    return canvas.convert("RGB")


# ---------------------------------------------------------------- 入口

SCENES = {
    "abyss": scene_abyss,
    "interior": scene_interior,
    "snow": scene_snow,
    "moonfest": scene_moonfest,
    "sakura": scene_sakura,
}

# --set all 只产出这 4 套内置场景；sakura 需要显式指定（--set sakura）。
ALL_SETS = ("abyss", "interior", "snow", "moonfest")


def require_src_dir() -> None:
    if not os.path.isdir(SRC_DIR):
        raise SystemExit(
            f"找不到立绘素材目录: {SRC_DIR}\n"
            "请先安装 dsh-whale-musume（https://github.com/Sutera-Diffusus/dsh-whale-musume），"
            "或用环境变量 DSH_WHALE_MUSUME_ASSETS 指向它的 assets/generated 目录。"
        )


def main() -> None:
    require_src_dir()
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", dest="which", default="all", choices=["all", *SCENES])
    parser.add_argument("--out", dest="out", default=None)
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = args.out or os.path.join(os.path.dirname(here), "dsh-whale-atelier", "assets")
    os.makedirs(out_dir, exist_ok=True)

    sets = list(ALL_SETS) if args.which == "all" else [args.which]
    for name in sets:
        for pose_key, filename in POSES.items():
            for theme in ("dark", "light"):
                path = os.path.join(out_dir, f"ww-{name}-{pose_key}-{theme}.webp")
                SCENES[name](theme, pose_key, filename).save(path, "WEBP", quality=84, method=6)
                print(f"{path}  {os.path.getsize(path) // 1024} KB")


if __name__ == "__main__":
    main()
