/** 依次跑完 tests/ 下的四个测试文件，汇总退出码。 */
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TESTS = ["test_skin_pack.mjs", "test_pack_routes.mjs", "test_normalize_pref.mjs", "test_state.mjs"];

let failed = 0;
for (const name of TESTS) {
  process.stdout.write(`\n=== ${name} ===\n`);
  const result = spawnSync(process.execPath, [path.join(HERE, name)], { stdio: "inherit" });
  if (result.status !== 0) failed += 1;
}
process.stdout.write(failed === 0 ? "\n全部测试通过\n" : `\n${failed} 个测试文件失败\n`);
process.exit(failed === 0 ? 0 : 1);
