---
name: infra-image-generator
description: |
  OfoxAI Images API 调用层（纯产出）。读取 prompt 文件、调用 API 生成图片并返回图片路径。
  文生图（无参考图）/ 图生图（带参考图），由是否有 ref_image_path 决定。
  不读写图数据库、不写 status。在需要生成美术图片或被其他 skill 调用时使用。
argument-hint: <prompt_path> <output_path> [<ref_image_path>]
arguments:
  - prompt_path
  - output_path
  - ref_image_path
allowed-tools: Read, Bash, Write, Edit
---

> **纯产出层**：本 skill 只读取 prompt 文件、调用 API 生成图片并**返回图片路径**，**不读写图数据库、不写 status**。节点 `image_path` 与 `status` 由调用方（生产 skill）在「保存结果」步统一写入。`status=-1`（作废重做）时调用方会再次调用本 skill 重新生成并**覆盖**旧图片——本 skill 每次被调用都重新生成。

# OfoxAI 图片生成

脚本：`${CLAUDE_SKILL_DIR}/scripts/ofoxai_api.py`。**不组装提示词、不读取风格文件、不查目标节点**——prompt 文件内容由调用方（prompt-assembler）先行产出。API Key 自动从工作目录向上搜索 `settings.json` 的 `ofox_api_key` 字段，无需传参。

## 调用方式

prompt 经 stdin 管道直送（支持多行 markdown，不经 shell 字面量）。是否传 `--image` 决定生成方式——参考图路径由调用方从已存在的前驱节点查得后传入：

```bash
# 文生图（如 SceneLayer background，无参考图）
cat "<prompt_path>" \
  | python "${CLAUDE_SKILL_DIR}/scripts/ofoxai_api.py" submit --prompt-stdin \
      --size 1536x1024 -o "<output_path>"

# 图生图（如 DesignSheet 用户参考照片 / IllusDesign / StandingIllustration，以参考图为底图）
cat "<prompt_path>" \
  | python "${CLAUDE_SKILL_DIR}/scripts/ofoxai_api.py" submit --prompt-stdin \
      --image "<ref_image_path>" --size 1024x1536 -o "<output_path>"
```

成功时 stdout 输出 JSON：`{"status": "done", "image_path": "<output_path>"}`——把 `image_path` 返回给调用方，由其写入节点 `image_path` 字段。

## 判定规则

**`--size`**：① prompt 文本写明分辨率（如「分辨率 1024×1536」）以其为准；② 否则按产物类型——横图（背景/设计图）`1536x1024`、竖图（立绘）`1024x1536`，图生图可沿用参考图比例；③ 仍无法确定时向用户确认。脚本缺省 `1536x1024`。本项目只有 3 种合法值，**必须用 ASCII `x` 分隔，勿用中文乘号 `×`**：`1024x1024` / `1024x1536` / `1536x1024`。

**透明背景（措辞 + 参数双在场）**：OfoxAI 服务端行为已变——prompt 英文透明措辞与 `--background transparent` **须同时在场**才稳定直出 RGBA（2026-09-13 生产实测：仅措辞连续 3 次返回 RGB，补传参数后连续 4 次全过；当时结论还要求 `--output-format png`，现已全局强制 png，无需显式传）。需透明的调用必须同时带：

- prompt 画风段固化英文措辞句：`fully transparent background with alpha channel, no background elements`
- CLI 参数：`--background transparent`

透明产物由调用方校验（alpha=0 像素占比 > 1%，char-stand-designer 的 `check_transparency.py`）。

## submit 参数

| 参数 | 必填 | 说明 |
|------|:----:|------|
| prompt / `--prompt-stdin` | Y | prompt 文本；长文一律走 stdin 管道 |
| `--size` | Y | `1024x1024` / `1024x1536` / `1536x1024`（ASCII `x`） |
| `--image` | N | 参考图路径，可多次指定（多图引用） |
| `--background` | N | 识别到透明背景需求时传 `transparent` |
| `--output-format` | - | 脚本已强制 `png`（项目统一格式，无其他格式） |
| `-o, --output` | N | 直接保存路径（跳过 wait），推荐始终使用 |
| `--model` | N | 默认 `openai/gpt-image-2.5-sunburst` |
| `--n` | N | 生成数量，默认 1 |
| `--quality` | - | 脚本已强制 `medium`（成本控制），传了也被覆盖 |

脚本对 `moderation` 写死 `low`（叙事性提示词易被安全审核误拒，无需传参）。

## 错误处理

脚本对 429/502/503/504 与网络异常**自动重试**（5/10/20s 退避，共 3 次）。仍失败时按状态码处理：

| HTTP 状态码 | 处理 |
|-------------|------|
| 400 | 检查参数格式和尺寸（是否误用了中文乘号 `×`） |
| 401 | 检查 API Key（settings.json 的 `ofox_api_key`） |
| 402 | 余额不足，充值后重试 |
| 429 | 自动重试已耗尽，等待更久后重跑 |
| 500 | 服务端错误，重跑 |

生成失败（输出非 `status: done`）**不得写 image_path/status**，由调用方决定重试或报告。

## 其他命令

`wait '<json|file>' <output.png>`（从 submit 未直存的结果 JSON 落盘）、`download <url> <output.png>`（下载直链）——submit `-o` 直存模式下通常用不到。

## 参考文档

- [完整 API 参数](references/api-reference.md)
