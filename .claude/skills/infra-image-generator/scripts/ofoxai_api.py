#!/usr/bin/env python3
"""
OfoxAI Images API - 图片生成脚本

使用方式:
    # 文生图
    python ofoxai_api.py submit "提示词" --size 1024x1024

    # 图生图（单图）
    python ofoxai_api.py submit "提示词" --image ./设计图.png --size 1024x1024

    # 多图引用
    python ofoxai_api.py submit "提示词" --image ./图1.png --image ./图2.png --size 1024x1024

    # 保存结果（支持 JSON 字符串或文件路径）
    python ofoxai_api.py wait '<json_result>' ./output.png
    python ofoxai_api.py wait ./result.json ./output.png

    # 下载图片
    python ofoxai_api.py download <url> ./output.png
"""

import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

import requests


def find_settings() -> dict:
    """从当前工作目录向上搜索 settings.json"""
    dir_path = Path(os.getcwd()).resolve()
    for _ in range(8):
        candidate = dir_path / "settings.json"
        if candidate.exists():
            with open(candidate, "r", encoding="utf-8") as f:
                return json.load(f)
        parent = dir_path.parent
        if parent == dir_path:
            break
        dir_path = parent
    return {}


def load_api_key() -> str:
    settings = find_settings()
    key = settings.get("ofox_api_key", "")
    if key:
        return key
    raise SystemExit(
        "错误：未找到 API Key。\n"
        "请在工作目录的 settings.json 中设置 ofox_api_key 字段，例如：\n"
        '  {"ofox_api_key": "sk-of-xxxxx"}'
    )


API_BASE = "https://api.ofox.io/v1"
DEFAULT_MODEL = "openai/gpt-image-2.5-sunburst"

_API_KEY_CACHE: Optional[str] = None


def get_api_key() -> str:
    """惰性加载 API Key（wait/download 命令不需要 key，不应强制要求 settings.json 存在）"""
    global _API_KEY_CACHE
    if _API_KEY_CACHE is None:
        _API_KEY_CACHE = load_api_key()
    return _API_KEY_CACHE


def post_with_retry(url: str, **kwargs) -> requests.Response:
    """POST 请求，对 429/502/503/504 与网络异常自动重试（退避 5/10/20s，共 3 次）。

    重试前对 multipart 文件句柄 seek(0)——上次尝试已消费读取位置，不复位会重发空内容。
    """
    delays = [5, 10, 20]
    for attempt in range(len(delays) + 1):
        try:
            resp = requests.post(url, **kwargs)
            if resp.status_code not in (429, 502, 503, 504) or attempt == len(delays):
                return resp
            reason = f"HTTP {resp.status_code}"
        except requests.RequestException as e:
            if attempt == len(delays):
                raise
            reason = str(e)
        print(f"[retry] {reason}，{delays[attempt]}s 后重试（第 {attempt + 1}/{len(delays)} 次）", file=sys.stderr)
        time.sleep(delays[attempt])
        for item in kwargs.get("files") or []:
            try:
                item[1].seek(0)
            except Exception:
                pass
    raise RuntimeError("unreachable")


def submit_task(
    prompt: str,
    model: str = DEFAULT_MODEL,
    size: str = "1536x1024",
    n: int = 1,
    quality: Optional[str] = "medium",
    image: Optional[List[str]] = None,
    response_format: str = "b64_json",
    background: Optional[str] = None,
    output_format: Optional[str] = None,
) -> dict:
    has_images = image and len(image) > 0

    if has_images:
        # 图生图: multipart/form-data
        url = f"{API_BASE}/images/edits"
        files: List[tuple] = []
        # 多图用 image[]，单图用 image
        if len(image) > 1:
            for img_path in image:
                files.append(("image[]", open(img_path, "rb")))
        else:
            files.append(("image", open(image[0], "rb")))

        data = {"prompt": prompt, "model": model, "n": str(n), "size": size, "response_format": response_format}
        if quality:
            data["quality"] = quality
        data["moderation"] = "low"  # 写死，降低安全审核强度（叙事性提示词易被误拒）
        if background:
            data["background"] = background
        if output_format:
            data["output_format"] = output_format

        resp = post_with_retry(
            url,
            headers={"Authorization": f"Bearer {get_api_key()}"},
            data=data,
            files=files,
            timeout=1200,
        )
        # 关闭文件句柄
        for _, f in files:
            f.close()
    else:
        # 文生图: JSON
        url = f"{API_BASE}/images/generations"
        body: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "size": size,
            "response_format": response_format,
        }
        if quality:
            body["quality"] = quality
        body["moderation"] = "low"  # 写死，降低安全审核强度（叙事性提示词易被误拒）
        if background:
            body["background"] = background
        if output_format:
            body["output_format"] = output_format

        resp = post_with_retry(
            url,
            headers={"Authorization": f"Bearer {get_api_key()}", "Content-Type": "application/json"},
            json=body,
            timeout=1200,
        )

    if resp.status_code != 200:
        try:
            detail = json.dumps(resp.json(), ensure_ascii=False)
        except ValueError:
            detail = resp.text[:300]
        raise Exception(f"API error ({resp.status_code}): {detail}")
    return resp.json()


