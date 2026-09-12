#!/usr/bin/env python3
"""
gpt-image-2.5-sunburst 透明背景能力 demo
=========================================

在 infra-image-generator 的 ofoxai_api.py 之上做三件事：

1. 模型换成 openai/gpt-image-2.5-sunburst
2. 请求额外携带 background=transparent（原 submit_task 不带该参数，
   本脚本镜像其两条请求路径并扩展）
3. 为角色伊芙（eva，id NvCkQmFPFp）用固定提示词（06_角色美术/伊芙/prompt.md，
   去掉纯绿背景行）跑一次文生图 + 一次图生图（图生图以文生图产物为参考图），
   最后用 PIL 检测两张 PNG 是否真的带透明像素。

2026-09-09 对照实验结论（OfoxAI，三轮共 7 次生成）：
- **透明由提示词英文措辞驱动**（"fully transparent background with alpha channel"），
  中文「置于全透明背景」不触发、完全不描述背景也不触发。
- `background=transparent` 与 `output_format=png` 两个 API 参数在 OfoxAI 上
  **均未观察到效果**（显式传参 + 无背景描述提示词 → 两端点仍返回 RGB）；
  参数仍随请求发送，待 OfoxAI 将来实现后自动受益。
- generations 与 edits 两个端点行为一致：加英文 transparent 措辞都出 RGBA。
- 主体像素 alpha≈253（近不透明非 255），透明检测判据必须用 alpha=0 像素占比。
- 请求 1024x1024 实际返回 1024x1536 竖图。

运行：python demo/demo_sunburst.py（在项目根执行）
产物：demo/eva_t2i.png（文生图）、demo/eva_i2i.png（图生图）、eva_i2i_onwhite.jpg（白底预览）
"""

import json
import sys
from pathlib import Path

# 复用 skill 脚本：API key 定位（向上搜索 settings.json）与结果保存
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "skills" / "infra-image-generator" / "scripts"))
import ofoxai_api  # noqa: E402  顶层加载 API_KEY / API_BASE / save_result

import requests  # noqa: E402

DEMO_DIR = Path(__file__).resolve().parent
MODEL = "openai/gpt-image-2.5-sunburst"  # 沿用仓库 openai/ 前缀约定
SIZE = "1024x1024"

# 伊芙固定提示词（06_角色美术/伊芙/prompt.md），去掉「#00FF00 纯绿色背景（chroma key green）」
# 叙述（原纯绿底是抠图工作流），替换为英文 transparent 措辞——**这是唯一实测能触发透明的写法**
# （中文「全透明背景」/完全不描述背景/API 参数 background+output_format 均不触发，共 7 次实验）
T2I_PROMPT = """# 设计图提示词

## 画风

1. **画面类型**：角色设计图，全身三视图（正面、侧面、背面），静态站姿，双手自然垂于身侧，三视角外观一致
2. **线条**：Korean Flat-shading Illustration，细到中等线稿；外轮廓线略粗、内部结构线较细、面部线条极细；线条干净利落略柔和，平滑干净；深棕色近黑的线条颜色；外轮廓到细节有粗细过渡
3. **上色与光影**：Korean Cel-shading 平涂（Flat-shading），干净色块，分层平涂阴影；阴影边缘为半硬边（比硬边赛璐璐略柔，带轻微渐变过渡）；中等明暗对比；单主光源、简单光照、弱环境光；高光简洁点缀；皮肤轻微渐变过渡（非纯平面）
4. **比例**：7.5 头身；少女体态；写实度 6/10，动画风 60% + 写实风 40%
5. **色调**：清爽高级的中性偏暖色调；中等饱和度；中等色彩对比（靠明暗与色块层次）
6. **背景**：fully transparent background with alpha channel, no background elements
7. **分辨率**：1024 × 1024

## 角色设定

1. **整体气质**：约 165cm，柔和匀称的少女体态，肌肤透着微光，梦幻温柔、略带朦胧的天使之姿；仿佛随时会飘走的柔软云朵；形状语言以圆形为主，整体圆润温柔
2. **面部**：希腊人面孔，脸庞圆润温柔，瓷白肌肤透着微光；银色圆杏眼，瞳孔里似有星辰流动，常有失神的朦胧感，眉眼弯弯带着梦呓般的朦胧；饱满唇形；常有发丝不经意垂落脸颊
3. **发型**：银色超长大波浪长发，如瀑布般垂至腰际，质感柔和，发丝飘逸
4. **贴身基础衣物**：穿着深色基础衣物（黑色贴身背心 + 深色短裤），与瓷白肤色形成高对比，仅作为外形参照，不涉及服装设计细节
5. **外貌配色**：银色长发、银色瞳孔、瓷白肌肤——整体梦幻朦胧的银白冷调，由肌肤微光与瞳孔星辰流动的细节柔化
6. **特殊标记**：无疤痕、纹身、胎记或身体异征"""

# 图生图：同一固定画风的立绘转化——以文生图三视图为参考，单张正面全身立绘
I2I_PROMPT = """# 立绘提示词

依据参考设计图，保持同一角色外观一致性（面部、发型、体态、贴身基础衣物、外貌配色全部沿用），输出单张正面全身立绘。

## 画风

1. **画面类型**：角色立绘，全身正面视角，静态站姿，双手自然垂于身侧
2. **线条**：Korean Flat-shading Illustration，细到中等线稿；外轮廓线略粗、内部结构线较细、面部线条极细；线条干净利落略柔和，平滑干净；深棕色近黑的线条颜色；外轮廓到细节有粗细过渡
3. **上色与光影**：Korean Cel-shading 平涂（Flat-shading），干净色块，分层平涂阴影；阴影边缘为半硬边（比硬边赛璐璐略柔，带轻微渐变过渡）；中等明暗对比；单主光源、简单光照、弱环境光；高光简洁点缀；皮肤轻微渐变过渡（非纯平面）
4. **比例**：7.5 头身；少女体态；写实度 6/10，动画风 60% + 写实风 40%
5. **色调**：清爽高级的中性偏暖色调；中等饱和度；中等色彩对比（靠明暗与色块层次）
6. **背景**：主体完整居中，fully transparent background with alpha channel, no background elements, no cast shadow on background"""


