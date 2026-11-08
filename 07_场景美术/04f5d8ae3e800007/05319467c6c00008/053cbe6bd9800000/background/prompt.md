游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 登山步道-半山观景台
scene_id: Re2PEUaYTx
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [2, 48, 65, 4]
  ground: [4, 67, 61, 8]
  ground_desc: 山坡林地与远处山脊轮廓，晨雾未散尽
  sky_desc: 晴朗上午，淡蓝少量薄云
  floor_material: 混凝土
lights:
- name: 光源
  pos: [49, -255]
  color: '#fff2dc'
  intensity: 2.3
  out_of_frame: true
objects:
- id: treebelt_right
  name: 林带·右
  spot: 登山步道-全线
  bbox: [20, 0, 27, 57]
  depth: 9.91
  clipped: 上缘越出
- id: treebelt_left
  name: 林带·左
  spot: 登山步道-全线
  bbox: [5, 7, 11, 43]
  depth: 9.88
- id: stair_far
  name: 石阶·远段
  spot: 登山步道-全线
  material: 混凝土
  bbox: [0, 41, 33, 11]
  depth: 8.87
  clipped: 左缘越出
- id: stair_mid
  name: 石阶·中段
  spot: 登山步道-全线
  material: 混凝土
  bbox: [0, 55, 15, 45]
  depth: 6.67
  clipped: 左下缘越出
- id: rail_deck
  name: 观景台护栏
  spot: 登山步道-全线
  material: 原木
  bbox: [23, 37, 46, 15]
  depth: 5.84
- id: bench
  name: 观景台长凳
  spot: 登山步道-全线
  material: 原木
  bbox: [0, 50, 8, 23]
  depth: 4.69
  clipped: 左缘越出
- id: platform
  name: 观景台平台
  spot: 登山步道-全线
  material: 原木
  bbox: [0, 49, 84, 51]
  depth: 4.2
  clipped: 左下缘越出
deco: 木平台上散着松针，长凳上搁着登山包与一瓶镇痛喷雾，护栏上搭着条毛巾
atmosphere: 半山开阔处山风清凉，脚下林海翻着浅浪，远处城市在薄雾里淡成剪影
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
