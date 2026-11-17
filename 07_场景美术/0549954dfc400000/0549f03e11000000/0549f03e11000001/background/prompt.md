游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 vibe 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 电影院-电影厅
scene_id: S9RLZ9jCsr
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  back_wall: [30, 29, 40, 30]
  floor_material: 地毯
  wall_material: 布艺
lights:
- name: 光源
  pos: [50, 45]
  color: '#cfe0ff'
  intensity: 2.4
objects:
- id: screen
  name: 巨幅银幕
  spot: 电影厅
  material: 玻璃
  bbox: [33, 35, 34, 21]
  depth: 15.58
- id: seats_r1
  name: 连排座椅
  spot: 电影厅
  material: 布艺
  bbox: [27, 56, 45, 7]
  depth: 10.97
- id: seats_r2
  name: 连排座椅
  spot: 电影厅
  material: 布艺
  bbox: [24, 57, 52, 9]
  depth: 9.58
- id: seats_r3
  name: 连排座椅
  spot: 电影厅
  material: 布艺
  bbox: [19, 58, 62, 10]
  depth: 8.2
- id: seats_r4
  name: 连排座椅
  spot: 电影厅
  material: 布艺
  bbox: [12, 59, 76, 13]
  depth: 6.82
- id: seats_r5
  name: 连排座椅
  spot: 电影厅
  material: 布艺
  bbox: [1, 61, 98, 17]
  depth: 5.45
deco: 扶手杯槽里的可乐与半桶爆米花；搭在前排空座的薄外套；侧墙亮着的青色安全出口指示灯
vibe: 放映中的影厅近乎全黑，银幕冷光勾出一排排座椅轮廓，空气里浮着爆米花甜味与空调冷气
time_of_day: 夜晚

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
