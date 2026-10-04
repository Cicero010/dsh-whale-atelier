# 皮肤包格式与安装

`dsh-whale-wallpaper` 的皮肤可以来自插件外部 —— 一个目录 + 一份 `skin.json` 就是一套皮肤。

## 两条安装路径

| 路径 | 需要重启宿主？ | 适用 |
| --- | --- | --- |
| **A. 索引安装**（推荐，示例包即用此法）`python tools/install_skin_pack.py <包目录>` | **不需要**，刷新页面即生效 | 把包复制进插件的 `assets/packs/<id>/` 并在 `assets/packs/index.json` 登记；走插件已有的 `/assets` 只读路由 |
| **B. 宿主发现** | 需要重启一次 | ① 投放目录 `$DSH_HOME/whale-wallpaper-skins/<id>/`；② 任意已安装插件在 `package.json` 里声明 `"dsh": { "whaleWallpaperSkins": "./skins" }` |

> 为什么 B 要重启：DSH 的 HMR 会重读 profile 与 patch 层，但**替换已有包的 JavaScript 模块版本需要重启进程**（Node 的 ESM 缓存按解析后的路径缓存）。B 的两条路由是宿主半边新增的代码，所以第一次启用要重启一次；之后投放/卸载皮肤包都不再需要重启。

客户端启动时**两个来源都读**并合并：先读插件的 `assets/packs/index.json`（路径 A，该目录由安装脚本生成、不随仓库发布），再读 `/api/dsh-whale-wallpaper/skins`（路径 B，取不到就跳过）。同名时宿主发现的优先，与内置皮肤同名时内置优先。

卸载：`python tools/install_skin_pack.py --uninstall <id>`（路径 A）或删掉投放目录（路径 B）。

> **路径 A 是复制安装**：改了包内容（换壁纸、改 `skin.json`）之后要**重新跑一次** `install_skin_pack.py <包目录>`，否则 GUI 用的还是上一次复制进去的副本。路径 B 是引用式发现，改完直接刷新即可。

## 目录结构

```
sakura/
├── skin.json                     # 必需
├── thumb.webp                    # 可选，选择器缩略图
└── assets/                       # 可选目录；资源也可以直接放在包根
    ├── ww-sakura-companion-dark.webp
    ├── ww-sakura-companion-light.webp
    ├── …（companion/debug/slack × dark/light，共 6 张）
    ├── orn-corner-gold.png       # 可选，自带饰件（金/银成套提供）
    ├── orn-lace-gold.png
    ├── orn-divider-gold.png
    ├── orn-bow-gold.png
    └── mascot-curious.webp       # 可选，自带常驻立绘
```

## skin.json

| 字段 | 必填 | 取值 / 说明 |
| --- | --- | --- |
| `id` | 是 | `^[a-z0-9][a-z0-9-]{0,31}$`；与内置皮肤同名时该包被忽略 |
| `name` | 是 | 选择器显示名，≤40 字 |
| `desc` | 否 | 一句话说明，≤120 字 |
| `scene` | 否 | 场景 id，决定壁纸文件名 `ww-<scene>-<pose>-<theme>.webp`；缺省等于 `id` |
| `metal` | 否 | `gold` / `silver` / `none`，缺省 `gold` |
| `decor` | 否 | 是否启用描边装饰；`metal: none` 时缺省关闭 |
| `bow` | 否 | 是否要蝴蝶结，缺省关闭 |
| `lace` | 否 | 是否要蕾丝花边，缺省跟随 `decor` |
| `mascot` | 否 | `notebook` / `pointer` / `curious`，缺省 `curious` |
| `mascotCorner` | 否 | `left` / `right` / `none`，缺省 `right` |
| `particles` | 否 | `petal` / `mote` / `bubble` / `snow` / `blossom` / `sakura`，缺省 `mote` |
| `version` | 否 | 清单版本，当前 `1` |

## 可以只带一部分资源

宿主按「文件确实存在」决定用包内文件还是回落到插件内置资源（`/skins` 会给出 `wallpapers` / `ornaments` / `mascots` / `thumb` 四份存在性列表，客户端据此拼 URL）：

- 只带部分 `ww-<scene>-*`：缺的立绘或明暗自动用内置同名文件，不会 404；
- 不带 `orn-*`：用插件内置饰件（`metal` 决定金/银）；
- 不带 `mascot-*`：用插件内置的七只立绘（含四只状态立绘）；
- 不带 `thumb.webp`：选择器显示「无缩略图」占位块。

## 坏包不会影响别人

`skin.json` 缺失 / JSON 损坏 / `id` 非法 / 缺 `name` 时，宿主跳过该包并把原因写进 `/api/dsh-whale-wallpaper/skins` 的 `problems`；其它皮肤照常工作。路径安全性：`/assets` 与 `/pack` 都做目录穿越检查（`../` 一律 404），`/pack` 的 `p` 参数必须匹配 id 规则。

## 示例包

[`skins/sakura`](../skins/sakura) —— 樱吹雪：6 张樱花夜庭壁纸（金色蕾丝 + 蝴蝶结 + 左下好奇 + 粉色樱花粒子），已用路径 A 装到本机。

它的枝干骨架坐标是**固化**在 `tools/make_wallpapers.py` 的 `branch_paths` 里的（由一份未随仓库发布的采样脚本递归生成后注入）；想改枝形就重跑那个脚本再把坐标贴回去。