def save_result(result: dict, output_path: str) -> dict:
    if "error" in result:
        return {"status": "error", "message": result["error"].get("message", "未知错误"), "code": result["error"].get("code")}

    data_list = result.get("data", [])
    if not data_list:
        return {"status": "error", "message": "返回结果中没有图片数据"}

    saved = []
    for i, item in enumerate(data_list):
        path = Path(output_path)
        save_path = str(path.parent / f"{path.stem}_{i+1}{path.suffix}") if len(data_list) > 1 else output_path
        path.parent.mkdir(parents=True, exist_ok=True)

        if "b64_json" in item:
            with open(save_path, "wb") as f:
                f.write(base64.b64decode(item["b64_json"]))
            saved.append(save_path)
        elif "url" in item:
            resp = requests.get(item["url"], timeout=1200)
            resp.raise_for_status()
            with open(save_path, "wb") as f:
                f.write(resp.content)
            saved.append(save_path)

    if saved:
        return {
            "status": "done",
            "image_path": saved[0] if len(saved) == 1 else saved,
            "image_paths": saved,
        }
    return {"status": "error", "message": "未能获取图片数据"}


def download_image(url: str, output_path: str) -> dict:
    resp = requests.get(url, timeout=1200)
    resp.raise_for_status()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(resp.content)
    return {"status": "success", "path": output_path}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "submit":
        if len(sys.argv) < 3:
            print("用法: python ofoxai_api.py submit <prompt|--prompt-stdin> [options]")
            print("")
            print("选项:")
            print("  --model <name>       模型 (默认: openai/gpt-image-2.5-sunburst)")
            print("  --size <WxH>         输出尺寸 (1024x1024 / 1024x1536 / 1536x1024，ASCII x，默认 1536x1024)")
            print("  --n <int>            生成数量 (默认: 1)")
            print("  --quality <val>      已强制为 `medium`")
            print("  --image <path>       参考图片路径 (可多次指定)")
            print("  --response-format    b64_json 或 url (默认: b64_json)")
            print("  --background <val>   transparent/opaque(当识别到需求为透明背景时，就传transparent)")
            print("  --output-format <val> 已强制为 png（项目统一格式）")
            print("  --prompt-stdin       从标准输入读取 prompt（管道消费，支持多行 markdown）")
            print("  -o, --output <path>  直接保存到指定路径（跳过 wait 步骤）")
            sys.exit(1)

        prompt = None
        prompt_stdin = False
        model = DEFAULT_MODEL
        size = "1536x1024"
        n = 1
        quality = None
        image = []
        response_format = "b64_json"
        background = None
        output_format = None
        output = None

        i = 2
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg == "--prompt-stdin":
                prompt_stdin = True; i += 1
            elif arg == "--model" and i + 1 < len(sys.argv):
                model = sys.argv[i + 1]; i += 2
            elif arg == "--size" and i + 1 < len(sys.argv):
                size = sys.argv[i + 1]; i += 2
            elif arg == "--n" and i + 1 < len(sys.argv):
                n = int(sys.argv[i + 1]); i += 2
            elif arg == "--quality" and i + 1 < len(sys.argv):
                quality = sys.argv[i + 1]; i += 2
            elif arg == "--image" and i + 1 < len(sys.argv):
                image.append(sys.argv[i + 1]); i += 2
            elif arg == "--response-format" and i + 1 < len(sys.argv):
                response_format = sys.argv[i + 1]; i += 2
            elif arg == "--background" and i + 1 < len(sys.argv):
                background = sys.argv[i + 1]; i += 2
            elif arg == "--output-format" and i + 1 < len(sys.argv):
                output_format = sys.argv[i + 1]; i += 2
            elif arg in ("-o", "--output") and i + 1 < len(sys.argv):
                output = sys.argv[i + 1]; i += 2
            elif prompt is None and not arg.startswith("--"):
                prompt = arg; i += 1
            else:
                i += 1

        if prompt_stdin:
            prompt = sys.stdin.read()

        # 强制质量为 medium、输出格式为 png（项目统一，无其他格式）
        quality = "medium"
        output_format = "png"

        if prompt is None:
            print("错误：必须提供 prompt（位置参数或 --prompt-stdin）", file=sys.stderr)
            sys.exit(1)

        # 校验图片文件
        for img in image:
            if not Path(img).exists():
                print(json.dumps({"error": f"图片不存在: {img}"}, ensure_ascii=False))
                sys.exit(1)

        try:
            result = submit_task(prompt=prompt, model=model, size=size, n=n, quality=quality, image=image or None, response_format=response_format, background=background, output_format=output_format)
            if output:
                result = save_result(result, output)
            print(json.dumps(result, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
            sys.exit(1)

    elif command == "wait":
        if len(sys.argv) < 4:
            print("用法: python ofoxai_api.py wait '<json_result>|<json_file>' <output_path>")
            sys.exit(1)
        raw = sys.argv[2]
        # 支持从文件读取 JSON（处理大响应）
        if Path(raw).exists():
            with open(raw, encoding="utf-8") as f:
                result = json.load(f)
        else:
            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                print(json.dumps({"status": "error", "message": "无效的 JSON"}, ensure_ascii=False))
                sys.exit(1)
        output_path = sys.argv[3]
        result = save_result(result, output_path)
        print(json.dumps(result, ensure_ascii=False))

    elif command == "download":
        if len(sys.argv) < 4:
            print("用法: python ofoxai_api.py download <url> <output_path>")
            sys.exit(1)
        try:
            result = download_image(sys.argv[2], sys.argv[3])
            print(json.dumps(result, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
            sys.exit(1)

    else:
        print(f"未知命令: {command}")
        print("可用命令: submit, wait, download")
        sys.exit(1)


if __name__ == "__main__":
    main()
