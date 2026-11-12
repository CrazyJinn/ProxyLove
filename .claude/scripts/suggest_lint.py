r"""
suggest_lint.py — 建议 JSON cypher 语句级护栏（MERGE 绑定语义，2026-11-02 重复节点事故后新增）

对 02_剧情数据/*_建议.json 逐项的 cypher 做拆条后逐语句静态校验，拦截两类事故形态：
  根因一（跨语句悬空变量）：`;` 拆条后每条语句是独立查询，引用前条语句变量的
    MERGE/CREATE 边要么静默挂错既有边、要么新建幽灵节点；
  根因二（MERGE 整 pattern 语义）：MERGE 边 pattern 端点带标签/属性但未在本语句
    先前位置绑定——pattern 未命中时整条创建，产出只带 {id} 的重复节点。
根因详解与正确写法权威：Asset/.claude/skills/event-stager/references/多语句cypher与MERGE绑定语义.md

── 检测规则表（与 Dashboard 侧 D:\\project\\ProxyLove\\Dashboard\\app\\services\\cypher_lint.py
    逐字同一规格；改规则必须同次双侧改，并同步对侧用例。先例：node_fields.py 抄 Schema）──

拆条逻辑镜像 dashboard 执行侧 cascade.split_statements 的
re.split(r";[ \t]*(?:\\r?\\n|$)")（不复用 cypher_exec.split_cypher_statements——
语义对齐执行侧才是重点）。拆条后逐条语句检测：

  R1_dangling_endpoint_var   MERGE/CREATE 边 pattern 端点为裸变量 (v)，且 v 未在
                             本语句先前位置由锚定节点模式（MATCH/OPTIONAL MATCH/
                             CREATE/MERGE 节点模式，含逗号多 pattern、含 MATCH 边
                             的锚定端点）声明 → FAIL（根因一）
  R2_merge_unbound_endpoint  MERGE 边 pattern 端点带标签或属性（含匿名 (:Label
                             {..})）且未在本语句先前位置绑定 → FAIL（根因二）。
                             CREATE 边的锚定端点合法（CREATE 语义即创建），不触发
  R3a_semicolon_in_string    字符串字面量内出现 ASCII ; → FAIL（项目约定描述文本
                             用中文标点；执行侧按分号拆条依赖此约定）
  R3b_semicolon_not_at_eol   字符串外某 ; 之后同行还有非空白内容 → FAIL（dashboard
                             正则「;+换行」不会在此拆分，语句会被拼成非法 Cypher）
  R4_bare_merge_node         MERGE 独立节点模式无标签 → FAIL（cypher_exec 硬约束 4）
  R5_unsupported_clause      含 WITH/UNWIND/FOREACH/CALL/LOAD CSV/$param（字符串与
                             注释剥离后判定）→ FAIL（不支持形态，fail-closed 要求
                             改写；逃生口 = dashboard Cypher 控制台，不经本护栏）

防误报关键语义：
  - MERGE 节点模式绑定的变量，在同语句后续 MERGE 边中裸引用合法（正确写法即此形态）；
  - MATCH/OPTIONAL MATCH 治理的边端点任意形态不检（只读 pattern 匹配自绑定）；
  - 已声明变量的锚定端点（如 MATCH 过再带 pattern 引用）语义安全，PASS；
  - 裸匿名 () 作 MERGE/CREATE 边端点 → R1（会 CREATE 匿名幽灵节点）。

已知盲区（lint 不覆盖，见事故文档「执行后回查」兜底）：
  - MATCH 绑定 0 行（id 打错）时 MERGE 边静默 0 行——结构 lint 管不了数据存在性；
  - 缺 ; 的换行分隔：lint 与 dashboard 一致视为单语句（Cypher 合法），非事故形态；
  - MATCH (l) CREATE (l)-[:T]->(sp:Spot {id:'已存在id'}) 这类 CREATE 变体重建：
    CREATE 语义自明，R1/R2 均不覆盖（产出模板已无此形态）。

── 轻量解析策略（正则非解析器；项目语句形态规整：内联值、单引号、;+换行分隔、禁嵌套 map）──

  1. mask(stmt)：字符串字面量内容与 // 行注释替换为等长空格（保位置；防注释里的
     pattern 示例与字符串内 (){};:- 干扰正则）；
  2. 边 pattern 链提取 (a)-[r:T]->(b)-[..]->(c)（finditer 天然处理链式）；
  3. 节点模式 \(([^()]*)\)+ 结构判形，不符节点形状的括号对忽略（WHERE 子句、
     count(*) 防误报）；落在边 span 内的为边端点，否则独立节点模式；
  4. 正向关键字游走定每个 pattern 的治理子句（ON CREATE/ON MATCH 先于 CREATE/MATCH
     识别，不污染归属）；
  5. R3 用字符串感知扫描（只感知字符串不感知注释——与 dashboard 正则视角一致）。

── CLI ──

  python .claude/scripts/suggest_lint.py <建议.json> [--json]   # 退出码 0=全 PASS/SKIP，1=有 FAIL，2=用法/IO/JSON 错误
  python .claude/scripts/suggest_lint.py --selftest             # 内置用例表自测（与 Dashboard tests/test_cypher_lint.py 同源语料）
"""

