游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 八楼出租屋-厨房餐区
scene_id: QW77oRdOwT
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [0, 65, 83, 35]
  back_wall: [0, 1, 39, 99]
  right_wall: [37, 0, 54, 76]
  floor_material: 旧瓷砖
lights:
- name: 光源
  pos: [45, 1]
  color: '#dfe8f0'
  intensity: 1.0
objects:
- id: w1
  name: 窗
  bbox: [45, 21, 10, 14]
  depth: 3.32
  kind: opening
  desc: 东墙高处小窗（厨房天光窗），深夜无光
- id: kitchen_stove
  name: 旧单灶台与水槽
  spot: 门厅
  material: 不锈钢
  bbox: [37, 46, 28, 32]
  depth: 3.23
- id: fridge
  name: 冰箱
  spot: 门厅
  material: 金属喷涂
  bbox: [64, 23, 22, 62]
  depth: 2.89
- id: inner_door
  name: 卧室内门
  spot: 门厅
  material: 原木
  bbox: [4, 9, 26, 84]
  depth: 2.66
- id: door
  name: 入户门
  bbox: [83, 4, 17, 96]
  depth: 2.44
  kind: opening
  clipped: 右下缘越出
deco: ''
atmosphere: 十几平米里挤出来的窄小厨房与折叠餐桌,烟火气和生活痕迹并存,白天也局促却踏实
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
