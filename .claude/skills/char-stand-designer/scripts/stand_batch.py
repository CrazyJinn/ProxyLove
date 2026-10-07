#!/usr/bin/env python3
"""立绘批量出图（char-stand-designer 批量模式执行层）。

职责边界：本脚本只做 **出图 → 透明校验 → 写图** 三步的并发流水；
六标签推导与 prompt 组装（创作判断）仍由调用方 LLM 先行完成——
任务清单里每项的 prompt_path 必须已存在，缺失项直接 failed 不出图。

并发模型：ThreadPoolExecutor（默认 3 并发）。出图是 OfoxAI API 纯 IO 等待，
线程池足够；每个 worker 独立 subprocess 调 ofoxai_api.py（复用其 429/5xx 退避
重试），透明校验 import 同目录 check_transparency.main，写图走
cypher_exec.py --stdin --multi（图写入收敛到唯一入口的铁律不变）。

「先产物后写图」铁律在 worker 内保持：出图成功且透明校验通过才写
image_path/status=10；任一环节失败则该节点保持原 status（0/-1）待人工处置。

用法：
    python stand_batch.py --tasks <tasks.json> [--workers 3] [--retry 2]

tasks.json 格式（数组，每项一个变体）：
    [{
      "stand_id": "...", "variant_label": "...",
      "prompt_path": "06_角色美术/.../立绘/<variant>.md",   # 必须已存在（LLM 已组装）
      "output_path": "06_角色美术/.../立绘/<variant>.png",
      "ref_image":   "06_角色美术/.../立绘设计图.png",
      "illus_id": "...", "voice_id": "...",                  # voice_id 可省（跳过 ref_style 边）
      "tags": {"eye": "...", "brow": "...", "mouth": "...",
               "head_angle": "...", "hand": "...", "foot": "..."}
    }]

退出码：0 全部成功 / 1 部分或全部失败 / 2 任务文件不可用。
汇总报告：stdout 末行 JSON（total/done/failed/results）。
"""
import argparse
import concurrent.futures as cf
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../char-stand-designer/scripts
SKILL_DIR = HERE.parent                          # .../char-stand-designer
ROOT = SKILL_DIR.parent.parent.parent            # Asset 项目根（scripts→skill→skills→.claude→根）
OFOXAI = ROOT / ".claude" / "skills" / "infra-image-generator" / "scripts" / "ofoxai_api.py"
CYPHER = ROOT / ".claude" / "scripts" / "cypher_exec.py"

sys.path.insert(0, str(HERE))
from check_transparency import main as check_transparency  # noqa: E402

GEN_TIMEOUT = 900   # 单次出图 subprocess 超时（秒）——释然级偶发慢单 10min+ 需容纳


def esc(s: str) -> str:
    """cypher 字符串单引号转义。"""
    return s.replace("\\", "\\\\").replace("'", "\'")


def build_write_cypher(t: dict) -> str:
    """按 SKILL「保存结果」段生成写图语句（六标签 + expands_to/ref_style 边 + 产物 + status=10）。"""
    sid, tags = t["stand_id"], t["tags"]
    stmts = [f"""MATCH (stand:StandingIllustration {{id: '{sid}'}})
SET stand.eye = '{esc(tags["eye"])}', stand.brow = '{esc(tags["brow"])}',
    stand.mouth = '{esc(tags["mouth"])}', stand.head_angle = '{esc(tags["head_angle"])}',
    stand.hand = '{esc(tags["hand"])}', stand.foot = '{esc(tags["foot"])}';""",
             f"""MATCH (illus:IllusDesign {{id: '{t["illus_id"]}'}}), (stand:StandingIllustration {{id: '{sid}'}})
MERGE (illus)-[r:expands_to]->(stand) SET r.sync = true, r.variant_label = '{esc(t["variant_label"])}';"""]
    if t.get("voice_id"):
        stmts.append(f"""MATCH (voice:LanguageStyle {{id: '{t["voice_id"]}'}}), (stand:StandingIllustration {{id: '{sid}'}})
MERGE (voice)-[r:ref_style]->(stand) SET r.sync = true;""")
    stmts.append(f"""MATCH (stand:StandingIllustration {{id: '{sid}'}})
SET stand.prompt_path = '{esc(t["prompt_path"])}',
    stand.image_path  = '{esc(t["output_path"])}',
    stand.status = 10;""")
    return "\n".join(stmts)