import json
import re
import sys
from pathlib import Path

# ── 拆条（镜像 Dashboard/app/services/cascade.py::split_statements，改那边必须同步这边）──
SPLIT_RE = re.compile(r";[ \t]*(?:\r?\n|$)")


def split_statements(text: str) -> list:
    """按「;+换行/文末」拆分多语句文本——与 dashboard 执行侧逐字同款。"""
    text = text.strip().rstrip(";")
    if not text:
        return []
    parts = SPLIT_RE.split(text)
    return [p.strip().rstrip(";") for p in parts if p.strip()]


# ── 掩码：字符串内容与 // 行注释 → 等长空格（保位置）──

def mask(stmt: str) -> str:
    """字符串字面量内容与 // 行注释替换为等长空格，保留引号/换行位置。

    处理 \\' 反斜杠转义与 '' 双写转义。后续正则在此结果上跑。
    """
    out = []
    i, n = 0, len(stmt)
    in_string = False
    string_char = None
    while i < n:
        ch = stmt[i]
        if not in_string and ch == "/" and i + 1 < n and stmt[i + 1] == "/":
            while i < n and stmt[i] != "\n":  # 注释整段掩为空格，留 \n
                out.append(" ")
                i += 1
            continue
        if in_string:
            if ch == "\\" and i + 1 < n:  # 转义对（含 \'）整体掩掉
                out.append("  ")
                i += 2
                continue
            if ch == string_char and i + 1 < n and stmt[i + 1] == ch:  # '' 双写
                out.append("  ")
                i += 2
                continue
            if ch == string_char:
                in_string = False
                out.append(ch)  # 闭引号保留
            else:
                out.append("\n" if ch == "\n" else " ")  # 内容掩空格、保换行
            i += 1
            continue
        if ch in ("'", '"'):
            in_string = True
            string_char = ch
            out.append(ch)  # 开引号保留
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _scan_semicolons(text: str) -> list:
    """字符串感知扫描（只感知字符串、不感知注释——与 dashboard 正则视角一致）。

    返回 [(分号位置, 'in_string'|'outside')]。
    """
    out = []
    i, n = 0, len(text)
    in_string = False
    string_char = None
    while i < n:
        ch = text[i]
        if in_string:
            if ch == "\\" and i + 1 < n:
                i += 2
                continue
            if ch == string_char:
                if i + 1 < n and text[i + 1] == ch:  # '' 双写
                    i += 2
                    continue
                in_string = False
        elif ch in ("'", '"'):
            in_string = True
            string_char = ch
        if ch == ";":
            out.append((i, "in_string" if in_string else "outside"))
        i += 1
    return out


# ── 规则元数据与固定文案（与 Dashboard 侧逐字一致）──

RULE_R1 = "R1_dangling_endpoint_var"
RULE_R2 = "R2_merge_unbound_endpoint"
RULE_R3A = "R3a_semicolon_in_string"
RULE_R3B = "R3b_semicolon_not_at_eol"
RULE_R4 = "R4_bare_merge_node"
RULE_R5 = "R5_unsupported_clause"

MSG_R1 = ("边 pattern 端点变量 `{var}` 未在本语句内声明——`;` 分隔的语句间变量不延续，"
          "MERGE/CREATE 会挂错节点或新建幽灵节点。修法：把该端点写成本语句内的 "
          "MATCH ({var}:Label {{id:'…'}})（或把整段合成一条语句）。")
