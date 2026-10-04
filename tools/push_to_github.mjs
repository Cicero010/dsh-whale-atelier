/**
 * 用 GitHub REST + Git Data API 把发布树推成一个仓库（本机不需要 git）。
 *
 * 用法：
 *   node tools/push_to_github.mjs --repo dsh-whale-wallpaper [--private] [--dry-run]
 *                                [--tree _publish/dsh-whale-wallpaper]
 *                                [--token-file .github-token] [--owner <login>]
 *                                [--message "…"] [--delete-token-file]
 *
 * 令牌来源（按顺序）：--token-file 指向的文件 > 环境变量 GITHUB_TOKEN > GH_TOKEN。
 * 全程只放在 Authorization 头里：不写进命令行参数、不打印、不落盘到 .git/config。
 */
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync, rmSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const API = "https://api.github.com";
const HERE = path.dirname(fileURLToPath(import.meta.url));
const WORKSPACE = path.dirname(HERE);

const TOPICS = ["dsh-plugin", "deepseek-harness", "wallpaper", "theme", "skin", "desktop-pet"];
const DESCRIPTION = "DeepSeek Harness 的鲸鱼皮肤包：全界面壁纸 + 金/银描边装饰 + 蕾丝蝴蝶结 + 角落立绘 + 环境粒子，支持第三方皮肤包与 Agent 状态联动";

function parseArgs(argv) {
  const args = {
    tree: path.join(WORKSPACE, "_publish", "dsh-whale-wallpaper"),
    repo: "dsh-whale-wallpaper",
    owner: null,
    private: false,
    dryRun: false,
    tokenFile: path.join(WORKSPACE, ".github-token"),
    message: "feat: 鲸鱼皮肤包 v1.1.0（五套内置皮肤 + 第三方皮肤包 + 装饰层 + 环境粒子 + Agent 状态联动）",
    deleteTokenFile: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const flag = argv[i];
    if (flag === "--private") args.private = true;
    else if (flag === "--dry-run") args.dryRun = true;
    else if (flag === "--delete-token-file") args.deleteTokenFile = true;
    else if (flag.startsWith("--")) {
      const key = flag.slice(2).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      const value = argv[i + 1];
      if (value === undefined) throw new Error(`缺少 ${flag} 的参数`);
      args[key] = value;
      i += 1;
    }
  }
  return args;
}

