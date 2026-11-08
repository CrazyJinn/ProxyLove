游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 林梦家-客厅
scene_id: RrCNuG0g2V
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  back_wall: [2, 10, 84, 56]
  left_wall: [2, 10, 3, 56]
  right_wall: [83, 10, 3, 56]
  floor_material: 浅色大板砖
  wall_material: 乳胶漆
lights:
- name: 光源
  pos: [-36, 14]
  color: '#d8e6f2'
  intensity: 1.6
  out_of_frame: true
- name: 光源
  pos: [50, 11]
  color: '#ffe2b8'
  intensity: 1.0
objects:
- id: tv
  name: 壁挂大屏电视
  spot: 林梦家-客厅
  material: 玻璃
  bbox: [31, 24, 38, 31]
  depth: 5.03
- id: low_board
  name: 电视矮柜
  spot: 林梦家-客厅
  material: 木饰面
  bbox: [35, 58, 31, 12]
  depth: 4.92
- id: w1
  name: 窗
  bbox: [0, 11, 1, 89]
  depth: 4.6
  kind: opening
  desc: 整面落地窗,上午日光
  clipped: 左下缘越出
- id: coffee_table
  name: 低矮长茶几
  spot: 林梦家-客厅
  material: 木饰面
  bbox: [0, 84, 18, 16]
  depth: 3.15
  clipped: 左下缘越出
- id: sofa
  name: 客厅组合沙发
  spot: 林梦家-客厅
  material: 布艺
  bbox: [0, 85, 13, 15]
  depth: 2.95
  clipped: 左下缘越出
deco: 茶几上摊着几页打印的切片方案和遥控器，两杯温水冒着余温，沙发一角堆着林梦惯用的抱枕，大屏上热血混剪正放到一半
atmosphere: 上午日光从整面落地窗铺满空旷客厅，沙发区只两个人和一块循环播放切片的大屏，亮堂里带着一点不知往哪坐的客气
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
