"""透明立绘直通 + 头位归一化 → 透明 PNG（chapter-publisher 搬运处理层）。

2026-09 起立绘由生成端直出透明 PNG（透明措辞与 --background transparent
参数双在场触发），绿幕抠图管线（4 角采样 / 连续 alpha / grabCut /
despill）整体退役。本脚本只做两件事：

  ① 输入校验：源图必须带 alpha 通道，否则直接报错——不兼容旧绿底输入，
     存量绿底立绘一律重新生成，不做兼容抠图
  ② 头位归一化：**人物前景高 ÷ 7.5 头身**作尺度 → 各变体等高（默认 1200）；
     垂直贴顶贴底（alpha bbox 上下）；**水平以 YuNet 双眼中心为锚**——左右对称取
     max(到左身,到右身) 使双眼中心落在 PNG 水平中线 ⇒ 运行时居中显示，任意立绘
     切换头部水平 x 恒定；等高+贴顶 ⇒ 头部 y 同水平线。身体不对称可能单侧留透明
     （为保双眼居中）。PNG 宽高比不固定 2:3，需 PortraitLayer 按实际宽高比
     显示。回退：L2 用 bbox 中心（无脸），L3 贴底 letterbox。

原图（06_/07_）不动，只写输出路径。CLI 调用形态不变：
``python process_portrait.py <src> -o <dst>``，chapter-publisher 调用处零改动。

依赖：opencv-python（自带 numpy）。YuNet onnx 与本脚本同目录自带
（``face_detection_yunet.onnx``，opencv zoo 官方模型）。

中文路径：cv2.imread/imwrite 不支持非 ASCII 文件名，统一用
np.fromfile + imdecode / imencode + tofile。

退码：0 成功 / 1 处理失败（含输入无 alpha 通道）/ 2 参数错（与 99_game/tools 既有工具对齐）。
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

# ── 画布与归一化规范（默认，CLI 可调）──────────────────────────────
CANVAS_W, CANVAS_H = 800, 1200          # 输出画布（2:3，与 PortraitLayer 素材比一致）
HEAD_RATIO = 7.5                         # 头身比（00_init/美术风格.md：7.5 头身）
DEFAULT_TARGET_HEAD_PX = round(CANVAS_H / HEAD_RATIO)   # 160：目标头长（=画布高/7.5），缩放使各变体人物等高（高 1200）

_HERE = Path(__file__).resolve().parent
_YUNET_PATH = _HERE / "face_detection_yunet.onnx"


# ── 中文路径 IO ───────────────────────────────────────────────────
def imread_unicode(path: str):
    """cv2.imread 不支持非 ASCII 路径；用 fromfile + imdecode 绕过。
    IMREAD_UNCHANGED 保住 alpha 通道（透明直通必需，IMREAD_COLOR 会静默丢弃）。"""
    return cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_UNCHANGED)


def imwrite_unicode(path: str, img) -> None:
    """cv2.imwrite 不支持非 ASCII 路径；用 imencode + tofile 绕过。"""
    ext = Path(path).suffix or ".png"
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise RuntimeError("imencode 失败: %s" % path)
    buf.tofile(str(path))


# ── 头位归一化 ────────────────────────────────────────────────────
def _fallback_letterbox(rgba):
    """L3：贴底居中、等比放进画布（不做头位对齐）。"""
    H, W = rgba.shape[:2]
    s = min(CANVAS_W / W, CANVAS_H / H)
    nw, nh = max(1, int(W * s)), max(1, int(H * s))
    sc = cv2.resize(rgba, (nw, nh), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)
    canvas = np.zeros((CANVAS_H, CANVAS_W, 4), np.uint8)
    x0 = (CANVAS_W - nw) // 2
    y0 = CANVAS_H - nh                               # 贴底（与 PortraitLayer 脚踩地面线一致）
    canvas[y0:y0 + nh, x0:x0 + nw] = sc
    return canvas


def normalize_head(rgba, target_head_px: int,
                   score_thr: float = 0.5, yunet_path: Path = _YUNET_PATH):
    """头位归一化：等高缩放 + 以双眼中心为水平锚定裁剪（头部水平居中）。

    尺度：人物前景高 ÷ 7.5 头身（稳定）→ 各变体人物等高（默认 1200）。裁剪：垂直贴顶
    贴底（alpha bbox 上下）；水平以 YuNet 双眼中心为锚——左右相对双眼中心对称取
    max(双眼到左身, 双眼到右身)，使双眼中心落在 PNG 水平中线。⇒ 运行时 PortraitLayer
    居中显示，**任意立绘切换头部（双眼）水平 x 恒定**；等高+贴顶 ⇒ 头部 y 同水平线。
    身体不对称时可能单侧留透明（为保双眼居中）。输出 PNG 宽高比不固定 2:3，需 PortraitLayer
    按实际宽高比显示。YuNet 失败则用 bbox 中心（L2），前景过小贴底 letterbox（L3）。

    返回 (out_rgba, level, info)：level ∈ {'L1','L2','L3'}。
    """
    H, W = rgba.shape[:2]
    alpha = rgba[:, :, 3]
    ys, xs = np.where(alpha > 127)

    if len(xs) == 0 or (ys.max() - ys.min()) < H * 0.2:
        return _fallback_letterbox(rgba), "L3", "no foreground"
    person_h = float(ys.max() - ys.min())
    s = target_head_px / (person_h / HEAD_RATIO)     # 等高（默认 → 人物高 1200）
    new_w, new_h = max(1, int(round(W * s))), max(1, int(round(H * s)))
    interp = cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR
    scaled = cv2.resize(rgba, (new_w, new_h), interpolation=interp)

    a2 = scaled[:, :, 3]
    ys2, xs2 = np.where(a2 > 127)
    if len(xs2) == 0:
        return scaled, "L3", "no fg after scale"
    top, bot = int(ys2.min()), int(ys2.max())
    lf, rt = int(xs2.min()), int(xs2.max())

    # 水平锚：YuNet 双眼中心（缩放后坐标）/ bbox 中心（L2）
    cx_s = (lf + rt) / 2.0
    level = "L2"
    if yunet_path.exists():
        try:
            bgr = cv2.cvtColor(rgba, cv2.COLOR_BGRA2BGR)
            det = cv2.FaceDetectorYN_create(str(yunet_path), "", (W, H), score_thr, 0.3, 1)
            det.setInputSize((W, H))
            _, faces = det.detect(bgr)
            if faces is not None and len(faces) > 0:
                f = faces[0]                          # x,y,w,h,re_x,re_y,le_x,le_y,...,score
                cx_s = (float(f[4]) + float(f[6])) / 2.0 * s
                level = "L1"
        except cv2.error:
            pass

    # 双眼中心居中：左右对称取 max(到左身,到右身)，含整个身体；越界侧补透明
    half_w = max(cx_s - lf, rt - cx_s)
    x0 = int(round(cx_s - half_w))
    x1 = int(round(cx_s + half_w))
    out_w = x1 - x0 + 1
    out = np.zeros((bot - top + 1, out_w, 4), np.uint8)
    sx0 = max(x0, 0)
    sx1 = min(x1, scaled.shape[1] - 1)
    if sx1 >= sx0:
        out[:, sx0 - x0:sx1 - x0 + 1] = scaled[top:bot + 1, sx0:sx1 + 1]
    return out, level, "person_h=%d s=%.3f out=%dx%d eye@center" % (
        int(person_h), s, out.shape[1], out.shape[0])


# ── 主管线 ────────────────────────────────────────────────────────
def process(src: str, dst: str, *,
            target_head_px: int = DEFAULT_TARGET_HEAD_PX,
            normalize: bool = True, score_thr: float = 0.5) -> dict:
    rgba = imread_unicode(src)
    if rgba is None:
        raise RuntimeError("读图失败（路径/格式）: %s" % src)
    if rgba.ndim != 3 or rgba.shape[2] != 4:
        raise RuntimeError(
            "输入无 alpha 通道（shape=%s）: %s —— 立绘自 2026-09 起由模型直出透明 PNG"
            "（提示词英文透明措辞驱动），绿幕抠图管线已退役；请重新生成该立绘后再发布"
            % (rgba.shape, src))
    # 软告警（不阻断）：有 alpha 通道但 alpha=0 占比 <1%——疑似生成期透明措辞失效的不透明图转存
    if (rgba[:, :, 3] == 0).mean() < 0.01:
        sys.stderr.write("警告: alpha=0 占比 <1%%，疑似不透明图（透明措辞未生效？）: %s\n" % src)

    if normalize:
        rgba, level, info = normalize_head(rgba, target_head_px, score_thr)
    else:
        rgba = _fallback_letterbox(rgba)
        level, info = "skip", "normalize disabled"

    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    imwrite_unicode(dst, rgba)
    return {"level": level, "info": info,
            "out_size": "%dx%d" % (rgba.shape[1], rgba.shape[0])}


def main(argv) -> int:
    p = argparse.ArgumentParser(description="透明立绘直通 + 头位归一化 → 透明 PNG（无 alpha 通道输入直接报错；绿幕抠图已退役）")
    p.add_argument("src", help="源立绘 PNG（项目根相对路径）")
    p.add_argument("-o", "--out", required=True, help="输出透明 PNG 路径")
    p.add_argument("--target-head-px", type=int, default=DEFAULT_TARGET_HEAD_PX,
                   help="目标头长像素（默认 %d，= 画布高/7.5 头身）" % DEFAULT_TARGET_HEAD_PX)
    p.add_argument("--score-thr", type=float, default=0.5, help="YuNet 检测置信度阈值（默认 0.5）")
    p.add_argument("--no-normalize", action="store_true", help="跳过头位归一化，仅贴底 letterbox 居中")
    args = p.parse_args(argv)

    if not Path(args.src).is_file():
        sys.stderr.write("源文件不存在: %s\n" % args.src)
        return 2
    try:
        r = process(args.src, args.out,
                    target_head_px=args.target_head_px,
                    normalize=not args.no_normalize, score_thr=args.score_thr)
    except (OSError, RuntimeError, cv2.error) as e:
        sys.stderr.write("处理失败: %s\n" % e)
        return 1
    print("OK: %s -> %s [%s] (level=%s, %s)" % (
        args.src, args.out, r["out_size"], r["level"], r["info"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
