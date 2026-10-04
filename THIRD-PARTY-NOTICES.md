# 第三方素材与代码声明

本仓库包含来自第三方项目的素材，按各自许可使用。

## 1. dsh-whale-musume（鲸鱼娘桌宠）

- 来源：<https://github.com/Sutera-Diffusus/dsh-whale-musume>
- 许可：MIT（`package.json` 声明 `"license": "MIT"`，仓库根有 LICENSE）
- 版权：Copyright (c) 2026 Sutera-Diffusus

**被本仓库使用的部分**

| 本仓库文件 | 来源 | 处理方式 |
| --- | --- | --- |
| `assets/mascot-*.webp`（7 只） | 该包 `assets/generated/dsh-whale-state-*.webp` | 原样复制 |
| `assets/ww-*.webp`（24 张）与 `skins/sakura/assets/ww-*.webp`（6 张） | 该包同一批立绘 | 作为角色素材合成到程序化生成的场景中（Pillow 脚本见 `tools/make_wallpapers.py`） |
| `assets/thumb-*.webp`、`skins/sakura/thumb.webp` | 上述产物 | 缩略图 |

立绘版权归原作者所有；本仓库仅做本地渲染用途的合成与分发，未修改角色形象本身。若原作者有不同意见，删除上述文件即可让插件仍可运行（会回落到纯程序化壁纸）。

**上游许可原文**

```
MIT License

Copyright (c) 2026 Sutera-Diffusus

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 2. DeepSeek Harness（宿主运行时）

本插件的宿主半边与浏览器半边依赖 DSH 的公开契约（`dsh.bundle` / `dsh.client`、`ctx.inject`、`webServer.register`、客户端模块系统的 `__ModuleLoader__.load`、`ctx.theme` 令牌等），并读取其 CSS-module 类名后缀与 `--dsw-*` 令牌来挂载样式。

本仓库**不包含**任何 DSH 源码；DSH 自身许可见其发行包 `LICENSES.chromium.html` 与 `LICENSE.electron.txt` 及上游说明。

## 3. 字体与图标

无。本插件的饰件（角花、蕾丝、蝴蝶结、分隔线）与壁纸场景均由 `tools/` 下的 Pillow 脚本程序化生成，未使用第三方字体或图标集。
