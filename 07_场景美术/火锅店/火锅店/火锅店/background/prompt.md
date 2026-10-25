游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 火锅店
scene_id: RVkysIzpeD
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [0, 63, 100, 33]
  back_wall: [41, 0, 59, 96]
  left_wall: [0, 0, 41, 86]
  ceiling: [0, 0, 100, 19]
  floor_material: 瓷砖
  wall_material: 瓷砖
lights:
- name: 光源
  pos: [48, 13]
  color: '#ffd9a0'
  intensity: 2.4
objects:
- id: booth_sofa_n
  name: 卡座沙发北位
  spot: 火锅店
  material: 原木
  bbox: [37, 50, 25, 23]
  depth: 4.91
  cname: 卡座沙发北位
- id: booth_table
  name: 火锅卡座桌
  spot: 火锅店
  material: 原木
  bbox: [30, 53, 23, 24]
  depth: 4.44
  cname: 火锅卡座桌
- id: booth_sofa_e
  name: 卡座沙发南位
  spot: 火锅店
  material: 原木
  bbox: [23, 53, 28, 32]
  depth: 4.07
  cname: 卡座沙发南位
- id: w1
  name: 窗
  bbox: [59, 9, 41, 50]
  depth: 4.0
  kind: opening
  desc: 临街大窗,午后日光斜照进来
  clipped: 右缘越出
- id: side_table
  name: 临窗小方桌
  spot: 火锅店
  material: 原木
  bbox: [63, 57, 15, 24]
  depth: 3.96
  cname: 临窗小方桌
- id: door
  name: 入户门
  bbox: [0, 0, -17, 100]
  depth: 0.58
  kind: opening
  clipped: 左上下缘越出
deco: 油碟蒜泥香菜小料摆一圈,塑封菜单立在锅边,纸巾盒压着两听酸梅汤,公筷搁在锅沿
atmosphere: 午市喧腾的市井火锅店,红汤翻滚白汽蒸腾,邻桌谈笑,相亲两人隔着锅气对坐尴尬又好笑
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
