#!/usr/bin/env python3
"""Fact 后效实证扫描：每条 Fact 的特征词扫全部剧本正文，找成立节之外的后续引用。
用法: uv run python scan_fact_usage.py  (工作目录 /home/ubuntu/ProxyLove)
"""
import json, re, glob, unicodedata
from pathlib import Path

ROOT = Path("/home/ubuntu/ProxyLove/25_剧本")
# fid -> (成立节, title, [特征词组] 每组=AND词列表, 命中任一组即算引用)
FACTS = {
 "RxhLwLmgng": ("ch00/sec02", "试炼规则", [["拯救","弱者"],["替","生活","30"],["下地狱","试炼"]]),
 "RxhLwLmgni": ("ch00/sec02", "陆择理解为找女朋友", [["拯救","女朋友"],["拯救","对象"]]),
 "RxhLwLmgnj": ("ch01/sec00", "转账66666", [["66666"],["转账","零回复"],["转账记录","删"]]),
 "RxhLwLmgnn": ("ch01/sec01", "拼命代练钱给女人", [["代练","女人"],["钱","全给"]]),
 "RxhLwLmgno": ("ch01/sec01", "幼时罚站", [["罚站"],["小时候","门外"]]),
 "RxhLwLmgnt": ("ch01/sec01", "陆择羡慕牵挂", [["羡慕","牵挂"],["无人收尸"]]),
 "RxhLwLmgnm": ("ch01/sec02", "余额86.2两单待交付", [["86.2"],["两单","待交付"]]),
 "RxhLwLmgo0": ("ch01/sec02", "代练群纪律", [["超时","移出"],["赔三倍"],["交付","踢群"],["通报","群"]]),
 "RxhLwLmgnu": ("ch01/sec03", "林梦单子规矩", [["价高","三成"],["不动她的号"],["陪玩","语音"]]),
 "RxhLwLmgny": ("ch01/sec03", "星耀离队开天窗", [["离队","一号位"],["吵翻","离队"],["开天窗"]]),
 "RxhLwLmgnl": ("ch01/sec05", "家底全景", [["房租","1800"],["设备款","8600"]]),
 "RxhLwLmgns": ("ch01/sec05", "陆择经营人生", [["人生","经营"],["当自己的"]]),
 "RxhLwLmgo8": ("ch01/sec05", "视频火了", [["视频","火"]]),
 "RxhLwLmgo4": ("ch01/sec06", "试训两轮制", [["五局","solo"],["solo","训练赛"],["两轮","试训"]]),
 "RxhLwLmgo7": ("ch01/sec07", "江烈零容忍", [["团队协作","零容忍"],["五个人的游戏"],["个人主义"]]),
 "RxhLwLmgo6": ("ch01/sec08", "沈暮雪挖人动机", [["挖人","理由"],["反对","挖"]]),
 "RxhLwLmgnr": ("ch02/sec07", "陈念张罗对象", [["张罗","对象"],["张罗","介绍"]]),
}

def norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s)

# 读全部正文
docs = {}
for f in sorted(glob.glob(str(ROOT / "ch*" / "sec*" / "*.ink")) + glob.glob(str(ROOT / "ch*" / "sec*" / "小说.md")) + glob.glob(str(ROOT / "ch*" / "sec*" / "*.md"))):
    rel = Path(f).relative_to(ROOT).parent.as_posix()
    docs.setdefault(rel, []).append(norm(Path(f).read_text(encoding="utf-8")))

order = sorted(docs.keys())
def sec_key(k):
    m = re.match(r"ch(\d+)/sec(\d+)", k)
    return (int(m.group(1)), int(m.group(2))) if m else (99, 99)
order.sort(key=sec_key)

print(f"{'成立节':<12}{'Fact':<16}{'后续引用(成立节之后)':<40}")
print("-" * 110)
verdicts = {}
for fid, (home, title, groups) in FACTS.items():
    hits = []
    for sec in order:
        if sec == home: continue
        text = "\n".join(docs.get(sec, []))
        if not text: continue
        if any(all(w in text for w in g) for g in groups):
            hits.append(sec)
    later = [h for h in hits if sec_key(h) > sec_key(home)]
    verdicts[fid] = (title, home, later)
    print(f"{home:<12}{title:<16}{', '.join(later) if later else '— 无':<40}")

print()
print("== 判定（保留判据：成立节之后有真实文本引用）==")
for fid, (title, home, later) in verdicts.items():
    print(f"{'保留' if later else '冗余-删':<8}{title}  {home} → {later}")
