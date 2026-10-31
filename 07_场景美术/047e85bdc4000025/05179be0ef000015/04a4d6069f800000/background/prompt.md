游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 马路-路口
scene_id: Oib4U5kSnI
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [0, 50, 100, 18]
  ground: [0, 63, 100, 37]
  ground_desc: 路口下方城市地面
  sky_desc: 阴雨天幕,雨丝斜织
  floor_material: 沥青
lights:
- name: 光源
  pos: [-24, 1]
  color: '#cfe0ee'
  intensity: 1.2
  out_of_frame: true
objects:
- id: sidewalk_left
  name: 人行道西段
  spot: 路口
  material: 混凝土
  bbox: [0, 50, 50, 13]
  depth: 13.55
  clipped: 左缘越出
- id: sidewalk_far
  name: 人行道远段
  spot: 路口
  material: 混凝土
  bbox: [44, 49, 56, 39]
  depth: 12.61
  clipped: 右缘越出
- id: crosswalk
  name: 斑马线
  spot: 路口
  material: 油漆标线
  bbox: [0, 65, 38, 35]
  depth: 4.47
  clipped: 左下缘越出
deco: 雨幕斜织,湿滑路面反射霓虹与车灯冷光,积水洼倒映破碎街景,打伞等红灯的行人,一辆摩托车正冲过来
atmosphere: 雨幕笼罩的喧嚣城市路口,湿滑路面反射着霓虹与车灯的冷光,积水洼里倒映着破碎的街景,路边有打着伞等红灯的行人
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
