游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 网吧-训练区
scene_id: RxoSkCPyin
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  back_wall: [8, 16, 85, 53]
  floor_material: 瓷砖
  wall_material: 乳胶漆
lights:
- name: 光源
  pos: [50, -5]
  color: '#9fc3e8'
  intensity: 1.1
  out_of_frame: true
- name: 光源
  pos: [50, 46]
  color: '#7fb0d8'
  intensity: 0.9
objects:
- id: monitor_wall
  name: 五联显示器排
  spot: 训练区
  material: 玻璃
  bbox: [14, 47, 72, 10]
  depth: 4.89
- id: storage_cabinet
  name: 储物柜
  spot: 训练区
  material: 金属
  bbox: [0, 35, 12, 52]
  depth: 4.86
  clipped: 左缘越出
- id: train_desk_row
  name: 训练长桌
  spot: 训练区
  material: 金属
  bbox: [8, 57, 84, 17]
  depth: 4.7
- id: partition_screen
  name: 隔断屏风
  spot: 训练区
  material: 布艺
  bbox: [92, 0, 8, 100]
  depth: 4.27
  clipped: 右上下缘越出
deco: 桌面缠绕的线缆与机械键盘，成排的能量饮料罐，泡面桶沿桌角堆叠，椅背上搭着队服外套，白板角贴着赛程便签
atmosphere: 遮光帘拉满的昏暗网吧训练区，白天光被挡在帘外，五联显示器的冷色荧光是室内主光源，顶灯只余微光，键盘敲击声密集起伏，混着泡面与功能饮料的气味
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
