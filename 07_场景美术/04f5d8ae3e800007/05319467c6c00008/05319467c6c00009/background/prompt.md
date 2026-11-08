游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 登山步道-林间石阶
scene_id: RsQjKULMe0
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  ground_desc: 山坡林地与远处山脊轮廓，晨雾未散尽
  sky_desc: 晴朗上午，淡蓝少量薄云
  floor_material: 混凝土
lights:
- name: 光源
  pos: [77, -34]
  color: '#fff2dc'
  intensity: 2.2
  out_of_frame: true
objects:
- id: treebelt_right
  name: 林带·右
  spot: 登山步道-全线
  bbox: [55, 13, 12, 48]
  depth: 13.25
- id: stair_far
  name: 石阶·远段
  spot: 登山步道-全线
  material: 混凝土
  bbox: [40, 52, 20, 4]
  depth: 10.42
- id: rail_deck
  name: 观景台护栏
  spot: 登山步道-全线
  material: 原木
  bbox: [62, 47, 29, 8]
  depth: 10.25
- id: platform
  name: 观景台平台
  spot: 登山步道-全线
  material: 原木
  bbox: [62, 55, 38, 10]
  depth: 8.56
  clipped: 右缘越出
- id: treebelt_left
  name: 林带·左
  spot: 登山步道-全线
  bbox: [0, 0, 39, 100]
  depth: 8.17
  clipped: 左上下缘越出
- id: bench
  name: 观景台长凳
  spot: 登山步道-全线
  material: 原木
  bbox: [65, 51, 8, 8]
  depth: 6.74
- id: stair_mid
  name: 石阶·中段
  spot: 登山步道-全线
  material: 混凝土
  bbox: [32, 59, 36, 13]
  depth: 6.71
- id: stair_near
  name: 石阶·近段
  spot: 登山步道-全线
  material: 混凝土
  bbox: [0, 78, 100, 22]
  depth: 3.3
  clipped: 左右下缘越出
deco: 石阶边缘的青苔与落叶，级缝里钻出的蕨叶，步道旁褪色的里程指示牌
atmosphere: 上午阳光透过杉樟树冠筛下斑驳光斑，石阶上落着碎叶，林间蝉声初起带一点潮气
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
