/**
 * 测试用的路径解析：同一份测试要能在两种布局下跑
 *   1) 发布仓库：仓库根就是插件包（tests/ 与 lib/ 同级）
 *   2) 开发工作区：插件在 tests/ 的兄弟目录 dsh-whale-wallpaper/
 */
import { existsSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));

const CANDIDATES = [path.join(HERE, ".."), path.join(HERE, "..", "dsh-whale-wallpaper")];

export const PLUGIN_DIR = CANDIDATES.find((dir) => existsSync(path.join(dir, "lib", "index.js")));

if (PLUGIN_DIR === undefined) {
  throw new Error("找不到插件目录（lib/index.js）：请在仓库根或工作区根运行测试");
}

/** 临时目录固定放系统 temp 下，测试自己清理。 */
export const TMP_ROOT = path.join(os.tmpdir(), "dsh-whale-wallpaper-tests");

export const pluginFile = (...parts) => path.join(PLUGIN_DIR, ...parts);