MSG_R2 = ("MERGE 边端点带标签/属性但未在本语句先前位置绑定——MERGE 未命中会整 pattern "
          "重建（新建仅带 {{id}} 的重复节点，2026-11-02 事故根因）。修法：端点先在本语句内 "
          "MATCH ({var}:Label {{id:'…'}}) 绑定，MERGE 边中只用裸变量 ({var})。")
MSG_R3A = "字符串内出现 ASCII 分号——描述文本请用中文分号『；』（执行侧按分号拆条依赖此约定）。"
MSG_R3B = ("分号后同行还有内容——dashboard 按『;+换行』拆条，此分号不是语句边界，语句会被拼成"
           "非法 Cypher。修法：每个分号独占行尾。")
MSG_R4 = "裸 MERGE 节点（无标签）违反 cypher_exec 硬约束 4——必须 MERGE (n:Label {{…}})。"
MSG_R5 = ("语句含建议 JSON 不支持的子句（WITH/UNWIND/FOREACH/CALL/LOAD CSV/$param）——"
          "请改写为自包含的常规 CREATE/MATCH/MERGE/SET/DELETE 语句。")

# ── pattern 提取（在 mask 后文本上）──

_REL = r"(?:<-\s*\[[^\]]*\]\s*-|-\s*\[[^\]]*\]\s*->|--?>|<--?)"
_PATH_RE = re.compile(r"\(([^()]*)\)\s*(?:" + _REL + r"\s*\(([^()]*)\)\s*)+")
_NODE_INNER_RE = re.compile(
    r"^\s*([A-Za-z_]\w*)?\s*(?::\s*[A-Za-z_]\w*)?\s*(\{\s*\}|\{[^{}]*\})?\s*$"
)
# 治理子句游走：顺序敏感（ON CREATE / ON MATCH / OPTIONAL MATCH / DETACH DELETE 先于短词）
_CLAUSE_RE = re.compile(
    r"\b(ON\s+CREATE|ON\s+MATCH|OPTIONAL\s+MATCH|DETACH\s+DELETE|ORDER\s+BY|LOAD\s+CSV"
    r"|MATCH|MERGE|CREATE|SET|WHERE|DELETE|DETACH|WITH|RETURN|UNWIND|CALL|FOREACH"
    r"|LIMIT|SKIP)\b"
)
_GOVERNING = {"MATCH", "OPTIONAL MATCH", "MERGE", "CREATE"}
_R5_RE = re.compile(r"\b(WITH|UNWIND|FOREACH|CALL|LOAD\s+CSV)\b|\$[A-Za-z_]", re.IGNORECASE)


def _clause_walk(masked: str):
    """返回 [(pos, keyword)]——治理子句识别用的有序关键字位置表。"""
    return [(m.start(), re.sub(r"\s+", " ", m.group(1)).upper())
            for m in _CLAUSE_RE.finditer(masked)]


def _governing_at(clauses, pos):
    """pos 之前最后一个治理子句关键字（MATCH/OPTIONAL MATCH/MERGE/CREATE），无则 None。"""
    gov = None
    for cpos, kw in clauses:
        if cpos >= pos:
            break
        if kw in _GOVERNING:
            gov = kw
    return gov


def _parse_node(inner: str):
    """节点模式内层判形：'(var)(:Label)({props})' → (var|None, has_label, has_props)；
    非节点形状（WHERE 子句、count(*) 等）→ None。
    """
    m = _NODE_INNER_RE.match(inner)
    if not m:
        return None
    var, props = m.group(1), m.group(2)
    has_label = ": " in inner or bool(re.search(r":\s*[A-Za-z_]", inner))
    return (var, has_label, props is not None)


