/* 服务端版（FastAPI）」专用的登录层：登录浮层 + 令牌注入。
 *
 * 只在服务端渲染 index.html 时被注入（见 backend/app/main.py 的 _mount_web），
 * 桌面版 webserver.py 不会加载这个文件，所以桌面版的「单人本机」体验完全不受影响。
 *
 * 做两件事：
 *   1. 包一层 fetch：凡是以 /api/ 开头的请求自动带上 Authorization: Bearer <token>；
 *      一旦收到 401，就清掉本地令牌并把登录浮层叫出来。
 *   2. 登录浮层：用户名 + 密码，登录失败且是「用户不存在」时可以直接注册
 *      （服务端配置了邀请码就要求填邀请码）。
 */

(function () {
  "use strict";

  var TOKEN_KEY = "pyquiz.token";
  var USER_KEY = "pyquiz.username";
  var nativeFetch = window.fetch ? window.fetch.bind(window) : null;

  var overlay = null;
  var errorEl = null;
  var busy = false;
  var prompting = false;

  /* ---------------------------------------------------------------- 存储 */
  function read(key) {
    try { return localStorage.getItem(key) || ""; } catch (e) { return ""; }
  }

  function write(key, value) {
    try { localStorage.setItem(key, value); } catch (e) { /* 隐私模式忽略 */ }
  }

  function drop(key) {
    try { localStorage.removeItem(key); } catch (e) { /* ignore */ }
  }

  function token() { return read(TOKEN_KEY); }

  function forget() {
    drop(TOKEN_KEY);
    drop(USER_KEY);
    paintChip();
  }

  /* ---------------------------------------------------------------- 请求 */
  function post(path, body) {
    return nativeFetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (resp) {
      return resp.json().catch(function () { return null; }).then(function (data) {
        return { status: resp.status, data: data };
      });
    });
  }

  function textOf(data) {
    if (!data) { return "服务端没有响应"; }
    var err = data.error;
    if (typeof err === "string") { return err; }
    if (err && typeof err.message === "string") { return err.message; }
    if (err && typeof err.code === "string") { return err.code; }
    return "出错了（HTTP " + (data.status || "?") + "）";
  }

  /* ---------------------------------------------------------------- 令牌注入 */
  if (nativeFetch) {
    window.fetch = function (input, init) {
      var url = typeof input === "string" ? input : (input && input.url) || "";
      var isApi = url.indexOf("/api/") === 0;

      if (isApi) {
        init = init || {};
        var headers = new Headers(init.headers || {});
        var t = token();
        if (t) { headers.set("Authorization", "Bearer " + t); }
        init.headers = headers;
      }

      return nativeFetch(input, init).then(function (resp) {
        if (isApi && resp.status === 401) {
          forget();
          show("登录已过期，请重新登录");
        }
        return resp;
      });
    };
  }

  /* ---------------------------------------------------------------- 浮层 */
  function style(el, css) {
    for (var key in css) {
      if (Object.prototype.hasOwnProperty.call(css, key)) { el.style[key] = css[key]; }
    }
    return el;
  }

  function build() {
    if (overlay) { return; }

    overlay = style(document.createElement("div"), {
      position: "fixed", inset: "0", zIndex: "9999",
      display: "none", alignItems: "center", justifyContent: "center",
      background: "rgba(8, 10, 14, .72)", backdropFilter: "blur(3px)"
    });

    var card = style(document.createElement("div"), {
      width: "min(92vw, 360px)", padding: "26px 24px 22px",
      borderRadius: "14px", background: "#15181f",
      border: "1px solid #2a2f3a", color: "#e6e9ef",
      boxShadow: "0 24px 64px rgba(0,0,0,.5)",
      font: "14px/1.6 -apple-system, 'Segoe UI', 'Microsoft YaHei', sans-serif"
    });

    var title = document.createElement("div");
    title.textContent = "登录 Python 刷题系统";
    style(title, { fontSize: "17px", fontWeight: "600", marginBottom: "4px" });

    var sub = document.createElement("div");
    sub.textContent = "进度按账号保存，换设备用同一个账号即可继续。";
    style(sub, { fontSize: "12px", color: "#8b93a3", marginBottom: "18px" });

    function field(label, type, placeholder, id) {
      var wrap = style(document.createElement("div"), { marginBottom: "12px" });
      var lab = document.createElement("div");
      lab.textContent = label;
      style(lab, { fontSize: "12px", color: "#8b93a3", marginBottom: "6px" });
      var input = document.createElement("input");
      input.type = type;
      input.placeholder = placeholder;
      input.id = id;
      input.autocomplete = type === "password" ? "current-password" : "username";
      style(input, {
        width: "100%", boxSizing: "border-box", padding: "10px 12px",
        borderRadius: "9px", border: "1px solid #2d3340", background: "#0f1218",
        color: "#e6e9ef", fontSize: "14px", outline: "none"
      });
      wrap.appendChild(lab);
      wrap.appendChild(input);
      card.appendChild(wrap);
      return input;
    }

    var userInput = field("用户名", "text", "字母/数字/下划线，3–32 位", "pyquiz-user");
    var passInput = field("密码", "password", "至少 8 位", "pyquiz-pass");

    var codeWrap = style(document.createElement("div"), { marginBottom: "12px" });
    var codeLab = document.createElement("div");
    codeLab.textContent = "邀请码（如果管理员设置了才需要填）";
    style(codeLab, { fontSize: "12px", color: "#8b93a3", marginBottom: "6px" });
    var codeInput = document.createElement("input");
    codeInput.type = "text";
    codeInput.placeholder = "没有就留空";
    style(codeInput, {
      width: "100%", boxSizing: "border-box", padding: "10px 12px",
      borderRadius: "9px", border: "1px solid #2d3340", background: "#0f1218",
      color: "#e6e9ef", fontSize: "14px", outline: "none"
    });
    codeWrap.appendChild(codeLab);
    codeWrap.appendChild(codeInput);
    card.appendChild(codeWrap);

    errorEl = style(document.createElement("div"), {
      minHeight: "20px", margin: "4px 0 12px", fontSize: "12px", color: "#ff6b6b"
    });
    card.appendChild(errorEl);

    var row = style(document.createElement("div"), { display: "flex", gap: "10px" });

    function button(text, primary) {
      var btn = document.createElement("button");
      btn.textContent = text;
      style(btn, {
        flex: "1", padding: "10px 0", borderRadius: "9px", cursor: "pointer",
        fontSize: "14px", fontWeight: "600",
        border: primary ? "1px solid #2f6fed" : "1px solid #2d3340",
        background: primary ? "#2f6fed" : "transparent",
        color: primary ? "#fff" : "#c9cfdb"
      });
      return btn;
    }

    var loginBtn = button("登录", true);
    var registerBtn = button("注册并登录", false);
    row.appendChild(loginBtn);
    row.appendChild(registerBtn);
    card.appendChild(row);

    var tip = document.createElement("div");
    tip.textContent = "首次使用点「注册并登录」；忘记密码目前只能找管理员重置。";
    style(tip, { marginTop: "14px", fontSize: "11px", color: "#6c7484", lineHeight: "1.5" });
    card.appendChild(tip);

    overlay.appendChild(card);
    document.body.appendChild(overlay);

    function submit(register) {
      if (busy) { return; }
      var name = (userInput.value || "").trim();
      var pass = passInput.value || "";
      if (!name || !pass) { return setError("用户名和密码都要填"); }
      if (register && pass.length < 8) { return setError("密码至少 8 位"); }

      var body = { username: name, password: pass };
      if (register) {
        var code = (codeInput.value || "").trim();
        if (code) { body.code = code; }
      }

      busy = true;
      setError("");
      loginBtn.textContent = "请稍候…";
      var path = register ? "/api/v1/auth/register" : "/api/v1/auth/login";

      post(path, body).then(function (res) {
        var data = res.data;
        if (res.status < 300 && data && data.ok && data.data && data.data.token) {
          write(TOKEN_KEY, data.data.token);
          write(USER_KEY, (data.data.user && data.data.user.username) || name);
          location.reload();
          return;
        }
        throw new Error(textOf(data));
      }).catch(function (err) {
        busy = false;
        loginBtn.textContent = "登录";
        setError(err && err.message ? err.message : "请求失败");
      });
    }

    loginBtn.onclick = function () { submit(false); };
    registerBtn.onclick = function () { submit(true); };
    [userInput, passInput, codeInput].forEach(function (input) {
      input.onkeydown = function (e) {
        if (e.key === "Enter") { submit(false); }
      };
    });
  }

  function setError(text) {
    if (errorEl) { errorEl.textContent = text || ""; }
  }

  function show(hint) {
    if (prompting) { if (hint) { setError(hint); } return; }
    prompting = true;
    build();
    overlay.style.display = "flex";
    setError(hint || "");
    setTimeout(function () {
      var input = document.getElementById("pyquiz-user");
      if (input) { input.focus(); }
    }, 30);
  }

  /* ---------------------------------------------------------------- 用户角标 */
  var chip = null;

  function paintChip() {
    var name = read(USER_KEY);
    if (!name) {
      if (chip) { chip.style.display = "none"; }
      return;
    }
    if (!chip) {
      chip = style(document.createElement("div"), {
        position: "fixed", right: "14px", bottom: "14px", zIndex: "9998",
        display: "flex", alignItems: "center", gap: "8px",
        padding: "6px 10px", borderRadius: "999px",
        background: "rgba(21,24,31,.92)", border: "1px solid #2a2f3a",
        color: "#aeb6c5", font: "12px/1 -apple-system, 'Segoe UI', sans-serif"
      });
      document.body.appendChild(chip);
    }
    chip.style.display = "flex";
    chip.innerHTML = "";

    var label = document.createElement("span");
    label.textContent = "👤 " + name;
    chip.appendChild(label);

    var out = document.createElement("span");
    out.textContent = "退出";
    out.style.cursor = "pointer";
    out.style.color = "#6f8fe8";
    out.onclick = function () {
      forget();
      location.reload();
    };
    chip.appendChild(out);
  }

  /* ---------------------------------------------------------------- 启动 */
  function boot() {
    paintChip();
    if (!token()) {
      show("");
      return;
    }
    nativeFetch("/api/v1/auth/me", {
      headers: { Authorization: "Bearer " + token() }
    }).then(function (resp) {
      if (resp.status === 401) {
        forget();
        show("登录已过期，请重新登录");
      }
    }).catch(function () { /* 离线先不打扰，页面自己会报错 */ });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
