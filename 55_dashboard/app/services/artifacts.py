"""artifacts.py — 产物文件访问（审批中心渲染用）。

artifact_root（settings.json）= 代恋项目产物根目录。未配置/文件缺失 → 优雅降级：
模板拿到 artifact=None 显示路径文本 + 「⚠ 产物未挂载」徽章。
"""

from __future__ import annotations

from pathlib import Path

from app.repo.graph_repo import PROJECT_ROOT, ROOT, load_settings


def _roots() -> list[Path]:
    """产物根列表：artifact_roots（先真后 mock 叠加）兼容旧单 artifact_root 字段。

    相对路径以 55_dashboard/ 为基准解析（与旧版 CWD 行为一致，服务 CWD 恰为该目录）。
    """
    s = load_settings()
    raw = s.get("artifact_roots")
    if not raw:
        single = (s.get("artifact_root") or "").strip()
        raw = [single] if single else []
    roots = []
    for r in raw:
        r = (r or "").strip()
        if r:
            p = Path(r)
            roots.append(p.resolve() if p.is_absolute() else (ROOT / r).resolve())
    return roots


def resolve(rel_path: str | None, kind: str = "file") -> dict | None:
    """相对路径 → {exists, abs, url, missing}；rel_path 空 → None（无路径字段）。

    依序在多个产物根中查找（真实仓库优先，mock 兜底）；均未配置 → unmounted。
    """
    if not rel_path:
        return None
    roots = _roots()
    if not roots:
        return {"exists": False, "abs": "", "url": "", "missing": "unmounted"}
    for base in roots:
        target = (base / rel_path).resolve()
        # 防目录穿越：必须仍在该根内（is_relative_to 跨平台且含相等）
        if not target.is_relative_to(base):
            continue
        if target.is_file():
            return {
                "exists": True,
                "abs": str(target),
                "url": f"/media/{kind}/{encode_rel(rel_path)}",
                "missing": "",
            }
    return {"exists": False, "abs": "", "url": "", "missing": "nofile"}


def encode_rel(rel_path: str) -> str:
    import urllib.parse

    return urllib.parse.quote(rel_path, safe="")


def decode_rel(token: str) -> str:
    import urllib.parse

    return urllib.parse.unquote(token)


def local_path(rel_path: str) -> Path | None:
    """已存在的产物绝对路径（media 路由取文件用）。"""
    info = resolve(rel_path)
    if info and info["exists"]:
        return Path(info["abs"])
    return None
