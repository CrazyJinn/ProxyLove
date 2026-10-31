游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 南滨路-滨江步道
scene_id: QW7CSvlX5k
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  ground_desc: 江面,浮着薄雾般的晨光
  sky_desc: 清晨薄雾天光,低角度暖阳
  floor_material: 塑胶跑道
lights:
- name: 光源
  pos: [58, 38]
  color: '#ffd9a8'
  intensity: 2.4
objects:
- id: railing_near
  name: 江侧护栏近段
  spot: 滨江步道
  material: 金属
  bbox: [55, 50, 21, 21]
  depth: 10.99
- id: lamp_head
  name: 路灯头
  spot: 滨江步道
  material: 金属
  bbox: [25, 0, 7, 6]
  depth: 6.33
  cname: 暖白路灯光
  clipped: 上缘越出
- id: lamp_post
  name: 路灯杆
  spot: 滨江步道
  material: 金属
  bbox: [27, 2, 4, 70]
  depth: 5.7
- id: railing_mid
  name: 江侧护栏中段
  spot: 滨江步道
  material: 金属
  bbox: [74, 54, 2, 16]
  depth: 3.3
deco: 江面浮着薄雾般的晨光,栏杆上凝着露水,岸边偶有长椅,跑者稀疏的剪影
atmosphere: 清晨的沿江跑步道,江面浮着薄雾般的晨光,跑者稀疏——搭讪碰壁与不说破的陪伴都发生在这条路上
time_of_day: 清晨

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
