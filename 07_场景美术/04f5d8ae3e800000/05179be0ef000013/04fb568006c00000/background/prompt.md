游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 长江大桥-护栏段
scene_id: QW6yYoIiSu
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  ground_desc: 江面：暗青色，反射对岸城市灯火成模糊光斑，无岸线细节
  sky_desc: 深夜阴天夜空，无星无月，近地平线处被城市光污染染出微弱暖橙
  floor_material: 混凝土
lights:
- name: 光源
  pos: [42, -29]
  color: '#cfe0ee'
  intensity: 2.6
  out_of_frame: true
objects:
- id: railing_far
  name: 金属护栏·远段
  spot: 护栏段
  material: 金属
  bbox: [52, 48, 4, 5]
  depth: 37.63
- id: road_far
  name: 桥面人行道·远段
  spot: 护栏段
  material: 混凝土
  bbox: [39, 50, 58, 17]
  depth: 26.57
- id: lamp_head_2
  name: 灯头·远
  spot: 护栏段
  material: 金属
  bbox: [51, 12, 2, 4]
  depth: 18.83
- id: railing_mid
  name: 金属护栏·中段
  spot: 护栏段
  material: 金属
  bbox: [46, 49, 6, 8]
  depth: 18.77
- id: lamppost_2
  name: 桥面路灯·远
  spot: 护栏段
  material: 金属
  bbox: [51, 15, 1, 40]
  depth: 17.82
- id: lamppost_1
  name: 桥面路灯·近
  spot: 护栏段
  material: 金属
  bbox: [41, 0, 2, 64]
  depth: 8.22
  clipped: 上缘越出
- id: railing_near
  name: 金属护栏·近段
  spot: 护栏段
  material: 金属
  bbox: [39, 51, 1, 11]
  depth: 4.03
- id: road_near
  name: 桥面人行道·近段
  spot: 护栏段
  material: 混凝土
  bbox: [39, 62, 58, 5]
  depth: 3.13
deco: ''
atmosphere: 深夜长江大桥护栏段,江风冷冽,桥灯冷白,城市在对岸明灭
time_of_day: 夜晚

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
