游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 林梦家-卧室
scene_id: RrCNuG0g2U
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  back_wall: [30, 10, 40, 44]
  floor_material: 浅色大板砖
  wall_material: 乳胶漆
lights:
- name: 光源
  pos: [50, 27]
  color: '#dceafa'
  intensity: 2.2
objects:
- id: w1
  name: 窗
  bbox: [37, 14, 26, 33]
  depth: 6.13
  kind: opening
  desc: 北墙大窗,清晨日光正照在床上
- id: bedside_l
  name: 床头柜(左)
  spot: 林梦家-卧室
  material: 木饰面
  bbox: [34, 48, 6, 9]
  depth: 5.89
- id: bedside_r
  name: 床头柜(右)
  spot: 林梦家-卧室
  material: 木饰面
  bbox: [60, 48, 6, 9]
  depth: 5.89
- id: bed
  name: 低床架双人床
  spot: 林梦家-卧室
  material: 布艺
  bbox: [37, 49, 25, 13]
  depth: 5.36
deco: 床头柜上一杯隔夜温水和亮着的手机，床尾长凳搭着未拆吊牌的客用浴袍，衣柜门缝漏出一线更暗的阴影
atmosphere: 清晨微光从北墙大窗正照在浅灰床品上，酒店般空旷的主卧静得只剩中央空调低鸣，陌生感随宿醉一起浮上来
time_of_day: 清晨

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
