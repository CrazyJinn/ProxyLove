游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 vibe 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 美食街-公共长桌区
scene_id: S7DBKNvoO2
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [43, 56, 45, 4]
  ground: [43, 73, 44, 10]
  ground_desc: 主街延伸出去的远处街面与邻楼底层，正午日光下泛白
  sky_desc: 初夏正午，淡蓝少云，日头明亮
  floor_material: 沥青
lights:
- name: 光源
  pos: [37, -85]
  color: '#fff2d0'
  intensity: 2.6
  out_of_frame: true
objects:
- id: bench_b
  name: 条凳-桌后侧
  spot: 档口街面区
  material: 原木
  bbox: [39, 54, 12, 9]
  depth: 8.47
- id: long_table
  name: 公共长桌
  spot: 档口街面区
  material: 金属
  bbox: [44, 52, 15, 14]
  depth: 8.0
- id: awning
  name: 遮阳棚
  spot: 档口街面区
  material: 布艺
  bbox: [40, 31, 23, 7]
  depth: 7.96
- id: bench_a
  name: 条凳-桌前侧
  spot: 档口街面区
  material: 原木
  bbox: [56, 55, 8, 11]
  depth: 7.71
deco: 桌上一摞不锈钢餐盘与用过的纸巾；一次性筷子筒和醋瓶油辣罐；吃剩的串签堆；歪着拼桌的塑料凳
vibe: 遮阳棚滤下一块阴凉，正午日光晒白街面，闹中带闲的喘口气角落
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
