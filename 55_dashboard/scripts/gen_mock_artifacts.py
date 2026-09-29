"""gen_mock_artifacts.py — 生成 mock 产物树（与图数据严格一致的演示数据）。

产物根 = 仓库根（55_dashboard 与 25_剧本/06_角色美术/13_BGM/14_声音设计/15_声音/ 同级，
镜像代恋项目结构）。图数据不动；本脚本幂等（已存在的 wav 不重造，md/ink 按图重建覆盖）。

wav 用纯 Python 合成正弦波（8000Hz 单声道 16bit，~0.4s，各音不同基频可听出区别），
无第三方依赖；png 用最小合法 PNG（1x1 像素按角色着色）。
"""

from __future__ import annotations

import json
import math
import struct
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根 = 产物根（55_dashboard 的上级）
if str(ROOT / "55_dashboard") not in sys.path:
    sys.path.insert(0, str(ROOT / "55_dashboard"))


def make_wav(path: Path, freq: float = 440.0, seconds: float = 0.4) -> None:
    rate = 8000
    n = int(rate * seconds)
    frames = bytearray()
    for i in range(n):
        # 简单包络 + 基频 + 泛音，听感区分度更好
        t = i / rate
        env = min(1.0, (n - i) / rate / 0.05) * min(1.0, t / 0.02)
        v = 0.6 * env * (
            math.sin(2 * math.pi * freq * t)
            + 0.3 * math.sin(2 * math.pi * freq * 2 * t)
        )
        frames += struct.pack("<h", int(v * 22000))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


