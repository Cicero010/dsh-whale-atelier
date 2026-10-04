"""构建本地预览页：用真实 DSH 客户端样式（UI 令牌 + 外壳网格）渲染皮肤效果。

从 app.asar 导出的 ui-theme / ui-layout 客户端 bundle 中抽出 CSS 字面量，
配上最小化的会话 DOM 模拟，并复刻插件装饰层的几何对齐逻辑，
用于在 headless 浏览器里截图校准 wallpaper.css 与饰件。

用法：
    python tools/build_preview.py [--theme dark|light] [--pose companion|debug|slack]
                                 [--scope full|workspace] [--skin atelier|garden|abyss]
输出：
    _probe/replica-<theme>-<scope>-<skin>.html
"""

from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROBE = os.path.join(ROOT, "_probe")
PLUGIN = ROOT if os.path.isdir(os.path.join(ROOT, "lib")) else os.path.join(ROOT, "dsh-whale-atelier")

CSS_LITERAL = re.compile(r'([A-Za-z_$][\w$]*)\s*=\s*"((?:[^"\\]|\\.){200,})";')

# 只挑与外壳底色、令牌、滚动条相关的样式表；业务包样式不参与预览。
WANTED = {
    "ui-theme.client.js": ["base_css_default", "design_platform_css_default", "scrollbar_css_default"],
    "ui-layout.client.js": ["css"],
}

# 与 lib/client.js 的 SKINS 表保持一致（预览用，不参与运行时）
SKINS = {
    "atelier": {"scene": "interior", "metal": "gold", "decor": True, "bow": True, "mascot": "notebook", "corner": "left", "particles": "petal"},
    "garden": {"scene": "interior", "metal": "silver", "decor": True, "bow": False, "mascot": "pointer", "corner": "right", "particles": "mote"},
    "abyss": {"scene": "abyss", "metal": "silver", "decor": False, "bow": False, "mascot": "curious", "corner": "right", "particles": "bubble"},
    "snow": {"scene": "snow", "metal": "silver", "decor": True, "bow": False, "mascot": "pointer", "corner": "right", "particles": "snow"},
    "moonfest": {"scene": "moonfest", "metal": "gold", "decor": True, "bow": True, "mascot": "curious", "corner": "left", "particles": "blossom"},
    # 皮肤包示例：素材在 skins/sakura/assets/ 下，用 wallpaper_dir 指定
    "sakura": {"scene": "sakura", "metal": "gold", "decor": True, "bow": True, "mascot": "curious", "corner": "left", "particles": "sakura", "wallpaper_dir": "skins/sakura/assets"},
}

METAL_RGB = {"gold": "214, 178, 110", "silver": "150, 168, 204"}


def unescape_js(text: str) -> str:
    return text.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")


def collect_css() -> str:
    chunks = []
    for filename, names in WANTED.items():
        path = os.path.join(PROBE, filename)
        if not os.path.exists(path):
            sys.exit(f"缺少 {path}：先用 _asar_probe.py 导出对应客户端 bundle")
        text = open(path, encoding="utf-8", errors="replace").read()
        found = {}
        for match in CSS_LITERAL.finditer(text):
            if match.group(1) in names or (match.group(1) == "css" and "BynINW_frame" in match.group(2)):
                found[match.group(1)] = unescape_js(match.group(2))
        for name in names:
            if name not in found:
                sys.exit(f"{filename} 里找不到样式表 {name}")
            chunks.append(f"/* ==== {filename}:{name} ==== */\n{found[name]}")
    return "\n\n".join(chunks)