def lint_statement(stmt: str) -> dict:
    """单条语句检测（R1/R2/R4/R5；R3 全文级在 lint_cypher 归并）。"""
    violations = []
    masked = mask(stmt)
    preview = re.sub(r"\s+", " ", stmt.strip())[:60]

    if _R5_RE.search(masked):
        violations.append({"rule": RULE_R5, "var": "", "at": preview, "message": MSG_R5})
        return {"preview": preview, "status": "FAIL", "violations": violations}

    clauses = _clause_walk(masked)
    # 边 pattern span（含链式）与端点
    path_spans = []
    endpoints = []  # [(pos, (var, has_label, has_props))]
    for m in _PATH_RE.finditer(masked):
        path_spans.append((m.start(), m.end()))
        for nm in re.finditer(r"\(([^()]*)\)", m.group(0)):
            parsed = _parse_node(nm.group(1))
            if parsed:
                endpoints.append((m.start() + nm.start(1) - 1, parsed))
    # 声明集：锚定节点模式（有变量 +（有标签或有属性）），独立节点与边端点均算
    declarations = []  # [(var, pos)]
    for nm in re.finditer(r"\(([^()]*)\)", masked):
        in_path = any(s <= nm.start() < e for s, e in path_spans)
        parsed = _parse_node(nm.group(1))
        if not parsed:
            continue
        var, has_label, has_props = parsed
        pos = nm.start()
        if var and (has_label or has_props):
            declarations.append((var, pos))
        # R4：MERGE 治理的独立节点无标签 → FAIL
        if not in_path and not has_label:
            gov = _governing_at(clauses, pos)
            if gov == "MERGE":
                violations.append({
                    "rule": RULE_R4, "var": var or "",
                    "at": re.sub(r"\s+", " ", stmt[pos:pos + 40]),
                    "message": MSG_R4.format(var=var or ""),
                })

    def declared_before(var, pos):
        return any(v == var and p < pos for v, p in declarations)

    # R1/R2：MERGE/CREATE 治理的边端点
    for pos, (var, has_label, has_props) in endpoints:
        gov = _governing_at(clauses, pos)
        if gov not in ("MERGE", "CREATE"):
            continue
        anchored = has_label or has_props
        at = re.sub(r"\s+", " ", stmt[pos:pos + 50])
        if not var and not anchored:  # 裸匿名 ()
            violations.append({"rule": RULE_R1, "var": "", "at": at, "message": MSG_R1.format(var="")})
            continue
        if var and not anchored:  # 裸变量：须先前声明
            if not declared_before(var, pos):
                violations.append({"rule": RULE_R1, "var": var, "at": at, "message": MSG_R1.format(var=var)})
            continue
        # 锚定端点：已声明变量的重复锚定语义安全；MERGE 未声明 → R2；CREATE 放行
        if gov == "MERGE" and not (var and declared_before(var, pos)):
            violations.append({"rule": RULE_R2, "var": var or "", "at": at,
                               "message": MSG_R2.format(var=var or "")})

    status = "FAIL" if violations else "PASS"
    return {"preview": preview, "status": status, "violations": violations}


def lint_cypher(text: str) -> list:
    """整段 cypher：R3 全文级（按分号位置归属语句）+ 拆条后逐语句 R1/R2/R4/R5。"""
    text = text.strip().rstrip(";")
    stmts = split_statements(text)
    # 各语句在原文中的起始 offset（用于 R3 违规归属）
    offsets, cursor = [], 0
    for s in stmts:
        idx = text.find(s, cursor)
        offsets.append(idx if idx >= 0 else cursor)
        cursor = idx + len(s)
    results = [lint_statement(s) for s in stmts]
    for pos, where in _scan_semicolons(text):
        if where == "in_string":
            rule, msg = RULE_R3A, MSG_R3A
        else:
            rest = text[pos + 1:]
            if not rest or rest[0] in " \t":
                stripped = rest.lstrip(" \t")
                if not stripped or stripped[0] in "\r\n":
                    continue  # ;+换行/EOF：合法语句边界
            elif rest[0] in "\r\n":
                continue
            rule, msg = RULE_R3B, MSG_R3B
        # 归属：分号所在位置之前的最后一条语句
        si = max(i for i, o in enumerate(offsets) if o <= pos) if offsets else 0
        results[si]["violations"].append({
            "rule": rule, "var": "", "at": text[max(0, pos - 30):pos + 1].strip(), "message": msg,
        })
        results[si]["status"] = "FAIL"
    return results


def lint_item(item: dict, index: int) -> dict:
    """建议 JSON 单项：cypher 空/缺 → SKIP（通知/派单类）。"""
    cypher = (item or {}).get("cypher") or ""
    base = {"index": index, "check": (item or {}).get("check", ""),
            "source": (item or {}).get("source", "")}
    if not cypher.strip():
        base.update({"status": "SKIP", "statements": []})
        return base
    stmts = lint_cypher(cypher)
    base.update({
        "status": "FAIL" if any(s["status"] == "FAIL" for s in stmts) else "PASS",
        "statements": stmts,
    })
    return base


