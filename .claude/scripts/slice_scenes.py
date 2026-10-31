#!/usr/bin/env python3
"""slice_scenes.py — Room DSL v3 → 出图 prompt（投影 + 拼装，现场计算，零中间文件）。

用法：
  python slice_scenes.py <room.yml> --check
      几何/结构校验（scene-designer 写 room.yml 后的质量门）。
  python slice_scenes.py <room.yml> --emit-prompt --scene <scene_id> --out <prompt.md> [--scene-type dialogue] [--tod <图 Scene.time_of_day>] [--deco <图 Scene.deco>] [--atmosphere <图 Scene.atmosphere>] [--aspect 1.5]
      出图 prompt 现场生成直写 prompt.md（scene-layer-designer 模式 E 出图链）：
      用途前缀 + 导语（固定文案）+ scene2d 投影正文 + 收尾串（动态读 00_init/美术风格.md）。
      tod/deco/atmosphere 从图 Scene 节点查得传入（yaml 只留几何；不传则用 scene 条目残留值）。
  python slice_scenes.py <room.yml> --stdout --scene <scene_id>
      打印 scene2d 布局 YAML（含 # 头注释）——/room3d 复制通道、人眼检视。

模型：Scene = room.yml 一条机位（camera）；prompt 从房间 3D 数据 + 机位现场投影生成，
不再有 scene2d.yml / scene.yml 派生文件（投影确定性，随时可重算；零中间文件无新鲜度问题）。

投影规则：
  - 物件：先视锥剔除（包围盒 8 角全在视锥同一侧外 → 剔除；fov 为竖直，水平按宽高比换算），
    再投影为画幅百分比 bbox [x,y,w,h]（y 向下）+ 相机距离 depth（远近排序=遮挡序）+ 越缘标记
  - 房间结构：地板/后墙/左墙/右墙/天花的 2D 投影区域（外景 shell:open 为 ground/sky）
  - 光源：画面内位置（画外标 out_of_frame）
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


class FlowList(list):
    """流式（内联）输出 list——bbox/pos 等数字列表紧凑为 [a, b, c, d]，省 token。"""


def _flow_list_dumper(dumper, data):
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)


yaml.SafeDumper.add_representer(FlowList, _flow_list_dumper)


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
    rect = FlowList([round(x0c * 100), round(y0c * 100), round((x1c - x0c) * 100), round((y1c - y0c) * 100)])
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
            "floor": [[-fx, 0, -fz], [fx, 0, -fz], [fx, 0, fz], [-fx, 0, fz]],
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
        if g.get("material"):
            out["ground_material"] = g["material"]
        if room.get("sky", {}).get("desc"):
            out["sky_desc"] = room["sky"]["desc"]
        if room.get("floor_material"):
            out["floor_material"] = room["floor_material"]
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
    if room.get("floor_material"):
        out["floor_material"] = room["floor_material"]
    if room.get("wall_material"):
        out["wall_material"] = room["wall_material"]
    return out


def room_openings(room: dict) -> list[dict]:
    """room.door + room.windows 归一化为 plane 物件（参与投影，kind=opening）。

    door.pos.y 为底边贴地高度（side 推 rotY：z+→0 / x+→90 / z-→180 / x-→270）；
    windows[].pos 为中心形式，rot 直接沿用。归一化项带内部标记 _opening。
    """
    out: list[dict] = []
    door = room.get("door")
    if door and door.get("pos") and door.get("size"):
        side_rot = {"z+": 0, "x+": 90, "z-": 180, "x-": 270}
        w, h = door["size"]
        out.append({
            "id": door.get("id") or "door",
            "name": door.get("name") or "入户门",
            "type": "plane",
            "pos": [door["pos"][0], door["pos"][1] + h / 2, door["pos"][2]],
            "size": [w, h],
            "rot": [0, side_rot.get(door.get("side", "z+"), 0), 0],
            "desc": door.get("desc"),
            "_opening": True,
        })
    for w in room.get("windows") or []:
        if not (w.get("pos") and w.get("size")):
            continue
        out.append({
            "id": w.get("id") or "window",
            "name": w.get("name") or "窗",
            "type": "plane",
            "pos": list(w["pos"]),
            "size": list(w["size"]),
            "rot": list(w.get("rot") or [0, 0, 0]),
            "desc": w.get("desc"),
            "_opening": True,
        })
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
    ALLOWED_OBJ = {"id", "spot", "name", "type", "pos", "size", "rot", "color", "cname", "desc", "material"}
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
    # 开口（door/windows）：缺字段报错；室内须贴墙且不出墙不越层
    if room.get("door") and not (room["door"].get("pos") and room["door"].get("size")):
        errs.append("room.door 缺 pos/size")
    if room.get("door") and room["door"].get("side") not in (None, "z+", "z-", "x+", "x-"):
        errs.append(f"room.door.side 非法 {room['door'].get('side')}")
    for w in room.get("windows") or []:
        if not (w.get("pos") and w.get("size")):
            errs.append(f"window {w.get('id')} 缺 pos/size")
    for o in room_openings(room):
        if o["id"] in ids:
            errs.append(f"开口 id 重复: {o['id']}")
        ids.add(o["id"])
        if open_shell:
            continue
        pts = corners(o)
        xs = [p[0] for p in pts]
        zs = [p[2] for p in pts]
        ys = [p[1] for p in pts]
        x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
        outside = x0 > fx / 2 + 0.05 or x1 < -fx / 2 - 0.05 or z0 > fz / 2 + 0.05 or z1 < -fz / 2 - 0.05
        touching = x1 >= fx / 2 - 0.2 or x0 <= -fx / 2 + 0.2 or z1 >= fz / 2 - 0.2 or z0 <= -fz / 2 + 0.2
        if outside or not touching:
            errs.append(f"开口 {o['id']} 未贴墙 x∈[{x0:.2f},{x1:.2f}] z∈[{z0:.2f},{z1:.2f}] (墙 x±{fx/2:.2f} z±{fz/2:.2f})")
        if max(ys) > h + 0.05 or min(ys) < -0.05:
            errs.append(f"开口 {o['id']} 高度越界 y∈[{min(ys):.2f},{max(ys):.2f}] (层高 {h})")
    # objects_delta（机位级增减）：remove/replace 的 id 须存在于 objects；add 项走物件同规则
    all_ids = set(ids)
    for scn in data["scenes"]:
        dl = scn.get("objects_delta") or {}
        for rid in dl.get("remove") or []:
            if rid not in all_ids:
                errs.append(f"{scn.get('id')} objects_delta.remove 未知物件: {rid}")
        for p in dl.get("replace") or []:
            if p.get("id") not in all_ids:
                errs.append(f"{scn.get('id')} objects_delta.replace 未知物件: {p.get('id')}")
        for o in dl.get("add") or []:
            if not o.get("id") or not o.get("pos") or not o.get("size"):
                errs.append(f"{scn.get('id')} objects_delta.add 缺 id/pos/size")
            elif o["id"] in all_ids:
                errs.append(f"{scn.get('id')} objects_delta.add id 与现有物件重复: {o['id']}")
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


# ── 出图 prompt 拼装（原 scene-prompt-assembler 模式 E 规则的代码化——零 LLM 转抄）──

MODE_E_LEAD = (
    "以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下"
    "（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；"
    "room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色"
    "（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；"
    "物件与地面/墙面可含 material 材质词，材质质感以该词为准。"
    "请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。"
)

USE_PREFIX = {  # 按 scene_type（assembler 模式 A 前缀表）
    "dialogue": "游戏对话背景图。",
    "functional": "游戏场景背景图。",
    "combat": "游戏场景背景图。",
    "ui": "游戏UI背景",
}


def style_tail() -> str:
    """从 00_init/美术风格.md「提示词硬约束」节动态提取风格收尾串（唯一来源，不写死）。"""
    import re
    art = Path(__file__).resolve().parents[1] / "00_init" / "美术风格.md"
    m = re.search(r"风格收尾串[^\n]*\n\s*`([^`]+)`", art.read_text(encoding="utf-8"))
    if not m:
        raise ValueError("美术风格.md 未找到风格收尾串（『提示词硬约束』节）")
    return m.group(1).strip()


def project_scene(data: dict, scn: dict, aspect: float, room_name: str,
                  tod: str | None = None, deco: str | None = None,
                  atmosphere: str | None = None) -> tuple[dict, str]:
    """单 scene 投影（单实现）：→ (scene2d dict, YAML 文本[含 # 头注释——人读])。

    tod/deco/atmosphere 为图 Scene 节点的文字字段（调用方查图传入；yaml 只留几何）；
    None 时回退 scene 条目残留值（兼容）。
    prompt 用正文请走 body_of()（去 # 注释行）。
    """
    cull = make_culler(scn["camera"], aspect)
    # objects_delta（机位级物件增减）：remove 按 id 剔除、replace 同 id 部分键覆盖、add 追加
    delta = scn.get("objects_delta") or {}
    remove_ids = set(delta.get("remove") or [])
    repl = {p["id"]: {k: v for k, v in p.items() if k != "id"}
            for p in (delta.get("replace") or []) if p.get("id")}
    objs = []
    for o in data["objects"] + room_openings(data["room"]):
        if o["id"] in remove_ids:
            continue
        if o["id"] in repl:
            o = {**o, **repl[o["id"]]}
        objs.append(o)
    objs += list(delta.get("add") or [])
    objs = [o for o in objs if not cull(corners(o))]
    cam = scn["camera"]
    pos, _, _, _ = basis(cam)
    proj = make_projector(cam, aspect)
    items = []
    for o in objs:
        pts_proj = [proj(p) for p in corners(o)]
        pts_proj = [p for p in pts_proj if p]
        rect, clipped = bbox_pct(pts_proj)
        if not rect:
            continue
        d_mid = math.sqrt(sum((a - b) ** 2 for a, b in zip(o["pos"], pos)))
        item = {"id": o["id"], "name": o["name"]}
        if o.get("spot"):
            item["spot"] = o["spot"]
        if o.get("material"):
            item["material"] = o["material"]
        item["bbox"] = rect                    # [x,y,w,h] 画幅百分比，y 向下
        item["depth"] = round(d_mid, 2)        # 相机距离（m），小=近=后画
        if o.get("_opening"):
            item["kind"] = "opening"
            if o.get("desc"):
                item["desc"] = o["desc"]
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
            "name": "光源", "pos": FlowList([round(sx), round(sy)]),
            "color": l["color"], "intensity": l["intensity"],
        }
        if not (0 <= sx <= 100 and 0 <= sy <= 100):
            entry["out_of_frame"] = True  # 灯头在画外（如近处高杆灯）——光照效果仍有效
        lights2d.append(entry)
    out2d = {
        "scene_name": scn["scene_name"],
        "scene_id": scn["scene_id"],
        "canvas": f"百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）",
        "room_regions": room_shell_regions(data["room"], cam),
        "lights": lights2d,
        "objects": items,
        "deco": deco if deco is not None else scn.get("deco", ""),
        "atmosphere": atmosphere if atmosphere is not None else scn.get("atmosphere", ""),
        "time_of_day": tod if tod is not None else scn.get("time_of_day", ""),
    }
    hdr = (
        f"# Scene 2D YAML（3D→2D 投影布局，供文生图直用）\n"
        f"# 源：{room_name} → scene: {scn['scene_name']}（竖直fov {cam['fov']}° · 宽高比 {aspect}）\n"
        f"# bbox 为画幅百分比 [x,y,w,h]；由确定性投影计算，模型无需理解 3D 坐标\n\n"
    )
    return out2d, hdr + yaml.safe_dump(out2d, allow_unicode=True, sort_keys=False, width=110)


def body_of(yaml_text: str) -> str:
    """YAML 文本去 # 注释行（prompt 正文——导语已解释读法，注释冗余）。"""
    return "\n".join(l for l in yaml_text.splitlines() if not l.startswith("#")).strip()


def _load_scene(room_path: Path, scene_id: str) -> tuple[dict, dict]:
    data = yaml.safe_load(room_path.read_text(encoding="utf-8"))
    errs = validate_room(data)
    if errs:
        raise ValueError("room.yml 校验失败:\n  " + "\n  ".join(errs))
    for scn in data.get("scenes", []):
        if scn.get("scene_id") == scene_id:
            return data, scn
    avail = [f"{s.get('scene_id')}({s.get('scene_name')})" for s in data.get("scenes", [])]
    raise ValueError(f"scene 未找到: {scene_id}；可用: {', '.join(avail) or '（无）'}")


def emit_prompt(room_path: Path, scene_id: str, out_path: Path | None, aspect: float = 1.5,
                scene_type: str | None = None, tod: str | None = None,
                deco: str | None = None, atmosphere: str | None = None) -> str:
    """出图 prompt 现场生成：用途前缀 + 导语 + scene2d 投影正文 + 收尾串。

    out_path 给定则写盘并打印 PROMPT_PATH；始终返回 prompt 全文（dashboard 内存调用不落盘）。
    scene_type/tod/deco/atmosphere 为图 Scene 节点字段（调用方查图传入）；scene_type 优先级：
    参数 > scene 条目 > dialogue。tod/deco/atmosphere 为 None 时回退 scene 条目残留（兼容）。
    """
    data, scn = _load_scene(room_path, scene_id)
    _, yaml_text = project_scene(data, scn, aspect, room_path.name,
                                  tod=tod, deco=deco, atmosphere=atmosphere)
    st = scene_type or scn.get("scene_type") or "dialogue"
    tp = " ".join(scn.get("text_passthrough") or []).strip()  # v3 预留：物件文字放行（如招牌/屏幕）
    if tp:
        tail = f"{style_tail()}，除{tp}上的文字外，图面无其他描述性文字。"
    else:
        tail = f"{style_tail()}，图面无描述性文字。"
    prompt = f"{USE_PREFIX.get(st, USE_PREFIX['dialogue'])}\n\n{MODE_E_LEAD}\n\n{body_of(yaml_text)}\n\n{tail}\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(prompt, encoding="utf-8")
        print(f"PROMPT_PATH: {out_path}")
    return prompt


def scene2d_text(room_path: Path, scene_id: str, aspect: float = 1.5) -> str:
    """投影 → scene2d YAML 全文（含 # 头注释）——stdout 通道：/room3d 复制、人眼检视。"""
    data, scn = _load_scene(room_path, scene_id)
    _, yaml_text = project_scene(data, scn, aspect, room_path.name)
    return yaml_text


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)

    def _val(flag: str) -> str | None:
        return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else None

    ap = float(_val("--aspect") or 1.5)
    rp = Path(sys.argv[1])
    if "--check" in sys.argv:
        data = yaml.safe_load(rp.read_text(encoding="utf-8"))
        errs = validate_room(data)  # 几何/结构质量门（无派生文件，无新鲜度问题）
        if errs:
            print("\n".join(errs)); sys.exit(1)
        print("✅ 校验通过（几何/结构）")
    elif "--emit-prompt" in sys.argv:
        scene = _val("--scene") or ""
        out = _val("--out")
        if not scene or not out:
            sys.exit("--emit-prompt 需要 --scene <scene_id> 与 --out <prompt.md 路径>")
        emit_prompt(rp, scene, Path(out), ap, _val("--scene-type"),
                    tod=_val("--tod"), deco=_val("--deco"), atmosphere=_val("--atmosphere"))
    elif "--stdout" in sys.argv:
        scene = _val("--scene") or ""
        if not scene:
            sys.exit("--stdout 需要 --scene <scene_id>")
        print(scene2d_text(rp, scene, ap))
    else:
        sys.exit(__doc__)