MOCK_CSS = """
/* ---- 预览用的会话模拟（只借主题令牌，不冒充产品样式） ---- */
html, body { height: 100%; margin: 0; }
:root { --dsw-specific-sidebar-fill: var(--dsw-alias-bg-layer-1); --dsh-windows-titlebar-height: 40px; }
.mock-titlebar { align-items: center; color: var(--dsw-alias-label-secondary); display: flex; font-size: 12px; height: var(--dsh-windows-titlebar-height); justify-content: space-between; padding: 0 6px 0 16px; position: absolute; inset: 0 0 auto; }
.mock-titlebar-buttons { display: flex; gap: 2px; }
.mock-titlebar-buttons span { align-items: center; border-radius: 6px; display: flex; height: 26px; justify-content: center; width: 40px; }
.mock-titlebar-buttons span[data-close] { color: var(--dsw-alias-state-error-primary, #d54941); }
.mock-sidebar { display: flex; flex-direction: column; gap: 10px; padding: 18px 14px; height: 100%; }
.mock-brand { color: var(--dsw-alias-label-primary); font-size: 15px; font-weight: 600; }
.mock-item { border-radius: var(--dsw-radius-md); color: var(--dsw-alias-label-secondary); font-size: 13px; padding: 8px 10px; }
.mock-item[data-active] { background: var(--dsw-alias-interactive-bg-hover); color: var(--dsw-alias-label-primary); }
.mock-header { align-items: center; color: var(--dsw-alias-label-primary); display: flex; font-size: 14px; height: 56px; padding: 0 28px; }
.mock-transcript { display: flex; flex-direction: column; gap: 18px; padding: 22px 40px; overflow: hidden; flex: 1; }
.mock-role { color: var(--dsw-alias-label-tertiary); font-size: 12px; margin-bottom: 6px; }
.mock-text { color: var(--dsw-alias-label-primary); font-size: 14px; line-height: 24px; }
.mock-user { display: flex; justify-content: flex-end; }
.mock-user > div { background: var(--dsw-alias-bg-layer-1); border: .5px solid var(--dsw-alias-border-l3); border-radius: var(--dsw-radius-lg); color: var(--dsw-alias-label-primary); font-size: 14px; line-height: 22px; max-width: 60%; padding: 10px 14px; }
.mock-tool { align-items: center; background: var(--dsw-alias-bg-layer-2); border: .5px solid var(--dsw-alias-border-l3); border-radius: var(--dsw-radius-md); color: var(--dsw-alias-label-secondary); display: inline-flex; font-size: 12px; gap: 8px; padding: 7px 12px; }
.mock-code { background: var(--dsw-alias-bg-layer-2); border: .5px solid var(--dsw-alias-border-l3); border-radius: var(--dsw-radius-md); color: var(--dsw-alias-label-primary); font-family: Consolas, monospace; font-size: 12.5px; line-height: 20px; padding: 12px 14px; white-space: pre; }
.mock-composer { background: var(--dsw-alias-bg-layer-1); border: .5px solid var(--dsw-alias-border-l3); border-radius: var(--dsw-radius-panel); color: var(--dsw-alias-label-tertiary); font-size: 14px; padding: 16px 18px; }
"""

