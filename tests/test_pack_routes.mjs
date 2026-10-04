/**
 * 皮肤包路由的集成测试：用桩 ctx 起一个真实的 http server，跑真实的三条路由。
 * 覆盖：/assets 正常与越界、/skins 清单合并、/pack 取包内资源（双根解析）、未知包 404、目录穿越与非法 id 被拒。
 *
 * 注意：桩包一律用带 -fixture 后缀的 id，避免和仓库自带皮肤包（skins/*）撞名——
 * 宿主对同名包的处理是「自带 > 投放 > 插件声明」，撞名会让断言依赖仓库里装了什么。
 */
import { createServer } from "node:http";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { PLUGIN_DIR, TMP_ROOT } from "./_layout.mjs";

const { apply } = await import(pathToFileURL(path.join(PLUGIN_DIR, "lib", "index.js")).href);

const ROOT = path.join(TMP_ROOT, "pack-routes");
const SKINS_ROOT = path.join(ROOT, "whale-wallpaper-skins");
const PROFILE = path.join(ROOT, "profiles", "desktop");

// —— 造一个投放目录皮肤包 + 一个「声明了 whaleWallpaperSkins 的已安装插件」+ 一个坏包 ——
rmSync(ROOT, { recursive: true, force: true });
const dropIn = path.join(SKINS_ROOT, "dropin-fixture");
mkdirSync(path.join(dropIn, "assets"), { recursive: true });
writeFileSync(
  path.join(dropIn, "skin.json"),
  JSON.stringify({
    id: "dropin-fixture",
    name: "投放包",
    scene: "dropin",
    metal: "gold",
    mascot: "curious",
    mascotCorner: "left",
    particles: "sakura",
  }),
);
writeFileSync(path.join(dropIn, "assets", "ww-dropin-companion-dark.webp"), "DROPIN-DARK");
writeFileSync(path.join(dropIn, "thumb.webp"), "DROPIN-THUMB");

const pluginPack = path.join(PROFILE, "node_modules", "dsh-whale-skin-demo", "skins", "plugin-fixture");
mkdirSync(pluginPack, { recursive: true });
writeFileSync(
  path.join(PROFILE, "node_modules", "dsh-whale-skin-demo", "package.json"),
  JSON.stringify({ name: "dsh-whale-skin-demo", dsh: { whaleWallpaperSkins: "./skins" } }),
);
writeFileSync(path.join(pluginPack, "skin.json"), JSON.stringify({ id: "plugin-fixture", name: "插件包", metal: "silver" }));
writeFileSync(path.join(pluginPack, "orn-corner-silver.png"), "PLUGIN-ORN");

const broken = path.join(SKINS_ROOT, "broken-fixture");
mkdirSync(broken, { recursive: true });
writeFileSync(path.join(broken, "skin.json"), "{ nope");

writeFileSync(
  path.join(PROFILE, "package.json"),
  JSON.stringify({ name: "dsh-profile-desktop", dependencies: { "dsh-whale-skin-demo": "^1" } }),
);

process.env.DSH_HOME = ROOT;

// —— 桩 ctx：只提供 webServer.register 与 profileContext ——
const routes = [];
const webServer = {
  register(route) {
    routes.push(route);
    return () => {};
  },
};
const ctx = {
  inject(names, callback) {
    callback({ get: (name) => (name === "webServer" ? webServer : undefined), effect: () => {} });
  },
  get(name) {
    return name === "profileContext" ? { dir: PROFILE, name: "desktop" } : undefined;
  },
  logger: { info: () => {} },
};

await apply(ctx);

