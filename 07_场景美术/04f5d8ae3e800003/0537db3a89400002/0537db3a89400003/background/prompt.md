游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 星耀电竞基地-荣誉墙
scene_id: Rm85LQWh4V
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  back_wall: [4, 16, 92, 63]
  floor_material: 抛光瓷砖
  wall_material: 吸音板
lights:
- name: 光源
  pos: [50, -13]
  color: '#eaf2ff'
  intensity: 2.5
  out_of_frame: true
objects:
- id: lounge_sofa
  name: 等候沙发
  spot: 大厅
  material: 布艺
  bbox: [0, 64, 17, 33]
  depth: 4.83
  clipped: 左缘越出
- id: reception
  name: 前台接待台
  spot: 大厅
  material: 金属
  bbox: [86, 58, 14, 42]
  depth: 4.71
  clipped: 右下缘越出
- id: honor_wall
  name: 荣誉墙板
  spot: 大厅
  material: 亚克力灯板
  bbox: [13, 16, 74, 40]
  depth: 4.44
- id: trophy_base
  name: 展示底座
  spot: 大厅
  material: 金属
  bbox: [12, 66, 76, 16]
  depth: 4.37
deco: 荣誉墙灯带下一队金杯成排，二队位置只有一排空白铭牌，前台桌上访客登记册与访客卡，等候沙发区茶几上叠着基地宣传册
atmosphere: 挑高大厅空旷安静，一队历年金杯在灯带下成排发亮，二队那排只有空白铭牌——一面沉默的军功簿
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
