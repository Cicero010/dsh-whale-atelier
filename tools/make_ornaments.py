"""生成皮肤装饰层的位图饰件（Pillow，超采样后降采样，边缘干净）。

用法：
    python tools/make_ornaments.py [输出目录]

产出（透明 PNG，运行时由 /api/dsh-whale-wallpaper/assets 提供）：
    orn-corner-<gold|silver>.png   角花（左上角朝向；其余三角由 CSS 镜像）
    orn-bow-<gold|silver>.png      蝴蝶结（输入框顶饰 / 侧栏底饰）
    orn-divider-<gold|silver>.png  标题分隔线中央饰件（可九宫拉伸用，左右留透明）
    mascot-<pose>.webp             角落立绘（从 dsh-whale-musume 立绘复制，透明底）
"""

from __future__ import annotations

import math
import os
import shutil
import sys

from PIL import Image, ImageDraw, ImageFilter

SS = 4  # 超采样倍数

def resolve_src_dir() -> str:
    """立绘素材目录（dsh-whale-musume 的 generated/）：

    解析顺序：环境变量 DSH_WHALE_MUSUME_ASSETS > ~/.dsh/plugins/dsh-whale-musume/assets/generated
    """
    env = os.environ.get("DSH_WHALE_MUSUME_ASSETS")
    if env:
        return os.path.expanduser(env)
    return os.path.join(os.path.expanduser("~"), ".dsh", "plugins", "dsh-whale-musume", "assets", "generated")


SRC_DIR = resolve_src_dir()
MASCOTS = {
    # 用户可选的常驻形象
    "notebook": "dsh-whale-state-work-review.webp",   # 抱笔记本的小人
    "pointer": "dsh-whale-state-work-meeting.webp",   # 拿教鞭的小人
    "curious": "dsh-whale-state-curious.webp",
    # 跟随 Agent 状态临时切换的形象
    "thinking": "dsh-whale-state-thinking.webp",
    "waiting": "dsh-whale-state-waiting.webp",
    "failure": "dsh-whale-state-failure.webp",
    "success": "dsh-whale-state-success.webp",
}

METALS = {
    "gold": {"light": (226, 196, 132), "mid": (196, 158, 88), "dark": (132, 100, 48)},
    "silver": {"light": (208, 220, 242), "mid": (150, 168, 204), "dark": (92, 108, 144)},
}

RIBBON = {
    "gold": {"light": (108, 146, 226), "mid": (58, 90, 170), "dark": (30, 48, 98), "trim": (214, 178, 110)},
    "silver": {"light": (128, 162, 232), "mid": (66, 100, 178), "dark": (34, 54, 106), "trim": (198, 210, 232)},
}


