# dsh-whale-wallpaper

鲸鱼皮肤包 —— 把 `dsh-whale-musume` 的鲸鱼娘立绘铺成 **DeepSeek Harness Web GUI 的背景**，并叠一层金/银描边装饰与角落立绘。

- **五套内置皮肤 + 第三方皮肤包**（壁纸场景 + 描边金属 + 蕾丝/蝴蝶结 + 角落立绘 + 环境粒子，整套切换，即时生效，选择器带缩略图）；内置含两套**季节限定**：雪夜庭（落雪/霜花）、桂月夜庭（满月/灯笼/桂花）
- **皮肤包机制**：一个目录 + 一份 `skin.json` 就是一套皮肤；`tools/install_skin_pack.py` 装进插件索引**刷新即生效、不需要重启**，也支持投放目录与「安装插件即多一套皮肤」两种宿主发现路径（见 [docs/SKIN-PACKS.md](SKIN-PACKS.md)）。本机已装示例包 **樱吹雪**（樱花夜庭 + 粉色樱花粒子）
- **四种明暗策略**：跟随主题 / **按时段自动切昼夜壁纸**（07:00–18:30 用白天版）/ 固定深色 / 固定浅色
- **三个画面维度**：遮罩浓度、**暗角强度**、**景深模糊**（模糊时自动放大壁纸以吃掉边缘透明带）
- **全界面 / 仅工作区** 两种覆盖范围
- **装饰层**：藤蔓角花（四角）、顶边与侧栏描线、标题分隔饰件、蕾丝花边、输入框与侧栏蝴蝶结、面板描边；**角落立绘与蕾丝/蝴蝶结在菜单弹层之下**，不会挡住交互
- **角落立绘**：抱本子 / 拿教鞭 / 好奇（可选位置），带呼吸浮动；开启「跟随状态」后会在**等待审批 / 出错 / 生成中 / 刚完成**时临时换成对应形象，呼吸节奏也跟着变
- **环境粒子**：花瓣 / 萤火 / 气泡 / 雪花 / 桂花，随皮肤切换，可一键关掉；遵循 `prefers-reduced-motion`
- **设置导出/导入**：一段自包含 JSON，可复制到别的机器一键套用
- 零外部请求：壁纸与饰件都由插件自带的宿主静态路由提供；装饰层、粒子层、立绘层都是插件自建的 DOM，只读外壳几何，不写产品元素的属性

## 皮肤包

| id | 名称 | 壁纸场景 | 描边 | 蕾丝/蝴蝶结 | 角落立绘 | 环境粒子 |
| --- | --- | --- | --- | --- | --- | --- |
| `atelier` | 女仆工坊 | 夜庭室内（吊灯/高窗/窗帘/挂画） | 金色 | 蕾丝 + 蝴蝶结 | 左下 · 抱本子 | 花瓣飘落 |
| `garden` | 夜庭银饰 | 夜庭室内 | 银蓝 | 蕾丝，无蝴蝶结 | 右下 · 拿教鞭 | 萤火漂浮 |
| `abyss` | 深海 | 水下渐变 + 气泡 + 水面波纹 | 无 | 无 | 右下 · 好奇 | 气泡上浮 |
| `snow` | 雪夜庭（季节） | 夜庭室内 · 落雪 + 窗台积雪 + 霜花 | 银蓝 | 蕾丝 | 右下 · 拿教鞭 | 雪花飘落 |
| `moonfest` | 桂月夜庭（季节） | 夜庭室内 · 满月 + 纸灯笼 + 桂花 | 金色 | 蕾丝 + 蝴蝶结 | 左下 · 好奇 | 桂花飘落 |
| `sakura` | 樱吹雪（**皮肤包**） | 夜庭室内 · 樱花枝 + 落英 | 金色 | 蕾丝 + 蝴蝶结 | 左下 · 好奇 | 粉色樱花 |

> `sakura` 不在插件代码里，而是 `packs/sakura/` 这个皮肤包 —— 用来演示第三方皮肤包格式（详见 [docs/SKIN-PACKS.md](SKIN-PACKS.md)）。

