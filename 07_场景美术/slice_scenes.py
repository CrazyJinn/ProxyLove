#!/usr/bin/env python3
"""slice_scenes.py — Room DSL v3 → 各 scene 自包含 YAML（相机视锥剔除版）。

用法：python slice_scenes.py 07_场景美术/八楼出租屋/八楼出租屋.room.yml [--aspect 1.5]

产出：与 room.yml 同目录，每个 scene 一份 <scene_name>.scene.yml：
  location + room（壳常留；windows/door 按视锥剔除） + objects（仅视锥内） + scene 块（原样）

剔除规则：
  - 物件/窗/门：取包围盒 8 角（含 rot Y 旋转），全部角在视锥同一侧外 → 剔除
  - 视锥：camera.fov 为竖直 fov，水平按宽高比换算（默认 1.5 = 1536x1024）
  - 不做遮挡剔除：视锥内但被挡住的物件保留（对 t2i 更安全）

--mode 2d：额外产出 <scene>.scene2d.yml —— 3D→2D 投影后的画幅布局：
  - 物件：画幅百分比 bbox [x,y,w,h]（y 向下）+ 相机距离（远近排序=遮挡序）+ 越缘标记
  - 房间结构：地板/后墙/左墙/右墙/天花的 2D 投影区域
  - 光源：画面内位置
  rationale：t2i 模型理解 2D 构图远好于 3D 坐标；投影是确定性数学，由代码完成。
"""
from __future__ import annotations

import sys
import math
import yaml
from pathlib import Path


def norm(v):
    l = math.sqrt(sum(x * x for x in v))
    return [x / l for x in v]


def sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def rot_y(p, deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return [c * p[0] + s * p[2], p[1], -s * p[0] + c * p[2]]


def half_extents(o):
    ty = o.get("type", "box")
    s = list(o.get("size", [0, 0, 0])) + [0, 0, 0]
    if ty == "cylinder":
        return (s[0], s[1], s[0])
    if ty == "sphere":
        return (s[0], s[0], s[0])
    if ty == "plane":
        return (s[0], s[1], 0.02)
    return (s[0], s[1], s[2])


def corners(o, y_center=None):
    """物件包围盒 8 角（世界系，含绕 Y 旋转）。y_center 用于 door 这类只给尺寸的。"""
    sx, sy, sz = half_extents(o)
    pos = list(o["pos"])
    if y_center is not None:
        pos[1] = y_center + sy / 2
    ry = (o.get("rot") or [0, 0, 0])[1]
    pts = []
    for dx in (-sx / 2, sx / 2):
        for dy in (-sy / 2, sy / 2):
            for dz in (-sz / 2, sz / 2):
                q = rot_y([dx, dy, dz], ry)
                pts.append([pos[i] + q[i] for i in range(3)])
    return pts


def make_culler(cam, aspect):
    """返回 cull(pts)->bool：True=剔除（全部角在视锥同一侧外）。"""
    pos = cam["pos"]
    f = norm(sub(cam["look_at"], pos))
    r = norm(cross(f, [0, 1, 0]))
    u = cross(r, f)
    tan_hv = math.tan(math.radians(cam["fov"]) / 2)
    tan_hh = tan_hv * aspect
    near, far = 0.05, 60.0

    def cull(pts):
        zf = [dot(sub(p, pos), f) for p in pts]
        xr = [dot(sub(p, pos), r) for p in pts]
        yu = [dot(sub(p, pos), u) for p in pts]
        if all(z <= near for z in zf):
            return True
        if all(z >= far for z in zf):
            return True
        if all(x - z * tan_hh >= 0 for x, z in zip(xr, zf)):
            return True  # 全在右侧外
        if all(x + z * tan_hh <= 0 for x, z in zip(xr, zf)):
            return True  # 全在左侧外
        if all(y - z * tan_hv >= 0 for y, z in zip(yu, zf)):
            return True  # 全在上侧外
        if all(y + z * tan_hv <= 0 for y, z in zip(yu, zf)):
            return True  # 全在下侧外
        return False

    return cull


def basis(cam):
    """相机基：f 前 / r 右 / u 上（单位向量）。"""
    pos = cam["pos"]
    f = norm(sub(cam["look_at"], pos))
    r = norm(cross(f, [0, 1, 0]))
    u = cross(r, f)
    return pos, f, r, u


def make_projector(cam, aspect):
    """返回 proj(p)->(sx, sy) 归一化画幅坐标（y 向下）；z<=near 返回 None。"""
    pos, f, r, u = basis(cam)
    tan_hv = math.tan(math.radians(cam["fov"]) / 2)
    tan_hh = tan_hv * aspect
    near = 0.05

    def proj(p):
        d = sub(p, pos)
        z = dot(d, f)
        if z <= near:
            return None
        x = dot(d, r)
        y = dot(d, u)
        sx = 0.5 + x / (2 * z * tan_hh)
        sy = 0.5 - y / (2 * z * tan_hv)
        return sx, sy

    return proj


def bbox_pct(pts_proj):
    """可见角点 → (x0,y0,x1,y1) 百分比 + 越缘边列表。"""
    if len(pts_proj) < 2:
        return None, []
    xs = [p[0] for p in pts_proj]
    ys = [p[1] for p in pts_proj]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    clipped = []
    if x0 < 0:
        clipped.append("左")
    if x1 > 1:
        clipped.append("右")
    if y0 < 0:
        clipped.append("上")
    if y1 > 1:
        clipped.append("下")
    x0c, y0c = max(0.0, x0), max(0.0, y0)
    x1c, y1c = min(1.0, x1), min(1.0, y1)
    rect = [round(x0c * 100), round(y0c * 100), round((x1c - x0c) * 100), round((y1c - y0c) * 100)]
    return rect, clipped


def room_shell_regions(room, cam):
    """房间结构面片的 2D 投影 bbox（可见性过滤）。shell=open 外景：无墙无天花，报 ground/sky。"""
    fx, fz = room["floor"][0] / 2, room["floor"][1] / 2
    h = room["height"]
    proj = make_projector(cam, 1.5)
    out = {}
    if room.get("shell") == "open":
        g = room.get("ground") or {}
        gy = g.get("y", -20.0)
        for name, pts in {
            "ground": [[-fx, gy, -fz], [fx, gy, -fz], [fx, gy, fz], [-fx, gy, fz]],
            "sky": [[-fx, 200, -fz], [fx, 200, -fz], [fx, 200, fz], [-fx, 200, fz]],
        }.items():
            pp = [proj(p) for p in pts]
            pp = [p for p in pp if p]
            rect, _ = bbox_pct(pp)
            if rect and rect[2] >= 3 and rect[3] >= 3:
                out[name] = rect
        if g.get("desc"):
            out["ground_desc"] = g["desc"]
        if room.get("sky", {}).get("desc"):
            out["sky_desc"] = room["sky"]["desc"]
        return out
    quads = {
        "floor": [[-fx, 0, -fz], [fx, 0, -fz], [fx, 0, fz], [-fx, 0, fz]],
        "back_wall": [[-fx, 0, -fz], [fx, 0, -fz], [fx, h, -fz], [-fx, h, -fz]],
        "left_wall": [[-fx, 0, -fz], [-fx, 0, fz], [-fx, h, fz], [-fx, h, -fz]],
        "right_wall": [[fx, 0, -fz], [fx, 0, fz], [fx, h, fz], [fx, h, -fz]],
        "ceiling": [[-fx, h, -fz], [fx, h, -fz], [fx, h, fz], [-fx, h, fz]],
    }
    proj = make_projector(cam, 1.5)
    out = {}
    for name, pts in quads.items():
        pp = [proj(p) for p in pts]
        pp = [p for p in pp if p]
        rect, _ = bbox_pct(pp)
        if rect and rect[2] >= 3 and rect[3] >= 3:  # 过小的投影省略
            out[name] = rect
    return out


def validate_room(data: dict) -> list[str]:
    """几何与结构校验（保存/重切前置门）。返回错误列表，空 = 通过。

    检查：顶层键、物件必要字段、出墙/穿顶（室内壳）、相机在承载面内。
    室内（无 shell:open）物件须贴墙/贴顶或有支撑；外景豁免墙体检查。
    """
    errs: list[str] = []
    if list(data.keys()) != ["location", "room", "objects", "scenes"]:
        errs.append(f"顶层键序异常: {list(data.keys())}")
        return errs
    room = data["room"]
    fl = list(room.get("floor") or [0, 0])
    fx, fz = fl[0], (fl[1] if len(fl) > 1 else 0)
    h = room.get("height", 0)
    open_shell = room.get("shell") == "open"
    ALLOWED_OBJ = {"id", "spot", "name", "type", "pos", "size", "rot", "color", "cname", "desc"}
    ids = set()
    for o in data["objects"]:
        if o.get("id") in ids:
            errs.append(f"物件 id 重复: {o.get('id')}")
        ids.add(o.get("id"))
        bad = set(o.keys()) - ALLOWED_OBJ
        if bad:
            errs.append(f"物件 {o.get('id')} 未知键 {sorted(bad)}")
        if not o.get("id") or not o.get("pos") or not o.get("size"):
            errs.append(f"物件 {o.get('id')} 缺 id/pos/size")

    def he(o):
        s = list(o.get("size", [0, 0, 0])) + [0, 0, 0]
        t = o.get("type", "box")
        if t == "cylinder":
            return (s[0] / 2, s[1] / 2, s[0] / 2)
        if t == "sphere":
            return (s[0] / 2, s[0] / 2, s[0] / 2)
        if t == "plane":
            return (s[0] / 2, s[1] / 2, 0.02)
        return (s[0] / 2, s[1] / 2, s[2] / 2)

    def bbox(o):
        hx, hy, hz = he(o)
        px, py, pz = o["pos"]
        return (px - hx, px + hx, py - hy, py + hy, pz - hz, pz + hz)

    for o in data["objects"]:
        x0, x1, y0, y1, z0, z1 = bbox(o)
        if not open_shell:
            if x0 < -fx / 2 - 0.05 or x1 > fx / 2 + 0.05:
                errs.append(f"{o['id']} X 出墙 [{x0:.2f},{x1:.2f}] (墙 ±{fx/2:.2f})")
            if z0 < -fz / 2 - 0.05 or z1 > fz / 2 + 0.05:
                errs.append(f"{o['id']} Z 出墙 [{z0:.2f},{z1:.2f}] (墙 ±{fz/2:.2f})")
            if y1 > h + 0.05:
                errs.append(f"{o['id']} 穿天花 {y1:.2f} > {h}")
    scene_ids = set()
    for scn in data["scenes"]:
        if scn.get("scene_id") in scene_ids:
            errs.append(f"scene_id 重复: {scn.get('scene_id')}")
        scene_ids.add(scn.get("scene_id"))
        c = scn.get("camera") or {}
        pos = c.get("pos") or [0, 0, 0]
        if not open_shell:
            if abs(pos[0]) > fx / 2 + 0.05 or abs(pos[2]) > fz / 2 + 0.05 or not (0 <= pos[1] <= h + 0.05):
                errs.append(f"{scn.get('id', scn.get('scene_id'))} 相机出房 {pos}")
        if not (20 <= (c.get("fov") or 0) <= 120):
            errs.append(f"{scn.get('id')} fov 异常 {c.get('fov')}")
    return errs


def freshness_check(room_path: Path, out_dir: Path | None = None) -> list[str]:
    """派生新鲜度：room.yml 改动后未重切（scene/scene2d 比真源旧）即报。git 提交前跑。"""
    errs = []
    out_dir = out_dir or room_path.parent
    src_mtime = room_path.stat().st_mtime
    data = yaml.safe_load(room_path.read_text(encoding="utf-8"))
    for scn in data.get("scenes", []):
        for suffix in (".scene.yml", ".scene2d.yml"):
            p = out_dir / f"{scn['scene_name']}{suffix}"
            if not p.exists():
                errs.append(f"缺派生文件: {p.name}")
            elif p.stat().st_mtime < src_mtime:
                errs.append(f"派生过期（room.yml 更新后未重切）: {p.name}")
    return errs


def slice_room(room_path: Path, aspect: float = 1.5, mode_2d: bool = False,
               skip_validate: bool = False) -> list[Path]:
    data = yaml.safe_load(room_path.read_text(encoding="utf-8"))
    if not skip_validate:
        errs = validate_room(data)
        if errs:
            raise ValueError("room.yml 校验失败:\n  " + "\n  ".join(errs))
    out_files = []
    for scn in data.get("scenes", []):
        cull = make_culler(scn["camera"], aspect)
        objs = [o for o in data["objects"] if not cull(corners(o))]
        wins = [w for w in data["room"].get("windows", []) if not cull(corners(w))]
        keep_door = data["room"].get("door") and not cull(corners(
            {"pos": data["room"]["door"]["pos"], "size": [*data["room"]["door"]["size"], 0.06]}, y_center=0))
        room_out = {k: v for k, v in data["room"].items() if k not in ("windows", "door")}
        if wins:
            room_out["windows"] = wins
        if keep_door:
            room_out["door"] = data["room"]["door"]
        out = {
            "location": data["location"],
            "room": room_out,
            "objects": objs,
            "scene": scn,
        }
        hdr = (
            f"# Scene YAML（视锥剔除版，供文生图直用）\n"
            f"# 源：{room_path.name} → scene: {scn['scene_name']}\n"
            f"# 物件 {len(objs)}/{len(data['objects'])} 在相机视锥内（竖直fov {scn['camera']['fov']}° · 宽高比 {aspect}）\n"
            f"# 派生产物：改布局请改 room.yml 再重跑 slice_scenes.py\n\n"
        )
        dst = room_path.parent / f"{scn['scene_name']}.scene.yml"
        dst.write_text(hdr + yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")
        dropped = [o["id"] for o in data["objects"] if o not in objs]
        print(f"{scn['scene_name']}: 保留 {len(objs)} 件 {sorted(o['id'] for o in objs)} | 剔除 {dropped}")
        out_files.append(dst)

        if mode_2d:
            cam = scn["camera"]
            pos, f, _, _ = basis(cam)
            proj = make_projector(cam, aspect)
            items = []
            for o in objs:
                pts_proj = [proj(p) for p in corners(o)]
                pts_proj = [p for p in pts_proj if p]
                rect, clipped = bbox_pct(pts_proj)
                if not rect:
                    continue
                d_mid = math.sqrt(sum((a - b) ** 2 for a, b in zip(o["pos"], pos)))
                item = {
                    "id": o["id"], "name": o["name"], "spot": o["spot"],
                    "bbox": rect,                     # [x,y,w,h] 画幅百分比，y 向下
                    "depth": round(d_mid, 2),          # 相机距离（m），小=近=后画
                }
                if o.get("cname"):
                    item["cname"] = o["cname"]
                if clipped:
                    item["clipped"] = "".join(clipped) + "缘越出"
                items.append(item)
            items.sort(key=lambda it: -it["depth"])  # 远→近（绘制/遮挡序）
            lights2d = []
            for l in scn.get("lights", []):
                if l.get("type") != "point":
                    continue
                p = proj(l["pos"])
                if not p:
                    continue
                sx, sy = p[0] * 100, p[1] * 100
                entry = {
                    "name": "光源", "pos": [round(sx), round(sy)],
                    "color": l["color"], "intensity": l["intensity"],
                }
                if not (0 <= sx <= 100 and 0 <= sy <= 100):
                    entry["out_of_frame"] = True  # 灯头在画外（如近处高杆灯）——光照效果仍有效
                lights2d.append(entry)
            out2d = {
                "scene_name": scn["scene_name"],
                "scene_id": scn["scene_id"],
                "canvas": f"百分比布局（x/y/w/h，y 向下；depth=距相机米数，列表由远及近=遮挡序）",
                "room_regions": room_shell_regions(data["room"], cam),
                "lights": lights2d,
                "objects": items,
                "deco": scn.get("deco", ""),
                "atmosphere": scn.get("atmosphere", ""),
                "preview": {   # /room3d 相机预览直接消费（后端算，前端展示——投影单实现）
                    "aspect": aspect,
                    "fov": cam["fov"],
                    "camera": cam,
                    "objects": [dict(it) for it in items],
                    "lights": [dict(l) for l in lights2d],
                    "room_regions": room_shell_regions(data["room"], cam),
                },
            }
            hdr2 = (
                f"# Scene 2D YAML（3D→2D 投影布局，供文生图直用）\n"
                f"# 源：{room_path.name} → scene: {scn['scene_name']}（竖直fov {cam['fov']}° · 宽高比 {aspect}）\n"
                f"# bbox 为画幅百分比 [x,y,w,h]；由确定性投影计算，模型无需理解 3D 坐标\n\n"
            )
            dst2 = room_path.parent / f"{scn['scene_name']}.scene2d.yml"
            dst2.write_text(hdr2 + yaml.safe_dump(out2d, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")
            print(f"  2D → {dst2.name}: {len(items)} 件布局 + {len(lights2d)} 光源")
            out_files.append(dst2)
    return out_files


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ap = 1.5
    if "--aspect" in sys.argv:
        ap = float(sys.argv[sys.argv.index("--aspect") + 1])
    m2 = "--mode" in sys.argv and sys.argv[sys.argv.index("--mode") + 1] == "2d"
    rp = Path(sys.argv[1])
    if "--check" in sys.argv:
        data = yaml.safe_load(rp.read_text(encoding="utf-8"))
        errs = validate_room(data) + freshness_check(rp)
        if errs:
            print("\n".join(errs)); sys.exit(1)
        print("✅ 校验通过（几何/结构/新鲜度）")
        sys.exit(0)
    for f in slice_room(rp, ap, mode_2d=m2):
        print("  →", f)
