/* mindmap.js — 自绘 canvas 分层 DAG 图：按跳数分列（左→右），同列垂直排列，
   支持共享节点多入边（图结构），局部折叠（隐藏该节点全部后代），拖拽/缩放/点击编辑。 */
'use strict';

var ST_COLORS = { '-1': '#dc2626', '0': '#9ca3af', '1': '#3b82f6', '2': '#3b82f6', '10': '#f59e0b', '11': '#16a34a', 'null': '#6b7280' };
var ST_TEXT = { '-1': '作废重做', '0': '待处理', '1': '已完成', '2': '图片完成', '10': '待审', '11': '批准' };
var FONT = '12px -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif';

function Mindmap(container, data, onNodeClick) {
  this.container = container;
  this.onNodeClick = onNodeClick || function () {};
  this.canvas = document.createElement('canvas');
  this.canvas.style.width = '100%'; this.canvas.style.height = '100%';
  this.canvas.style.display = 'block';
  container.appendChild(this.canvas);
  this.ctx = this.canvas.getContext('2d');
  this.collapsed = {};
  this.scale = 1; this.tx = 40; this.ty = 40;
  this.data = data;
  this.buildGraph();
  this.bindEvents();
  var self = this;
  window.addEventListener('resize', function () { self.resize(); });
  container._mindmap = this;
  this.resize();
}

Mindmap.prototype.buildGraph = function () {
  var d = this.data;
  this.nodeMap = {}; this.children = {}; this.roots = [];
  d.nodes.forEach(function (n) { this.nodeMap[n.id] = n; this.children[n.id] = []; }, this);
  d.links.forEach(function (l) {
    if (this.nodeMap[l.source] && this.nodeMap[l.target]) this.children[l.source].push(l.target);
  }, this);
  var hasParent = {};
  Object.keys(this.children).forEach(function (pid) {
    this.children[pid].forEach(function (cid) { hasParent[cid] = true; }, this);
  }, this);
  d.nodes.forEach(function (n) { if (!hasParent[n.id]) this.roots.push(n.id); }, this);
};

Mindmap.prototype.visibleSet = function () {
  // 从 roots 出发可达集；collapsed 节点的后代不可达（collapsed 节点本身可见）
  var vis = {}, q = this.roots.slice();
  while (q.length) {
    var id = q.shift();
    if (vis[id]) continue;
    vis[id] = true;
    if (this.collapsed[id]) continue;
    (this.children[id] || []).forEach(function (k) { q.push(k); });
  }
  return vis;
};

Mindmap.prototype.descendantCount = function (id) {
  var vis = this.visibleSet(), n = 0, q = (this.children[id] || []).slice(), seen = {};
  while (q.length) {
    var x = q.shift();
    if (seen[x] || !vis[x]) continue;
    seen[x] = true; n++;
    (this.children[x] || []).forEach(function (k) { q.push(k); });
  }
  return n;
};