def submit_with_background(prompt, *, model=MODEL, size=SIZE, n=1,
                           quality="low", image=None, background="transparent",
                           output_format="png"):
    """镜像 ofoxai_api.submit_task，额外携带 background + output_format 参数。

    文生图走 /images/generations（JSON），图生图走 /images/edits（multipart），
    与原脚本一致（moderation=low 写死）；额外字段：
    - background=transparent：要求透明背景（OfoxAI 实测未生效，见模块 docstring）
    - output_format=png：gpt-image 文档要求透明需显式 png 输出格式（实测同未生效）
    """
    payload = {"model": model, "prompt": prompt, "n": n, "size": size,
               "response_format": "b64_json", "quality": quality,
               "moderation": "low", "background": background,
               "output_format": output_format}

    if image:
        files = [("image", open(p, "rb")) for p in image]
        resp = requests.post(
            f"{ofoxai_api.API_BASE}/images/edits",
            headers={"Authorization": f"Bearer {ofoxai_api.API_KEY}"},
            data=payload, files=files, timeout=180,
        )
        for _, f in files:
            f.close()
    else:
        resp = requests.post(
            f"{ofoxai_api.API_BASE}/images/generations",
            headers={"Authorization": f"Bearer {ofoxai_api.API_KEY}"},
            json=payload, timeout=180,
        )

    result = resp.json()
    if resp.status_code != 200:
        raise RuntimeError(f"API error ({resp.status_code}): {json.dumps(result, ensure_ascii=False)}")
    return result


def check_transparency(path):
    """检测 PNG 是否真透明背景。

    口径注意：gpt-image 系主体像素 alpha 常为 ~253（近不透明但非 255），
    所以「alpha<255 占比」会把整个主体也算进去（实测 1.0，无意义）；
    判透明背景看 **alpha=0 的像素占比** 是否显著（>1%）。
    """
    from PIL import Image
    img = Image.open(path)
    info = {"path": str(path), "format": img.format, "mode": img.mode}

    has_alpha = "A" in img.getbands() or (img.mode == "P" and "transparency" in img.info)
    if not has_alpha:
        info.update(has_alpha_channel=False, transparent=False,
                    note="无 alpha 通道（缺英文 transparent 措辞时模型不出透明）")
        return info

    alpha = img.convert("RGBA").getchannel("A")
    hist = alpha.histogram()
    total = alpha.width * alpha.height
    zero_px = hist[0]                   # 完全透明（被扣除的背景）
    sub255_px = sum(hist[:255])         # 非 255（含半透明主体，仅作参考）
    info.update(
        has_alpha_channel=True,
        min_alpha=alpha.getextrema()[0],
        alpha_zero_px=zero_px,
        alpha_zero_ratio=round(zero_px / total, 4),
        non_opaque_ratio=round(sub255_px / total, 4),
        transparent=zero_px > total * 0.01,
    )
    return info


def save_onwhite_preview(path, out_path):
    """透明 PNG 合成白底 JPG 预览（透明图的显示效果因查看器而异）。"""
    from PIL import Image
    img = Image.open(path).convert("RGBA")
    Image.alpha_composite(
        Image.new("RGBA", img.size, (255, 255, 255, 255)), img
    ).convert("RGB").save(out_path, quality=85)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    check_only = "--check-only" in sys.argv  # 只重跑检测，不重新生成（省 API 费用）
    summary = {"model": MODEL, "background": "transparent"}

    if check_only:
        t2i_path, i2i_path = str(DEMO_DIR / "eva_t2i.png"), str(DEMO_DIR / "eva_i2i.png")
    else:
        print(f"[1/3] 文生图（{MODEL}，background=transparent）...")
        t2i = ofoxai_api.save_result(
            submit_with_background(T2I_PROMPT), str(DEMO_DIR / "eva_t2i.png"))
        print(json.dumps(t2i, ensure_ascii=False, indent=2))
        if t2i.get("status") != "done":
            sys.exit(f"文生图失败: {t2i}")
        t2i_path = t2i["image_path"]

        print("[2/3] 图生图（以文生图产物为参考图）...")
        i2i = ofoxai_api.save_result(
            submit_with_background(I2I_PROMPT, image=[t2i_path]),
            str(DEMO_DIR / "eva_i2i.png"))
        print(json.dumps(i2i, ensure_ascii=False, indent=2))
        if i2i.get("status") != "done":
            sys.exit(f"图生图失败: {i2i}")
        i2i_path = i2i["image_path"]

    print("[3/3] 透明背景检测...")
    summary["t2i"] = {"transparency": check_transparency(t2i_path)}
    summary["i2i"] = {"transparency": check_transparency(i2i_path)}
    if summary["i2i"]["transparency"]["has_alpha_channel"]:
        preview = str(DEMO_DIR / "eva_i2i_onwhite.jpg")
        save_onwhite_preview(i2i_path, preview)
        summary["i2i"]["onwhite_preview"] = preview

    print("\n===== 汇总 =====")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
