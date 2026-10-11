游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 八楼出租屋-床铺区
scene_id: QW77oRdOwU
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [0, 49, 100, 51]
  back_wall: [56, 0, 44, 100]
  left_wall: [0, 0, 58, 87]
lights:
- name: 光源
  pos: [90, -121]
  color: '#e8d9b0'
  intensity: 1.2
  out_of_frame: true
objects:
- id: bed
  name: 单人床
  spot: 卧室
  bbox: [15, 36, 57, 57]
  depth: 2.79
- id: suitcase
  name: 旧行李箱
  spot: 卧室
  bbox: [0, 48, 22, 43]
  depth: 2.62
  clipped: 左缘越出
- id: w1
  name: 窗
  bbox: [77, 0, 23, 50]
  depth: 2.59
  kind: opening
  desc: 卧室旧窗，深夜窗外无光，窗帘半拉
  clipped: 右上缘越出
deco: 窗墙以半旧蓝灰床帘与斑驳墙皮为主，墙上贴着一张褪色的电竞海报；床头靠窗墙堆着旧抱枕与缠乱的充电线；床尾立着一只兼作边几的旧行李箱
atmosphere: 深夜睡域，旧吸顶灯昏黄微亮，床铺皱褶透着居住痕迹，安静中带着压抑的沉默，晴天
time_of_day: ''

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
