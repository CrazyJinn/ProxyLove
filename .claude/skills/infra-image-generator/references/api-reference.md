# OfoxAI Images API 参考

## 端点

### 文生图
```
POST https://api.ofox.io/v1/images/generations
Content-Type: application/json
```

### 图生图（编辑）
```
POST https://api.ofox.io/v1/images/edits
Content-Type: multipart/form-data
```

## 认证
Header: `Authorization: Bearer $OFOX_API_KEY`
API Key 存储位置: 项目根目录 `settings.json` → `ofox_api_key` 字段

## 文生图参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| model | string | Y | 模型名称 |
| prompt | string | Y | 图像描述文本 |
| n | number | N | 生成数量，默认 1 |
| size | string | N | 尺寸，如 `1024x1024` |
| quality | string | N | 见下方质量参数对照 |
| response_format | string | N | `b64_json`（默认）或 `url` |
| background | string | N | `transparent` / `opaque` |
| output_format | string | N | API 支持 `png` / `jpeg` / `webp`；本项目统一 `png`（脚本已强制） |

## 图生图参数（multipart/form-data）

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| image / image[] | file | Y | 单图用 `image`，多图引用用 `image[]` |
| prompt | string | Y | 编辑指令 |
| model | string | Y | 模型名称 |
| n | number | N | 生成数量 |
| size | string | N | 输出尺寸 |
| mask | file | N | 蒙版图片（仅 gpt-image 模型，需含 alpha 通道） |
| background | string | N | 同文生图（透明需与英文措辞同时在场，2026-09-13 实测） |
| output_format | string | N | 同文生图（本项目统一 `png`，脚本已强制） |

### 多图引用
使用 `image[]` 字段名上传多张参考图片：
```bash
curl ... \
  -F "image[]=@ref1.png" \
  -F "image[]=@ref2.png" \
  -F "image[]=@ref3.png" \
  -F 'prompt=生成包含所有参考图元素的礼物篮'
```

## 质量参数对照

不同模型系列使用不同的质量值：

| 模型系列 | 可选值 | 说明 |
|---------|--------|------|
| gpt-image-2 / gpt-image-1 | `low` / `medium` / `high` / `auto` | low 用于快速草稿，high 用于最终产出 |
| dall-e-3 | `standard` / `hd` | hd 质量更高但更慢 |
| dall-e-2 | — | 不支持 quality 参数 |

## 尺寸约束（gpt-image-2）

- 最大边长: 3840px
- 两边必须是 16 的倍数
- 长短边比例不超过 3:1
- 总像素: 655,360 ~ 8,294,400
- 尺寸格式必须 ASCII `x` 分隔（`1024x1024`），传错（如中文乘号 `×`）可能触发服务端自动改尺寸逻辑（2026-09-14 判断：此前观测到的非请求尺寸返回疑源于此，格式修正后尺寸应严格遵守，再遇漂移按异常排查）

## 响应格式

### b64_json（默认）
```json
{
  "created": 1703123456,
  "data": [
    {
      "b64_json": "..."
    }
  ]
}
```

### url
```json
{
  "created": 1703123456,
  "data": [
    {
      "url": "https://...",
      "revised_prompt": "..."
    }
  ]
}
```

## 常用模型

| 模型 ID | 文生图 | 图生图 | 质量 | 说明 |
|---------|:------:|:------:|------|------|
| openai/gpt-image-2.5-sunburst | Y | Y | low/medium/high | 透明背景实测可用（需措辞+参数双在场，见 SKILL.md） |

> 错误码处理见 [SKILL.md](../SKILL.md) 的「错误处理」节（脚本已内置 429/5xx 自动重试）。
