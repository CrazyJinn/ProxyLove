游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 林梦家-院门口
scene_id: RslBusGXcf
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [0, 66, 100, 34]
  ground: [0, 67, 100, 33]
  ground_desc: 别墅区安静的沥青街路，院墙与行道树向两侧延伸，路灯刚亮起
  sky_desc: 橘粉暮色渐深的夏日傍晚天空，西边残照未尽，东边已透出蓝
  floor_material: 花岗岩
lights:
- name: 光源
  pos: [52, 46]
  color: '#ffd9a0'
  intensity: 2.2
- name: 光源
  pos: [43, 41]
  color: '#ffcf96'
  intensity: 1.4
- name: 光源
  pos: [366, -172]
  color: '#bcd4e8'
  intensity: 1.2
  out_of_frame: true
objects:
- id: villa_facade
  name: 两层别墅主立面
  spot: 林梦家-门外
  material: 石材
  bbox: [31, 9, 54, 56]
  depth: 14.39
- id: planter
  name: 院内花坛
  spot: 林梦家-门外
  material: 石材
  bbox: [28, 61, 14, 6]
  depth: 11.35
- id: walkway
  name: 院内石板步道
  spot: 林梦家-门外
  material: 花岗岩
  bbox: [44, 63, 16, 9]
  depth: 11.08
- id: wall_l
  name: 院墙(左)
  spot: 林梦家-门外
  material: 石材
  bbox: [2, 47, 37, 24]
  depth: 9.98
- id: wall_r
  name: 院墙(右)
  spot: 林梦家-门外
  material: 石材
  bbox: [67, 45, 33, 31]
  depth: 8.69
  clipped: 右缘越出
- id: gate_post_l
  name: 石材门柱(左)
  spot: 林梦家-门外
  material: 石材
  bbox: [37, 45, 5, 26]
  depth: 8.38
- id: gate_iron
  name: 黑色铁艺院门
  spot: 林梦家-门外
  material: 金属
  bbox: [41, 50, 23, 22]
  depth: 7.92
- id: gate_post_r
  name: 石材门柱(右)
  spot: 林梦家-门外
  material: 石材
  bbox: [64, 44, 5, 29]
  depth: 7.84
deco: 陈默两手拎满漫展战利品袋与纸箱，林梦背着帆布包，黑色铁艺院门一扇虚掩，门柱灯映着修剪齐整的绿篱花坛
atmosphere: 漫展散场的夏日傍晚，天边橘粉暮色未尽，别墅铁艺院门与门柱灯初亮，晚风微凉，道别时刻一点暧昧的余韵
time_of_day: 黄昏

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
