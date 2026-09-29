/* char_edit.js — 角色 tab：中间 ECharts 美术图 + 右侧编辑框（中文字段名）+ 页内确认卡 */
'use strict';

var ST_COLORS = { '-1': '#dc2626', '0': '#9ca3af', '1': '#3b82f6', '2': '#3b82f6', '10': '#f59e0b', '11': '#16a34a' };
var ST_TEXT = { '-1': '作废重做', '0': '待处理', '1': '已完成', '2': '图片完成', '10': '待审', '11': '批准' };
var SIZE = { Character: 58, AppearanceStyle: 38, LanguageStyle: 34, CostumeStyle: 30, VoiceDesign: 36, DesignSheet: 42, IllusDesign: 32, StandingIllustration: 24, Location: 56, Scene: 40, SceneLayer: 28, BgmTrack: 28 };

function esc(s) { var d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; }
function escAttr(s) { return esc(s).replace(/"/g, '&quot;'); }

function layoutTree(nodes, links) {
  // 从左到右分层树：Character→数据/声音层→DesignSheet→IllusDesign→Stand
  var children = {}, hasParent = {}, byId = {};
  nodes.forEach(function (n) { byId[n.id] = n; children[n.id] = []; });
  links.forEach(function (l) {
    if (byId[l.source] && byId[l.target]) { children[l.source].push(l.target); hasParent[l.target] = true; }
  });
  var roots = nodes.filter(function (n) { return !hasParent[n.id]; }).map(function (n) { return n.id; });
  if (!roots.length && nodes.length) roots = [nodes[0].id];

  var COL_GAP = 260, ROW_GAP = 74;
  var pos = {}, cursor = { y: 60 };
  function place(id, depth) {
    var kids = children[id] || [];
    // 叶子优先占行，父节点居中于子节点
    if (!kids.length) {
      pos[id] = { x: 60 + depth * COL_GAP, y: cursor.y };
      cursor.y += ROW_GAP;
      return pos[id].y;
    }
    var ys = kids.map(function (k) { return place(k, depth + 1); });
    var y = (Math.min.apply(null, ys) + Math.max.apply(null, ys)) / 2;
    // 父与子最小间距保护：往下挤
    if (y < cursor.y - ROW_GAP * kids.length) y = cursor.y - ROW_GAP * kids.length;
    pos[id] = { x: 60 + depth * COL_GAP, y: y };
    return y;
  }
  roots.forEach(function (r) { place(r, 0); });

  // 同列重叠消解（自上而下微调）
  var cols = {};
  nodes.forEach(function (n) {
    var p = pos[n.id]; if (!p) return;
    var col = Math.round((p.x - 60) / COL_GAP);
    if (!cols[col]) cols[col] = [];
    cols[col].push(n.id);
  });
  Object.keys(cols).forEach(function (col) {
    var ids = cols[col].sort(function (a, b) { return pos[a].y - pos[b].y; });
    var lastY = -1e9;
    ids.forEach(function (id) {
      if (pos[id].y - lastY < ROW_GAP) pos[id].y = lastY + ROW_GAP;
      lastY = pos[id].y;
    });
  });
  return pos;
}

function initCharArt(data) {
  var el = document.getElementById('artgraph');
  var legend = document.getElementById('legend');
  if (legend) {
    legend.innerHTML = Object.keys(ST_TEXT).map(function (k) {
      return '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:' + ST_COLORS[k] + ';margin:0 3px 0 10px"></span>' + ST_TEXT[k];
    }).join('') + '<span class="muted"> · 节点右上 +/- 折叠 · 滚轮缩放 · 拖拽平移</span>';
  }
  new Mindmap(el, data, function (id, label, name) {
    loadEditor(id, label, name);
  });
  window._mm = el._mindmap;
}

function lit(v) {
  var s = String(v == null ? '' : v).trim();
  if (s === '') return 'null';
  if (/^-?\d+$/.test(s)) return s;
  if (/^-?\d+\.\d+$/.test(s)) return s;
  if (/^(true|false)$/i.test(s)) return s.toLowerCase();
  return "'" + s.replace(/\\/g, '\\\\').replace(/'/g, "\\'") + "'";
}

function loadEditor(id, label, name) {
  fetch('/board/node/' + id + '/props').then(function (r) { return r.json(); }).then(function (d) {
    var box = document.getElementById('editor');
    document.getElementById('editor-title').textContent = '编辑 · ' + label + ' · ' + (name || id);
    document.getElementById('confirm-card').style.display = 'none';
    var html = '<input type="hidden" id="node-id" value="' + escAttr(id) + '">';

    // ── 成果预览 + 审批 ──
    html += '<div id="art-view"></div>';
    fetch('/board/node/' + id + '/art').then(function (r) { return r.json(); }).then(function (a) {
      var av = document.getElementById('art-view');
      if (!av) return;
      var h = '';
      if (a.kind === 'image') {
        h += a.url
          ? '<a href="' + escAttr(a.url) + '" target="_blank"><img class="artwork" style="max-height:340px" src="' + escAttr(a.url) + '" alt="产物图"></a>'
          : '<div class="flash warn small">⚠ 图片未挂载：' + esc(a.path || '（无路径）') + '</div>';
        if (a.text) h += '<details><summary class="small">prompt</summary><pre class="doc small">' + esc(a.text) + '</pre></details>';
      } else if (a.kind === 'voice') {
        h += '<div class="kv small"><b>instruct</b>：' + esc(a.instruct || '—') + '</div>';
        if (a.cands && a.cands.length) {
          a.cands.forEach(function (c, i) {
            h += '<div class="cand"><b>候选' + (i + 1) + '·' + esc(c.name) + '</b>';
            if (c.url) h += '<div>ref：<audio controls preload="none" src="' + escAttr(c.url) + '"></audio></div>';
            c.audios.forEach(function (u) { if (u) h += '<div><audio controls preload="none" src="' + escAttr(u) + '"></audio></div>'; });
            h += '</div>';
          });
        } else if (a.url) {
          h += '<div>参考音频：<audio controls preload="none" src="' + escAttr(a.url) + '"></audio></div>';
        } else {
          h += '<div class="flash warn small">⚠ ref 未挂载</div>';
        }
      } else if (a.kind === 'brief' && a.text) {
        h += '<details open><summary class="small">设计简报</summary><pre class="doc small" style="max-height:260px">' + esc(a.text) + '</pre></details>';
      }
      if (a.status === 10) {
        h += '<div class="actions"><button class="btn ok" data-review="approve">✅ 批准（10→11）</button>' +
             '<button class="btn bad" data-review="reject">❌ 驳回（10→0）</button></div>';
      } else if (h) {
        h += '<p class="muted small">status=' + esc(a.status) + '（非待审，无审批按钮）</p>';
      }
      av.innerHTML = h;
      av.querySelectorAll('[data-review]').forEach(function (btn) {
        btn.onclick = function () {
          var fd = new URLSearchParams(); fd.append('action', btn.getAttribute('data-review'));
          fetch('/board/node/' + id + '/review', { method: 'POST', body: fd })
            .then(function (r) { return r.json(); })
            .then(function (res) {
              av.insertAdjacentHTML('afterbegin', res.ok
                ? '<div class="flash">✅ 已' + (res.status === 11 ? '批准' : '驳回') + ' — <a href="javascript:location.reload()">刷新图</a></div>'
                : '<div class="flash warn">❌ ' + esc(res.error) + '</div>');
            });
        };
      });
    });

    html += '<h3 style="margin:14px 0 6px">属性</h3>';
    html += '<table class="kv"><tr><th style="width:130px">字段</th><th>值</th></tr>';
    d.fields.forEach(function (f) {
      if (f.locked) {
        html += '<tr><th title="' + escAttr(f.key) + '">' + esc(f.zh || f.key) + '</th><td class="muted small">' + esc(f.value) + ' 🔒</td></tr>';
      } else {
        html += '<tr><th title="' + escAttr(f.key) + '">' + esc(f.zh || f.key) + '</th>' +
          '<td><input class="ginput" style="width:96%" data-key="' + escAttr(f.key) + '" value="' + escAttr(f.value) + '"></td></tr>';
      }
    });
    html += '</table>';
    html += '<p><button class="btn ok" id="gen-btn" type="button">确认修改…</button> ' +
            '<a class="btn" href="/approvals/image/' + escAttr(id) + '">审批页 →</a></p>';
    html += '<pre id="cypher-preview" class="doc small" style="display:none"></pre>';
    box.innerHTML = html;
    box.className = '';
    box.querySelectorAll('input[data-key]').forEach(function (inp) { inp.addEventListener('input', buildCypher); });
    document.getElementById('gen-btn').addEventListener('click', showConfirm);
    function buildCypher() {
      var sets = [];
      box.querySelectorAll('input[data-key]').forEach(function (inp) {
        sets.push('n.' + inp.getAttribute('data-key') + ' = ' + lit(inp.value));
      });
      var cy = 'MATCH (n {id: "' + id + '"}) SET ' + sets.join(', ');
      var pre = document.getElementById('cypher-preview');
      pre.style.display = 'block'; pre.textContent = cy;
      return cy;
    }
    window._build = buildCypher;
  });
}

function showConfirm() {
  var cy = window._build();
  var id = document.getElementById('node-id').value;
  fetch('/board/node/' + id + '/preview?cypher=' + encodeURIComponent(cy))
    .then(function (r) { return r.json(); })
    .then(function (d) {
      var card = document.getElementById('confirm-card');
      var html = '<div class="flash warn"><b>确认执行？</b>（写操作，含级联）</div>';
      html += '<pre class="doc small">' + esc(cy) + '</pre>';
      if (d.n === 0) {
        html += '<p class="muted small">目标节点无 sync=true 下游，无级联影响。</p>';
      } else {
        html += '<p><b>级联影响：' + d.n + ' 个下游节点将置 -1（作废重做）</b></p><table><tr><th>节点</th><th>类型</th><th>状态</th></tr>';
        d.preview.forEach(function (x) {
          html += '<tr><td>' + esc(x.name) + '</td><td><span class="tag">' + esc(x.label) + '</span></td><td>' + (ST_TEXT[x.status] || '—') + '</td></tr>';
        });
        html += '</table>';
      }
      html += '<p><button class="btn bad" id="exec-btn" type="button">我已理解，执行</button> ' +
              '<button class="btn" id="cancel-btn" type="button">取消</button></p>';
      card.innerHTML = html;
      card.style.display = 'block';
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      document.getElementById('cancel-btn').onclick = function () { card.style.display = 'none'; };
      document.getElementById('exec-btn').onclick = function () {
        var fd = new FormData();
        fd.append('cypher', cy);
        fetch('/board/node/' + id + '/save', { method: 'POST', body: new URLSearchParams(fd) })
          .then(function (r) { return r.json(); })
          .then(function (res) {
            card.innerHTML = res.ok
              ? '<div class="flash">✅ 已执行（级联重置 ' + res.cascaded + ' 个节点）— <a href="/board?tab=char&sel=' + res.char_id + '">刷新结构图</a></div>'
              : '<div class="flash warn">❌ ' + esc(res.error) + '</div>';
            card.style.display = 'block';
          });
      };
    });
}
