游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 美术馆-展厅
scene_id: RxmKnebFy7
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  back_wall: [9, 22, 82, 40]
  floor_material: 瓷砖
  wall_material: 乳胶漆
lights:
- name: 光源
  pos: [50, 23]
  color: '#f5f3ea'
  intensity: 2.6
- name: 光源
  pos: [50, -35]
  color: '#eef0ea'
  intensity: 1.6
  out_of_frame: true
objects:
- id: pedestal_corner
  name: 雕塑基座
  spot: 展厅
  material: 混凝土
  bbox: [84, 52, 9, 13]
  depth: 9.77
- id: painting_main
  name: 主画墙大画
  spot: 展厅
  material: 布艺
  bbox: [41, 33, 19, 19]
  depth: 8.81
- id: bench_mid
  name: 观展长凳
  spot: 展厅
  material: 原木
  bbox: [12, 61, 17, 7]
  depth: 7.33
- id: partition_wall
  name: 自由展墙
  spot: 展厅
  material: 金属
  bbox: [85, 0, 15, 100]
  depth: 6.44
  clipped: 右上下缘越出
deco: 画框下贴着小小说明牌与语音导览编号，观众手腕上夹着纸质手环，长凳上坐着小声交谈的休息者，墙边地贴导流线弯向下一展厅
atmosphere: 恒温展厅里射灯把静光打在画布上，吸音吊顶把脚步与低语压得很轻，看画的间隔里能听见空调风声，午后的时间在这里放慢
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
