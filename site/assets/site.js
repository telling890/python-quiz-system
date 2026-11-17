/* ==========================================================================
   介绍页交互：进度条 / 导航态 / 入场动画 / 截图巡览 / 灯箱 / 复制命令
   全部原生 JS，无依赖；JS 出错也不影响静态内容可读。
   ========================================================================== */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ------------------------------------------------------------ 顶部进度条 */
  var bar = document.getElementById("progress-bar");
  var nav = document.getElementById("nav");

  function onScroll() {
    var h = document.documentElement;
    var max = h.scrollHeight - h.clientHeight;
    var p = max > 0 ? h.scrollTop / max : 0;
    if (bar) bar.style.width = (p * 100).toFixed(2) + "%";
    if (nav) nav.classList.toggle("is-scrolled", h.scrollTop > 12);
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  /* ------------------------------------------------------------ 入场动画 */
  var revealEls = Array.prototype.slice.call(document.querySelectorAll(".reveal"));
  if (reduceMotion || !("IntersectionObserver" in window)) {
    revealEls.forEach(function (el) { el.classList.add("in"); });
  } else {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("in");
          io.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.12 }
    );
    revealEls.forEach(function (el) { io.observe(el); });
  }

  /* ------------------------------------------------------------ 截图数据 */
  var SHOTS = [
    {
      file: "dashboard",
      title: "概览",
      desc: "四张统计卡、接着上次继续、章节进度与最近提交，点章节直接从该章第一道未做的题开始。",
      w: 1440, h: 900
    },
    {
      file: "hero-workspace",
      title: "刷题工作台",
      desc: "左边选题、中间题面与测试用例、右边编辑器；判题结果按用例逐条展开，首个不一致的行标红。",
      w: 1440, h: 900
    },
    {
      file: "trace",
      title: "单步执行",
      desc: "把代码逐行走一遍再回放：当前行高亮、变量快照随步更新、已输出内容同步累积，时间轴可拖。",
      w: 1440, h: 900
    },
    {
      file: "book",
      title: "题本",
      desc: "错题本、收藏、没通过三张清单，一键跳题继续做，通过后自动移出错题本，还能导出成绩 CSV。",
      w: 1440, h: 900
    },
    {
      file: "free",
      title: "自由编程",
      desc: "没有题目和用例的空白草稿：stdin、运行结果、草稿自动保存与代码片段，浅色主题下同样顺手。",
      w: 1440, h: 900
    },
    {
      file: "stats",
      title: "学习统计",
      desc: "覆盖率环形图、章节与难度掌握度、7 天提交趋势，以及近半年的学习热力图（连续打卡与活跃天数）。",
      w: 1440, h: 1000
    },
    {
      file: "exam-report",
      title: "交卷报告",
      desc: "模拟组卷交卷后给出得分、逐题明细，以及按考点分组的薄弱点，可以直接跳到对应题目补练。",
      w: 1440, h: 1000
    },
    {
      file: "light",
      title: "浅色模式",
      desc: "外观默认跟随系统 prefers-color-scheme，侧栏底部可手动固定「跟随系统 / 浅色 / 深色」，首帧就应用、不闪白。",
      w: 1440, h: 900
    },
    {
      file: "mobile",
      title: "手机竖屏",
      desc: "侧栏变抽屉、底部导航，手机上也能判题、看执行过程；进度存在本机浏览器里。",
      w: 390, h: 844
    },
    {
      file: "desktop",
      title: "Windows 桌面版",
      desc: "PyInstaller --onedir 打包，解压双击即用；进度默认存在程序旁边的 data\\state.json，拷走整个文件夹就带走了。",
      w: 1600, h: 1043
    }
  ].map(function (s) {
    s.src = "assets/img/" + s.file + ".webp";
    return s;
  });

  var stageImg = document.getElementById("stage-img");
  var stageTitle = document.getElementById("stage-title");
  var stageDesc = document.getElementById("stage-desc");
  var stageCount = document.getElementById("stage-count");
  var stageOpen = document.getElementById("stage-open");
  var rail = document.getElementById("rail");
  var index = 0;

  function pad(n) { return n < 10 ? "0" + n : String(n); }

  function render() {
    var s = SHOTS[index];
    if (!s) return;
    if (stageImg) {
      stageImg.src = s.src;
      stageImg.alt = "界面截图：" + s.title;
      stageImg.width = s.w;
      stageImg.height = s.h;
    }
    if (stageTitle) stageTitle.textContent = s.title;
    if (stageDesc) stageDesc.textContent = s.desc;
    if (stageCount) stageCount.textContent = index + 1 + " / " + SHOTS.length;
    if (rail) {
      Array.prototype.forEach.call(rail.querySelectorAll(".thumb"), function (btn, i) {
        var active = i === index;
        btn.classList.toggle("is-active", active);
        btn.setAttribute("aria-selected", active ? "true" : "false");
        if (active && btn.scrollIntoView) {
          btn.scrollIntoView({ block: "nearest", inline: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
        }
      });
    }
    if (lbImg && !lightbox.classList.contains("is-hidden")) syncLightbox();
  }

  function go(delta) {
    index = (index + delta + SHOTS.length) % SHOTS.length;
    render();
  }

  /* 缩略图 */
  if (rail) {
    SHOTS.forEach(function (s, i) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "thumb";
      btn.setAttribute("role", "tab");
      btn.setAttribute("aria-label", s.title);

      var img = document.createElement("img");
      img.src = s.src;
      img.alt = "";
      img.loading = "lazy";
      img.width = 132;
      img.height = 83;

      var label = document.createElement("span");
      label.textContent = s.title;

      btn.appendChild(img);
      btn.appendChild(label);
      btn.addEventListener("click", function () {
        index = i;
        render();
      });
      rail.appendChild(btn);
    });
  }

  var prevBtn = document.getElementById("prev");
  var nextBtn = document.getElementById("next");
  if (prevBtn) prevBtn.addEventListener("click", function () { go(-1); });
  if (nextBtn) nextBtn.addEventListener("click", function () { go(1); });

  /* ------------------------------------------------------------ 灯箱 */
  var lightbox = document.getElementById("lightbox");
  var lbImg = document.getElementById("lb-img");
  var lbCap = document.getElementById("lb-cap");
  var lbClose = document.getElementById("lb-close");
  var lbPrev = document.getElementById("lb-prev");
  var lbNext = document.getElementById("lb-next");
  var lastFocus = null;

  function syncLightbox() {
    var s = SHOTS[index];
    if (!s) return;
    lbImg.src = s.src;
    lbImg.alt = "界面截图：" + s.title;
    lbCap.textContent = s.title + " · " + (index + 1) + " / " + SHOTS.length + " · " + s.desc;
    lbImg.width = s.w;
    lbImg.height = s.h;
  }

  function openLightbox() {
    if (!lightbox) return;
    lastFocus = document.activeElement;
    lightbox.hidden = false;
    lightbox.classList.remove("is-hidden");
    syncLightbox();
    document.body.style.overflow = "hidden";
    if (lbClose) lbClose.focus();
  }

  function closeLightbox() {
    if (!lightbox) return;
    lightbox.hidden = true;
    lightbox.classList.add("is-hidden");
    document.body.style.overflow = "";
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  if (stageOpen) stageOpen.addEventListener("click", openLightbox);
  if (lbClose) lbClose.addEventListener("click", closeLightbox);
  if (lbPrev && lbNext) {
    lbPrev.addEventListener("click", function (e) { e.stopPropagation(); go(-1); });
    lbNext.addEventListener("click", function (e) { e.stopPropagation(); go(1); });
  }
  if (lightbox) {
    lightbox.addEventListener("click", function (e) {
      if (e.target === lightbox) closeLightbox();
    });
  }

  document.addEventListener("keydown", function (e) {
    var open = lightbox && !lightbox.hidden;
    if (e.key === "Escape" && open) { closeLightbox(); return; }
    if (e.key === "ArrowLeft") { if (open || isGalleryVisible()) { go(-1); } return; }
    if (e.key === "ArrowRight") { if (open || isGalleryVisible()) { go(1); } return; }
  });

  function isGalleryVisible() {
    if (!stageImg) return false;
    var r = stageImg.getBoundingClientRect();
    return r.top < window.innerHeight && r.bottom > 0;
  }

  /* ------------------------------------------------------------ 复制命令 */
  Array.prototype.forEach.call(document.querySelectorAll(".code"), function (block) {
    var btn = block.querySelector(".copy");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var codeEl = block.querySelector("code");
      var text = codeEl ? codeEl.textContent : "";
      var done = function () {
        btn.classList.add("is-done");
        btn.textContent = "已复制";
        window.setTimeout(function () {
          btn.classList.remove("is-done");
          btn.textContent = "复制";
        }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, fallback);
      } else {
        fallback();
      }
      function fallback() {
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand("copy"); done(); } catch (err) { btn.textContent = "复制失败"; }
        document.body.removeChild(ta);
      }
    });
  });

  /* ------------------------------------------------------------ 其它 */
  var year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());

  /* 首次渲染（放在最后，保证 SHOTS 与 DOM 都就绪） */
  render();
  document.body.classList.add("is-ready");
})();
