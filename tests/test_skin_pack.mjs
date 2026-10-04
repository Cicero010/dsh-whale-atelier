/**
 * readSkinPack 的行为测试：合法包、缺字段、坏 JSON、非法 id、枚举回落、自带资源探测。
 * 直接 import 宿主半边的真实实现（该模块 import 时无副作用）。
 */
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { PLUGIN_DIR, TMP_ROOT } from "./_layout.mjs";

const { readSkinPack } = await import(pathToFileURL(path.join(PLUGIN_DIR, "lib", "index.js")).href);

const ROOT = path.join(TMP_ROOT, "pack-parse");

function makePack(name, manifest, files = []) {
  const dir = path.join(ROOT, name);
  mkdirSync(dir, { recursive: true });
  if (manifest !== null) {
    writeFileSync(path.join(dir, "skin.json"), typeof manifest === "string" ? manifest : JSON.stringify(manifest, null, 2));
  }
  for (const file of files) {
    const full = path.join(dir, file);
    mkdirSync(path.dirname(full), { recursive: true });
    writeFileSync(full, "x");
  }
  return dir;
}

rmSync(ROOT, { recursive: true, force: true });

const cases = [];

// 1. 最小合法包：其余字段走默认
cases.push(["最小包走默认", makePack("minimal", { id: "sakura", name: "樱吹雪" }), (pack) =>
  pack.id === "sakura" && pack.name === "樱吹雪" && pack.scene === "sakura" && pack.metal === "gold" &&
  pack.decor === true && pack.lace === true && pack.bow === false && pack.mascot === "curious" &&
  pack.mascotCorner === "right" && pack.particles === "mote" && pack.wallpapers.length === 0 && pack.ornaments.length === 0 && pack.mascots.length === 0 && pack.thumb === false]);

// 2. 完整包 + 自带资源探测
cases.push(["完整包与自带资源", makePack("full", {
  id: "shrine", name: "神社夜", desc: "示例", scene: "interior", metal: "silver", decor: true, bow: true,
  lace: false, mascot: "notebook", mascotCorner: "left", particles: "blossom",
}, ["ww-interior-companion-dark.webp", "orn-corner-silver.png", "mascot-notebook.webp", "thumb.webp"]), (pack) =>
  pack.metal === "silver" && pack.bow === true && pack.lace === false && pack.mascotCorner === "left" &&
  pack.particles === "blossom" && pack.wallpapers.join(",") === "companion-dark" &&
  pack.ornaments.join(",") === "silver" && pack.mascots.join(",") === "notebook" && pack.thumb === true]);

// 3. 枚举非法值全部回落
cases.push(["非法枚举回落", makePack("badEnums", {
  id: "weird", name: "奇怪", metal: "neon", particles: "lava", mascot: "dragon", mascotCorner: "top", scene: "Bad Scene",
}), (pack) => pack.problem === "invalid-scene"]);
cases.push(["非法枚举回落(合法 scene)", makePack("badEnums2", {
  id: "weird", name: "奇怪", metal: "neon", particles: "lava", mascot: "dragon", mascotCorner: "top",
}), (pack) => pack.metal === "gold" && pack.particles === "mote" && pack.mascot === "curious" && pack.mascotCorner === "right"]);

// 4. 各种坏包
cases.push(["缺 skin.json", makePack("noManifest", null), (pack) => pack.problem === "missing-skin-json"]);
cases.push(["坏 JSON", makePack("brokenJson", "{ not json"), (pack) => pack.problem === "invalid-skin-json"]);
cases.push(["非法 id", makePack("badId", { id: "../evil", name: "越界" }), (pack) => pack.problem === "invalid-id"]);
cases.push(["缺 name", makePack("noName", { id: "noname" }), (pack) => pack.problem === "missing-name"]);
cases.push(["超长 name 被截断", makePack("longName", { id: "longname", name: "鲸".repeat(80) }), (pack) => pack.name.length === 40]);
cases.push(["decor=false 时 lace 默认跟随", makePack("nodecor", { id: "plain", name: "素色", metal: "none" }), (pack) =>
  pack.decor === false && pack.lace === false && pack.metal === "none"]);

let failed = 0;
for (const [name, dir, check] of cases) {
  const result = readSkinPack(dir);
  let ok = false;
  let detail = "";
  if (result.problem !== undefined) {
    ok = check(result);
    detail = `problem=${result.problem}`;
  } else {
    ok = check(result.pack);
    detail = `id=${result.pack.id}`;
  }
  if (!ok) failed += 1;
  console.log(`${ok ? "ok  " : "FAIL"}  ${name}  ${detail}`);
}
rmSync(ROOT, { recursive: true, force: true });
console.log(failed === 0 ? "\n皮肤包解析用例全部通过" : `\n${failed} 个用例失败`);
process.exit(failed === 0 ? 0 : 1);
