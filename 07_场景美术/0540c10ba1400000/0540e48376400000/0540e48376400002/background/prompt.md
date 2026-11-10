游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 美术馆-门厅
scene_id: RxmKnebFy6
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  back_wall: [6, 2, 88, 68]
  floor_material: 瓷砖
  wall_material: 乳胶漆
lights:
- name: 光源
  pos: [50, -44]
  color: '#f4f2ec'
  intensity: 2.4
  out_of_frame: true
- name: 光源
  pos: [50, 4]
  color: '#eef0ea'
  intensity: 1.4
objects:
- id: bench_entry
  name: 入口长凳
  spot: 门厅
  material: 原木
  bbox: [0, 64, 14, 21]
  depth: 5.75
  clipped: 左缘越出
- id: column_left
  name: 结构柱·左
  spot: 门厅
  material: 混凝土
  bbox: [0, 0, 7, 80]
  depth: 5.41
  clipped: 左上缘越出
- id: column_right
  name: 结构柱·右
  spot: 门厅
  material: 混凝土
  bbox: [93, 0, 7, 80]
  depth: 5.41
  clipped: 右上缘越出
- id: poster_wall
  name: 展览海报墙
  spot: 门厅
  material: 布艺
  bbox: [23, 19, 54, 36]
  depth: 5.22
deco: 售票台上立着扫码立牌与一摞对折宣传册，寄存柜格口贴着编号钥匙牌，长凳上摊着翻开的展览手册，导览图立牌旁一盆修剪齐整的绿植
atmosphere: 周六午后的日光从临街玻璃幕墙斜切进挑高门厅，白色石材地面亮得反光，空调凉意里混着宣传册的油墨味，广播偶尔压低声音提醒文明观展
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
