# 皮肤包：樱吹雪（sakura）

`dsh-whale-wallpaper` 的示例第三方皮肤包 —— 演示「放进目录就能用」的皮肤包格式。

## 装它

**方式一：直接投放（最简单）**

```powershell
# DSH_HOME 默认是 ~/.dsh
Copy-Item -Recurse packs/sakura "$env:USERPROFILE\.dsh\whale-wallpaper-skins\sakura"
```

刷新 GUI，设置 → 皮肤 列表末尾会出现带「皮肤包」标签的 **樱吹雪**。

**方式二：作为 DSH 插件安装**

把本目录放进一个普通插件包里，在它的 `package.json` 声明皮肤目录：

```json
{
  "name": "dsh-whale-skin-sakura",
  "dsh": { "whaleWallpaperSkins": "./skins" }
}
```

然后在 profile 里 `dsh plugin add <spec>`（或 GUI 插件页安装）。`whaleWallpaperSkins` 指向的目录下每个子目录就是一个皮肤包 —— 安装插件即多一套皮肤。

## 它包含什么

| 文件 | 说明 |
| --- | --- |
| `skin.json` | 皮肤清单（字段见下） |
| `assets/ww-sakura-<立绘>-<明暗>.webp` | 6 张 1920×1080 壁纸（3 立绘 × 深/浅） |
| `thumb.webp` | 设置面板选择器里的缩略图（可选） |

## skin.json 字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `id` | 是 | `^[a-z0-9][a-z0-9-]{0,31}$`；与内置皮肤同名时**内置优先**（包被忽略） |
| `name` | 是 | 面板里显示的名字（≤40 字） |
| `desc` | 否 | 一句话说明（≤120 字） |
| `scene` | 否 | 场景 id，决定壁纸文件名 `ww-<scene>-<pose>-<theme>.webp`；缺省等于 `id` |
| `metal` | 否 | `gold` / `silver` / `none`，缺省 `gold` |
| `decor` | 否 | 是否要描边装饰；`metal: none` 时缺省关闭 |
| `bow` / `lace` | 否 | 蝴蝶结 / 蕾丝；`lace` 缺省跟随 `decor`，`bow` 缺省关闭 |
| `mascot` | 否 | 常驻角落立绘：`notebook` / `pointer` / `curious`，缺省 `curious` |
| `mascotCorner` | 否 | `left` / `right` / `none`，缺省 `right` |
| `particles` | 否 | `petal` / `mote` / `bubble` / `snow` / `blossom` / `sakura`，缺省 `mote` |

## 可以只带一部分资源

插件按「文件确实存在」决定用包内文件还是回落到内置资源：

- 只带 `ww-<scene>-*` 的一部分，其余立绘/明暗自动用内置同名文件；
- 不带 `orn-*`，就用插件内置的饰件（`metal` 决定金/银）；
- 不带 `mascot-*`，就用插件内置的七只立绘（含四只状态立绘）；
- 不带 `thumb.webp`，选择器里显示内置缩略图占位。

## 坏包不会影响别人

`skin.json` 缺失 / JSON 损坏 / `id` 非法 / 缺 `name` 时，宿主会跳过该包并把原因记在 `/api/dsh-whale-wallpaper/skins` 的 `problems` 里，其它皮肤照常工作。
