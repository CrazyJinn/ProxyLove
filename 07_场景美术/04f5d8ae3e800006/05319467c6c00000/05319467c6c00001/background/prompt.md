游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 超市-店内
scene_id: Re2PEUaYTp
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  back_wall: [11, 32, 78, 28]
  floor_material: 瓷砖
  wall_material: 乳胶漆
lights:
- name: 光源
  pos: [50, 20]
  color: '#f2f7f0'
  intensity: 2.6
- name: 光源
  pos: [50, 33]
  color: '#eaf2ec'
  intensity: 1.6
objects:
- id: produce_back
  name: 生鲜台
  spot: 店内
  material: 原木
  bbox: [7, 53, 11, 9]
  depth: 10.94
- id: cooler_back
  name: 立式冷柜组
  spot: 店内
  material: 玻璃
  bbox: [82, 40, 11, 21]
  depth: 10.93
- id: shelf_back
  name: 后墙货架墙
  spot: 店内
  material: 金属
  bbox: [19, 34, 61, 18]
  depth: 9.3
- id: gondola_left
  name: 通道货架岛·左
  spot: 店内
  material: 金属
  bbox: [23, 44, 12, 20]
  depth: 8.73
- id: gondola_right
  name: 通道货架岛·右
  spot: 店内
  material: 金属
  bbox: [65, 44, 12, 20]
  depth: 8.73
deco: 冷柜层架上的排排牛奶，货架端头黄底促销签，促销堆头成箱的酸奶
atmosphere: 清晨白炽灯通亮的宽敞沿街超市，冷柜压缩机嗡嗡作响，空气里飘着淡淡的生鲜与纸箱味
time_of_day: 清晨

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
