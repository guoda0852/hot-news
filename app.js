/* 热榜聚合前端：读取 data/meta.json + data/<id>.json 本地渲染 */
(function () {
  "use strict";
  var tabsEl = document.getElementById("tabs");
  var listEl = document.getElementById("news-list");
  var emptyEl = document.getElementById("empty");
  var filterEl = document.getElementById("filter");
  var timeEl = document.getElementById("update-time");

  var cache = {};      // id -> payload
  var currentId = null;
  var currentItems = [];

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function renderList() {
    var kw = filterEl.value.trim().toLowerCase();
    var html = "";
    var shown = 0;
    currentItems.forEach(function (it, i) {
      if (kw && it.title.toLowerCase().indexOf(kw) === -1) return;
      shown++;
      html += '<li><span class="rank">' + (i + 1) + "</span>" +
        '<a href="' + esc(it.url) + '" target="_blank" rel="noopener">' + esc(it.title) + "</a>" +
        (it.hot ? '<span class="hot">' + esc(it.hot) + "</span>" : "") + "</li>";
    });
    listEl.innerHTML = html;
    emptyEl.classList.toggle("hidden", shown > 0);
  }

  function select(id) {
    currentId = id;
    Array.prototype.forEach.call(tabsEl.children, function (b) {
      b.classList.toggle("active", b.dataset.id === id);
    });
    if (cache[id]) {
      currentItems = cache[id].items;
      timeEl.textContent = cache[id].updated_at;
      renderList();
      return;
    }
    listEl.innerHTML = '<li><span class="rank">…</span><a>加载中</a></li>';
    fetch("data/" + id + ".json")
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) {
        cache[id] = d;
        if (id === currentId) {
          currentItems = d.items;
          timeEl.textContent = d.updated_at;
          renderList();
        }
      })
      .catch(function () {
        listEl.innerHTML = '<li><span class="rank">!</span><a>该榜单暂未抓取到数据，稍后再试</a></li>';
      });
  }

  filterEl.addEventListener("input", renderList);

  fetch("data/meta.json")
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (meta) {
      meta.sources.forEach(function (s) {
        var b = document.createElement("button");
        b.className = "tab";
        b.dataset.id = s.id;
        b.style.setProperty("--c", s.color || "#999");
        b.innerHTML = '<span class="dot"></span>' + esc(s.name);
        b.addEventListener("click", function () { select(s.id); });
        tabsEl.appendChild(b);
      });
      if (meta.sources.length) select(meta.sources[0].id);
      else listEl.innerHTML = "<li>暂无榜单数据</li>";
    })
    .catch(function () {
      listEl.innerHTML = "<li>数据加载失败，请检查网络后刷新</li>";
    });
})();
