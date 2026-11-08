游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 康复中心-门口
scene_id: RkWSqCnC4X
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  ground_desc: 临街人行道与慢车道，上午车流稀少
  sky_desc: 晴朗上午，淡蓝少云
  floor_material: 混凝土
lights:
- name: 光源
  pos: [119, -88]
  color: '#fff1d6'
  intensity: 2.4
  out_of_frame: true
objects:
- id: facade
  name: 临街主立面
  spot: 门口
  material: 混凝土
  bbox: [10, 10, 80, 52]
  depth: 10.5
- id: sign_board
  name: 门楣招牌
  spot: 门口
  material: 金属
  bbox: [40, 33, 20, 7]
  depth: 10.15
- id: door_glass
  name: 玻璃主门
  spot: 门口
  material: 玻璃
  bbox: [43, 42, 15, 20]
  depth: 10.11
- id: planter
  name: 门口绿植箱
  spot: 门口
  bbox: [66, 55, 8, 9]
  depth: 9.78
- id: ramp
  name: 无障碍坡道
  spot: 门口
  material: 混凝土
  bbox: [26, 59, 15, 7]
  depth: 9.51
- id: entry_apron
  name: 门前平台
  spot: 门口
  material: 混凝土
  bbox: [45, 60, 23, 4]
  depth: 9.46
deco: 陈默手里拎着的运动饮料，门边导诊立牌与一摞宣传折页，绿植箱里龟背竹叶上落灰
atmosphere: 晴朗上午的阳光落在临街入口，玻璃门里透出大厅白光，康复中心的日常被一个不速之客打断
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