const server = createServer((req, res) => {
  const route = routes.find((candidate) => new URL(req.url, "http://x").pathname === candidate.path);
  if (route === undefined) {
    res.writeHead(404).end("no route");
    return;
  }
  route.handler(req, res);
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const base = `http://127.0.0.1:${server.address().port}`;

const get = async (url) => {
  const response = await fetch(base + url);
  return { status: response.status, text: await response.text() };
};

const checks = [];

checks.push([
  "三条路由齐了",
  routes.map((route) => route.path).sort().join(",") ===
    [
      "/api/dsh-whale-wallpaper/assets",
      "/api/dsh-whale-wallpaper/pack",
      "/api/dsh-whale-wallpaper/skins",
    ].sort().join(","),
]);

const css = await get("/api/dsh-whale-wallpaper/assets?f=wallpaper.css");
checks.push(["/assets 能取到 wallpaper.css", css.status === 200 && css.text.includes("--ww-image")]);

const traversal = await get("/api/dsh-whale-wallpaper/assets?f=../../../package.json");
checks.push(["/assets 拒绝目录穿越", traversal.status === 404]);

const skinsResponse = await get("/api/dsh-whale-wallpaper/skins");
let payload = {};
try {
  payload = JSON.parse(skinsResponse.text);
} catch (error) {
  payload = {};
}
const listed = Array.isArray(payload.skins) ? payload.skins : [];
const ids = listed.map((skin) => skin.id);

checks.push(["/skins 发现投放目录里的包", ids.includes("dropin-fixture")]);
checks.push(["/skins 发现插件声明的包", ids.includes("plugin-fixture")]);

const dropin = listed.find((skin) => skin.id === "dropin-fixture");
checks.push([
  "投放包的自带资源被逐个列出",
  dropin !== undefined &&
    Array.isArray(dropin.wallpapers) &&
    dropin.wallpapers.join(",") === "companion-dark" &&
    dropin.thumb === true &&
    dropin.mascotCorner === "left" &&
    dropin.particles === "sakura",
]);

const problems = Array.isArray(payload.problems) ? payload.problems : [];
checks.push([
  "坏包被跳过并记录原因",
  problems.some((entry) => entry.problem === "invalid-skin-json" && String(entry.dir).includes("broken-fixture")),
]);

const packFile = await get("/api/dsh-whale-wallpaper/pack?p=dropin-fixture&f=ww-dropin-companion-dark.webp");
checks.push(["/pack 能取到包内壁纸（裸文件名）", packFile.status === 200 && packFile.text === "DROPIN-DARK"]);

const packFilePrefixed = await get("/api/dsh-whale-wallpaper/pack?p=dropin-fixture&f=assets/ww-dropin-companion-dark.webp");
checks.push(["/pack 也能用 assets/ 前缀取到", packFilePrefixed.status === 200 && packFilePrefixed.text === "DROPIN-DARK"]);

const packThumb = await get("/api/dsh-whale-wallpaper/pack?p=dropin-fixture&f=thumb.webp");
checks.push(["/pack 能取到贴在包根的缩略图", packThumb.status === 200 && packThumb.text === "DROPIN-THUMB"]);

const packOrn = await get("/api/dsh-whale-wallpaper/pack?p=plugin-fixture&f=orn-corner-silver.png");
checks.push(["/pack 能取到插件包内的饰件", packOrn.status === 200 && packOrn.text === "PLUGIN-ORN"]);

const unknown = await get("/api/dsh-whale-wallpaper/pack?p=nope-fixture&f=x.webp");
checks.push(["未知包 404", unknown.status === 404]);

const packTraversal = await get("/api/dsh-whale-wallpaper/pack?p=dropin-fixture&f=../../../../package.json");
checks.push(["/pack 拒绝目录穿越", packTraversal.status === 404]);

const badId = await get("/api/dsh-whale-wallpaper/pack?p=../evil&f=x");
checks.push(["非法包 id 404", badId.status === 404]);

let failed = 0;
for (const [name, ok] of checks) {
  if (!ok) failed += 1;
  console.log(`${ok ? "ok  " : "FAIL"}  ${name}`);
}
server.close();
rmSync(ROOT, { recursive: true, force: true });
console.log(failed === 0 ? "\n皮肤包路由集成测试全部通过" : `\n${failed} 项失败`);
process.exit(failed === 0 ? 0 : 1);
