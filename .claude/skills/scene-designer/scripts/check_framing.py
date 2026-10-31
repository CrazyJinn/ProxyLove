# -*- coding: utf-8 -*-
"""check_framing.py —— galgame 背景立绘安全区检查器(机位质量门)。

立绘渲染事实(99_game PortraitLayer.gd / DialogueBox.gd):
  立绘贴底、高约 87% 屏高;左/中/右三槽,左槽左缘锚 x=10%、右槽右缘锚 x=90%;
  对话框遮底部 23.4%。⇒ 背景物件 bbox 底缘深入 y>65% 且横向落入 x∈[10,90] 带,
  即与立绘穿插("近景遮挡物导致两侧立绘突兀")。

规则:
  豁免:opening(门窗,立绘可挡其前)与低矮面物件(高度<0.35m:路面/人行道/斑马线/石滩)。
  R1 近景侵入脚区: depth<7m ∧ bbox 底缘>65% ∧ 与 [10,90] 横向重叠>8% 画宽
  R2 近景大块压中: depth<4m ∧ 面积>20% ∧ 中心 x∈(15,85) ∧ 底缘>45%(远景墙元豁免)

用法:
  python .claude/skills/scene-designer/scripts/check_framing.py [room.yml ...]  # 默认扫 07_场景美术/ 全部 yaml
  python .claude/skills/scene-designer/scripts/check_framing.py --strict      # 有 FAIL 即 exit 1(供门禁)
退出码:0=全 PASS;1=存在 FAIL(--strict 时非零退出才阻断,默认恒 0 便于人读)
"""
import sys
from pathlib import Path

import yaml

# slice_scenes 已按「公用脚本」归 .claude/scripts/（本脚本单 skill 引用归 skill scripts/）
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import slice_scenes as ss

ASPECT = 1.5          # 1536x1024
PORTRAIT_X = (10, 90)  # 立绘三槽带(左槽左缘/右槽右缘锚点)
FOOT_Y = 65            # 脚区线:bbox 底缘超过即深入立绘脚区
OVERLAP_MAX = 8        # 与立绘带允许的最大横向重叠(% 画宽)
NEAR_R1 = 7.0          # R1 近景深度阈值(m)
NEAR_R2 = 4.0          # R2 近中景深度阈值(m)(远景墙元豁免)
NEAR_R3 = 4.0          # R3 近中景深度阈值(m)
CENTER_IMG_H = 20.0    # R3 中央大件像高阈值(%):房间正中挡视线大件
AREA_MAX = 20.0        # R2 面积阈值(%)
LOW_HEIGHT = 0.35      # 低矮面物件豁免高度(m)
IMG_H_MIN = 18.0       # R1 物件投影像高阈值(%):小像物件立绘挡前即可,不判穿插


def check_item(it: dict, low_ids: set) -> list[str]:
    """返回该物件的违规原因列表(空=通过)。"""
    if it.get("kind") == "opening" or it["id"] in low_ids:
        return []
    x, y, w, h = it["bbox"]
    d = it["depth"]
    overlap = max(0, min(x + w, PORTRAIT_X[1]) - max(x, PORTRAIT_X[0]))
    bottom = y + h
    area = w * h / 100.0
    cx = x + w / 2
    reasons = []
    if d < NEAR_R1 and bottom > FOOT_Y and overlap > OVERLAP_MAX and h > IMG_H_MIN:
        reasons.append(f"R1脚区(底{bottom:.0f}% 叠{overlap:.0f}% 深{d}m 像高{h:.0f}%)")
    if d < NEAR_R2 and area > AREA_MAX and 15 < cx < 85 and bottom > 45:
        reasons.append(f"R2大块({area:.0f}%)")
    if d < NEAR_R3 and 32 < cx < 68 and h > CENTER_IMG_H and bottom > 45:
        reasons.append(f"R3中央大件(像高{h:.0f}% 深{d}m)")
    return reasons


def run(paths: list[Path]) -> int:
    fail_cnt = 0
    for yf in paths:
        data = yaml.safe_load(open(yf, encoding="utf-8"))
        low_ids = {o["id"] for o in data["objects"] if (o.get("size") + [0])[1] < LOW_HEIGHT}
        for scn in data["scenes"]:
            out2d, _ = ss.project_scene(data, scn, ASPECT, yf.stem)
            fails = [(it["id"], it["bbox"], it["depth"], check_item(it, low_ids))
                     for it in out2d["objects"] if check_item(it, low_ids)]
            if fails:
                fail_cnt += 1
                print(f"FAIL {scn['scene_name']}  ({yf})")
                for fid, bb, d, rs in fails:
                    print(f"     {fid:16s} bbox=[{', '.join(str(round(v)) for v in bb)}] depth={d}  {'; '.join(rs)}")
            else:
                print(f"PASS {scn['scene_name']}  ({yf})")
    print(f"\n== FAIL 机位: {fail_cnt} ==")
    return fail_cnt


if __name__ == "__main__":
    here = Path(__file__).resolve().parents[4] / "07_场景美术"  # 项目根产物区（脚本已内化到 skill）
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict = "--strict" in sys.argv
    paths = [Path(a) for a in args] or sorted(set(here.rglob("*.yml")) - set(here.rglob("prompt.yml")))
    n = run(paths)
    sys.exit(1 if (strict and n) else 0)
