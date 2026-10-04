// dsh-whale-wallpaper —— 鲸鱼壁纸 / 皮肤包插件(宿主半边,零侵入)。
//
// 三件事:
//   1. /api/dsh-whale-wallpaper/assets  包内 assets(wallpaper.css、ww-*.webp、饰件、立绘)只读路由;
//   2. /api/dsh-whale-wallpaper/skins   发现到的第三方皮肤包清单(JSON);
//   3. /api/dsh-whale-wallpaper/pack    按包 id 提供该包自己的资源。
//
// 皮肤包从三处发现,全部只读、缺一个不影响其它:
//   · <插件>/skins/*            随插件自带的皮肤包
//   · <DSH_HOME>/whale-wallpaper-skins/*   直接放进去就能用
//   · profile 里已安装、且 package.json 声明 dsh.whaleWallpaperSkins 的插件
// 不修改任何内置包文件。
import { createReadStream, existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

/** Cordis 插件名(loader 诊断用)。 */
export const name = "dsh-whale-wallpaper";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ASSETS_DIR = path.join(HERE, "..", "assets");
const BUILTIN_SKINS_DIR = path.join(HERE, "..", "skins");

const ROUTE_ASSETS = "/api/dsh-whale-wallpaper/assets";
const ROUTE_SKINS = "/api/dsh-whale-wallpaper/skins";
const ROUTE_PACK = "/api/dsh-whale-wallpaper/pack";

const MIME = {
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".webp": "image/webp",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};

const PACK_FORMAT_VERSION = 1;
const ID_PATTERN = /^[a-z0-9][a-z0-9-]{0,31}$/;
const METALS = new Set(["gold", "silver", "none"]);
const PARTICLES = new Set(["petal", "mote", "bubble", "snow", "blossom", "sakura"]);
const MASCOTS = new Set(["notebook", "pointer", "curious"]);
const CORNERS = new Set(["left", "right", "none"]);
const SKINS_CACHE_MS = 5000;

/** 把请求参数解析为某个根目录内的安全路径;越界返回 null。 */
function safeResolve(root, rel) {
  if (typeof rel !== "string" || rel.length === 0 || rel.length > 256) return null;
  const target = path.normalize(path.join(root, rel));
  if (target !== root && !target.startsWith(root + path.sep)) return null;
  return target;
}

function readJson(file) {
  try {
    return JSON.parse(readFileSync(file, "utf8"));
  } catch (error) {
    return null;
  }
}

function listDir(dir) {
  try {
    return readdirSync(dir, { withFileTypes: true });
  } catch (error) {
    return [];
  }
}

function clip(value, max) {
  return typeof value === "string" ? value.slice(0, max) : "";
}

/**
 * 读取并校验一个皮肤包目录(skin.json + 资源)。
 * 任何一处不合法都返回 { problem }，调用方跳过该包并记日志——坏包不影响其它包。
 */
export function readSkinPack(dir) {
  const manifestPath = path.join(dir, "skin.json");
  if (!existsSync(manifestPath)) return { problem: "missing-skin-json" };
  const raw = readJson(manifestPath);
  if (raw === null || typeof raw !== "object") return { problem: "invalid-skin-json" };

  const id = clip(raw.id, 32) || path.basename(dir);
  if (!ID_PATTERN.test(id)) return { problem: "invalid-id" };
  const name = clip(raw.name, 40);
  if (name.length === 0) return { problem: "missing-name" };

  const scene = clip(raw.scene, 32) || id;
  if (!ID_PATTERN.test(scene)) return { problem: "invalid-scene" };
  const metal = METALS.has(raw.metal) ? raw.metal : "gold";
  const decor = raw.decor === undefined ? metal !== "none" : raw.decor !== false;
  const bow = raw.bow === true;
  const lace = raw.lace === undefined ? decor : raw.lace !== false;
  const mascot = MASCOTS.has(raw.mascot) ? raw.mascot : "curious";
  const mascotCorner = CORNERS.has(raw.mascotCorner) ? raw.mascotCorner : "right";
  const particles = PARTICLES.has(raw.particles) ? raw.particles : "mote";

  // 资源既可以放在包根目录，也可以集中放在 assets/ 子目录（两者都支持，assets/ 优先）
  const assetsDir = existsSync(path.join(dir, "assets")) ? path.join(dir, "assets") : dir;
  const has = (rel) => existsSync(path.join(assetsDir, rel));
  const hasRoot = (rel) => existsSync(path.join(dir, rel));
  const POSES = ["companion", "debug", "slack"];
  const THEMES = ["dark", "light"];
  return {
    pack: {
      id,
      name,
      desc: clip(raw.desc, 120),
      scene,
      metal,
      decor,
      bow,
      lace,
      mascot,
      mascotCorner,
      particles,
      // 自带资源逐个列出(客户端只在这些文件确实存在时才走包内路由,否则回落到插件内置资源)
      wallpapers: POSES.flatMap((pose) => THEMES.map((theme) => `${pose}-${theme}`)).filter((key) =>
        has(`ww-${scene}-${key}.webp`),
      ),
      ornaments: ["gold", "silver"].filter((kind) => has(`orn-corner-${kind}.png`)),
      mascots: [...MASCOTS].filter((kind) => has(`mascot-${kind}.webp`)),
      // 缩略图允许贴在 skin.json 旁边，也允许放进 assets/
      thumb: hasRoot("thumb.webp") || has("thumb.webp"),
    },
    dir: assetsDir,
    root: dir,
  };
}

/** 在某个目录下扫描「一层子目录 = 一个皮肤包」。 */
function scanRoot(root, source, out) {
  for (const entry of listDir(root)) {
    if (!entry.isDirectory() && !entry.isSymbolicLink()) continue;
    if (entry.name.startsWith(".")) continue;
    const result = readSkinPack(path.join(root, entry.name));
    if (result.problem !== undefined) {
      out.problems.push({ dir: path.join(root, entry.name), source, problem: result.problem });
      continue;
    }
    out.packs.push({ ...result.pack, source, dir: result.dir, root: result.root });
  }
}

/** profile 里已安装、且声明了 dsh.whaleWallpaperSkins 的插件。 */
function scanProfilePlugins(profileDir, out) {
  const manifestPath = path.join(profileDir, "package.json");
  const manifest = readJson(manifestPath);
  const dependencies = manifest !== null && typeof manifest === "object" ? manifest.dependencies : null;
  if (dependencies === null || typeof dependencies !== "object") return;
  for (const packageName of Object.keys(dependencies)) {
    const packageDir = path.join(profileDir, "node_modules", ...packageName.split("/"));
    const packageManifest = readJson(path.join(packageDir, "package.json"));
    const declared = packageManifest?.dsh?.whaleWallpaperSkins;
    if (typeof declared !== "string" || declared.length === 0) continue;
    const skinsDir = path.normalize(path.join(packageDir, declared));
    if (!skinsDir.startsWith(packageDir + path.sep) || !existsSync(skinsDir)) {
      out.problems.push({ dir: skinsDir, source: `plugin:${packageName}`, problem: "invalid-skins-dir" });
      continue;
    }
    scanRoot(skinsDir, `plugin:${packageName}`, out);
  }
}

/** 汇总三处发现结果,并做缓存(5 秒)。 */
function collectPacks(ctx) {
  const now = Date.now();
  const cached = collectPacks.cache;
  if (cached !== undefined && now - cached.at < SKINS_CACHE_MS) return cached.value;

  const profileContext = ctx.get?.("profileContext") ?? ctx.profileContext;
  const profileDir = typeof profileContext?.dir === "string" ? profileContext.dir : null;
  const dshHome =
    process.env.DSH_HOME && process.env.DSH_HOME.length > 0
      ? process.env.DSH_HOME
      : profileDir !== null
        ? path.dirname(path.dirname(profileDir))
        : path.join(os.homedir(), ".dsh");

  const out = { packs: [], problems: [], roots: [] };
  const dropIn = path.join(dshHome, "whale-wallpaper-skins");
  if (existsSync(BUILTIN_SKINS_DIR)) {
    out.roots.push(BUILTIN_SKINS_DIR);
    scanRoot(BUILTIN_SKINS_DIR, "bundled", out);
  }
  if (existsSync(dropIn)) {
    out.roots.push(dropIn);
    scanRoot(dropIn, "drop-in", out);
  }
  if (profileDir !== null && existsSync(profileDir)) {
    out.roots.push(`profile:${profileDir}`);
    scanProfilePlugins(profileDir, out);
  }

  // 同名包以「先发现者为准」:自带 > 投放 > 插件声明
  const seen = new Set();
  out.packs = out.packs.filter((pack) => {
    if (seen.has(pack.id)) return false;
    seen.add(pack.id);
    return true;
  });

  collectPacks.cache = { at: now, value: out };
  return out;
}

function sendJson(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function sendFile(res, file) {
  const type = MIME[path.extname(file).toLowerCase()] ?? "application/octet-stream";
  res.writeHead(200, { "Content-Type": type, "Cache-Control": "public, max-age=600" });
  createReadStream(file).pipe(res);
}

function sendMissing(res) {
  res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
  res.end("not found");
}

export async function apply(ctx) {
  // 必须走 inject —— apply 运行时刻 webserver 的 fiber 可能尚未创建
  ctx.inject(["webServer"], (wctx) => {
    const webServer = wctx.get("webServer");

    const disposers = [
      webServer.register({
        kind: "exact",
        path: ROUTE_ASSETS,
        handler: async (req, res) => {
          try {
            const url = new URL(req.url, "http://127.0.0.1");
            // f 的值可能带形如 ?v=3 的版本尾巴(表现层拼 URL 时追加),剥掉再解析
            const rel = (url.searchParams.get("f") ?? "").split("?")[0];
            const file = safeResolve(ASSETS_DIR, rel);
            if (file === null || !existsSync(file) || !statSync(file).isFile()) return sendMissing(res);
            sendFile(res, file);
          } catch (error) {
            res.writeHead(400, { "Content-Type": "text/plain; charset=utf-8" });
            res.end(String(error?.message ?? error));
          }
        },
      }),
      webServer.register({
        kind: "exact",
        path: ROUTE_SKINS,
        handler: async (req, res) => {
          try {
            const collected = collectPacks(ctx);
            sendJson(res, 200, {
              version: PACK_FORMAT_VERSION,
              roots: collected.roots.length,
              problems: collected.problems,
              skins: collected.packs.map(({ dir, root, ...rest }) => rest),
            });
          } catch (error) {
            sendJson(res, 500, { version: PACK_FORMAT_VERSION, skins: [], error: String(error?.message ?? error) });
          }
        },
      }),
      webServer.register({
        kind: "exact",
        path: ROUTE_PACK,
        handler: async (req, res) => {
          try {
            const url = new URL(req.url, "http://127.0.0.1");
            const id = url.searchParams.get("p") ?? "";
            const rel = (url.searchParams.get("f") ?? "").split("?")[0];
            if (!ID_PATTERN.test(id)) return sendMissing(res);
            const found = collectPacks(ctx).packs.find((pack) => pack.id === id);
            if (found === undefined) return sendMissing(res);
            // 资源根优先，其次包根（缩略图常贴在 skin.json 旁边）
            const file = [safeResolve(found.dir, rel), safeResolve(found.root, rel)].find(
              (candidate) => candidate !== null && existsSync(candidate) && statSync(candidate).isFile(),
            );
            if (file === undefined) return sendMissing(res);
            sendFile(res, file);
          } catch (error) {
            res.writeHead(400, { "Content-Type": "text/plain; charset=utf-8" });
            res.end(String(error?.message ?? error));
          }
        },
      }),
    ];

    wctx.effect(() => () => disposers.forEach((dispose) => dispose()), "dsh-whale-wallpaper: 静态资源与皮肤包路由");
  });

  try {
    const collected = collectPacks(ctx);
    ctx.logger?.info?.(
      `dsh-whale-wallpaper: 已挂载(资源/皮肤包路由),发现皮肤包 ${collected.packs.length} 个${
        collected.problems.length > 0 ? `,跳过 ${collected.problems.length} 个` : ""
      }`,
    );
  } catch (error) {
    ctx.logger?.info?.(`dsh-whale-wallpaper: 已挂载(资源路由);皮肤包扫描失败 ${String(error?.message ?? error)}`);
  }
}