function readToken(file) {
  const fromEnv = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
  if (typeof fromEnv === "string" && fromEnv.trim().length > 0) {
    return { token: fromEnv.trim(), source: "环境变量" };
  }
  if (existsSync(file)) {
    const value = readFileSync(file, "utf8").trim();
    if (value.length > 0) return { token: value, source: file };
  }
  throw new Error(`没有拿到令牌：请设置 GITHUB_TOKEN，或把 PAT 写进 ${file}`);
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function api(token, method, url, body) {
  const target = url.startsWith("http") ? url : API + url;
  let lastError = null;
  for (let attempt = 0; attempt < 5; attempt += 1) {
    const response = await fetch(target, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "dsh-whale-wallpaper-publisher",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (response.status === 403 || response.status === 429) {
      const retryAfter = Number(response.headers.get("retry-after") ?? "0");
      const waitMs = retryAfter > 0 ? retryAfter * 1000 : 2500 * (attempt + 1);
      lastError = new Error(`${method} ${url} -> ${response.status}（限流，等待 ${waitMs}ms 后重试）`);
      await sleep(waitMs);
      continue;
    }
    const text = await response.text();
    let data = null;
    if (text.length > 0) {
      try {
        data = JSON.parse(text);
      } catch (error) {
        data = { raw: text.slice(0, 200) };
      }
    }
    if (!response.ok) {
      const message = data && typeof data === "object" ? data.message : text;
      const error = new Error(`${method} ${url} -> ${response.status} ${message ?? ""}`);
      error.status = response.status;
      throw error;
    }
    return data;
  }
  throw lastError ?? new Error(`${method} ${url} 失败`);
}

function walk(root, prefix = "") {
  const out = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const abs = path.join(root, entry.name);
    const rel = prefix.length === 0 ? entry.name : `${prefix}/${entry.name}`;
    if (entry.isDirectory()) out.push(...walk(abs, rel));
    else if (entry.isFile()) out.push({ abs, rel, size: statSync(abs).size });
  }
  return out;
}

/**
 * 保证默认分支存在。
 * 空仓库上 Git Data API（blob/tree/commit）会返回 409「Git Repository is empty」，
 * 所以先用 Contents API 落一个占位文件把 refs/heads/main 建出来；
 * 之后用「无父提交」的孤儿提交 + 强制更新 ref 覆盖它，最终历史仍然只有一个提交。
 */
async function ensureHead(token, owner, repo) {
  try {
    const ref = await api(token, "GET", `/repos/${owner}/${repo}/git/ref/heads/main`);
    return { head: ref.object.sha, bootstrapped: false };
  } catch (error) {
    if (error.status !== 404 && error.status !== 409) throw error;
  }
  await api(token, "PUT", `/repos/${owner}/${repo}/contents/.bootstrap`, {
    message: "chore: bootstrap empty repository",
    content: Buffer.from("bootstrap\n").toString("base64"),
  });
  const ref = await api(token, "GET", `/repos/${owner}/${repo}/git/ref/heads/main`);
  return { head: ref.object.sha, bootstrapped: true };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!existsSync(args.tree)) throw new Error(`发布树不存在：${args.tree}（先跑 tools/build_repo.py）`);

  const { token, source } = readToken(args.tokenFile);
  console.log(`令牌来源：${source}`);

  const me = await api(token, "GET", "/user");
  const owner = args.owner ?? me.login;
  console.log(`账号：${owner}（${me.name ?? ""}）`);

  const files = walk(args.tree);
  const totalBytes = files.reduce((sum, file) => sum + file.size, 0);
  console.log(`发布树：${files.length} 个文件 / ${(totalBytes / 1024 / 1024).toFixed(2)} MB`);
  console.log(`目标仓库：${owner}/${args.repo}（${args.private ? "私有" : "公开"}）`);

  if (args.dryRun) {
    console.log("\n--dry-run：只校验令牌与账号，不做任何写操作。");
    return;
  }

  let exists = true;
  try {
    await api(token, "GET", `/repos/${owner}/${args.repo}`);
  } catch (error) {
    if (error.status === 404) exists = false;
    else throw error;
  }

  if (!exists) {
    await api(token, "POST", "/user/repos", {
      name: args.repo,
      private: args.private,
      description: DESCRIPTION,
      has_issues: true,
      has_wiki: false,
      has_projects: false,
      auto_init: false,
    });
    console.log(`已创建仓库 ${owner}/${args.repo}`);
  } else {
    console.log(`仓库已存在，将推送到 main 分支`);
  }

  // 空仓库必须先有一次提交，否则后面的 blob 写入会 409
  const { head, bootstrapped } = await ensureHead(token, owner, args.repo);
  if (bootstrapped) console.log("空仓库：已用 Contents API 引导出默认分支 main");

  const known = new Map();
  const tree = [];
  let created = 0;
  for (const [index, file] of files.entries()) {
    const content = readFileSync(file.abs);
    const digest = createHash("sha1").update(content).digest("hex");
    let sha = known.get(digest);
    if (sha === undefined) {
      sha = (await api(token, "POST", `/repos/${owner}/${args.repo}/git/blobs`, {
        content: content.toString("base64"),
        encoding: "base64",
      })).sha;
      known.set(digest, sha);
      created += 1;
      if (created % 10 === 0) {
        process.stdout.write(`  已上传 ${created} 个 blob…\n`);
        await sleep(500);
      }
    }
    tree.push({ path: file.rel, mode: "100644", type: "blob", sha });
  }
  console.log(`blob 完成：新建 ${created} 个（按内容去重），树条目 ${tree.length}`);

  const parents = bootstrapped ? [] : head === undefined ? [] : [head];

  const treeSha = (await api(token, "POST", `/repos/${owner}/${args.repo}/git/trees`, { tree })).sha;
  const commit = await api(token, "POST", `/repos/${owner}/${args.repo}/git/commits`, {
    message: args.message,
    tree: treeSha,
    parents,
  });

  if (bootstrapped) {
    // 覆盖引导提交：最终历史只有一个提交，占位文件也不在树里
    await api(token, "PATCH", `/repos/${owner}/${args.repo}/git/refs/heads/main`, { sha: commit.sha, force: true });
    console.log("已用孤儿提交覆盖引导提交（历史只有一次提交）");
  } else if (parents.length === 0) {
    await api(token, "POST", `/repos/${owner}/${args.repo}/git/refs`, { ref: "refs/heads/main", sha: commit.sha });
  } else {
    await api(token, "PATCH", `/repos/${owner}/${args.repo}/git/refs/heads/main`, { sha: commit.sha });
  }

  try {
    await api(token, "PUT", `/repos/${owner}/${args.repo}/topics`, { names: TOPICS });
  } catch (error) {
    console.log(`（topics 设置失败，忽略：${error.message}）`);
  }

  console.log(`\n完成 ✅  ${commit.sha.slice(0, 10)}`);
  console.log(`仓库：https://github.com/${owner}/${args.repo}`);
  console.log(`提交：https://github.com/${owner}/${args.repo}/commit/${commit.sha}`);

  if (args.deleteTokenFile && existsSync(args.tokenFile)) {
    rmSync(args.tokenFile, { force: true });
    console.log(`已删除令牌文件：${args.tokenFile}`);
  }
}

await main();
