游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 漫展会场-主舞台
scene_id: Rs4wQwUYEb
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  back_wall: [20, 13, 60, 50]
  floor_material: 混凝土
  wall_material: 金属
lights:
- name: 光源
  pos: [50, 16]
  color: '#ffffff'
  intensity: 2.6
- name: 光源
  pos: [50, 32]
  color: '#ffd9a0'
  intensity: 1.8
objects:
- id: speaker_l
  name: 线阵音箱塔·左
  spot: 漫展会场-舞台区
  material: 金属
  bbox: [19, 41, 7, 22]
  depth: 16.28
- id: speaker_r
  name: 线阵音箱塔·右
  spot: 漫展会场-舞台区
  material: 金属
  bbox: [74, 41, 7, 22]
  depth: 16.28
- id: led_screen
  name: 主屏LED墙
  spot: 漫展会场-舞台区
  material: 金属
  bbox: [29, 30, 42, 26]
  depth: 15.41
  cname: 应援主屏
- id: stage_main
  name: 主舞台台体
  spot: 漫展会场-舞台区
  material: 金属
  bbox: [17, 56, 66, 11]
  depth: 13.04
- id: truss_lights
  name: 灯光桁架
  spot: 漫展会场-舞台区
  material: 金属
  bbox: [10, 5, 79, 6]
  depth: 12.46
deco: 眼前起伏的应援棒与灯牌海，举过头顶的手机屏幕阵，舞台飘落的彩带，工作人员的黑Tee与对讲机
atmosphere: 漫展主舞台环节的午后高光，大屏亮着应援色，主持人声与欢呼浪一阵阵漫过观众区
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
