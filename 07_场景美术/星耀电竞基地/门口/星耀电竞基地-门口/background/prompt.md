游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 星耀电竞基地-门口
scene_id: RLaHS521Kb
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [0, 72, 100, 28]
  ground: [0, 74, 100, 26]
  ground_desc: 街道沥青路面与行道树延伸
  sky_desc: 午后晴空,薄云高挂
  floor_material: 花岗岩
lights:
- name: 光源
  pos: [401, -299]
  color: '#fff1d6'
  intensity: 2.8
  out_of_frame: true
objects:
- id: pillar_l
  name: 幕墙结构柱(左)
  spot: 门口
  material: 金属
  bbox: [34, 0, 4, 71]
  depth: 9.52
  clipped: 上缘越出
- id: pillar_r
  name: 幕墙结构柱(右)
  spot: 门口
  material: 金属
  bbox: [69, 0, 5, 73]
  depth: 9.17
  clipped: 上缘越出
- id: facade_wall
  name: 玻璃幕墙立面
  spot: 门口
  material: 玻璃
  bbox: [0, 0, 100, 74]
  depth: 9.14
  clipped: 左右上缘越出
- id: entrance_door
  name: 入口玻璃门组
  spot: 门口
  material: 玻璃
  bbox: [41, 45, 24, 27]
  depth: 8.73
- id: canopy
  name: 门头悬挑雨棚
  spot: 门口
  material: 金属
  bbox: [36, 38, 34, 6]
  depth: 8.23
- id: planter_l
  name: 门前花坛(左)
  spot: 门口
  material: 石材
  bbox: [5, 67, 22, 10]
  depth: 8.18
- id: entry_plat
  name: 门前抬升平台
  spot: 门口
  material: 花岗岩
  bbox: [30, 69, 46, 9]
  depth: 7.77
- id: planter_r
  name: 门前花坛(右)
  spot: 门口
  material: 石材
  bbox: [79, 69, 21, 13]
  depth: 7.54
  clipped: 右缘越出
deco: 楼顶两个发光大字:星耀,门侧金属铭牌与访客指示牌,花坛绿篱修剪齐整
atmosphere: 午后阳光洒在玻璃幕墙上,楼顶发光大字「星耀」,气派敞亮的基地入口
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
