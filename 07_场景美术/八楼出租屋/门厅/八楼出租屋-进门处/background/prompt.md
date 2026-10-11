游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 八楼出租屋-进门处
scene_id: QW77oRdOwV
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [0, 73, 100, 27]
  right_wall: [0, 0, 37, 100]
lights:
- name: 光源
  pos: [52, -30]
  color: '#e8d9b0'
  intensity: 1.2
  out_of_frame: true
objects:
- id: fridge
  name: 冰箱
  spot: 门厅
  bbox: [15, 20, 28, 75]
  depth: 2.44
- id: kitchen_stove
  name: 旧单灶台与水槽
  spot: 门厅
  bbox: [0, 56, 24, 44]
  depth: 2.33
  clipped: 左下缘越出
- id: door
  name: 入户门
  bbox: [40, 9, 18, 80]
  depth: 2.33
  kind: opening
- id: shoe_cabinet
  name: 窄鞋柜
  spot: 门厅
  bbox: [83, 74, 17, 26]
  depth: 1.92
  clipped: 右下缘越出
deco: 一扇磨旧的薄铁门位于前方（即入户门），门旁墙面刷着半截褪色绿漆，猫眼与锁扣泛着钝光；门侧窄鞋柜上堆着钥匙串与外卖传单，柜边立着一柄收拢的雨伞与吸水地垫，门后挂着一件微湿的薄外套
atmosphere: 进门瞬间的局部特写氛围，白炽灯亮着，门后外套微湿暗示刚有人进出，平凡日常里的细节感，雨天
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