Mindmap.prototype.layout = function () {
  var GAP_X = 90, GAP_Y = 16, NODE_H = 30;
  var self = this;
  var vis = this.visibleSet();

  // ── 排列维度：主链推导（业务层级，非图跳数）──
  // rank = 主链前驱 rank+1（主链前驱 = 深度更浅者；并列取 label 优先级）；
  // 折叠节点的后代不占列。共享节点排在「最深主链」决定的列，但折叠该链后
  // 自动落到剩余主链的列（重新按当前可见边推导，无残留）。
  var RANK_ORDER = ['Character', 'Location', 'Event', 'Choice',
    'AppearanceStyle', 'LanguageStyle', 'CostumeStyle', 'VoiceDesign', 'Info',
    'Scene', 'DesignSheet', 'SecOutline', 'SecScript',
    'IllusDesign', 'SceneLayer', 'BgmTrack',
    'StandingIllustration', 'LineAudio'];
  var labelPri = {};
  RANK_ORDER.forEach(function (l, i) { labelPri[l] = i; });

  // 可见父集合（折叠父的边不存在）
  var visParents = {};
  Object.keys(vis).forEach(function (cid) { visParents[cid] = []; });
  Object.keys(vis).forEach(function (pid) {
    if (self.collapsed[pid]) return;
    (self.children[pid] || []).forEach(function (cid) {
      if (vis[cid]) visParents[cid].push(pid);
    });
  });

  // rank：从根 BFS，节点 rank = 主父 rank+1，主父 = 父中 rank 最大者
  // （并列时 label 优先级高者为「更深链」，保证共享节点贴生产链）
  var rank = {};
  this.roots.forEach(function (r) { rank[r] = 0; });
  var queue = this.roots.slice();
  var guard = 0;
  // 迭代松弛至稳定（DAG）
  var changed = true;
  while (changed && guard++ < 200) {
    changed = false;
    queue = Object.keys(vis);
    queue.forEach(function (cid) {
      var ps = visParents[cid];
      if (!ps.length) return;
      var best = null;
      ps.forEach(function (p) {
        if (rank[p] === undefined) return;
        if (best === null) { best = p; return; }
        if (rank[p] > rank[best]) best = p;                       // 更深链优先
        else if (rank[p] === rank[best] && (labelPri[self.nodeMap[p].label] || 99) > (labelPri[self.nodeMap[best].label] || 99)) best = p;
      });
      if (best !== null) {
        var nr = rank[best] + 1;
        if (rank[cid] !== nr) { rank[cid] = nr; changed = true; }
      }
    });
  }

  // BFS 序（层内排序用）
  var order = [], seen = {}, q = this.roots.slice();
  while (q.length) {
    var id = q.shift();
    if (seen[id] || !vis[id]) continue;
    seen[id] = true; order.push(id);
    if (this.collapsed[id]) continue;
    (this.children[id] || []).forEach(function (k) { q.push(k); });
  }

  // 度量
  this.ctx.font = FONT;
  var widths = {};
  order.forEach(function (id) {
    var n = self.nodeMap[id];
    var label = n.depth === 0 ? '★ ' : '';
    var text = label + String(n.name || n.id);
    var w = Math.min(220, this.ctx.measureText(text).width + 30);
    if (self.collapsed[id] && self.descendantCount(id) > 0) w += 42;
    widths[id] = w;
  }, this);

  // 每列宽度 = 列内最宽盒；列 x 累进
  var cols = {};
  order.forEach(function (id) {
    var lv = rank[id] || 0;
    (cols[lv] = cols[lv] || []).push(id);
  });
  var colX = {}, x = 40;
  var colIdx = {}, colLabel = {};
  Object.keys(cols).map(Number).sort(function (a, b) { return a - b; }).forEach(function (lv, i) {
    var maxW = 0;
    cols[lv].forEach(function (id) { maxW = Math.max(maxW, widths[id]); });
    colX[lv] = x;
    colIdx[x] = i + 1;
    // 列语义名 = 列内最小 label 优先级（主导类型）
    var dom = null;
    cols[lv].forEach(function (id) {
      var pri = labelPri[self.nodeMap[id].label] || 99;
      if (dom === null || pri < dom.pri) dom = { pri: pri, label: self.nodeMap[id].label };
    });
    colLabel[x] = dom ? dom.label : '';
    x += maxW + GAP_X;
  });
  this._colIndex = colIdx;
  this._colLabel = colLabel;

  // 盒位：列内按 BFS 序垂直叠放
  this.boxes = {};
  var yCur = {};
  order.forEach(function (id) {
    var lv = rank[id] || 0;
    var y = yCur[lv] || 40;
    this.boxes[id] = { id: id, x: colX[lv], y: y, w: widths[id], h: NODE_H, n: this.nodeMap[id] };
    yCur[lv] = y + NODE_H + GAP_Y;
  }, this);
};

Mindmap.prototype.visibleEdges = function () {
  var vis = this.visibleSet(), out = [], self = this;
  Object.keys(vis).forEach(function (pid) {
    if (self.collapsed[pid]) return;
    (self.children[pid] || []).forEach(function (cid) {
      if (vis[cid]) out.push({ s: pid, t: cid });
    });
  });
  return out;
};

Mindmap.prototype.resize = function () {
  var dpr = window.devicePixelRatio || 1;
  var w = this.container.clientWidth, h = this.container.clientHeight;
  this.canvas.width = w * dpr; this.canvas.height = h * dpr;
  this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  this.layout();
  var xs = [], ys = [];
  Object.values(this.boxes).forEach(function (b) { xs.push(b.x + b.w); ys.push(b.y + b.h); });
  if (xs.length) {
    var maxX = Math.max.apply(null, xs), maxY = Math.max.apply(null, ys);
    var pad = 40;
    this.scale = Math.min((w - pad * 2) / maxX, (h - pad * 2) / maxY, 1.2);
    this.scale = Math.max(this.scale, 0.12);
    this.tx = Math.max(20, (w - maxX * this.scale) / 2);
    this.ty = Math.max(20, (h - maxY * this.scale) / 2);
  }
  this.draw();
};

