游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 vibe 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 美食街-档口街面
scene_id: S7DBKNvoO1
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [5, 56, 49, 6]
  ground: [6, 75, 48, 14]
  ground_desc: 主街延伸出去的远处街面与邻楼底层，正午日光下泛白
  sky_desc: 初夏正午，淡蓝少云，日头明亮
  floor_material: 沥青
lights:
- name: 光源
  pos: [71, -107]
  color: '#fff2d0'
  intensity: 2.6
  out_of_frame: true
objects:
- id: stall_row_far
  name: 档口排-远段
  spot: 档口街面区
  material: 金属
  bbox: [42, 38, 16, 22]
  depth: 10.43
- id: stall_row_mid
  name: 档口排-中段
  spot: 档口街面区
  material: 金属
  bbox: [26, 37, 19, 25]
  depth: 9.47
- id: stall_row_near
  name: 档口排-近段
  spot: 档口街面区
  material: 金属
  bbox: [3, 35, 24, 29]
  depth: 9.16
deco: 档口前排开的竹蒸笼与翻滚油锅；玻璃柜里的卤味凉菜；垂挂的价目牌与褪色灯串；打包纸袋与竹签筒；地面油点与团起的纸巾
vibe: 正午日头直晒的烟火小街，档口蒸汽与吆喝声把空气烘得发亮
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
