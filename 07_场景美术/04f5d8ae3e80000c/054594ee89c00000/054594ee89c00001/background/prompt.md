游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 vibe 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 康复中心-花园
scene_id: S3p7v2bvfN
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  ground_desc: 花园外围院区步道与绿化带，远处街区
  sky_desc: 晴朗上午，淡蓝少云
  floor_material: 草坪
lights:
- name: 光源
  pos: [307, -388]
  color: '#fff3d8'
  intensity: 2.5
  out_of_frame: true
objects:
- id: door_back
  name: 花园玻璃门
  spot: 花园
  material: 玻璃
  bbox: [60, 34, 16, 24]
  depth: 8.71
- id: facade_back
  name: 康复中心主体立面
  spot: 花园
  material: 混凝土
  bbox: [7, 14, 86, 44]
  depth: 8.62
- id: tree_crown
  name: 乔木树冠
  spot: 花园
  bbox: [0, 0, 34, 36]
  depth: 8.28
  clipped: 左上缘越出
- id: tree_trunk
  name: 乔木树干
  spot: 花园
  material: 原木
  bbox: [18, 29, 5, 32]
  depth: 8.05
- id: planter_l
  name: 抬高花坛(左)
  spot: 花园
  bbox: [0, 56, 15, 10]
  depth: 7.79
  clipped: 左缘越出
- id: planter_r
  name: 抬高花坛(右)
  spot: 花园
  bbox: [85, 56, 15, 10]
  depth: 7.79
  clipped: 右缘越出
- id: bench_garden
  name: 患者长椅
  spot: 花园
  material: 原木
  bbox: [62, 54, 9, 10]
  depth: 7.49
- id: pad_activity
  name: 塑胶活动垫
  spot: 花园
  material: 塑胶
  bbox: [28, 63, 44, 14]
  depth: 5.23
deco: 草坪上散落的彩色积木；活动垫边一摞软坐垫；长椅上搭着的薄毯；花坛边停一辆折叠轮椅
vibe: 晴朗上午的阳光铺满户外康复花园，草坪与花坛安静明亮，风里带青草气味，大厅器械声隔着玻璃门隐约传来
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
