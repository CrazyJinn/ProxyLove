# room.yml v3 速查（scene-designer 专用）

> 出处标注：`ss:N` = [07_场景美术/slice_scenes.py](../../../../07_场景美术/slice_scenes.py) 行号，`cf:N` = [07_场景美术/check_framing.py](../../../../07_场景美术/check_framing.py) 行号（2026-10-24 版本）。**规则真源是脚本代码**，本文件是速查——脚本更新后须同步。

## 目录

1. [结构模板与硬约束](#1-结构模板与硬约束)
2. [坐标系约定](#2-坐标系约定)
3. [路径与命名](#3-路径与命名)
4. [validate_room 校验规则](#4-validate_room-校验规则)
5. [立绘安全区（check_framing）](#5-立绘安全区check_framing)
6. [数值基线](#6-数值基线)
7. [外景分支](#7-外景分支)
8. [atmosphere / deco 例句](#8-atmosphere--deco-例句)

---

## 1. 结构模板与硬约束

- **顶层键序固定** `["location", "room", "objects", "scenes"]`，顺序错即报错（ss:271）
- 四块内容：
  - `location`: `{id, name, description}`（Location 图节点镜像）
  - `room`: `{floor[X宽,Z深], height, wall_color, floor_color, door?, windows?, deco?, floor_material?, wall_material?, shell?, ground?, sky?}`
  - `objects[]`: 见下
  - `scenes[]`: 机位条目（见 SKILL.md 2d）
- **物件允许键全集** `{id, spot, name, type, pos, size, rot, color, cname, desc, material}`——未知键直接报错（ss:279）
- **type 语义**（ss:291-300）：`box`（默认）/ `cylinder`（s0=直径）/ `sphere` / `plane`（size=[宽,高]，厚 0.02，用于墙面镜/挂画）
- 材质中文短词（material / floor_material / wall_material）：原木/金属/皮革/布艺/玻璃/瓷砖/塑胶/混凝土/沥青等——投影时自动进 prompt，**图节点不存材质**
- `door`: `{side: z+|z-|x+|x-, pos[x,y,z], size[宽,高]}`（y=0 贴地）；`windows[]`: `{id, pos, size, rot?, desc?}`

## 2. 坐标系约定

- 单位米；**原点=空间地面中心**；X 右、Y 上、**Z 朝入口（+Z）**；rot 单位度
- `pos` = 物件**中心**；`size` = **全尺寸**（非半尺寸），box 为 `[dx,dy,dz]`，plane 为 `[w,h]`
- 贴墙对齐速算：物件贴西墙 → `pos.x = -floor_w/2 + size_x/2`；贴 z+ 墙 → `pos.z = floor_d/2 - size_z/2`（±0.05 容差内即可）

## 3. 路径与命名

- 产/读路径：`07_场景美术/<Location名>/<Spot目录名>/<Spot短名>.yml`（**后缀 `.yml`**，与 Schema/磁盘一致；勿写 `.room.yml`）
- Spot 目录名：name 去 `<Location名>-` 前缀的短名；整点建模短名=Location 名，目录即 Location 名（存量 default Spot 的目录同为 Location 名，形态一致）
- 短名不得含文件系统保留字符 `\ / : * ? " < > |`
- 磁盘权威样例：整点型（目录=Location 名）[服装店.yml](../../../../07_场景美术/服装店/服装店/服装店.yml)（存量 default Spot 产物，目录形态相同）；zone 型 [训练大厅.yml](../../../../07_场景美术/康复中心/训练大厅/训练大厅.yml)、[卧室.yml](../../../../07_场景美术/八楼出租屋/卧室/卧室.yml)；外景 [路口.yml](../../../../07_场景美术/马路/路口/路口.yml)

## 4. validate_room 校验规则

`--check` 全规则（ss:264-368），写前对照可免返工：

| 规则 | 阈值 |
|---|---|
| 物件出墙（室内） | X/Z 超出 floor 半宽 ±0.05 容差即报错（ss:310-313） |
| 物件穿天花 | y_top > height + 0.05（ss:314-315） |
| 开口（door/windows）贴墙 | 距墙 ≤0.2 判贴墙；悬空即报错；高度越界 y<−0.05 或 y>height+0.05（ss:335-340） |
| 相机在房内（室内） | \|x\|≤floor_w/2+0.05、\|z\|≤floor_d/2+0.05、0≤y≤height+0.05（ss:363-365） |
| fov | 20–120（ss:366） |
| objects_delta | remove/replace 的 id 必须存在于 objects；add 项走物件同规则且 id 不得重复（ss:341-355） |
| scene_id 不得重复 | ss:357-360 |
| 物件 id 不得重复（含开口 id） | ss:281-284, 324-327 |

## 5. 立绘安全区（check_framing）

渲染事实：立绘贴底高约 87% 屏高，左/中/右三槽带 x∈[10,90]，对话框遮底部 23.4%（cf:6-10）。

| 规则 | 条件（同时满足才违规） |
|---|---|
| R1 近景侵入脚区 | depth<7m ∧ bbox 底缘>65% ∧ 与[10,90]带横向重叠>8% 画宽 ∧ 像高>18% |
| R2 近景大块压中 | depth<4m ∧ 面积>20% ∧ 中心 x∈(15,85) ∧ 底缘>45%（远景墙元豁免） |
| R3 中央大件 | depth<4m ∧ 中心 x∈(32,68) ∧ 像高>20% ∧ 底缘>45% |

**豁免**：opening（门窗——立绘可挡其前）、低矮面物件（高度<0.35m：路面/人行道/石滩）。

设计纪律（写 yaml 前就遵守，而非写完被门拦）：**固定大件每房间 ≤8 件、贴墙布置、房间正中不放挡视线大件**（中岛/中央桌类至多一件且须偏侧贴边）。

## 6. 数值基线

实测样例背书（两个室内样例均一次过双质量门）：

| 维度 | 服装店（小店） | 康复中心（大厅） |
|---|---|---|
| 房间 | 5×4，高 2.9 | 7×5，高 3.0 |
| 机位 pos | [0, 1.55, 1.6] | [0, 1.55, 1.9] |
| look_at | [0, 1.25, -1.2] | [0, 1.2, -1.5] |
| fov | 60 | 60 |
| 灯 | point 白 2.3 顶中 + ambient #57534d 0.3 | point 白 2.4 顶中 + ambient #57534d 0.3 |

惯例：室内对话机位**自门口（z+ 侧）平视略高**（y≈1.55），看向房内（look_at y≈1.2）；两灯起步（顶 point + ambient）。

## 7. 外景分支

`room.shell: open`（ss:183,278）触发：无墙无天花，投影报 ground/sky 替代墙面；豁免墙体/开口/相机室内校验（ss:268,328-329,363）。

- `ground`: `{y, color, desc?}`（地面标高常为负，如 -3.0）；`sky`: `{color, desc?}`
- floor 仍必填（如 20×20），floor_material 常为 沥青/混凝土
- **沿轴延伸物（护栏/长路）必须拆近/中/远段**——整件投影退化成线
- 样例：[马路·路口](../../../../07_场景美术/马路/路口/路口.yml)

## 8. atmosphere / deco 例句

atmosphere 一句话承担整体氛围与天气；deco 承担机位画面内可移动小物与杂物堆（不建几何）。写法参考：

> **atmosphere**（服装店）：店面不大却码得整齐，挂杆按色排开的平价成衣店；店员不过分热情也不怠慢，试衣间帘子一拉一开之间，人重新有了样子
>
> **atmosphere**（康复中心）：上午阳光从北墙大窗斜进训练大厅，白光通亮，空气里消毒水混着橡胶垫的气味，器械偶尔发出轻微金属声
>
> **deco**（康复中心）：墙边卷立的瑜伽垫，架格上的弹力带与泡沫轴，前台一摞预约单与纸巾盒，饮水机旁一排纸杯

风格：具体可感的小物+气味/声音细节，避免「温馨舒适」类空泛形容词；天气并入 atmosphere 一句话。