## 组成

| 文件 | 作用 |
| --- | --- |
| `lib/index.js` | 宿主半边：注册 `/api/dsh-whale-wallpaper/assets`（包内资源）、`/skins`（皮肤包清单）、`/pack`（皮肤包资源）三条只读路由，并扫描三处皮肤包来源。 |
| `lib/client.js` | 浏览器半边：注入 `wallpaper.css`；把皮肤/立绘/明暗/范围/遮罩投影成 `<html>` 上的 `data-ww*` 与自定义属性；建装饰层与立绘层并做几何对齐；注册设置面板「皮肤」栏目。 |
| `assets/wallpaper.css` | 视觉规则：壁纸层 + 让位层 + 装饰层样式。 |
| `assets/ww-<场景>-<立绘>-<dark\|light>.webp` | 12 张 1920×1080 壁纸图（2 场景 × 3 立绘 × 2 明暗）。 |
| `assets/orn-corner-<metal>.webp` | 藤蔓角花（同一张左上角朝向，其余三角由 CSS 镜像）。 |
| `assets/orn-lace-<metal>.webp` | 可平铺的蕾丝花边（输入框顶沿 / 侧栏底沿，`repeat-x`）。 |
| `assets/orn-bow-<metal>.webp` | 蝴蝶结（输入框顶饰 / 侧栏底饰）。 |
| `assets/orn-divider-<metal>.webp` | 标题分隔线中央饰件。 |
| `assets/thumb-<skin>.webp` | 皮肤选择器的缩略图（壁纸 + 角落立绘 + 金属描边）。 |
| `assets/mascot-<pose>.webp` | 角落立绘（取自 whale-musume 立绘，透明底）。 |
| `screenshots/*.webp` | 效果预览（深/浅 × 皮肤，用真实 DSH 令牌与外壳样式渲染）。 |

## 原理：三层，全部挂在 `html[data-ww="on"]` 下

1. **壁纸层** `html[data-ww="on"]::before`：根画布上 `position: fixed; z-index: -1` 的一层「遮罩渐变 + 壁纸图」，不吃指针事件。
   注意 `body` 若带背景，会被传播成**画布背景**（画在 `::before` 之下），这正是壁纸不会被 body 盖住的原因。
2. **让位层**：`[class*="_frame"]`、`[class*="_centerCol"]` 原本用 `--dsw-alias-bg-base` 铺不透明底色 —— 让它们透明，并在中栏作用域内把该令牌改成 `transparent`，工作区里所有读它的表面（会话 root、编辑器、附件卡…）一起透出去。
   「全界面」模式额外让 `[class*="_sidebarCol"]`/`[class*="_rightbarCol"]` 透明，并把主题定义在 **`body`** 上的 `--dsw-specific-sidebar-fill` 换成遮罩色半透明版（写在 `html` 上会被 body 自己的声明盖掉）；Windows 标题栏条 `.frame::before` 也读这个令牌，于是标题栏一起透出壁纸。
   输入区吸底 (`_composerSeat`)、压缩提示 (`_compactionButton`)、展开行 (`[data-disclosure-row]`) 会压住滚动内容，单独补一层遮罩色。
3. **装饰层** `[data-ww-decor="gold|silver"]` + `.ww-*`：面板描边与分隔线是纯 CSS 覆盖；角花、描线、蕾丝、蝴蝶结、标题分隔、角落立绘是插件自建的固定图层。
   分三个 z 序：边框角花 `z 40`（只在窗口边缘）→ 蝴蝶结/蕾丝/分隔 `z 9`（内容之上、菜单弹层之下）→ 环境粒子 `z -1`（壁纸之上、正文之下，永不压字）。
   几何靠**量真实外壳元素**对齐（只读 DOM，不写产品元素的属性）：
   - 标题分隔 → 中栏里最宽的 `_header` 的底边；
   - 输入框蕾丝与蝴蝶结 → `_composerSeat` 顶边；侧栏蕾丝与蝴蝶结 → `_sidebarCol` 底部；
   - 侧栏描线 → `_sidebarCol` 右边缘；左下角立绘 → 中栏左边缘（避免压住侧栏）。
   布局变化由 `resize` + 1.5k 低频同步兜住。
