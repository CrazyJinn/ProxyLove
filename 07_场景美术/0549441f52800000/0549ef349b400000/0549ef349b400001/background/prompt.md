游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 vibe 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 苏晓禾家-客厅
scene_id: S9R1UdkC3N
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  back_wall: [0, 0, 100, 86]
  floor_material: 原木
  wall_material: 乳胶漆
lights:
- name: 光源
  pos: [50, -21]
  color: '#fff4e0'
  intensity: 2.2
  out_of_frame: true
- name: 光源
  pos: [43, 26]
  color: '#eaf4ff'
  intensity: 1.2
objects:
- id: dining_table
  name: 小方餐桌
  spot: 苏晓禾家-客厅
  material: 原木
  bbox: [83, 62, 17, 38]
  depth: 3.54
  clipped: 右下缘越出
- id: sofa
  name: 双人沙发
  spot: 苏晓禾家-客厅
  material: 布艺
  bbox: [0, 63, 17, 37]
  depth: 3.2
  clipped: 左下缘越出
- id: w1
  name: 窗
  bbox: [22, 6, 42, 55]
  depth: 3.2
  kind: opening
  desc: 北墙大窗,上午阳光斜入
- id: coffee_table
  name: 茶几
  spot: 苏晓禾家-客厅
  material: 原木
  bbox: [0, 86, 19, 14]
  depth: 3.06
  clipped: 左下缘越出
deco: 东北角餐桌上的不锈钢保温桶与两只白瓷碗；沙发扶手搭着的抱枕薄毯；窗台一小盆绿萝；茶几上翻开的杂志与纸巾盒
vibe: 上午阳光从北窗斜漫进来，独居公寓收拾得干净利落的安静，空气里浮着淡淡的皂香
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