def canvas(size: tuple[int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (size[0] * SS, size[1] * SS), (0, 0, 0, 0))
    return image, ImageDraw.Draw(image)


def finish(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return image.resize(size, Image.LANCZOS)


def spiral(draw, cx, cy, r_start, r_end, turns, color, width):
    points = []
    steps = int(180 * turns)
    for i in range(steps + 1):
        t = i / steps
        angle = t * turns * 2 * math.pi
        radius = r_start + (r_end - r_start) * t
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    draw.line(points, fill=color, width=width, joint="curve")


def arc_band(draw, box, start, end, color, width):
    draw.arc(box, start=start, end=end, fill=color, width=width)


def leaf(draw, cx, cy, length, width, angle, fill, outline=None, ss=SS):
    """一片叶子：沿 angle 方向的水滴形（两段圆弧拼成）。"""
    dx, dy = math.cos(angle), math.sin(angle)
    nx, ny = -dy, dx
    tip = (cx + dx * length, cy + dy * length)
    left = []
    right = []
    for i in range(1, 11):
        t = i / 10
        bulge = math.sin(math.pi * t) * width
        px, py = cx + dx * length * t, cy + dy * length * t
        left.append((px + nx * bulge, py + ny * bulge))
        right.append((px - nx * bulge, py - ny * bulge))
    poly = [(cx, cy)] + left + [tip] + list(reversed(right))
    draw.polygon(poly, fill=fill)
    if outline is not None:
        draw.line(poly + [poly[0]], fill=outline, width=max(1, int(ss * 0.8)))


def flower(draw, cx, cy, radius, petal, core, ss=SS, petals: int = 5):
    """五瓣小花。"""
    for i in range(petals):
        angle = i * 2 * math.pi / petals - math.pi / 2
        px = cx + math.cos(angle) * radius * 0.62
        py = cy + math.sin(angle) * radius * 0.62
        draw.ellipse([px - radius * 0.46, py - radius * 0.46, px + radius * 0.46, py + radius * 0.46], fill=petal)
    draw.ellipse([cx - radius * 0.34, cy - radius * 0.34, cx + radius * 0.34, cy + radius * 0.34], fill=core)


def make_corner(metal: str, size: int = 200) -> Image.Image:
    """藤蔓角花：两条边线 + 卷草主藤 + 沿途叶片 + 角尖小花。"""
    m = METALS[metal]
    image, draw = canvas((size, size))
    s = size * SS
    pad = int(s * 0.09)

    # 两条边的金属描边（外粗内细）
    for offset, width, color in ((0.0, 0.028, m["mid"]), (0.052, 0.011, m["light"])):
        inset = pad + int(s * offset)
        draw.line([(inset, s - inset), (inset, inset), (s - inset, inset)], fill=color + (240,), width=max(2, int(s * width)))

    # 主藤：从角部向两条边各伸一条卷曲藤蔓
    spiral(draw, pad + s * 0.27, pad + s * 0.27, s * 0.02, s * 0.19, 1.30, m["light"] + (245,), max(3, int(s * 0.024)))
    spiral(draw, pad + s * 0.27, pad + s * 0.27, s * 0.02, s * 0.10, 0.95, m["dark"] + (205,), max(2, int(s * 0.014)))

    vine = (m["mid"][0], m["mid"][1], m["mid"][2], 210)
    for index in range(4):
        t = 0.26 + index * 0.17
        # 横向边上的叶片（朝内下方）
        leaf(draw, pad + s * t, pad + s * 0.045, s * 0.115, s * 0.028, math.radians(38 + index * 8), m["mid"] + (225,), m["dark"] + (150,))
        # 纵向边上的叶片（朝内右方）
        leaf(draw, pad + s * 0.045, pad + s * t, s * 0.115, s * 0.028, math.radians(52 - index * 8), m["mid"] + (225,), m["dark"] + (150,))
    # 藤蔓细线把叶片串起来
    for index in range(3):
        draw.line(
            [(pad + s * (0.24 + index * 0.17), pad + s * 0.085), (pad + s * (0.36 + index * 0.17), pad + s * 0.055)],
            fill=vine,
            width=max(1, int(s * 0.008)),
        )
        draw.line(
            [(pad + s * 0.085, pad + s * (0.24 + index * 0.17)), (pad + s * 0.055, pad + s * (0.36 + index * 0.17))],
            fill=vine,
            width=max(1, int(s * 0.008)),
        )

    flower(draw, pad + s * 0.075, pad + s * 0.075, s * 0.055, m["light"] + (250,), m["dark"] + (235,))
    return finish(image, (size, size))


def make_lace(metal: str, size: tuple[int, int] = (72, 26)) -> Image.Image:
    """可平铺的蕾丝花边条：连续底带 + 半圆扇贝 + 扇贝里的点。

    宽度就是一个平铺周期，左右边缘必须能接上，因此图案按周期 modulo 绘制。
    """
    m = METALS[metal]
    image, draw = canvas(size)
    w, h = size[0] * SS, size[1] * SS
    band = h * 0.30
    draw.rectangle([0, 0, w, band], fill=m["mid"] + (235,))
    draw.line([(0, band), (w, band)], fill=m["dark"] + (200,), width=max(1, int(h * 0.04)))

    period = w / 3  # 每张图三个扇贝，落在图内的完整周期
    r = period * 0.52
    for i in range(3):
        cx = period * (i + 0.5)
        draw.ellipse([cx - r, band - r * 0.2, cx + r, band + r * 1.5], fill=m["light"] + (235,))
        draw.ellipse([cx - r * 0.28, band + r * 0.35, cx + r * 0.28, band + r * 0.95], fill=m["dark"] + (215,))
    # 顶边一道细高光
    draw.line([(0, 0), (w, 0)], fill=m["light"] + (230,), width=max(1, int(h * 0.05)))
    return finish(image, size)


def make_corner_simple(metal: str, size: int = 200) -> Image.Image:
    """朴素角花（保留给不需要藤蔓的场合）。"""
    m = METALS[metal]
    image, draw = canvas((size, size))
    s = size * SS
    pad = int(s * 0.10)
    for offset, width, color in ((0.0, 0.030, m["mid"]), (0.055, 0.012, m["light"])):
        inset = pad + int(s * offset)
        draw.line([(inset, s - inset), (inset, inset), (s - inset, inset)], fill=color + (235,), width=max(2, int(s * width)))
    spiral(draw, pad + s * 0.30, pad + s * 0.30, s * 0.02, s * 0.20, 1.35, m["light"] + (245,), max(3, int(s * 0.026)))
    tip = pad + s * 0.055
    r = s * 0.055
    draw.polygon([(tip, tip - r), (tip + r, tip), (tip, tip + r), (tip - r, tip)], fill=m["light"] + (250,))
    return finish(image, (size, size))


def make_bow(metal: str, size: tuple[int, int] = (220, 120)) -> Image.Image:
    r = RIBBON[metal]
    image, draw = canvas(size)
    w, h = size[0] * SS, size[1] * SS
    cx, cy = w / 2, h * 0.40
    loop_w, loop_h = w * 0.30, h * 0.52

    def loop(sign: int):
        # 用参数曲线画一个饱满的环（外缘亮、内缘暗）
        pts = []
        for i in range(61):
            t = i / 60
            angle = math.pi * t
            x = cx + sign * (loop_w * 0.55 + loop_w * 0.45 * math.cos(angle)) * (1 - 0.06 * math.sin(angle))
            y = cy - loop_h * 0.5 * math.sin(angle)
            pts.append((x, y))
        inner = []
        for i in range(61):
            t = i / 60
            angle = math.pi * t
            x = cx + sign * (loop_w * 0.30 + loop_w * 0.42 * math.cos(angle)) * (1 - 0.06 * math.sin(angle))
            y = cy - loop_h * 0.42 * math.sin(angle)
            inner.append((x, y))
        draw.polygon(pts + list(reversed(inner)), fill=r["mid"] + (255,))
        draw.line(pts, fill=r["light"] + (255,), width=max(2, int(w * 0.012)))

    loop(-1)
    loop(1)
    # 飘带
    for sign in (-1, 1):
        tail = [
            (cx + sign * w * 0.03, cy + h * 0.05),
            (cx + sign * w * 0.20, cy + h * 0.52),
            (cx + sign * w * 0.10, cy + h * 0.60),
            (cx + sign * w * 0.02, cy + h * 0.22),
        ]
        draw.polygon(tail, fill=r["dark"] + (255,))
    # 中央结 + 金扣
    knot_w, knot_h = w * 0.13, h * 0.30
    draw.ellipse([cx - knot_w, cy - knot_h, cx + knot_w, cy + knot_h], fill=r["mid"] + (255,))
    draw.ellipse(
        [cx - knot_w * 0.55, cy - knot_h * 0.55, cx + knot_w * 0.55, cy + knot_h * 0.55],
        fill=r["trim"] + (255,),
    )
    return finish(image, size)


def make_divider(metal: str, size: tuple[int, int] = (240, 26)) -> Image.Image:
    m = METALS[metal]
    image, draw = canvas(size)
    w, h = size[0] * SS, size[1] * SS
    cy = h / 2
    # 中央菱形 + 两侧渐细横线 + 小卷
    draw.line([(w * 0.02, cy), (w * 0.38, cy)], fill=m["mid"] + (200,), width=max(2, int(h * 0.09)))
    draw.line([(w * 0.62, cy), (w * 0.98, cy)], fill=m["mid"] + (200,), width=max(2, int(h * 0.09)))
    r = h * 0.34
    draw.polygon([(w / 2, cy - r), (w / 2 + r, cy), (w / 2, cy + r), (w / 2 - r, cy)], fill=m["light"] + (250,))
    draw.polygon([(w / 2, cy - r * 0.45), (w / 2 + r * 0.45, cy), (w / 2, cy + r * 0.45), (w / 2 - r * 0.45, cy)], fill=m["dark"] + (230,))
    for sign in (-1, 1):
        spiral(
            draw,
            w / 2 + sign * w * 0.40,
            cy,
            h * 0.02,
            h * 0.22,
            1.1,
            m["light"] + (230,),
            max(2, int(h * 0.08)),
        )
    return finish(image, size)


def require_src_dir() -> None:
    if not os.path.isdir(SRC_DIR):
        raise SystemExit(
            f"找不到立绘素材目录: {SRC_DIR}\n"
            "请先安装 dsh-whale-musume（https://github.com/Sutera-Diffusus/dsh-whale-musume），"
            "或用环境变量 DSH_WHALE_MUSUME_ASSETS 指向它的 assets/generated 目录。"
        )


def main() -> None:
    require_src_dir()
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(here), "dsh-whale-wallpaper", "assets")
    os.makedirs(out_dir, exist_ok=True)

    for metal in ("gold", "silver"):
        for name, image in (
            (f"orn-corner-{metal}.png", make_corner(metal)),
            (f"orn-lace-{metal}.png", make_lace(metal)),
            (f"orn-bow-{metal}.png", make_bow(metal)),
            (f"orn-divider-{metal}.png", make_divider(metal)),
        ):
            path = os.path.join(out_dir, name)
            image.save(path, "PNG", optimize=True)
            print(f"{path}  {os.path.getsize(path) // 1024} KB")

    for name, source in MASCOTS.items():
        src = os.path.join(SRC_DIR, source)
        dst = os.path.join(out_dir, f"mascot-{name}.webp")
        shutil.copyfile(src, dst)
        print(f"{dst}  {os.path.getsize(dst) // 1024} KB")


if __name__ == "__main__":
    main()
