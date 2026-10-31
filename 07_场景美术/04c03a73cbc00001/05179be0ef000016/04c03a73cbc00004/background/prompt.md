游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 街角咖啡店-点餐台
scene_id: PHuTf3ogEu
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [0, 79, 100, 21]
  back_wall: [0, 0, 69, 98]
  right_wall: [68, 0, 32, 100]
  ceiling: [0, 0, 100, 15]
  floor_material: 水泥自流平
  wall_material: 乳胶漆
lights:
- name: 光源
  pos: [50, 18]
  color: '#ffd9a0'
  intensity: 2.2
objects:
- id: back_cabinet
  name: 后柜
  spot: 点餐台
  material: 原木
  bbox: [56, 60, 21, 32]
  depth: 3.56
- id: w1
  name: 窗
  bbox: [13, 16, 43, 54]
  depth: 3.17
  kind: opening
  desc: 临街大窗,清晨冷蓝天光
- id: counter_a
  name: 吧台横段
  spot: 点餐台
  material: 原木
  bbox: [19, 56, 49, 44]
  depth: 3.07
  clipped: 下缘越出
- id: display_case
  name: 蛋糕展示柜
  spot: 点餐台
  material: 玻璃
  bbox: [14, 52, 26, 48]
  depth: 3.05
  clipped: 下缘越出
- id: counter_b
  name: 吧台侧段
  spot: 点餐台
  material: 原木
  bbox: [0, 63, 7, 37]
  depth: 2.78
  clipped: 左下缘越出
deco: espresso 机蒸汽嘶嘶,台面纸杯堆与夹着的价目单,玻璃柜里隔夜贝果,咖啡师擦着杯子
atmosphere: 清晨清冷的街角咖啡店
time_of_day: 清晨

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
