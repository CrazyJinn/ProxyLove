游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 登山步道-山顶平台
scene_id: RspiQlM31t
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  ground_desc: 山下城区与蜿蜒来路，薄雾中城市缩成一小片剪影，云影掠过层叠山脊
  sky_desc: 晴朗近午，淡蓝少量云，能见度极好
  floor_material: 混凝土
lights:
- name: 光源
  pos: [88, -72]
  color: '#fff3e0'
  intensity: 2.4
  out_of_frame: true
objects:
- id: shrub_r
  name: 低丛灌木·右
  spot: 登山步道-山顶
  bbox: [69, 59, 15, 11]
  depth: 8.29
- id: rail_front
  name: 护栏·前缘
  spot: 登山步道-山顶
  material: 原木
  bbox: [22, 53, 57, 10]
  depth: 8.2
- id: summit_marker
  name: 登顶标桩
  spot: 登山步道-山顶
  material: 原木
  bbox: [70, 52, 4, 15]
  depth: 8.0
- id: rock_l
  name: 山石·左
  spot: 登山步道-山顶
  bbox: [16, 59, 14, 12]
  depth: 7.84
- id: rail_side_l
  name: 护栏·左
  spot: 登山步道-山顶
  material: 原木
  bbox: [0, 53, 23, 33]
  depth: 7.12
  clipped: 左缘越出
- id: rail_side_r
  name: 护栏·右
  spot: 登山步道-山顶
  material: 原木
  bbox: [77, 53, 23, 33]
  depth: 7.12
  clipped: 右缘越出
- id: summit_deck
  name: 山顶平台
  spot: 登山步道-山顶
  material: 混凝土
  bbox: [0, 63, 100, 37]
  depth: 5.49
  clipped: 左右下缘越出
deco: 平台石缝里探出的低草，护栏上搭着的毛巾与登山杖，登顶标桩顶的漆面被日晒剥落
atmosphere: 近午日光毫无遮拦地铺满山顶，山风把汗意吹干，脚下云影掠过层叠山脊，远处城市缩成薄雾里的一小片
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
