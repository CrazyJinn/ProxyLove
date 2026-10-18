游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 服装店
scene_id: QmJFWWyN17
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  back_wall: [8, 6, 84, 70]
  left_wall: [8, 6, 3, 70]
  right_wall: [89, 6, 3, 70]
  floor_material: 浅灰瓷砖
lights:
- name: 光源
  pos: [50, -21]
  color: '#ffffff'
  intensity: 2.3
  out_of_frame: true
objects:
- id: fitting
  name: 试衣间隔间
  spot: 服装店
  material: 布帘隔间
  bbox: [62, 21, 37, 64]
  depth: 3.65
- id: w1
  name: 窗
  bbox: [27, 17, 27, 44]
  depth: 3.64
  kind: opening
  desc: 临街橱窗,玻璃模特披着围巾
- id: shelf_wall_1
  name: 靠墙货架一
  spot: 服装店
  material: 金属镀铬
  bbox: [0, 0, 9, 100]
  depth: 2.86
  clipped: 左上下缘越出
- id: shelf_wall_2
  name: 靠墙货架二
  spot: 服装店
  material: 金属镀铬
  bbox: [91, 0, 9, 100]
  depth: 2.86
  clipped: 右上下缘越出
- id: rack_mid_1
  name: 中岛挂杆一
  spot: 服装店
  material: 金属镀铬
  bbox: [0, 8, 17, 92]
  depth: 2.36
  clipped: 左下缘越出
deco: 挂杆上按色码齐的衣服,橱窗玻璃模特披着围巾,试衣间帘子半拉,收银台小票与 POS 机
atmosphere: 店面不大却码得整齐,挂杆按色排开的平价成衣店;试衣间帘子一拉一开之间,人重新有了样子
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