GEOMETRY_JS = """
/* 复刻插件的装饰层几何对齐：只量真实元素，不改它们 */
function r(el) { return el.getBoundingClientRect(); }
const center = document.querySelector('[class*="_centerCol"]');
const sidebar = document.querySelector('[class*="_sidebarCol"]');
const header = center.querySelector('[class*="_header"]');
const seat = center.querySelector('[class*="_composerSeat"]');
if (header) {
  const rect = r(header);
  const node = document.querySelector('.ww-divider');
  node.style.left = rect.left + 'px';
  node.style.top = (rect.bottom - 1) + 'px';
  node.style.width = rect.width + 'px';
}
if (seat) {
  const rect = r(seat);
  const bow = document.querySelector('.ww-bow[data-anchor="composer"]');
  bow.style.left = (rect.left + rect.width / 2) + 'px';
  bow.style.top = (rect.top + 4) + 'px';
  const lace = document.querySelector('.ww-lace[data-anchor="composer"]');
  lace.style.left = (rect.left + 26) + 'px';
  lace.style.top = (rect.top - 2) + 'px';
  lace.style.width = Math.max(0, rect.width - 52) + 'px';
}
if (sidebar) {
  const rect = r(sidebar);
  const bow = document.querySelector('.ww-bow[data-anchor="sidebar"]');
  bow.style.left = (rect.left + rect.width / 2) + 'px';
  bow.style.top = (rect.bottom - 58) + 'px';
  const lace = document.querySelector('.ww-lace[data-anchor="sidebar"]');
  lace.style.left = (rect.left + 14) + 'px';
  lace.style.top = (rect.bottom - 92) + 'px';
  lace.style.width = Math.max(0, rect.width - 28) + 'px';
  document.querySelector('.ww-edge[data-edge="sidebar"]').style.left = rect.right + 'px';
}
const mascot = document.querySelector('.ww-mascot');
if (mascot && mascot.getAttribute('data-corner') === 'left' && center) {
  mascot.style.left = (r(center).left + 10) + 'px';
  mascot.style.right = 'auto';
}
/* 环境粒子：与插件同款确定性伪随机 */
const amb = document.querySelector('.ww-layer[data-ww-layer="ambient"]');
if (amb) {
  const kind = document.documentElement.getAttribute('data-ww-particles') || 'petal';
  let state = 20261004;
  const rnd = () => { state = (state * 1664525 + 1013904223) >>> 0; return state / 4294967296; };
  for (let i = 0; i < 20; i++) {
    const node = document.createElement('span');
    node.className = 'ww-particle';
    node.setAttribute('data-kind', kind);
    const size = 4 + rnd() * 11;
    node.style.left = (rnd() * 100).toFixed(2) + '%';
    node.style.width = size.toFixed(1) + 'px';
    node.style.height = size.toFixed(1) + 'px';
    node.style.animationDuration = (12 + rnd() * 16).toFixed(1) + 's';
    node.style.animationDelay = (-rnd() * 24).toFixed(1) + 's';
    node.style.setProperty('--ww-drift', ((rnd() * 2 - 1) * 84).toFixed(0) + 'px');
    amb.appendChild(node);
  }
}
"""


def file_url(*parts: str) -> str:
    return "file:///" + os.path.join(PLUGIN, "assets", *parts).replace("\\", "/")


