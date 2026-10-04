/**
 * 用真实 client.js 里的 normalizePref 跑一组导入用例（白名单/类型校验是否靠谱）。
 * 只做文本抽取 + 求值，不加载浏览器环境。
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { pluginFile } from "./_layout.mjs";

const source = readFileSync(pluginFile("lib", "client.js"), "utf8");
const start = source.indexOf("function normalizePref(key, value) {");
if (start < 0) throw new Error("找不到 normalizePref");
let depth = 0;
let end = start;
for (let i = source.indexOf("{", start); i < source.length; i += 1) {
  if (source[i] === "{") depth += 1;
  else if (source[i] === "}") {
    depth -= 1;
    if (depth === 0) {
      end = i + 1;
      break;
    }
  }
}
const body = source.slice(start, end);

const SKINS = { atelier: {}, garden: {}, abyss: {}, snow: {}, moonfest: {} };
const POSES = [["companion", ""], ["debug", ""], ["slack", ""]];
const THEMES = [["auto", ""], ["clock", ""], ["dark", ""], ["light", ""]];
const MASCOT_POSES = [["notebook", ""], ["pointer", ""], ["curious", ""]];

const normalizePref = new Function("SKINS", "POSES", "THEMES", "MASCOT_POSES", `${body}; return normalizePref;`)(
  SKINS,
  POSES,
  THEMES,
  MASCOT_POSES,
);

const cases = [
  ["skin", "snow", "snow"],
  ["skin", "evil", null],
  ["pose", "slack", "slack"],
  ["pose", "hack", null],
  ["theme", "clock", "clock"],
  ["theme", "neon", null],
  ["scope", "workspace", "workspace"],
  ["mascot", "none", "none"],
  ["mascot", "middle", null],
  ["mascotPose", "curious", "curious"],
  ["scrim", 0.5, "0.5"],
  ["scrim", "0.3", "0.3"],
  ["scrim", 9, null],
  ["scrim", "abc", null],
  ["decor", true, "1"],
  ["particles", false, "0"],
  ["particles", "1", "1"],
  ["mascotState", "2", null],
  ["unknownKey", "x", null],
];

let failed = 0;
for (const [key, input, expected] of cases) {
  const got = normalizePref(key, input);
  const ok = got === expected;
  if (!ok) failed += 1;
  console.log(`${ok ? "ok  " : "FAIL"}  ${key}(${JSON.stringify(input)}) -> ${JSON.stringify(got)}  期望 ${JSON.stringify(expected)}`);
}
console.log(failed === 0 ? "\n全部用例通过" : `\n${failed} 个用例失败`);
process.exit(failed === 0 ? 0 : 1);