4. **环境粒子层** `[data-ww-layer="ambient"]`：20 个粒子按皮肤切换 `data-kind`（花瓣/萤火/气泡），位置与速度用固定种子的 LCG 生成 —— 每次打开都一样，不会刷新乱跳。`prefers-reduced-motion: reduce` 时整体停播。

关掉壁纸（设置面板，或从 profile 停用插件）时 `data-ww="off"`，所有选择器失配，界面立刻回到出厂外观。

## 设置面板

设置 → **皮肤**：启用、皮肤包（带缩略图）、壁纸立绘（陪伴/查 bug/摸鱼）、覆盖范围（全界面/仅工作区）、明暗（跟随主题/按时段/深/浅）、描边装饰开关、角落立绘位置与形象、环境粒子开关、立绘跟随状态开关、遮罩浓度（0–92%）、导出/导入设置、恢复默认。偏好存在 `localStorage: whale-wallpaper:*`，即时生效、不需要重启。

### 五项进阶行为

- **按时段切昼夜**：`theme = clock` 时，07:00–18:30 用白天版壁纸、其余时段用夜景版；每 1.5k 轮询一次本地时间，跨过时间点会自动换图（遮罩仍跟随 GUI 主题，所以暗色 UI 下白天图也是压得住的）。
- **立绘跟随 Agent 状态**：只用三处稳定的 DOM 信号判断 —— 审批卡片的拒绝按钮（→ 等待审批）、轮次错误行（→ 出错）、「运行中」行（→ 生成中）；刚跑完会闪 4 秒成功形象。任何一处改名只会让状态退回常驻形象，不会报错。
- **导出 / 导入**：导出把 13 个偏好键写成一段 JSON（同时尝试写剪贴板），导入逐键白名单校验后落盘并立即应用；非法值会被跳过并在状态行里报数。
- **画面三维度**：遮罩浓度 / 暗角强度 / 景深模糊。模糊通过 `filter: blur()` 实现，同时把壁纸层按 `1 + ax/160` 放大，避免模糊把边缘透出底色。
- **皮肤包**：安装方式与格式见 [docs/SKIN-PACKS.md](SKIN-PACKS.md)。

## 安装到某个 profile

把插件目录链进 profile（路径以 Windows 为例）：

- 插件目录：`%USERPROFILE%\.dsh\plugins\dsh-whale-wallpaper`
- profile：`%USERPROFILE%\.dsh\profiles\<profile>`
  - `dependencies["dsh-whale-wallpaper"] = "link:C:/Users/<you>/.dsh/plugins/dsh-whale-wallpaper"`
  - `dsh.profile.bundles` 末尾含 `"dsh-whale-wallpaper"`
  - `node_modules\dsh-whale-wallpaper`：pnpm 建的 junction

换机器或换 profile：

```bash
ca -r dsh-whale-wallpaper ~/.dsh/plugins/dsh-whale-wallpaper
cd ~/.dsh/profiles/<profile>
"<runtime>/dependencies/node/bin/node.exe" "<runtime>/dependencies/pnpm/bin/pnpm.mjs" \
    add "link:C:/Users/<you>/.dsh/plugins/dsh-whale-wallpaper"
# 再把 "dsh-whale-wallpaper" 追加到 package.json 的 dsh.profile.bundles 末尾
```

profile 里 `dsh-hmr` 默认启用（`@deepseek-ai/dsh-base` 的 patch：`disabled: !!jk "!ctx.get('profileContext')"`），所以追加 bundles 后宿主半边**就地挂载**，不需要重启；浏览器半边在页面刷新时重新组合启动图。也可以直接在 GUI 的**插件**页启停这个组合包。

## 生成与预览工具（工作区 `tools/`）

