/**
 * dsh-whale-wallpaper 客户端插件:鲸鱼壁纸 + 装饰皮肤层。
 *
 * 零侵入:不改任何内置包文件、不写业务 DOM 的属性、无外部请求、不注册 RPC。
 * 只做四件事:
 *   1) 拉取 wallpaper.css 注入样式(真正的视觉规则全在样式表里);
 *   2) 把「皮肤 / 立绘 / 明暗 / 覆盖范围 / 遮罩」投影成 <html> 上的 data-ww* 与自定义属性;
 *   3) 建一层自己的装饰 DOM(角花、描边线、蝴蝶结、标题分隔、角落立绘),
 *      几何靠量真实外壳元素的位置来对齐 —— 只读 DOM,不修改它;
 *   4) 设置面板注册「皮肤」栏目(localStorage: whale-wallpaper:*)。
 *
 * 样式选择器全部挂在 html[data-ww="on"] 下:撤掉插件或在面板里关掉,界面立刻回到出厂外观。
 */
window.__ModuleLoader__.load({
  id: "dsh-whale-wallpaper",
  factory: (require) => {
    var module = { exports: {} };
    var exports = module.exports;

    var React = require("react");
    var jsxRuntime = require("react/jsx-runtime");
    var jsx = jsxRuntime.jsx;
    var jsxs = jsxRuntime.jsxs;

    const ROUTE = "/api/dsh-whale-wallpaper/assets?f=";
    const ROUTE_PACK = "/api/dsh-whale-wallpaper/pack?p=";
    const ROUTE_SKINS = "/api/dsh-whale-wallpaper/skins";
    const BOOT_FLAG = "__dshWhaleWallpaperBooted";
    const CHANGE_EVENT = "whale-wallpaper-change";
    const NS = "whale-wallpaper:";

    /** 壁纸立绘:值对应 ww-<场景>-<值>-<明暗>.webp */
    const POSES = [
      ["companion", "陪伴"],
      ["debug", "查 bug"],
      ["slack", "摸鱼"],
    ];
    const THEMES = [
      ["auto", "跟随主题"],
      ["clock", "按时段"],
      ["dark", "深色"],
      ["light", "浅色"],
    ];
    const SCOPES = [
      ["full", "全界面"],
      ["workspace", "仅工作区"],
    ];
    const MASCOT_SPOTS = [
      ["left", "左下"],
      ["right", "右下"],
      ["none", "关"],
    ];
    const MASCOT_POSES = [
      ["notebook", "抱本子"],
      ["pointer", "拿教鞭"],
      ["curious", "好奇"],
    ];
    /** Agent 状态 → 临时形象（等待审批 / 出错 / 生成中 / 刚完成）。 */
    const STATE_MASCOTS = {
      waiting: "waiting",
      failure: "failure",
      working: "thinking",
      success: "success",
    };
    /** 可导出/导入的偏好键（导出与他人分享的 JSON 只包含这些）。 */
    const SHARE_KEYS = ["enabled", "skin", "pose", "scope", "theme", "scrim", "vignette", "blur", "decor", "mascot", "mascotPose", "particles", "mascotState"];
    /** 环境粒子的尺寸区间（按氛围类型）。 */
    const PARTICLE_SIZE = { snow: [3, 6], blossom: [4, 7], sakura: [5, 11], petal: [5, 10], mote: [4, 8], bubble: [5, 11] };
    /** 发现到的第三方皮肤包：id → 清单（由宿主 /skins 提供）。 */
    let PACKS = {};

    /** 皮肤包 = 壁纸场景 + 描边金属 + 蝴蝶结 + 角落立绘 + 环境粒子。 */
    const SKINS = {
      atelier: {
        name: "女仆工坊",
        desc: "夜庭室内 · 金色描边 · 蕾丝与蝴蝶结 · 左下角抱本子 · 花瓣飘落",
        scene: "interior",
        metal: "gold",
        decor: true,
        bow: true,
        mascot: "notebook",
        mascotCorner: "left",
        particles: "petal",
      },
      garden: {
        name: "夜庭银饰",
        desc: "夜庭室内 · 银蓝描边 · 蕾丝无蝴蝶结 · 右下角拿教鞭 · 萤火漂浮",
        scene: "interior",
        metal: "silver",
        decor: true,
        bow: false,
        mascot: "pointer",
        mascotCorner: "right",
        particles: "mote",
      },
      abyss: {
        name: "深海",
        desc: "水下渐变 · 无描边装饰 · 右下角小立绘 · 气泡上浮",
        scene: "abyss",
        metal: "silver",
        decor: false,
        bow: false,
        mascot: "curious",
        mascotCorner: "right",
        particles: "bubble",
      },
      snow: {
        name: "雪夜庭",
        desc: "夜庭室内 · 落雪与霜花 · 银蓝描边 · 右下角拿教鞭 · 雪花飘落",
        scene: "snow",
        metal: "silver",
        decor: true,
        bow: false,
        mascot: "pointer",
        mascotCorner: "right",
        particles: "snow",
      },
      moonfest: {
        name: "桂月夜庭",
        desc: "夜庭室内 · 满月与灯笼 · 金色描边 · 左下角好奇 · 桂花飘落",
        scene: "moonfest",
        metal: "gold",
        decor: true,
        bow: true,
        mascot: "curious",
        mascotCorner: "left",
        particles: "blossom",
      },
    };

    const METAL_RGB = { gold: "214, 178, 110", silver: "150, 168, 204" };
    /** 遮罩浓度默认值(与 wallpaper.css 保持一致)。 */
    const SCRIM_DEFAULT = { dark: 0.64, light: 0.24 };

    /* ---- 偏好读写 ---- */

    function read(key, fallback) {
      try {
        const value = window.localStorage.getItem(NS + key);
        return value === null ? fallback : value;
      } catch (error) {
        return fallback;
      }
    }

    function write(key, value) {
      try {
        window.localStorage.setItem(NS + key, String(value));
      } catch (error) {
        /* 写不进去也要让本次会话生效 */
      }
    }

    function clear(key) {
      try {
        window.localStorage.removeItem(NS + key);
      } catch (error) {
        /* 同上 */
      }
    }

    function isDark() {
      return document.body !== null && document.body.hasAttribute("data-ds-dark-theme");
    }

    function enabled() {
      return read("enabled", "1") !== "0";
    }

    function skinDef() {
      const wanted = read("skin", "atelier");
      const found = skinById(wanted);
      return found !== null ? found : { ...SKINS.atelier, id: "atelier", builtin: true };
    }

    /** 内置皮肤与皮肤包合并后的查询：找不到返回 null。 */
    function skinById(id) {
      if (SKINS[id] !== undefined) return { ...SKINS[id], id, builtin: true };
      const pack = PACKS[id];
      if (pack !== undefined && typeof pack.id === "string") return { ...pack, builtin: false };
      return null;
    }

    /** 选择器里的顺序：内置在前，皮肤包在后。 */
    function skinIds() {
      return [...Object.keys(SKINS), ...Object.keys(PACKS).filter((id) => SKINS[id] === undefined)];
    }

    /** 该皮肤是否自带此文件（自带才走包内路由，否则回落到插件内置资源）。 */
    function packHas(skin, field, value) {
      return skin.builtin !== true && Array.isArray(skin[field]) && skin[field].indexOf(value) !== -1;
    }

    /** 皮肤资源 URL：包内自带用包路由（索引包走 /assets 的 packs/ 前缀，宿主发现包走 /pack），否则回落到插件 /assets。 */
    function skinAsset(skin, file, own) {
      if (own === true) {
        if (typeof skin.base === "string" && skin.base.length > 0) {
          return 'url("' + ROUTE + skin.base + file + '")';
        }
        return 'url("' + ROUTE_PACK + encodeURIComponent(skin.id) + "&f=" + encodeURIComponent(file) + '")';
      }
      return asset(file);
    }

    /** 缩略图 URL；皮肤包没带缩略图时返回 null（选择器显示占位块）。 */
    function skinThumb(skin) {
      if (skin.builtin === true) return ROUTE + "thumb-" + skin.id + ".webp";
      if (skin.thumb !== true) return null;
      if (typeof skin.base === "string" && skin.base.length > 0) return ROUTE + skin.base + "thumb.webp";
      return ROUTE_PACK + encodeURIComponent(skin.id) + "&f=thumb.webp";
    }

    function currentPose() {
      const pose = read("pose", "companion");
      return POSES.some((entry) => entry[0] === pose) ? pose : "companion";
    }

    function currentTheme() {
      const pref = read("theme", "auto");
      if (pref === "dark" || pref === "light") return pref;
      if (pref === "clock") return clockTheme();
      return isDark() ? "dark" : "light";
    }

    /** 按时段：07:00–18:30 用白天版壁纸，其余时段用夜景版。 */
    function clockTheme() {
      const now = new Date();
      const hour = now.getHours() + now.getMinutes() / 60;
      return hour >= 7 && hour < 18.5 ? "light" : "dark";
    }

    function mascotStateOn() {
      return read("mascotState", "1") !== "0";
    }

    function currentScope() {
      return read("scope", "full") === "workspace" ? "workspace" : "full";
    }

    function decorOn() {
      const value = read("decor", "");
      return value === "" ? skinDef().decor !== false : value !== "0";
    }

    function bowOn() {
      return decorOn() && skinDef().bow !== false;
    }

    /** 蕾丝：皮肤包可以显式关掉（lace: false），内置皮肤默认开。 */
    function laceOn() {
      return decorOn() && skinDef().lace !== false;
    }

    const VIGNETTE_DEFAULT = 0.28;
    const BLUR_MAX = 24;

    function vignetteValue() {
      const raw = read("vignette", "");
      const parsed = Number.parseFloat(raw);
      if (raw === "" || !Number.isFinite(parsed)) return VIGNETTE_DEFAULT;
      return Math.min(0.92, Math.max(0, parsed));
    }

    function blurValue() {
      const raw = read("blur", "");
      const parsed = Number.parseFloat(raw);
      if (raw === "" || !Number.isFinite(parsed)) return 0;
      return Math.min(BLUR_MAX, Math.max(0, parsed));
    }

    function metalName() {
      return skinDef().metal === "silver" ? "silver" : "gold";
    }

    function mascotCorner() {
      const value = read("mascot", "");
      const corner = value === "" ? skinDef().mascotCorner || "right" : value;
      return corner === "left" || corner === "none" ? corner : "right";
    }

    function mascotPose() {
      const value = read("mascotPose", "");
      const pose = value === "" ? skinDef().mascot || "notebook" : value;
      return MASCOT_POSES.some((entry) => entry[0] === pose) ? pose : "notebook";
    }

    function scrimValue() {
      const raw = read("scrim", "");
      const parsed = Number.parseFloat(raw);
      if (raw === "" || !Number.isFinite(parsed)) return SCRIM_DEFAULT[currentTheme()];
      return Math.min(0.92, Math.max(0, parsed));
    }

    /** 环境粒子默认开;偏好里存的是 "1"/"0"。 */
    function particlesOn() {
      if (read("particles", "1") === "0") return false;
      return skinDef().particles !== undefined;
    }

    function particleKind() {
      const kind = skinDef().particles;
      return PARTICLE_KINDS[kind] === undefined ? "mote" : kind;
    }

    /* ---- Agent 状态：只读 DOM 的存在性信号，不改产品元素 -------------------- */

    /**
     * 三处信号（都来自内置客户端的 CSS-module 类名后缀）：
     *   _reject        审批卡片里的拒绝按钮 → 在等你拍板
     *   _running       「运行中」行        → 生成中
     *   _turnErrorRow  / _turnErrorCode    → 轮次失败
     * 只做一次合并查询，并且只认真正渲染出来的元素（矩形非零），
     * 避免被隐藏节点或残留节点卡住状态。任何一处改名只会让状态退回常驻形象。
     */
    const STATE_SIGNALS = [
      ["waiting", "_reject"],
      ["working", "_running"],
      ["failure", "_turnErrorRow"],
      ["failure", "_turnErrorCode"],
    ];
    const FAILURE_HOLD_MS = 12000;
    const SUCCESS_FLASH_MS = 4000;

    let agentState = "idle";
    let stateSince = 0;
    let successUntil = 0;
    let lastMascotPose = "";
    let lastClockTheme = "";

    function detectAgentState() {
      if (document.body === null) return "idle";
      const selector = STATE_SIGNALS.map((entry) => '[class*="' + entry[1] + '"]').join(",");
      const candidates = document.body.querySelectorAll(selector);
      const visible = new Set();
      for (let i = 0; i < candidates.length; i += 1) {
        const rect = candidates[i].getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) continue;
        const list = candidates[i].classList;
        for (let j = 0; j < list.length; j += 1) {
          for (const [state, suffix] of STATE_SIGNALS) {
            if (list[j].endsWith(suffix)) visible.add(state);
          }
        }
      }
      if (visible.has("waiting")) return "waiting";
      if (visible.has("working")) return "working";
      if (visible.has("failure")) return "failure";
      return "idle";
    }

    function pollAgentState() {
      const detected = mascotStateOn() ? detectAgentState() : "idle";
      if (detected === agentState) return;
      const previous = agentState;
      agentState = detected;
      stateSince = Date.now();
      // 刚跑完 → 闪一下成功形象
      if (previous === "working" && detected === "idle") successUntil = Date.now() + SUCCESS_FLASH_MS;
    }

    /** 实际用于显示的状态：等待/生成中一直显示，报错只提醒一段，刚跑完闪成功。 */
    function displayState() {
      if (!mascotStateOn()) return "idle";
      if (agentState === "failure" && Date.now() - stateSince > FAILURE_HOLD_MS) return "idle";
      if (agentState !== "idle") return agentState;
      return Date.now() < successUntil ? "success" : "idle";
    }

    function applyMascotImage() {
      const state = displayState();
      const pose = state === "idle" ? mascotPose() : STATE_MASCOTS[state];
      // 状态形象永远用内置的四只；常驻形象可以来自皮肤包
      const own = state === "idle" && packHas(skinDef(), "mascots", pose);
      const root = document.documentElement;
      root.setAttribute("data-ww-mascot-state", state);
      if (pose === lastMascotPose) return;
      lastMascotPose = pose;
      root.style.setProperty("--ww-mascot", skinAsset(skinDef(), "mascot-" + pose + ".webp", own));
    }

    function asset(name) {
      return 'url("' + ROUTE + name + '")';
    }

    /* ---- 装饰层:自建 DOM,几何量真实外壳 ---- */

    /**
     * 装饰元件挂到哪一层：
     *   decor = 边框角花与边缘描线，压在最上面（z 40，只在窗口边缘，不挡交互区）
     *   trim  = 蝴蝶结与标题分隔，放在内容层之上、弹层/菜单之下（z 9）
     */
    const DECOR_SLOTS = [
      ["decor", "corner", "tl"],
      ["decor", "corner", "tr"],
      ["decor", "corner", "bl"],
      ["decor", "corner", "br"],
      ["decor", "edge", "top"],
      ["decor", "edge", "sidebar"],
      ["trim", "divider", "header"],
      ["trim", "lace", "composer"],
      ["trim", "lace", "sidebar"],
      ["trim", "bow", "composer"],
      ["trim", "bow", "sidebar"],
    ];

    /** 环境粒子数量与每套皮肤的氛围类型。 */
    const PARTICLE_COUNT = 20;
    const PARTICLE_KINDS = { petal: "petal", mote: "mote", bubble: "bubble", snow: "snow", blossom: "blossom", sakura: "sakura" };

    let decorLayer = null;
    let trimLayer = null;
    let mascotLayer = null;
    let ambientLayer = null;
    let mascotNode = null;
    const nodes = {};
    const particles = [];
    const anchors = { centerCol: null, composerSeat: null, sidebarCol: null, header: null };

    /** 类名后缀匹配:DSH 的 CSS-module 类是 <hash>_<name>,后缀比完整类名稳。 */
    function hasSuffix(element, suffix) {
      const list = element.classList;
      for (let i = 0; i < list.length; i += 1) {
        if (list[i].endsWith(suffix)) return true;
      }
      return false;
    }

    function findBySuffix(suffix, root) {
      const scope = root || document.body;
      if (scope === null) return null;
      const candidates = scope.querySelectorAll('[class*="' + suffix + '"]');
      for (let i = 0; i < candidates.length; i += 1) {
        if (hasSuffix(candidates[i], suffix)) return candidates[i];
      }
      return null;
    }

    /** 会话标题栏:中栏里最宽的那个 _header。 */
    function findHeader(centerCol) {
      if (centerCol === null) return null;
      const columnWidth = centerCol.getBoundingClientRect().width;
      const candidates = centerCol.querySelectorAll('[class*="_header"]');
      let best = null;
      let bestWidth = 0;
      for (let i = 0; i < candidates.length; i += 1) {
        if (!hasSuffix(candidates[i], "_header")) continue;
        const width = candidates[i].getBoundingClientRect().width;
        if (width > bestWidth && width >= columnWidth * 0.35) {
          best = candidates[i];
          bestWidth = width;
        }
      }
      return best;
    }

    function resolveAnchors() {
      const stale = anchors.centerCol === null || !anchors.centerCol.isConnected;
      if (stale) {
        anchors.centerCol = findBySuffix("_centerCol");
        anchors.sidebarCol = findBySuffix("_sidebarCol");
        anchors.composerSeat = anchors.centerCol ? findBySuffix("_composerSeat", anchors.centerCol) : null;
        anchors.header = findHeader(anchors.centerCol);
      }
      if (anchors.composerSeat !== null && !anchors.composerSeat.isConnected) anchors.composerSeat = findBySuffix("_composerSeat", anchors.centerCol);
      if (anchors.header !== null && !anchors.header.isConnected) anchors.header = findHeader(anchors.centerCol);
      if (anchors.sidebarCol !== null && !anchors.sidebarCol.isConnected) anchors.sidebarCol = findBySuffix("_sidebarCol");
    }

    function syncDecor() {
      if (decorLayer === null || trimLayer === null) return;
      const on = enabled();
      decorLayer.hidden = !(on && decorOn());
      trimLayer.hidden = !on;
      resolveAnchors();

      const showBows = on && bowOn();
      const showLace = on && decorOn();
      nodes.bowComposer.hidden = !showBows;
      nodes.bowSidebar.hidden = !showBows;
      nodes.laceComposer.hidden = !showLace;
      nodes.laceSidebar.hidden = !showLace;
      nodes.divider.hidden = !on;
      nodes.edgeSidebar.hidden = !showLace;

      // 几何一律更新（很便宜），可见性交给上面的 hidden 决定
      if (anchors.composerSeat !== null) {
        const rect = anchors.composerSeat.getBoundingClientRect();
        nodes.bowComposer.style.left = rect.left + rect.width / 2 + "px";
        nodes.bowComposer.style.top = rect.top + 4 + "px";
        nodes.laceComposer.style.left = rect.left + 26 + "px";
        nodes.laceComposer.style.top = rect.top - 2 + "px";
        nodes.laceComposer.style.width = Math.max(0, rect.width - 52) + "px";
      }
      if (anchors.sidebarCol !== null) {
        const rect = anchors.sidebarCol.getBoundingClientRect();
        nodes.bowSidebar.style.left = rect.left + rect.width / 2 + "px";
        nodes.bowSidebar.style.top = rect.bottom - 58 + "px";
        nodes.laceSidebar.style.left = rect.left + 14 + "px";
        nodes.laceSidebar.style.top = rect.bottom - 92 + "px";
        nodes.laceSidebar.style.width = Math.max(0, rect.width - 28) + "px";
        nodes.edgeSidebar.style.left = rect.right + "px";
      }
      if (anchors.header !== null) {
        const rect = anchors.header.getBoundingClientRect();
        nodes.divider.style.left = rect.left + "px";
        nodes.divider.style.top = rect.bottom - 1 + "px";
        nodes.divider.style.width = rect.width + "px";
      }

      // 环境粒子：按皮肤切换氛围类型与尺寸
      if (ambientLayer !== null) {
        const ambientOn = on && particlesOn();
        ambientLayer.hidden = !ambientOn;
        if (ambientOn) {
          const kind = particleKind();
          const range = PARTICLE_SIZE[kind] === undefined ? PARTICLE_SIZE.mote : PARTICLE_SIZE[kind];
          for (const node of particles) {
            if (node.getAttribute("data-kind") !== kind) {
              node.setAttribute("data-kind", kind);
              const size = range[0] + Number(node.dataset.r || "0.5") * (range[1] - range[0]);
              node.style.width = size.toFixed(1) + "px";
              node.style.height = size.toFixed(1) + "px";
            }
          }
        }
      }

      const mascotVisible = on && mascotCorner() !== "none";
      mascotLayer.hidden = !mascotVisible;
      if (mascotVisible) {
        const corner = mascotCorner();
        mascotNode.setAttribute("data-corner", corner);
        // 立绘贴边但不要压住侧栏:左下角以中栏左边缘为界。
        if (corner === "left" && anchors.centerCol !== null) {
          mascotNode.style.left = anchors.centerCol.getBoundingClientRect().left + 10 + "px";
          mascotNode.style.right = "auto";
        } else {
          mascotNode.style.left = "auto";
          mascotNode.style.right = "12px";
        }
      }
    }

    function buildLayers() {
      if (decorLayer !== null) return;
      decorLayer = document.createElement("div");
      decorLayer.className = "ww-layer";
      decorLayer.setAttribute("data-ww-layer", "decor");
      decorLayer.setAttribute("aria-hidden", "true");

      trimLayer = document.createElement("div");
      trimLayer.className = "ww-layer";
      trimLayer.setAttribute("data-ww-layer", "trim");
      trimLayer.setAttribute("aria-hidden", "true");

      for (const [layerName, kind, slot] of DECOR_SLOTS) {
        const node = document.createElement("span");
        node.className = "ww-" + kind;
        node.setAttribute("data-" + kind, slot);
        node.hidden = true;
        (layerName === "trim" ? trimLayer : decorLayer).appendChild(node);
        if (kind === "bow" && slot === "composer") nodes.bowComposer = node;
        if (kind === "bow" && slot === "sidebar") nodes.bowSidebar = node;
        if (kind === "lace" && slot === "composer") nodes.laceComposer = node;
        if (kind === "lace" && slot === "sidebar") nodes.laceSidebar = node;
        if (kind === "divider") nodes.divider = node;
        if (kind === "edge" && slot === "sidebar") nodes.edgeSidebar = node;
      }
      document.body.appendChild(decorLayer);
      document.body.appendChild(trimLayer);

      mascotLayer = document.createElement("div");
      mascotLayer.className = "ww-layer";
      mascotLayer.setAttribute("data-ww-layer", "mascot");
      mascotLayer.setAttribute("aria-hidden", "true");
      mascotNode = document.createElement("span");
      mascotNode.className = "ww-mascot";
      mascotNode.setAttribute("data-corner", "right");
      mascotLayer.appendChild(mascotNode);
      document.body.appendChild(mascotLayer);

      buildAmbient();
    }

    /** 确定性伪随机：同一台机器每次打开粒子的位置/速度都一致,不会每次刷新乱跳。 */
    function makeRandom(seed) {
      let state = seed >>> 0;
      return () => {
        state = (state * 1664525 + 1013904223) >>> 0;
        return state / 4294967296;
      };
    }

    function buildAmbient() {
      if (ambientLayer !== null) return;
      ambientLayer = document.createElement("div");
      ambientLayer.className = "ww-layer";
      ambientLayer.setAttribute("data-ww-layer", "ambient");
      ambientLayer.setAttribute("aria-hidden", "true");
      const random = makeRandom(20261004);
      for (let index = 0; index < PARTICLE_COUNT; index += 1) {
        const node = document.createElement("span");
        node.className = "ww-particle";
        const spread = random();
        node.dataset.r = spread.toFixed(3);
        const size = 4 + spread * 11;
        node.style.left = (random() * 100).toFixed(2) + "%";
        node.style.width = size.toFixed(1) + "px";
        node.style.height = size.toFixed(1) + "px";
        node.style.animationDuration = (12 + random() * 16).toFixed(1) + "s";
        node.style.animationDelay = (-random() * 24).toFixed(1) + "s";
        node.style.setProperty("--ww-drift", ((random() * 2 - 1) * 84).toFixed(0) + "px");
        particles.push(node);
        ambientLayer.appendChild(node);
      }
      document.body.appendChild(ambientLayer);
    }

    /** 把当前偏好投影到 <html> 与自建图层上;视觉结果全部由 wallpaper.css 决定。 */
    function apply() {
      const root = document.documentElement;
      const on = enabled();
      const skin = skinDef();
      const metal = metalName();

      root.setAttribute("data-ww-dark", isDark() ? "on" : "off");
      root.setAttribute("data-ww-scope", currentScope());
      root.setAttribute("data-ww-decor", decorOn() ? metal : "none");
      root.setAttribute("data-ww-mascot", mascotCorner());
      root.setAttribute("data-ww", on ? "on" : "off");

      if (!on) {
        root.style.removeProperty("--ww-image");
        if (decorLayer !== null) decorLayer.hidden = true;
        if (trimLayer !== null) trimLayer.hidden = true;
        if (mascotLayer !== null) mascotLayer.hidden = true;
        if (ambientLayer !== null) ambientLayer.hidden = true;
        return;
      }

      const pose = currentPose();
      const theme = currentTheme();
      const wallpaperKey = pose + "-" + theme;
      const wallpaperFile = "ww-" + (skin.scene || "abyss") + "-" + wallpaperKey + ".webp";
      root.style.setProperty("--ww-image", skinAsset(skin, wallpaperFile, packHas(skin, "wallpapers", wallpaperKey)));
      if (read("scrim", "") === "") root.style.removeProperty("--ww-scrim");
      else root.style.setProperty("--ww-scrim", String(scrimValue()));
      if (read("vignette", "") === "") root.style.removeProperty("--ww-vignette");
      else root.style.setProperty("--ww-vignette", String(vignetteValue()));
      if (read("blur", "") === "") {
        root.style.removeProperty("--ww-blur");
        root.style.removeProperty("--ww-scale");
      } else {
        const blur = blurValue();
        root.style.setProperty("--ww-blur", blur + "px");
        root.style.setProperty("--ww-scale", String(1 + blur / 160));
      }

      if (decorOn()) {
        const ownOrnaments = packHas(skin, "ornaments", metal);
        root.style.setProperty("--ww-orn", skinAsset(skin, "orn-corner-" + metal + ".png", ownOrnaments));
        root.style.setProperty("--ww-lace", laceOn() ? skinAsset(skin, "orn-lace-" + metal + ".png", ownOrnaments) : "none");
        root.style.setProperty("--ww-divider", skinAsset(skin, "orn-divider-" + metal + ".png", ownOrnaments));
        root.style.setProperty("--ww-metal", METAL_RGB[metal]);
      } else {
        root.style.removeProperty("--ww-orn");
        root.style.removeProperty("--ww-divider");
        root.style.removeProperty("--ww-lace");
        root.style.removeProperty("--ww-metal");
      }
      root.style.setProperty(
        "--ww-bow",
        bowOn() ? skinAsset(skin, "orn-bow-" + metal + ".png", packHas(skin, "ornaments", metal)) : "none",
      );
      pollAgentState();
      if (read("theme", "auto") === "clock") lastClockTheme = clockTheme();
      lastMascotPose = "";
      applyMascotImage();

      if (decorLayer !== null) decorLayer.hidden = false;
      syncDecor();
    }

    function notify() {
      window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
    }

    /**
     * 拉取皮肤包清单，两个来源合并：
     *   1) 插件自带的 packs/index.json（走已有 /assets 路由，刷新即生效，不需要重启宿主）；
     *   2) 宿主发现的投放目录 / 已安装插件（需要宿主重启后新路由才存在，取不到就跳过）。
     * 同名时宿主发现的优先。
     */
    async function fetchPacks() {
      const merged = {};
      try {
        const response = await fetch(ROUTE + "packs/index.json&t=" + Date.now());
        if (response.ok) {
          const data = await response.json();
          const list = data !== null && typeof data === "object" && Array.isArray(data.packs) ? data.packs : [];
          for (const skin of list) {
            if (skin === null || typeof skin !== "object") continue;
            if (typeof skin.id !== "string" || skin.id.length === 0) continue;
            if (SKINS[skin.id] !== undefined || merged[skin.id] !== undefined) continue;
            const base = typeof skin.base === "string" && skin.base.length > 0 ? skin.base : "packs/" + skin.id + "/";
            merged[skin.id] = { ...skin, base };
          }
        }
      } catch (error) {
        /* 没有索引文件是正常情况（还没装过皮肤包） */
      }
      try {
        const response = await fetch(ROUTE_SKINS, { cache: "no-store" });
        if (response.ok) {
          const data = await response.json();
          const list = data !== null && typeof data === "object" && Array.isArray(data.skins) ? data.skins : [];
          for (const skin of list) {
            if (skin === null || typeof skin !== "object") continue;
            if (typeof skin.id !== "string" || skin.id.length === 0) continue;
            if (SKINS[skin.id] !== undefined) continue;
            merged[skin.id] = skin;
          }
        }
      } catch (error) {
        /* 宿主发现不可用(还没重启)时只保留索引里的包 */
      }
      PACKS = merged;
      notify();
    }

    /** 宿主路由可能比页面晚一点就绪,给几次退避重试再放弃。 */
    async function fetchStyleSheet() {
      let lastError = new Error("样式表未取到");
      for (let attempt = 0; attempt < 4; attempt += 1) {
        try {
          const response = await fetch(ROUTE + "wallpaper.css");
          if (response.ok) return await response.text();
          lastError = new Error("HTTP " + response.status);
        } catch (error) {
          lastError = error;
        }
        await new Promise((resolve) => setTimeout(resolve, 300 * (attempt + 1)));
      }
      throw lastError;
    }

    /** 极端情况下 factory 可能早于 <body> 物化,等 DOM 就绪再落属性。 */
    function whenBodyReady() {
      if (document.body) return Promise.resolve();
      return new Promise((resolve) => {
        document.addEventListener("DOMContentLoaded", () => resolve(), { once: true });
      });
    }

    let syncQueued = false;
    function queueSync() {
      if (syncQueued) return;
      syncQueued = true;
      window.requestAnimationFrame(() => {
        syncQueued = false;
        syncDecor();
      });
    }

    async function boot() {
      if (window[BOOT_FLAG]) return;
      window[BOOT_FLAG] = true;
      try {
        const css = await fetchStyleSheet();
        const style = document.createElement("style");
        style.setAttribute("data-dsh-whale-wallpaper", "css");
        style.textContent = css;
        document.head.appendChild(style);
      } catch (error) {
        console.warn("[dsh-whale-wallpaper] 样式表加载失败,壁纸未生效:", error);
      }
      await whenBodyReady();
      buildLayers();
      apply();
      // 皮肤包清单在启动后单独拉一次：拿到后补进选择器并重新应用（当前皮肤若是包内皮肤即生效）
      fetchPacks().then(() => apply());
      // 主题在 <body> 的 data-ds-dark-theme 上切换;跟随主题时需要换图与换遮罩。
      try {
        new MutationObserver(apply).observe(document.body, {
          attributes: true,
          attributeFilter: ["data-ds-dark-theme", "class"],
        });
      } catch (error) {
        console.warn("[dsh-whale-wallpaper] 主题监听未挂上,切换明暗后需刷新页面:", error);
      }
      window.addEventListener(CHANGE_EVENT, apply);
      window.addEventListener("resize", queueSync);
      // 布局变化(侧栏展开/收起、右栏开关、面板换页)只靠 resize 抓不全,补一个低频同步;
      // 顺带在这里轮询 Agent 状态与「按时段」的昼夜切换。
      window.setInterval(() => {
        queueSync();
        const before = agentState;
        pollAgentState();
        applyMascotImage();
        if (before !== agentState) queueSync();
        if (read("theme", "auto") === "clock") {
          const theme = clockTheme();
          if (theme !== lastClockTheme) {
            lastClockTheme = theme;
            apply();
          }
        }
      }, 1500);
    }

    /* ---- 设置面板「皮肤」栏目 ---- */

    const ROW_STYLE = {
      alignItems: "center",
      borderBottom: "1px solid var(--dsw-alias-border-l2)",
      display: "flex",
      gap: "12px",
      justifyContent: "space-between",
      padding: "10px 0",
    };
    const CARD_STYLE = {
      background: "var(--dsw-alias-bg-module-platform, transparent)",
      border: "1px solid var(--dsw-alias-border-l2)",
      borderRadius: "14px",
      display: "flex",
      flexDirection: "column",
      gap: "2px",
      padding: "6px 14px",
      width: "100%",
    };
    const HINT_STYLE = {
      color: "var(--dsw-alias-label-secondary)",
      fontSize: "12px",
      lineHeight: "18px",
      padding: "4px 0 8px",
    };

    function Segmented({ options, value, onChange }) {
      return jsx("div", {
        style: {
          background: "var(--dsw-alias-interactive-bg-hover, transparent)",
          borderRadius: "10px",
          display: "flex",
          flexWrap: "wrap",
          gap: "4px",
          padding: "3px",
        },
        children: options.map(([key, label]) =>
          jsx("button", {
            key,
            type: "button",
            onClick: () => onChange(key),
            style: {
              background: key === value ? "var(--dsw-static-accent, #4d93f8)" : "transparent",
              border: "none",
              borderRadius: "8px",
              color: key === value ? "#fff" : "inherit",
              cursor: "pointer",
              fontSize: "12px",
              padding: "5px 10px",
            },
            children: label,
          }),
        ),
      });
    }

    function Switch({ on, onToggle }) {
      return jsx("button", {
        type: "button",
        role: "switch",
        "aria-checked": on,
        onClick: onToggle,
        style: {
          alignItems: "center",
          background: on ? "var(--dsw-static-accent, #4d93f8)" : "var(--dsw-alias-border-l3, #c9cdd6)",
          border: "none",
          borderRadius: "999px",
          cursor: "pointer",
          display: "flex",
          height: "24px",
          justifyContent: on ? "flex-end" : "flex-start",
          padding: "3px",
          width: "44px",
        },
        children: jsx("span", {
          style: {
            background: "#fff",
            borderRadius: "50%",
            boxShadow: "0 1px 3px rgb(0 0 0 / 25%)",
            height: "18px",
            width: "18px",
          },
        }),
      });
    }

    function Row({ label, children, last }) {
      return jsxs("div", {
        style: last ? { ...ROW_STYLE, borderBottom: "none" } : ROW_STYLE,
        children: [jsx("span", { children: label }), children],
      });
    }

    function StackedRow({ label, children }) {
      return jsxs("div", {
        style: { ...ROW_STYLE, alignItems: "flex-start", flexDirection: "column", gap: "8px" },
        children: [jsx("span", { children: label }), children],
      });
    }

    function SkinPicker({ value, onPick }) {
      return jsx("div", {
        style: { display: "flex", flexDirection: "column", gap: "8px", width: "100%" },
        children: skinIds().map((id) => {
          const skin = skinById(id);
          if (skin === null) return null;
          const selected = id === value;
          return jsx("button", {
            key: id,
            type: "button",
            onClick: () => onPick(id),
            style: {
              alignItems: "center",
              background: selected ? "var(--dsw-alias-interactive-bg-hover, transparent)" : "transparent",
              border: "1px solid " + (selected ? "var(--dsw-static-accent, #4d93f8)" : "var(--dsw-alias-border-l2)"),
              borderRadius: "12px",
              cursor: "pointer",
              display: "flex",
              gap: "10px",
              padding: "8px 10px",
              textAlign: "left",
              width: "100%",
            },
            children: [
              (() => {
                const thumb = skinThumb(skin);
                const boxStyle = {
                  alignItems: "center",
                  background: "var(--dsw-alias-bg-layer-2, transparent)",
                  border: "1px solid " + (selected ? "var(--dsw-static-accent, #4d93f8)" : "var(--dsw-alias-border-l3)"),
                  borderRadius: "8px",
                  color: "var(--dsw-alias-label-tertiary)",
                  display: "flex",
                  flex: "none",
                  fontSize: "11px",
                  height: "60px",
                  justifyContent: "center",
                  overflow: "hidden",
                  width: "96px",
                };
                if (thumb === null) return jsx("span", { style: boxStyle, children: "无缩略图" });
                return jsx("img", { src: thumb, alt: "", loading: "lazy", style: { ...boxStyle, objectFit: "cover" } });
              })(),
              jsxs("span", {
                style: { display: "flex", flexDirection: "column", gap: "2px", minWidth: 0 },
                children: [
                  jsxs("span", {
                    style: { alignItems: "center", display: "flex", fontSize: "13px", fontWeight: 600, gap: "6px" },
                    children: [
                      skin.name,
                      skin.builtin === true
                        ? null
                        : jsx("span", {
                            style: {
                              background: "var(--dsw-alias-bg-module-platform, transparent)",
                              border: "1px solid var(--dsw-alias-border-l3)",
                              borderRadius: "6px",
                              color: "var(--dsw-alias-label-secondary)",
                              fontSize: "10px",
                              fontWeight: 400,
                              padding: "1px 5px",
                            },
                            children: "皮肤包",
                          }),
                    ],
                  }),
                  jsx("span", {
                    style: { color: "var(--dsw-alias-label-secondary)", fontSize: "11px", lineHeight: "16px" },
                    children: skin.desc,
                  }),
                ],
              }),
            ],
          });
        }),
      });
    }

    /** 把导入的单个偏好值规范化；不合法返回 null（调用方跳过该项）。 */
    function normalizePref(key, value) {
      const text = String(value);
      switch (key) {
        case "enabled":
        case "decor":
        case "particles":
        case "mascotState":
          if (text === "1" || text === "0") return text;
          if (value === true) return "1";
          if (value === false) return "0";
          return null;
        case "skin":
          return SKINS[text] !== undefined ? text : null;
        case "pose":
          return POSES.some((entry) => entry[0] === text) ? text : null;
        case "scope":
          return text === "full" || text === "workspace" ? text : null;
        case "theme":
          return THEMES.some((entry) => entry[0] === text) ? text : null;
        case "mascot":
          return text === "left" || text === "right" || text === "none" ? text : null;
        case "mascotPose":
          return MASCOT_POSES.some((entry) => entry[0] === text) ? text : null;
        case "scrim": {
          const parsed = Number(value);
          return Number.isFinite(parsed) && parsed >= 0 && parsed <= 0.92 ? String(parsed) : null;
        }
        case "vignette": {
          const parsed = Number(value);
          return Number.isFinite(parsed) && parsed >= 0 && parsed <= 0.92 ? String(parsed) : null;
        }
        case "blur": {
          const parsed = Number(value);
          return Number.isFinite(parsed) && parsed >= 0 && parsed <= BLUR_MAX ? String(parsed) : null;
        }
        default:
          return null;
      }
    }

    /** 导出/导入皮肤设置：一段自包含 JSON，方便贴给别的机器。 */
    function ShareBlock({ onImported }) {
      const [text, setText] = React.useState("");
      const [status, setStatus] = React.useState("");

      const exportPrefs = () => {
        const prefs = {};
        for (const key of SHARE_KEYS) {
          const value = read(key, null);
          if (value !== null) prefs[key] = value;
        }
        const payload = JSON.stringify({ app: "dsh-whale-wallpaper", version: 1, prefs }, null, 2);
        setText(payload);
        setStatus("已导出当前设置");
        try {
          if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
            navigator.clipboard.writeText(payload).then(
              () => setStatus("已导出，并复制到剪贴板"),
              () => undefined,
            );
          }
        } catch (error) {
          /* 剪贴板不可用就只留在文本框里 */
        }
      };

      const copyText = () => {
        try {
          if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
            navigator.clipboard.writeText(text).then(() => setStatus("已复制"), () => setStatus("复制失败，请手动选中"));
          } else {
            setStatus("当前环境不允许写剪贴板，请手动选中复制");
          }
        } catch (error) {
          setStatus("复制失败，请手动选中");
        }
      };

      const importPrefs = () => {
        let parsed = null;
        try {
          parsed = JSON.parse(text);
        } catch (error) {
          setStatus("导入失败：JSON 解析错误");
          return;
        }
        const source = parsed && typeof parsed === "object" && parsed.prefs && typeof parsed.prefs === "object" ? parsed.prefs : parsed;
        if (source === null || typeof source !== "object") {
          setStatus("导入失败：不是有效的设置对象");
          return;
        }
        let applied = 0;
        let skipped = 0;
        for (const key of SHARE_KEYS) {
          const value = source[key];
          if (value === undefined || value === null) continue;
          const normalized = normalizePref(key, value);
          if (normalized === null) {
            skipped += 1;
            continue;
          }
          write(key, normalized);
          applied += 1;
        }
        onImported();
        setStatus("已导入 " + applied + " 项" + (skipped > 0 ? "，忽略 " + skipped + " 项无效值" : ""));
      };

      const buttonStyle = { cursor: "pointer", fontSize: "12px", padding: "5px 12px" };

      return jsxs("div", {
        style: { display: "flex", flexDirection: "column", gap: "8px", width: "100%" },
        children: [
          jsx("textarea", {
            value: text,
            onChange: (event) => setText(event.target.value),
            spellCheck: false,
            placeholder: "点「导出设置」得到一段 JSON，或把别人给的 JSON 粘进来后点「导入设置」",
            style: {
              background: "var(--dsw-alias-bg-layer-1, transparent)",
              border: "1px solid var(--dsw-alias-border-l2)",
              borderRadius: "10px",
              color: "var(--dsw-alias-label-primary)",
              fontFamily: "Consolas, monospace",
              fontSize: "11px",
              lineHeight: "16px",
              minHeight: "84px",
              padding: "8px 10px",
              resize: "vertical",
              width: "100%",
            },
          }),
          jsxs("div", {
            style: { alignItems: "center", display: "flex", flexWrap: "wrap", gap: "8px" },
            children: [
              jsx("button", { type: "button", onClick: exportPrefs, style: buttonStyle, children: "导出设置" }),
              jsx("button", { type: "button", onClick: copyText, style: buttonStyle, children: "复制" }),
              jsx("button", { type: "button", onClick: importPrefs, style: buttonStyle, children: "导入设置" }),
              jsx("span", {
                style: { color: "var(--dsw-alias-label-secondary)", fontSize: "11px" },
                children: status,
              }),
            ],
          }),
        ],
      });
    }

    function WallpaperPrefs() {
      const [on, setOn] = React.useState(enabled());
      const [skin, setSkin] = React.useState(read("skin", "atelier"));
      const [pose, setPose] = React.useState(currentPose());
      const [scope, setScope] = React.useState(currentScope());
      const [theme, setTheme] = React.useState(read("theme", "auto"));
      const [scrim, setScrim] = React.useState(scrimValue());
      const [vignette, setVignette] = React.useState(vignetteValue());
      const [blur, setBlur] = React.useState(blurValue());
      const [decor, setDecor] = React.useState(decorOn());
      const [mascot, setMascot] = React.useState(mascotCorner());
      const [mascotFace, setMascotFace] = React.useState(mascotPose());
      const [particles, setParticles] = React.useState(particlesOn());
      const [followState, setFollowState] = React.useState(mascotStateOn());

      const commit = (key, value) => {
        write(key, value);
        notify();
      };

      /** 从 localStorage 重新读回全部偏好（恢复默认、导入设置后用）。 */
      const refresh = () => {
        const skin = read("skin", "atelier");
        setOn(enabled());
        setSkin(skinById(skin) === null ? "atelier" : skin);
        setPose(currentPose());
        setScope(currentScope());
        setTheme(read("theme", "auto"));
        setScrim(scrimValue());
        setVignette(vignetteValue());
        setBlur(blurValue());
        setDecor(decorOn());
        setMascot(mascotCorner());
        setMascotFace(mascotPose());
        setParticles(particlesOn());
        setFollowState(mascotStateOn());
      };

      const reset = () => {
        ["skin", "pose", "scope", "theme", "scrim", "vignette", "blur", "decor", "mascot", "mascotPose", "particles", "mascotState", "enabled"].forEach(clear);
        refresh();
        notify();
      };

      return jsxs("div", {
        style: { display: "flex", flexDirection: "column", width: "100%" },
        children: [
          jsx("div", {
            style: HINT_STYLE,
            children: "皮肤包 = 壁纸 + 描边装饰 + 角落立绘,可整套切换;正文浮在遮罩之上,想更清楚就调高遮罩浓度。",
          }),
          jsxs("div", {
            style: CARD_STYLE,
            children: [
              jsx(Row, { label: "启用", children: jsx(Switch, { on, onToggle: () => {
                const next = !on;
                setOn(next);
                commit("enabled", next ? "1" : "0");
              } }) }),
              jsx(StackedRow, { label: "皮肤包", children: jsx(SkinPicker, { value: skin, onPick: (id) => {
                setSkin(id);
                write("skin", id);
                ["decor", "mascot", "mascotPose"].forEach(clear); // 跟随新皮肤的默认
                setDecor(decorOn());
                setMascot(mascotCorner());
                setMascotFace(mascotPose());
                notify();
              } }) }),
              jsx(StackedRow, { label: "壁纸立绘", children: jsx(Segmented, { options: POSES, value: pose, onChange: (key) => {
                setPose(key);
                commit("pose", key);
              } }) }),
              jsx(StackedRow, { label: "覆盖范围", children: jsx(Segmented, { options: SCOPES, value: scope, onChange: (key) => {
                setScope(key);
                commit("scope", key);
              } }) }),
              jsx(StackedRow, { label: "明暗", children: jsx(Segmented, { options: THEMES, value: theme, onChange: (key) => {
                setTheme(key);
                commit("theme", key);
              } }) }),
              jsx(Row, { label: "描边装饰", children: jsx(Switch, { on: decor, onToggle: () => {
                const next = !decor;
                setDecor(next);
                commit("decor", next ? "1" : "0");
              } }) }),
              jsx(StackedRow, { label: "角落立绘", children: jsx(Segmented, { options: MASCOT_SPOTS, value: mascot, onChange: (key) => {
                setMascot(key);
                commit("mascot", key);
              } }) }),
              jsx(StackedRow, { label: "角落立绘形象", children: jsx(Segmented, { options: MASCOT_POSES, value: mascotFace, onChange: (key) => {
                setMascotFace(key);
                commit("mascotPose", key);
              } }) }),
              jsx(Row, { label: "环境粒子", children: jsx(Switch, { on: particles, onToggle: () => {
                const next = !particles;
                setParticles(next);
                commit("particles", next ? "1" : "0");
              } }) }),
              jsx(Row, { label: "立绘跟随状态", children: jsx(Switch, { on: followState, onToggle: () => {
                const next = !followState;
                setFollowState(next);
                commit("mascotState", next ? "1" : "0");
              } }) }),
              jsxs("div", {
                style: ROW_STYLE,
                children: [
                  jsx("span", { children: "遮罩浓度" }),
                  jsxs("div", {
                    style: { alignItems: "center", display: "flex", gap: "8px" },
                    children: [
                      jsx("input", {
                        type: "range",
                        min: 0,
                        max: 92,
                        step: 2,
                        value: Math.round(scrim * 100),
                        onChange: (event) => {
                          const next = Number(event.target.value) / 100;
                          setScrim(next);
                          commit("scrim", next);
                        },
                      }),
                      jsx("span", {
                        style: { color: "var(--dsw-alias-label-secondary)", fontSize: "12px", minWidth: "34px", textAlign: "right" },
                        children: Math.round(scrim * 100) + "%",
                      }),
                    ],
                  }),
                ],
              }),
              jsxs("div", {
                style: ROW_STYLE,
                children: [
                  jsx("span", { children: "暗角" }),
                  jsxs("div", {
                    style: { alignItems: "center", display: "flex", gap: "8px" },
                    children: [
                      jsx("input", {
                        type: "range",
                        min: 0,
                        max: 92,
                        step: 2,
                        value: Math.round(vignette * 100),
                        onChange: (event) => {
                          const next = Number(event.target.value) / 100;
                          setVignette(next);
                          commit("vignette", next);
                        },
                      }),
                      jsx("span", {
                        style: { color: "var(--dsw-alias-label-secondary)", fontSize: "12px", minWidth: "34px", textAlign: "right" },
                        children: Math.round(vignette * 100) + "%",
                      }),
                    ],
                  }),
                ],
              }),
              jsxs("div", {
                style: ROW_STYLE,
                children: [
                  jsx("span", { children: "景深模糊" }),
                  jsxs("div", {
                    style: { alignItems: "center", display: "flex", gap: "8px" },
                    children: [
                      jsx("input", {
                        type: "range",
                        min: 0,
                        max: BLUR_MAX,
                        step: 1,
                        value: Math.round(blur),
                        onChange: (event) => {
                          const next = Number(event.target.value);
                          setBlur(next);
                          commit("blur", next);
                        },
                      }),
                      jsx("span", {
                        style: { color: "var(--dsw-alias-label-secondary)", fontSize: "12px", minWidth: "34px", textAlign: "right" },
                        children: Math.round(blur) + "px",
                      }),
                    ],
                  }),
                ],
              }),
              jsx(StackedRow, { label: "导出 / 导入", children: jsx(ShareBlock, { onImported: refresh }) }),
              jsx(Row, { label: "恢复默认", last: true, children: jsx("button", { type: "button", onClick: reset, children: "重置皮肤设置" }) }),
            ],
          }),
        ],
      });
    }

    function WallpaperSection(props) {
      const renderSlot = props && typeof props.renderSlot === "function" ? props.renderSlot : null;
      if (renderSlot !== null) {
        try {
          const rendered = renderSlot("settings.wallpaper.item", {});
          if (rendered !== null && rendered !== undefined) {
            return jsx("div", { style: { display: "flex", flexDirection: "column", width: "100%" }, children: rendered });
          }
        } catch (error) {
          console.warn("[dsh-whale-wallpaper] settings.wallpaper.item 渲染失败,回落到内置面板", error);
        }
      }
      return jsx(WallpaperPrefs, {});
    }

    function registerSettings(ctx) {
      const slots = ctx.get("slots");
      if (slots === undefined) {
        console.warn("[dsh-whale-wallpaper] slots 服务不可用,跳过设置面板注册(皮肤本体不受影响)");
        return;
      }
      slots.inject("settings.section", () =>
        slots.register(
          {
            name: "settings.section",
            id: "wallpaper",
            order: 7,
            label: "皮肤",
            children: { "settings.wallpaper.item": { kind: "list", scope: "root" } },
          },
          (props) => jsx(WallpaperSection, { ...props, ctx }),
        ),
      );
      slots.inject("settings.wallpaper.item", () =>
        slots.register({ name: "settings.wallpaper.item", id: "wallpaper-prefs", order: 0 }, () => jsx(WallpaperPrefs, {})),
      );
    }

    function apply$1(ctx) {
      /* 设置面板是增强项:注册失败也要保证壁纸本体正常出现。 */
      try {
        registerSettings(ctx);
      } catch (error) {
        console.warn("[dsh-whale-wallpaper] 设置面板注册失败,皮肤本体不受影响", error);
      }
    }

    exports.apply = apply$1;
    exports.inject = ["slots"];

    /* 客户端模块系统是惰性 CJS:factory 物化即执行副作用,
       因此样式注入与图层搭建都放在 factory 体内,不依赖 apply 的时序。 */
    boot();
    return module.exports;
  },
});