def lint_document(arr) -> dict:
    """顶层建议数组 → 结构化报告。顶层数组非法时抛 SystemExit(2)。"""
    if not isinstance(arr, list):
        raise SystemExit(2)
    items = [lint_item(it, i) for i, it in enumerate(arr)]
    n_viol = sum(len(s["violations"]) for it in items for s in it.get("statements", []))
    return {
        "ok": all(it["status"] != "FAIL" for it in items),
        "summary": {
            "items": len(items),
            "fail_items": sum(1 for it in items if it["status"] == "FAIL"),
            "statements": sum(len(it.get("statements", [])) for it in items),
            "violations": n_viol,
        },
        "items": items,
    }


# ── CLI ──

def _print_report(report: dict, path: str) -> None:
    for it in report["items"]:
        if it["status"] == "SKIP":
            continue
        for si, s in enumerate(it["statements"]):
            if s["status"] != "FAIL":
                continue
            for v in s["violations"]:
                print(f"[FAIL] 项#{it['index']} {it['check']} · 语句{si + 1} "
                      f"[{v['rule']}] {v['var'] or ''} — {v['at']}")
                print(f"       {v['message']}")
    sm = report["summary"]
    tail = "（--json 看全量）" if not report["ok"] else ""
    print(f"{sm['fail_items']}/{sm['items']} 项 FAIL，{sm['violations']} 处违规，"
          f"{sm['statements']} 条语句 {tail}")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--selftest" in argv:
        return selftest()
    args = [a for a in argv if a != "--json"]
    as_json = "--json" in argv
    if len(args) != 1:
        print("用法：python suggest_lint.py <建议.json> [--json] | --selftest", file=sys.stderr)
        return 2
    path = Path(args[0])
    try:
        arr = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"错误：读取/解析 {path} 失败：{exc}", file=sys.stderr)
        return 2
    try:
        report = lint_document(arr)
    except SystemExit:
        print(f"错误：{path} 顶层必须是建议数组（list）", file=sys.stderr)
        return 2
    if as_json:
        report["file"] = path.name
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_report(report, str(path))
    return 0 if report["ok"] else 1


# ── 自测（用例语料与 Dashboard tests/test_cypher_lint.py 同源；改语料双侧同改）──

# 事故形态一：Spot 占位节点 + 第二句引用前句悬空变量 sp（根因一）
INCIDENT_FORM1 = (
    "CREATE (sp:Spot {id:'SP1'}) SET sp.name='临江公园-观景台', sp.kind='zone', sp.status=0;\n"
    "MATCH (l:Location {id:'L1'}) MERGE (l)-[r:part_of]->(sp) ON CREATE SET r.sync=false;\n"
)
# 事故形态二：S2 单语句 MERGE 边内联锚定端点 scn/il（根因二）
INCIDENT_FORM2 = (
    "MATCH (e:Event {id:'E1'})\n"
    "MERGE (sub:SubEvent {id:'SUB1'})\n"
    "ON CREATE SET sub.title='清晨告白 · 开场', sub.time='07:00', sub.description='寒暄'\n"
    "MERGE (e)-[r:refines]->(sub) ON CREATE SET r.sync=true\n"
    "MERGE (sub)-[a:anchored_at]->(scn:Scene {id:'SCN1'}) ON CREATE SET a.sync=false\n"
    "MERGE (sub)-[ap:appears_as]->(il:IllusDesign {id:'IL1'}) ON CREATE SET ap.sync=false;\n"
)
# 事故文档「正确写法」全文（自包含语句）
CORRECT_STAGER = (
    "CREATE (sp:Spot {id:'SP2'}) SET sp.name='临江公园-观景台', sp.kind='zone', sp.status=0;\n"
    "MATCH (l:Location {id:'L2'}) MATCH (sp:Spot {id:'SP2'}) MERGE (l)-[r:part_of]->(sp) ON CREATE SET r.sync=false;\n"
    "MATCH (e:Event {id:'E2'}) MERGE (sub:SubEvent {id:'SUB2'})\n"
    "ON CREATE SET sub.title='清晨告白 · 开场', sub.time='07:00', sub.description='寒暄'\n"
    "MERGE (e)-[r:refines]->(sub) ON CREATE SET r.sync=true;\n"
    "MATCH (sub:SubEvent {id:'SUB2'}) MATCH (scn:Scene {id:'SCN2'})\n"
    "MERGE (sub)-[a:anchored_at]->(scn) ON CREATE SET a.sync=false;\n"
    "MATCH (sub:SubEvent {id:'SUB2'}) MATCH (il:IllusDesign {id:'IL2'})\n"
    "MERGE (sub)-[ap:appears_as]->(il) ON CREATE SET ap.sync=false, ap.detail='继承：同父兄弟着装';\n"
)
# 新 SKILL.md 模板形态（含注释行——掩码后不干扰；S3 收尾 DETACH DELETE）
CORRECT_TEMPLATE = (
    "// Spot 占位——节点本体\n"
    "CREATE (sp:Spot {id:'SP3'}) SET sp.name='小酒馆-吧台区', sp.kind='zone', sp.status=0;\n"
    "// part_of 边\n"
    "MATCH (l:Location {id:'L3'}) MATCH (sp:Spot {id:'SP3'}) MERGE (l)-[r:part_of]->(sp) ON CREATE SET r.sync=false;\n"
    "// S3 Hook 揭示\n"
    "MATCH (e:Event {id:'E3'})\n"
    "MERGE (sub:SubEvent {id:'SUB3'})\n"
    "ON CREATE SET sub.title='内心独白', sub.time='09:00', sub.description='忐忑'\n"
    "MERGE (e)-[r:refines]->(sub) ON CREATE SET r.sync=true;\n"
    "MATCH (sub:SubEvent {id:'SUB3'}) MATCH (scn:Scene {id:'SCN3'})\n"
    "MERGE (sub)-[a:anchored_at]->(scn) ON CREATE SET a.sync=false;\n"
    "MATCH (sub:SubEvent {id:'SUB3'}) MATCH (f:Hook {id:'FACT1'}) MERGE (sub)-[rv:reveals]->(f);\n"
)
# event-ideator 形态：逗号多 MATCH、无标签 MATCH 端点
CORRECT_IDEATOR = (
    "MATCH (e:Event {id:'E4'}), (l:Location {id:'L4'}) MERGE (e)-[r:occurs_at]->(l) ON CREATE SET r.sync=false;\n"
    "MATCH (a:Event {id:'E4'}), (f:Hook {id:'FACT2'}) MERGE (a)-[r2:establishes]->(f) ON CREATE SET r2.sync=false;\n"
    "MATCH (n {id:'E4'}) SET n.description='补充一句';\n"
)

