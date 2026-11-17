游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 vibe 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 书店-二楼书区
scene_id: S9D9aBn0u9
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  back_wall: [4, 5, 91, 73]
  left_wall: [4, 5, 4, 73]
  right_wall: [91, 5, 4, 73]
  floor_material: 原木
  wall_material: 乳胶漆
lights:
- name: 光源
  pos: [50, -27]
  color: '#ffffff'
  intensity: 2.3
  out_of_frame: true
objects:
- id: bench_low
  name: 窗下矮书台
  spot: 二楼书区
  material: 原木
  bbox: [26, 70, 48, 12]
  depth: 3.46
- id: w1
  name: 窗
  bbox: [28, 15, 43, 40]
  depth: 3.34
  kind: opening
  desc: 临街木框大窗,窗外街景与斜阳
- id: shelf_med
  name: 分类书架
  spot: 二楼书区
  material: 原木
  bbox: [85, 0, 15, 100]
  depth: 3.08
  clipped: 右上下缘越出
- id: shelf_main
  name: 分类书架墙
  spot: 二楼书区
  material: 原木
  bbox: [0, 0, 14, 100]
  depth: 3.03
  clipped: 左上下缘越出
deco: 架格里文学、社科、生活、科技类书按分类标牌密排；书架端头平台码放的新书与畅销推荐；翻开的样书斜插在书列间；架格端头分类索引牌；窗下矮台摞着新书样册；地板上待归架的书堆
vibe: 斜阳暖光混着白亮顶灯，分类书架通道码到视线尽头，油墨味里透着规整的安静
time_of_day: 黄昏

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
