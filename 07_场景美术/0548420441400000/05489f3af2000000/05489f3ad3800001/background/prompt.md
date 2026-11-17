游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 vibe 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 瑜伽馆
scene_id: S7k7py37ir
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [28, 70, 72, 3]
  back_wall: [28, 30, 72, 43]
  ceiling: [29, 30, 71, 3]
  floor_material: 原木
  wall_material: 乳胶漆
lights:
- name: 光源
  pos: [126, 13]
  color: '#ffffff'
  intensity: 2.4
  out_of_frame: true
objects:
- id: mirror_wall
  name: 练习区整面镜
  spot: 练习室
  material: 镜面玻璃
  bbox: [80, 38, 20, 30]
  depth: 9.47
  cname: 练习区整面镜
  clipped: 右缘越出
- id: plant_big
  name: 大盆龟背竹
  spot: 练习室
  material: 布艺
  bbox: [86, 53, 14, 22]
  depth: 8.19
  cname: 大盆龟背竹
  clipped: 右缘越出
- id: w1
  name: 窗
  bbox: [45, 37, 21, 24]
  depth: 6.7
  kind: opening
  desc: 北墙大窗,上午阳光斜进练习厅
deco: 地面并排铺开两张瑜伽垫,墙边卷立几卷备用垫,架格上码着瑜伽砖与弹力带,饮水机旁一排纸杯,窗台上一小盆绿萝
vibe: 上午阳光从北墙大窗斜进练习厅,白光匀净通透,空气里淡香薰混着橡胶垫气味,背景轻音乐若有若无
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