SELFTEST_CASES = [
    # (名称, cypher, 期望 FAIL 的规则列表——list 保留重复，一个端点一处违规)
    ("incident_form1_dangling_var", INCIDENT_FORM1, [RULE_R1]),
    ("incident_form2_merge_unbound", INCIDENT_FORM2, [RULE_R2, RULE_R2]),
    ("correct_stager_pass", CORRECT_STAGER, []),
    ("correct_template_pass", CORRECT_TEMPLATE, []),
    ("ideator_forms_pass", CORRECT_IDEATOR, []),
    ("bare_merge_node_fail", "MERGE (n {id:'X1'}) SET n.name='x';\n", [RULE_R4]),
    ("match_set_pass", "MATCH (n {id:'X2'}) SET n.name='x';\n", []),
    ("with_clause_fail", "MATCH (n:Event {id:'X3'}) WITH n MERGE (m:Hook {id:'X4'});\n", [RULE_R5]),
    ("semicolon_same_line_fail", "CREATE (a:X {id:'1'}); CREATE (b:Y {id:'2'});\n", [RULE_R3B]),
    ("semicolon_in_string_fail", "CREATE (a:X {id:'3'}) SET a.d='半角;分号';\n", [RULE_R3A]),
]


def selftest() -> int:
    ok = True
    for name, cypher, expected in SELFTEST_CASES:
        results = lint_cypher(cypher)
        got = sorted(v["rule"] for r in results for v in r["violations"])
        want = sorted(expected)
        if got != want:
            ok = False
            print(f"[SELFTEST-FAIL] {name}: 期望 {want}，实际 {got}")
            for r in results:
                for v in r["violations"]:
                    print(f"    [{v['rule']}] {v['var']} — {v['at']}")
        else:
            print(f"[SELFTEST-PASS] {name} ({len(results)} 语句)")
    # SKIP 与坏 JSON 行为
    if lint_item({"check": "I1", "cypher": ""}, 0)["status"] != "SKIP":
        ok = False
        print("[SELFTEST-FAIL] skip_empty_cypher")
    else:
        print("[SELFTEST-PASS] skip_empty_cypher")
    print("selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
