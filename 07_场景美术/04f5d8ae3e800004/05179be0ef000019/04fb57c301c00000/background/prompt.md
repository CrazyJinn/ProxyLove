游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 连锁咖啡店-座位区
scene_id: QW7MyzUtiS
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [7, 69, 93, 31]
  back_wall: [57, 0, 43, 100]
  left_wall: [5, 12, 52, 73]
  ceiling: [5, 0, 95, 25]
  floor_material: 浅木复合地板
lights:
- name: 光源
  pos: [61, 13]
  color: '#f5f2ea'
  intensity: 2.0
objects:
- id: booth
  name: 长条卡座
  spot: 座位区
  material: 布艺卡座
  bbox: [54, 56, 35, 33]
  depth: 4.63
- id: table_pair
  name: 双人对桌
  spot: 座位区
  material: 原木
  bbox: [32, 61, 15, 22]
  depth: 4.47
- id: w1
  name: 窗
  bbox: [64, 0, 36, 82]
  depth: 4.2
  kind: opening
  desc: 北面大窗,白天柔光
  clipped: 右上缘越出
- id: table4_b
  name: 四人方桌二
  spot: 座位区
  material: 原木
  bbox: [90, 69, 10, 31]
  depth: 3.62
  clipped: 右下缘越出
deco: 桌面两杯美式一台笔记本电脑,纸巾折角,邻桌低语与咖啡机嘶嘶声作背景
atmosphere: 标准化连锁店的整洁亮堂,咖啡机嘶嘶声作背景音——一场条件先行的挖人邀约
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
