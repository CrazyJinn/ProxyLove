游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 漫展会场-展厅通道
scene_id: Re2PEUaYTv
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  back_wall: [28, 9, 43, 52]
  floor_material: 瓷砖
  wall_material: 乳胶漆
lights:
- name: 光源
  pos: [50, -7]
  color: '#f2f5f8'
  intensity: 2.4
  out_of_frame: true
- name: 光源
  pos: [50, 17]
  color: '#eef1f5'
  intensity: 2.0
objects:
- id: banner
  name: 跨道主题横幅
  spot: 漫展会场-展厅区
  material: 布艺
  bbox: [31, 18, 37, 7]
  depth: 13.04
  cname: 漫展主视觉横幅
- id: booth_l_back
  name: 展位背板·左后
  spot: 漫展会场-展厅区
  material: 金属
  bbox: [11, 38, 22, 30]
  depth: 11.33
- id: booth_r_back
  name: 展位背板·右后
  spot: 漫展会场-展厅区
  material: 金属
  bbox: [67, 38, 22, 30]
  depth: 11.33
- id: stamp_desk
  name: 集章台
  spot: 漫展会场-展厅区
  material: 金属
  bbox: [71, 56, 16, 13]
  depth: 8.3
- id: booth_l_front
  name: 展位背板·左前
  spot: 漫展会场-展厅区
  material: 金属
  bbox: [0, 3, 11, 97]
  depth: 5.96
  clipped: 左下缘越出
- id: booth_r_front
  name: 展位背板·右前
  spot: 漫展会场-展厅区
  material: 金属
  bbox: [89, 3, 11, 97]
  depth: 5.96
  clipped: 右下缘越出
deco: 两侧展位的限定商品陈列与立牌，集章台上的印章与集章卡，拍照打卡点的立式相框，派发的塑料袋，手里越拎越多的战利品
atmosphere: 馆内展厅主通道的节庆式热闹，两侧展位灯箱与巨幅主题海报亮着，人声、广播声与快门声交织
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