| 脚本 | 用途 |
| --- | --- |
| `make_wallpapers.py --set abyss\|interior\|snow\|moonfest\|all` | 合成 24 张壁纸底图（水下 / 夜庭室内 / 雪夜庭 / 桂月夜庭，含吊灯、高窗、窗帘、挂画、雪与灯笼，左侧自动压暗保证正文可读）。 |
| `make_ornaments.py` | 生成金色/银蓝藤蔓角花、蕾丝花边、蝴蝶结、分隔饰件，并复制角落立绘。 |
| `make_thumbs.py [--pack <包目录>]` | 生成设置面板皮肤选择器用的缩略图；`--pack` 直接给一个皮肤包生成 `thumb.webp`。 |
| `install_skin_pack.py <包目录> \| --uninstall <id> \| --list` | 把皮肤包装进/移出插件索引（`assets/packs/`），刷新即生效；**包内容改动后要重跑一次**。 |
| `scan_classes.py [关键词]` | 从客户端 bundle 里抽 CSS-module 类名，用于确定装饰挂点。 |
| `build_preview.py --pack`（见 SKIN-PACKS） | 预览器已支持皮肤包：`--skin sakura` 直接渲染 `packs/sakura`。 |
| `build_preview.py --theme --skin --pose --scope` | 用 app.asar 里导出的真实 UI 令牌与外壳样式搭预览页（复刻装饰层几何对齐）。 |
| `diag_preview.py --theme` | 诊断页：把 `html::before` 的计算样式、各栏背景、图片加载结果写进 DOM，供 `msedge --headless --dump-dom` 读取。 |
| `scan_classes.py [关键词]` | 从客户端 bundle 里抽 CSS-module 类名，用于确定装饰挂点。 |

预览需要先导出客户端 bundle（`_probe/*.client.js`），用`tools/asar_probe.py`：

```bash
python tools/asar_probe.py --asar "<DSH 安装目录>/resources/app.asar" "node_modules/@deepseek-ai/dsh-client-ui-theme/lib/client.js" save "_probe/ui-theme.client.js"
python tools/asar_probe.py --asar "<DSH 安装目录>/resources/app.asar" "node_modules/@deepseek-ai/dsh-client-ui-layout/lib/client.js" save "_probe/ui-layout.client.js"
```

截图（Windows 自带 Edge）：

```bash
msedge --headless=new --disable-gpu --hide-scrollbars --window-size=1600,1000 \
  --screenshot=_probe/preview.webp "file:///.../_probe/replica-dark-full-atelier.html"
```

## 已知限制

- 依赖 DSH 客户端的 CSS-module 类名后缀（`_frame`、`_centerCol`、`_sidebarCol`、`_rightbarCol`、`_composerSeat`、`_header`、`_running`、`_turnErrorRow`、`_reject`）与 `--dsw-alias-bg-base`、`--dsw-specific-sidebar-fill` 令牌。DSH 改名后对应效果会**静默失效**（界面回到出厂外观，不报错），同步改 `wallpaper.css` / `client.js` 即可。
- 「立绘跟随状态」是启发式判断：审批、报错、生成中三种状态各自依赖一个类名后缀；识别不到时只是显示常驻形象，不会误报成出错。
- **皮肤包的宿主发现（投放目录 / 插件声明）需要重启一次宿主**（新路由属于宿主半边代码，Node 的 ESM 缓存要重启才换）；用 `install_skin_pack.py` 的索引安装路径不需要重启。
- 景深模糊是整层模糊（不是中心清晰、边缘虚化）；`prefers-reduced-motion` 下粒子与立绘动画停播，但模糊仍生效。
- 装饰层只读外壳几何，不做像素级像素锁定；侧栏折叠、右栏开关等布局变化会在一次低频同步内跟上（≤1.5k）。
- 亮色主题的壁纸为「白天室内」版本，遮罩默认更淡（0.24），深色主题默认 0.64。
- 立绘与饰件版权沿用 `dsh-whale-musume` 包内资源，仅本地使用。