Mindmap.prototype.draw = function () {
  var ctx = this.ctx, self = this;
  var w = this.container.clientWidth, h = this.container.clientHeight;
  ctx.save();
  ctx.clearRect(0, 0, w, h);
  ctx.translate(this.tx, this.ty);
  ctx.scale(this.scale, this.scale);
  ctx.font = FONT;

  // 列背景（浅色分隔，体现跳数分层）
  var cols = {};
  Object.values(this.boxes).forEach(function (b) {
    var k = b.x;
    (cols[k] = cols[k] || []).push(b);
  });
  Object.keys(cols).map(Number).forEach(function (k, i) {
    var bs = cols[k];
    var maxY = Math.max.apply(null, bs.map(function (b) { return b.y + b.h; }));
    var minY = Math.min.apply(null, bs.map(function (b) { return b.y; }));
    var maxW = Math.max.apply(null, bs.map(function (b) { return b.w; }));
    ctx.fillStyle = i % 2 ? 'rgba(148,163,184,0.05)' : 'rgba(148,163,184,0.10)';
    ctx.fillRect(k - 14, minY - 26, maxW + 28, maxY - minY + 46);
    ctx.fillStyle = '#94a3b8'; ctx.font = '10px sans-serif';
    ctx.fillText(self._colLabel[k] || ('第' + (self._colIndex[k]) + '跳'), k - 8, minY - 32);
    ctx.font = FONT;
  });

  // 边（跨列贝塞尔，可跨越多列）
  ctx.strokeStyle = '#c4c9d0'; ctx.lineWidth = 1.6 / this.scale;
  this.visibleEdges().forEach(function (e) {
    var a = self.boxes[e.s], b = self.boxes[e.t];
    if (!a || !b) return;
    var x1 = a.x + a.w, y1 = a.y + a.h / 2;
    var x2 = b.x, y2 = b.y + b.h / 2;
    var mx = x1 + Math.max(30, (x2 - x1) / 2);
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.bezierCurveTo(mx, y1, mx, y2, x2, y2);
    ctx.stroke();
    // 箭头
    var ang = Math.atan2(y2 - mx * 0 + (y2 - y1) * 0 + (y2 - (mx === x2 ? y1 : y2)) * 0 + (y2 - y1) * (x2 - mx) / Math.max(1, x2 - mx), x2 - mx);
    ang = Math.atan2(y2 - y2, x2 - mx); // 端点处切线近似水平
    ctx.beginPath();
    ctx.moveTo(x2, y2);
    ctx.lineTo(x2 - 7 / self.scale, y2 - 4 / self.scale);
    ctx.lineTo(x2 - 7 / self.scale, y2 + 4 / self.scale);
    ctx.closePath();
    ctx.fillStyle = '#c4c9d0'; ctx.fill();
  });

  // 节点
  Object.values(this.boxes).forEach(function (b) {
    var n = b.n;
    var st = n.status == null ? 'null' : String(n.status);
    var color = ST_COLORS[st] || '#6b7280';
    var isRoot = n.depth === 0;
    var r = Math.min(9, b.h / 2);
    ctx.beginPath();
    ctx.moveTo(b.x + r, b.y);
    ctx.arcTo(b.x + b.w, b.y, b.x + b.w, b.y + b.h, r);
    ctx.arcTo(b.x + b.w, b.y + b.h, b.x, b.y + b.h, r);
    ctx.arcTo(b.x, b.y + b.h, b.x, b.y, r);
    ctx.arcTo(b.x, b.y, b.x + b.w, b.y, r);
    ctx.closePath();
    ctx.fillStyle = isRoot ? color : '#ffffff';
    ctx.fill();
    ctx.strokeStyle = color;
    ctx.lineWidth = (isRoot ? 3 : 2) / self.scale;
    ctx.stroke();
    ctx.fillStyle = isRoot ? '#fff' : '#1c2024';
    var label = isRoot ? '★ ' : '';
    var text = label + String(n.name || n.id);
    ctx.save(); ctx.beginPath(); ctx.rect(b.x, b.y, b.w - 26, b.h); ctx.clip();
    ctx.fillText(text, b.x + 10, b.y + 20);
    ctx.restore();
    // status 角标
    ctx.beginPath(); ctx.arc(b.x + b.w - 12, b.y + b.h / 2, 5, 0, Math.PI * 2);
    ctx.fillStyle = color; ctx.fill();
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5 / self.scale; ctx.stroke();
    // 多父标记（图结构：被多条边指向的共享节点）
    var inDeg = self.inDegree(b.id);
    if (inDeg > 1) {
      ctx.fillStyle = '#7c3aed'; ctx.font = '10px sans-serif';
      ctx.fillText('⇄' + inDeg, b.x + 2, b.y - 4);
      ctx.font = FONT;
    }
    // 折叠钮
    var kids = self.children[b.id] || [];
    if (kids.length) {
      var cx = b.x + b.w - 12, cy = b.y - 9;
      ctx.beginPath(); ctx.arc(cx, cy, 7.5, 0, Math.PI * 2);
      ctx.fillStyle = self.collapsed[b.id] ? '#2563eb' : '#e5e7eb'; ctx.fill();
      ctx.strokeStyle = self.collapsed[b.id] ? '#fff' : '#9ca3af'; ctx.lineWidth = 1 / self.scale; ctx.stroke();
      ctx.strokeStyle = self.collapsed[b.id] ? '#fff' : '#4b5563';
      ctx.beginPath();
      ctx.moveTo(cx - 3.5, cy); ctx.lineTo(cx + 3.5, cy);
      if (self.collapsed[b.id]) { ctx.moveTo(cx, cy - 3.5); ctx.lineTo(cx, cy + 3.5); }
      ctx.stroke();
      if (self.collapsed[b.id]) {
        ctx.fillStyle = '#2563eb'; ctx.font = '10px sans-serif';
        ctx.fillText(String(self.descendantCount(b.id)), b.x + b.w + 8, b.y + 20);
        ctx.font = FONT;
      }
    }
  });
  ctx.restore();
};

