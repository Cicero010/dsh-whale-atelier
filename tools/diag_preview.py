"""诊断页：把亮/暗主题下各关键元素的实际背景与壁纸变量的计算值写进 DOM，供 --dump-dom 读取。

用法：
    python tools/diag_preview.py --theme light
    msedge --headless=new --dump-dom file:///.../_probe/diag-<theme>.html
"""

from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import build_preview  # noqa: E402  复用预览构建

DIAG_JS = """
const out = [];
function bg(sel, label) {
  const el = document.querySelector(sel);
  if (!el) { out.push(label + ': (未找到)'); return; }
  const cs = getComputedStyle(el);
  out.push(label + ': bg=' + cs.backgroundColor + ' img=' + (cs.backgroundImage || 'none').slice(0, 90) + ' pos=' + cs.position + ' z=' + cs.zIndex);
}
const root = getComputedStyle(document.documentElement);
out.push('meta: styleSheets=' + document.styleSheets.length + ' headStyles=' + document.querySelectorAll('style').length);
let found = 0;
for (const sheet of document.styleSheets) {
  let rules = null;
  try { rules = sheet.cssRules; } catch (e) { out.push('sheet 不可读: ' + e.message); continue; }
  for (const rule of rules) {
    const text = rule.cssText || '';
    if (text.includes('ww-scrim') || text.includes('ww-image')) {
      found += 1;
      if (found <= 4) out.push('rule[' + rule.selectorText + ']: ' + text.slice(0, 180));
    }
  }
}
out.push('匹配 ww-* 的规则数: ' + found);
out.push('html --ww-image: ' + root.getPropertyValue('--ww-image').trim().slice(0, 120));
out.push('html --ww-scrim: ' + root.getPropertyValue('--ww-scrim').trim() + '  color: ' + root.getPropertyValue('--ww-scrim-color').trim());
out.push('html::before bg: ' + (getComputedStyle(document.documentElement, '::before').backgroundImage || 'none').slice(0, 160));
bg('html', 'html');
bg('body', 'body');
bg('[class*="_frame"]', 'frame');
bg('[class*="_centerCol"]', 'centerCol');
bg('[class*="_sidebarCol"]', 'sidebarCol');
const probe = new Image();
probe.onload = () => { out.push('image load: ok ' + probe.naturalWidth + 'x' + probe.naturalHeight); done(); };
probe.onerror = () => { out.push('image load: FAILED'); done(); };
const url = root.getPropertyValue('--ww-image').trim().replace(/^url\\(['"]?/, '').replace(/['"]?\\)$/, '');
probe.src = url || 'about:blank';
function done() {
  const pre = document.createElement('pre');
  pre.id = 'diag';
  pre.textContent = out.join('\\n');
  document.body.appendChild(pre);
}
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", default="light", choices=["dark", "light"])
    parser.add_argument("--skin", default="atelier")
    parser.add_argument("--pose", default="companion")
    parser.add_argument("--scope", default="full")
    args = parser.parse_args()

    html = build_preview.build(args.theme, args.pose, args.scope, args.skin)
    html = html.replace("</body>", f"<script>{DIAG_JS}</script></body>")
    out = os.path.join(build_preview.PROBE, f"diag-{args.theme}-{args.skin}.html")
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(html)
    print(out)


if __name__ == "__main__":
    main()
