游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 理发店-剪发区
scene_id: QW7Q5BdYAq
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [0, 77, 100, 23]
  back_wall: [36, 0, 64, 100]
  left_wall: [0, 0, 36, 100]
  ceiling: [0, 0, 100, 23]
  floor_material: 黑白格瓷砖
lights:
- name: 光源
  pos: [56, 25]
  color: '#ffffff'
  intensity: 2.4
objects:
- id: w1
  name: 窗
  bbox: [0, 20, 19, 58]
  depth: 3.49
  kind: opening
  desc: 临街玻璃窗,白天街景
  clipped: 左缘越出
- id: bench
  name: 等候长凳
  spot: 剪发区
  material: 皮革
  bbox: [0, 78, 18, 22]
  depth: 3.42
  clipped: 左下缘越出
- id: mirror_station
  name: 镜台连桌
  spot: 剪发区
  material: 原木
  bbox: [35, 56, 43, 44]
  depth: 3.28
  clipped: 下缘越出
- id: barber_chair_1
  name: 理发椅一
  spot: 剪发区
  material: 皮革
  bbox: [28, 62, 22, 38]
  depth: 2.94
  clipped: 下缘越出
- id: washbed
  name: 洗头床
  spot: 剪发区
  material: 陶瓷
  bbox: [80, 68, 20, 32]
  depth: 2.65
  clipped: 右下缘越出
- id: barber_chair_2
  name: 理发椅二
  spot: 剪发区
  material: 皮革
  bbox: [49, 67, 27, 33]
  depth: 2.3
  clipped: 下缘越出
deco: 碎发散落地面,皮围布搭在椅背,镜台上推剪刀夹与发胶罐,角落复古音箱放着 hip-hop
atmosphere: 轻快 hip-hop 鼓点与推剪声里,飘着发胶、咖啡与皮革味;镜前灯带亮得干脆,是改头换面的仪式感
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