def build(theme: str, pose: str, scope: str, skin_id: str, state: str = "idle") -> str:
    skin = SKINS[skin_id]
    css = collect_css()
    wallpaper = open(os.path.join(PLUGIN, "assets", "wallpaper.css"), encoding="utf-8").read()
    # 皮肤包素材在仓库根的 skins/ 下（不在插件 assets/ 里），因此按 ROOT 解析
    wallpaper_dir = skin.get("wallpaper_dir")
    if wallpaper_dir:
        image = "file:///" + os.path.join(ROOT, wallpaper_dir, f"ww-{skin['scene']}-{pose}-{theme}.webp").replace("\\", "/")
    else:
        image = file_url(f"ww-{skin['scene']}-{pose}-{theme}.webp")
    metal = skin["metal"]
    dark_attr = ' data-ds-dark-theme=""' if theme == "dark" else ""
    decor_attr = metal if skin["decor"] else "none"
    # 行内 style 属性用双引号包住，所以 url() 一律用单引号，避免提前闭合属性
    bow_css = f"url('{file_url(f'orn-bow-{metal}.png')}')" if skin["bow"] else "none"
    orn_css = f"url('{file_url(f'orn-corner-{metal}.png')}')" if skin["decor"] else "none"
    lace_css = f"url('{file_url(f'orn-lace-{metal}.png')}')" if skin["decor"] else "none"
    divider_css = f"url('{file_url(f'orn-divider-{metal}.png')}')" if skin["decor"] else "none"
    mascot_spot = "left" if skin["corner"] == "left" else "right"
    mascot_file = f"mascot-{state}.webp" if state != "idle" else f"mascot-{skin['mascot']}.webp"
    values = {
        "--ww-image": f"url('{image}')",
        "--ww-orn": orn_css,
        "--ww-lace": lace_css,
        "--ww-bow": bow_css,
        "--ww-divider": divider_css,
        "--ww-mascot": f"url('{file_url(mascot_file)}')",
        "--ww-metal": METAL_RGB[metal],
    }
    inline_style = " ".join(f"{key}: {value};" for key, value in values.items())

    return f"""<!doctype html>
<html lang="zh-CN" data-ww="on" data-ww-scope="{scope}" data-ww-decor="{decor_attr}" data-ww-mascot="{mascot_spot}" data-ww-mascot-state="{state}" data-ww-particles="{skin['particles']}" data-platform="win32" data-windows-titlebar style="{inline_style}">
<head>
<meta charset="utf-8">
<title>dsh-whale-atelier 预览（{skin_id} / {theme} / {pose} / {scope}）</title>
<style>{css}</style>
<style>{MOCK_CSS}</style>
<style>{wallpaper}</style>
</head>
<body{dark_attr}>
  <div class="BynINW_frame" style="grid-template-columns:260px minmax(0,1fr) 0px">
    <div class="mock-titlebar">
      <span>DeepSeek Harness</span>
      <span class="mock-titlebar-buttons"><span>—</span><span>▢</span><span data-close="1">✕</span></span>
    </div>
    <div class="BynINW_sidebarCol">
      <div class="mock-sidebar">
        <div class="mock-brand">DeepSeek Harness</div>
        <div class="mock-item" data-active="1">my-workspace</div>
        <div class="mock-item">default-workspace</div>
        <div class="mock-item">插件</div>
        <div class="mock-item">设置</div>
      </div>
    </div>
    <div class="BynINW_centerCol">
      <div class="Dc7zOa_root" data-phase="active" style="display:flex;flex-direction:column;height:100%;min-width:0;width:100%">
        <div class="Dc7zOa_header mock-header">设置工作区鲸鱼壁纸</div>
        <div class="mock-transcript">
          <div>
            <div class="mock-role">你</div>
            <div class="mock-user"><div>设置工作区鲸鱼壁纸</div></div>
          </div>
          <div>
            <div class="mock-role">DeepSeek</div>
            <div class="mock-text">皮肤包已经装好：壁纸铺满整个界面，金饰描边、蝴蝶结输入框与角落立绘都在自己的图层上，只读 DOM、不改产品样式。</div>
            <div style="height:12px"></div>
            <div class="mock-tool">✔ dsh-whale-atelier · 6 套皮肤（含皮肤包）· 30 张壁纸 · 7 只立绘 · 6 种粒子</div>
            <div style="height:12px"></div>
            <div class="mock-code">html[data-ww="on"] [class*="_centerCol"] {{ --dsw-alias-bg-base: transparent !important; }}
.ww-corner[data-corner="br"] {{ transform: scale(-1, -1); }}</div>
          </div>
        </div>
        <div class="Dc7zOa_composerSeat" style="padding:0 24px 22px">
          <div class="mock-composer">给 DeepSeek 发消息…</div>
        </div>
      </div>
    </div>
    <div class="BynINW_rightbarCol"></div>
  </div>
  <div class="ww-layer" data-ww-layer="decor" aria-hidden="true">
    <span class="ww-corner" data-corner="tl"></span>
    <span class="ww-corner" data-corner="tr"></span>
    <span class="ww-corner" data-corner="bl"></span>
    <span class="ww-corner" data-corner="br"></span>
    <span class="ww-edge" data-edge="top"></span>
    <span class="ww-edge" data-edge="sidebar"></span>
    <span class="ww-divider"></span>
    <span class="ww-bow" data-anchor="composer"></span>
    <span class="ww-bow" data-anchor="sidebar"></span>
  </div>
  <div class="ww-layer" data-ww-layer="mascot" aria-hidden="true">
    <span class="ww-mascot" data-corner="{mascot_spot}"></span>
  </div>
<script>
{GEOMETRY_JS}
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", default="dark", choices=["dark", "light"])
    parser.add_argument("--pose", default="companion", choices=["companion", "debug", "slack"])
    parser.add_argument("--scope", default="full", choices=["full", "workspace"])
    parser.add_argument("--skin", default="atelier", choices=list(SKINS))
    parser.add_argument("--state", default="idle", choices=["idle", "working", "waiting", "failure", "success"])
    args = parser.parse_args()
    out = os.path.join(PROBE, f"replica-{args.theme}-{args.scope}-{args.skin}.html")
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(build(args.theme, args.pose, args.scope, args.skin, args.state))
    print(out)


if __name__ == "__main__":
    main()
