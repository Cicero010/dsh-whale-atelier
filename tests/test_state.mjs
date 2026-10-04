/**
 * 用真实 client.js 里的 detectAgentState 跑状态判定用例。
 * 桩 DOM：给定 class 列表与可见性，断言判定结果。
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { pluginFile } from "./_layout.mjs";

const src = readFileSync(pluginFile("lib", "client.js"), "utf8");
const start = src.indexOf("const STATE_SIGNALS = [");
const end = src.indexOf("function applyMascotImage()");
const block = src.slice(start, end);

const makeDetect = () => new Function("document", "Date", "Set", `${block}\nreturn detectAgentState;`);

function bodyOf(nodes) {
  return {
    querySelectorAll(selector) {
      const suffixes = [...selector.matchAll(/\[class\*="([^"]+)"\]/g)].map((match) => match[1]);
      return nodes
        .filter((node) => node.classes.some((cls) => suffixes.some((suffix) => cls.includes(suffix))))
        .map((node) => ({
          classList: node.classes,
          getBoundingClientRect: () => ({ width: node.visible ? 10 : 0, height: node.visible ? 10 : 0 }),
        }));
    },
  };
}

const cases = [
  ["空闲", [{ classes: ["xD_abc"], visible: true }], "idle"],
  ["生成中", [{ classes: ["xz4KEq_running"], visible: true }], "working"],
  ["等审批优先于生成中", [{ classes: ["xz4KEq_running"], visible: true }, { classes: ["j_8BDW_reject"], visible: true }], "waiting"],
  ["报错", [{ classes: ["cJsG2q_turnErrorRow"], visible: true }], "failure"],
  ["报错(错误码节点)", [{ classes: ["cJsG2q_turnErrorCode"], visible: true }], "failure"],
  ["生成中 + 旧错误行", [{ classes: ["cJsG2q_turnErrorRow"], visible: true }, { classes: ["xz4KEq_running"], visible: true }], "working"],
  ["隐藏的运行行不算", [{ classes: ["xz4KEq_running"], visible: false }], "idle"],
  ["无关类名不误判", [{ classes: ["foo_run"], visible: true }], "idle"],
];

let failed = 0;
for (const [name, nodes, expected] of cases) {
  const detect = makeDetect();
  const got = detect({ body: bodyOf(nodes) }, Date, Set)();
  const ok = got === expected;
  if (!ok) failed += 1;
  console.log(`${ok ? "ok  " : "FAIL"}  ${name}: ${got}（期望 ${expected}）`);
}
console.log(failed === 0 ? "\n状态判定用例全部通过" : `\n${failed} 个用例失败`);
process.exit(failed === 0 ? 0 : 1);
