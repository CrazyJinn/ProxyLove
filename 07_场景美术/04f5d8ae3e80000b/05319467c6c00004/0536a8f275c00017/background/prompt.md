游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 路边摊-摊外路灯下
scene_id: RkaSUg0DbD
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [0, 52, 100, 48]
  ground: [0, 68, 100, 32]
  ground_desc: 摊区外城市街面，远处夜市灯火与人流的虚化延伸
  sky_desc: 夏夜深蓝天幕，薄云遮月
  floor_material: 沥青
lights:
- name: 光源
  pos: [57, -2]
  color: '#f4e9cf'
  intensity: 1.5
  out_of_frame: true
- name: 光源
  pos: [-6, 35]
  color: '#e8b06a'
  intensity: 0.8
  out_of_frame: true
objects:
- id: signboard
  name: 灯箱招牌
  spot: 路边摊-夜市摊区
  material: 玻璃
  bbox: [6, 36, 6, 11]
  depth: 9.63
  cname: 暖黄灯箱光
- id: grill_cart
  name: 烧烤炉车
  spot: 路边摊-夜市摊区
  material: 金属
  bbox: [0, 47, 8, 19]
  depth: 9.18
  clipped: 左缘越出
- id: stall_canopy
  name: 摊位遮棚
  spot: 路边摊-夜市摊区
  material: 布艺
  bbox: [0, 28, 12, 8]
  depth: 9.01
  clipped: 左缘越出
- id: lamp_head
  name: 路灯头
  spot: 路边摊-夜市摊区
  material: 金属
  bbox: [53, 0, 7, 3]
  depth: 6.97
  cname: 暖白路灯光
  clipped: 上缘越出
- id: lamp_post
  name: 路灯杆
  spot: 路边摊-夜市摊区
  material: 金属
  bbox: [55, 0, 4, 63]
  depth: 6.3
  clipped: 上缘越出
- id: sidewalk_front
  name: 人行道
  spot: 路边摊-夜市摊区
  material: 混凝土
  bbox: [79, 59, 21, 8]
  depth: 1.89
  clipped: 右缘越出
deco: 路灯杆下歪倒的共享单车，散落的空啤酒瓶与揉皱纸巾，路缘一滩积着油花的浅水洼
atmosphere: 散场后的夜市边缘，路灯暖白光把人影拉长，晚风带着残余炭烟味，远处传来收摊的卷帘门声
time_of_day: 夜晚

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