Mindmap.prototype._colIndex = null;

Mindmap.prototype.inDegree = function (id) {
  var vis = this.visibleSet(), n = 0, self = this;
  Object.keys(vis).forEach(function (pid) {
    if (self.collapsed[pid]) return;
    (self.children[pid] || []).forEach(function (cid) { if (cid === id && vis[cid]) n++; });
  });
  return n;
};

Mindmap.prototype.bindEvents = function () {
  var self = this, down = null, moved = false;
  this.canvas.addEventListener('mousedown', function (e) {
    down = { x: e.offsetX, y: e.offsetY, tx: self.tx, ty: self.ty }; moved = false;
  });
  this.canvas.addEventListener('mousemove', function (e) {
    if (!down) { self.hover(e); return; }
    var dx = e.offsetX - down.x, dy = e.offsetY - down.y;
    if (Math.abs(dx) + Math.abs(dy) > 4) moved = true;
    self.tx = down.tx + dx; self.ty = down.ty + dy;
    self.draw();
  });
  this.canvas.addEventListener('mouseup', function (e) {
    if (down && !moved) self.click(e);
    down = null;
  });
  this.canvas.addEventListener('wheel', function (e) {
    e.preventDefault();
    var f = e.deltaY < 0 ? 1.12 : 0.89;
    var mx = e.offsetX, my = e.offsetY;
    self.tx = mx - (mx - self.tx) * f;
    self.ty = my - (my - self.ty) * f;
    self.scale = Math.min(2.5, Math.max(0.12, self.scale * f));
    self.draw();
  }, { passive: false });
};

Mindmap.prototype.toWorld = function (ex, ey) {
  return { x: (ex - this.tx) / this.scale, y: (ey - this.ty) / this.scale };
};

Mindmap.prototype.hit = function (ex, ey) {
  var p = this.toWorld(ex, ey);
  var found = null, toggle = null;
  var self = this;
  Object.values(this.boxes).forEach(function (b) {
    if (p.x >= b.x && p.x <= b.x + b.w && p.y >= b.y - 14 && p.y <= b.y + b.h + 4) {
      if ((self.children[b.id] || []).length) {
        var cx = b.x + b.w - 12, cy = b.y - 9;
        if ((p.x - cx) * (p.x - cx) + (p.y - cy) * (p.y - cy) < 121) toggle = b;
      }
      found = b;
    }
  });
  return { box: found, toggle: toggle };
};

Mindmap.prototype.hover = function (e) {
  var h = this.hit(e.offsetX, e.offsetY);
  this.canvas.style.cursor = (h.toggle || h.box) ? 'pointer' : 'grab';
};

Mindmap.prototype.click = function (e) {
  var h = this.hit(e.offsetX, e.offsetY);
  if (h.toggle) {
    this.collapsed[h.toggle.id] = !this.collapsed[h.toggle.id];
    this.resize();
    return;
  }
  if (h.box) this.onNodeClick(h.box.id, h.box.n.label, h.box.n.name);
};