def make_png(path: Path, rgb: tuple[int, int, int]) -> None:
    """最小 1x1 PNG（zlib+struct 纯标准库）。"""
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = zlib.compress(bytes([0, *rgb]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")
    )


# ── 主流程（图驱动）──

def main() -> None:
    from app.repo.graph_repo import get_client

    c = get_client()
    stem = "chapter01_新皮肤"
    sec = "sec04_碰壁与投资"

    # 1) 25_剧本：设计简报 + sec04 outline + 台词.ink（从图行重建）
    d = ROOT / "25_剧本" / f"{stem}"
    (d / sec).mkdir(parents=True, exist_ok=True)
    ch = c.run("MATCH (ch:Chapter {chapter_no:1}) RETURN ch.title AS t, ch.summary AS s")[0]
    (d / "设计简报.md").write_text(
        f"# {ch['t']} · 设计简报（mock）\n\n> 本章概要：{ch['s']}\n\n"
        "## 分节规划（10 节，情感弧）\n\n"
        "sec00 酒店醒来 → sec01 天台对峙 → sec02 街头试水 → sec03 转账风波 → "
        "sec04 碰壁与投资 → sec05 直播间初体验 → sec06 首播之夜 → sec07 星耀试训 → "
        "sec08 不说破 → sec09 咖啡店邀约\n\n"
        "## 情感弧\n\n坠入（00-01）→ 挣扎（02-04）→ 微光（05-06）→ 考验（07-08）→ 靠近（09）\n",
        encoding="utf-8",
    )
    rows = c.run(
        """
        MATCH (:Section {id:'QW7rkkfJwL'})-[:has_outline]->(:SecOutline)-[:produces]->(sc:SecScript)-[p:produces]->(l:LineAudio)
        RETURN sc.scene_blocks AS blocks, l.op AS op, l.who AS who, l.text AS text, l.bed AS bed,
               l.scene_block_id AS block, l.voice_key AS vk
        ORDER BY p.order
        """
    )
    blocks = json.loads(rows[0]["blocks"].replace("'", '"')) if isinstance(rows[0]["blocks"], str) else rows[0]["blocks"]
    ink = [f"// 碰壁与投资（mock 重建，与图行一致）", ""]
    scene_name = {b["block"]: b["scene_name"] for b in blocks}
    cur = None
    for r in rows:
        if r["block"] != cur:
            cur = r["block"]
            ink += [f"=== {cur} // {scene_name.get(cur, '')}", ""]
        op, who, text = r["op"], r["who"], r["text"]
        if op == "say":
            ink.append(f"{who}:{text}")
        elif op == "narrate":
            ink.append(f"旁白:{text}")
        elif op == "transition":
            ink.append(f"sfx:{text}")
        elif op == "bed_start":
            ink.append(f"bed+ {r['bed']} // {text}")
        elif op == "bed_end":
            ink.append(f"bed- {r['bed']}")
        ink.append("")
    (d / sec / "台词.ink").write_text("\n".join(ink), encoding="utf-8")
    (d / sec / "outline.md").write_text(
        "# 碰壁与投资 · 提纲（mock）\n\n上午南滨路晨跑渣男话术被技术流零回应层层剥落——剧本第一次失效；"
        "中午林梦提议直播、设备款投资，服从度从此有经济解释。\n", encoding="utf-8",
    )

    # 2) 15_声音：sec04 全部有 voice_key 的行 → 母带 wav；transition/bed_start 行 → ambient_track wav
    made = 0
    for i, r in enumerate(rows):
        key = r.get("vk")
        if key and not r.get("ambient_track"):
            p = ROOT / "15_声音" / stem / r["block"] / f"{key}.wav"
            if not p.exists():
                make_wav(p, freq=220 + (i % 12) * 55)
                made += 1
    amb = c.run(
        """
        MATCH (:Section {id:'QW7rkkfJwL'})-[:has_outline]->(:SecOutline)-[:produces]->(:SecScript)-[:produces]->(l:LineAudio)
        WHERE l.ambient_track IS NOT NULL
        RETURN l.ambient_track AS t, l.scene_block_id AS b
        """
    )
    for j, r in enumerate(amb):
        p = ROOT / "15_声音" / stem / r["b"] / f"{r['t']}.wav"
        if not p.exists():
            make_wav(p, freq=500 + j * 80, seconds=0.6)
            made += 1

    # 3) 14_声音设计：江烈 3 候选 × (1 ref + 3 情绪)
    chars_freq = {"候选A": 180, "候选B": 240, "候选C": 300}
    cand_dir = ROOT / "14_声音设计" / "江烈" / "candidates"
    manifest = {"character": "江烈", "note": "mock candidates manifest", "candidates": []}
    for cname, f0 in chars_freq.items():
        entry = {
            "name": cname,
            "instruct": f"mock {cname}：低沉浑厚实声有力，语速偏快起音硬（{f0}Hz 基频）",
            "ref_path": f"14_声音设计/江烈/candidates/{cname}/ref.wav",
            "audios": [],
        }
        for emo, mul in (("平静", 1.0), ("愤怒", 1.3), ("温柔", 0.8)):
            rel = f"14_声音设计/江烈/candidates/{cname}/{emo}.wav"
            p = ROOT / rel
            if not p.exists():
                make_wav(p, freq=f0 * mul, seconds=0.5)
            entry["audios"].append({"emotion": emo, "path": rel})
        if not (cand_dir / cname / "ref.wav").exists():
            make_wav(cand_dir / cname / "ref.wav", freq=f0, seconds=1.0)
        manifest["candidates"].append(entry)
    cand_dir.mkdir(parents=True, exist_ok=True)
    (cand_dir / "candidates.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    # 4) 06_角色美术：江烈设计图（status=0 待生成，mock 成「已有图」演示图片审）+ prompt
    jl = ROOT / "06_角色美术" / "江烈"
    make_png(jl / "设计图.png", (200, 60, 40))
    (jl / "prompt.md").write_text(
        "# 江烈 · 三视图设计图 prompt（mock）\n\n22 岁电竞队长，黑色短发利落，眉骨深，肩宽背厚，站姿压场。\n",
        encoding="utf-8",
    )

    # 5) 13_BGM：等归档的两个 BGM wav + md
    for b in c.run("MATCH (:Scene)-[:has_bgm]->(g:BgmTrack {status:1}) RETURN g.name AS n, g.prompt AS p"):
        p = ROOT / "13_BGM" / f"{b['n']}.wav"
        if not p.exists():
            make_wav(p, freq=150, seconds=1.2)
        (ROOT / "13_BGM" / f"{b['n']}.md").write_text(
            f"# {b['n']}（mock BGM）\n\nprompt: {b['p'] or '—'}\n", encoding="utf-8",
        )

    print(f"mock 完成：wav 新建 {made}，详见 {ROOT}/25_剧本 {ROOT}/14_声音设计 {ROOT}/15_声音 {ROOT}/06_角色美术 {ROOT}/13_BGM")


if __name__ == "__main__":
    main()