def generate_once(t: dict) -> None:
    """单次出图（subprocess 调 ofoxai，prompt 走 stdin）。失败/超时抛异常。"""
    prompt = Path(t["prompt_path"]).read_text(encoding="utf-8")
    cmd = [sys.executable, str(OFOXAI), "submit", "--prompt-stdin",
           "--image", t["ref_image"], "--size", "1024x1536",
           "--background", "transparent", "-o", t["output_path"]]
    proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                          cwd=str(ROOT), timeout=GEN_TIMEOUT)
    if proc.returncode != 0:
        raise RuntimeError(f"ofoxai rc={proc.returncode}: {proc.stderr.strip()[:300]}")
    out = proc.stdout.strip().splitlines()
    payload = json.loads(out[-1]) if out else {}
    if payload.get("status") != "done":
        raise RuntimeError(f"ofoxai status={payload.get('status')}: {str(payload)[:300]}")


def worker(t: dict, retry: int) -> dict:
    """单个变体全流程：出图（含透明不合格重试）→ 校验 → 写图。任何失败不写 status。"""
    sid, label = t["stand_id"], t["variant_label"]
    result = {"stand_id": sid, "variant_label": label, "attempts": 0}
    try:
        for attempt in range(1 + retry):
            result["attempts"] = attempt + 1
            generate_once(t)
            rc = check_transparency([t["output_path"]])
            if rc == 0:
                break
            print(f"[warn] {label}({sid}) 第 {attempt + 1} 次出图不透明（rc={rc}），重试", flush=True)
        else:
            return {**result, "ok": False, "stage": "transparency",
                    "error": f"透明校验连续 {1 + retry} 次未通过，未写图"}
        proc = subprocess.run([sys.executable, str(CYPHER), "--stdin", "--multi"],
                              input=build_write_cypher(t), capture_output=True, text=True,
                              cwd=str(ROOT), timeout=60)
        if proc.returncode != 0:
            return {**result, "ok": False, "stage": "write_graph",
                    "error": f"cypher rc={proc.returncode}: {proc.stderr.strip()[:300]}"}
        print(f"[done] {label}({sid}) status=10", flush=True)
        return {**result, "ok": True}
    except subprocess.TimeoutExpired:
        return {**result, "ok": False, "stage": "generate", "error": f"出图超时 >{GEN_TIMEOUT}s"}
    except Exception as e:  # noqa: BLE001 —— 单变体失败不拖垮整批
        return {**result, "ok": False, "stage": "generate", "error": str(e)[:300]}


def main(argv) -> int:
    p = argparse.ArgumentParser(description="立绘批量出图（并发出图+透明校验+写图）")
    p.add_argument("--tasks", required=True, help="任务清单 JSON 路径")
    p.add_argument("--workers", type=int, default=3, help="并发数（默认 3，OfoxAI 429 由其内部退避兜底）")
    p.add_argument("--retry", type=int, default=2, help="透明不合格重试次数（默认 2，同 SKILL 单变体流程）")
    args = p.parse_args(argv)

    tasks_file = Path(args.tasks)
    if not tasks_file.is_file():
        print(json.dumps({"error": f"tasks 文件不存在: {args.tasks}"}, ensure_ascii=False))
        return 2
    tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
    if not isinstance(tasks, list) or not tasks:
        print(json.dumps({"error": "tasks 须为非空数组"}, ensure_ascii=False))
        return 2

    # 前置校验：prompt/ref 必须已在盘上（组装是 LLM 的活，本脚本不越界）
    runnable, pre_failures = [], []
    for t in tasks:
        missing = [k for k in ("prompt_path", "ref_image") if not (ROOT / t[k]).is_file()]
        if missing:
            pre_failures.append({"stand_id": t.get("stand_id"), "variant_label": t.get("variant_label"),
                                 "ok": False, "stage": "preflight",
                                 "error": f"文件缺失: {', '.join(missing)}"})
        else:
            runnable.append(t)
    for f in pre_failures:
        print(f"[fail] {f['variant_label']}({f['stand_id']}) {f['error']}", flush=True)

    results = []
    if runnable:
        with cf.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futures = {pool.submit(worker, t, args.retry): t for t in runnable}
            for fut in cf.as_completed(futures):
                results.append(fut.result())

    done = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]] + pre_failures
    report = {"total": len(tasks), "done": len(done), "failed": failed, "results": results}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
