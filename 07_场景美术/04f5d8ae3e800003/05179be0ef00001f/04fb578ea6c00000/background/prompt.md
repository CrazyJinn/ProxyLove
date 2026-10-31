游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 星耀电竞基地-训练馆
scene_id: QW7J1XaAFc
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [0, 74, 100, 26]
  back_wall: [21, 15, 79, 65]
  left_wall: [0, 0, 22, 100]
  ceiling: [0, 0, 100, 21]
  floor_material: 深色橡胶地垫
  wall_material: 吸音板
lights:
- name: 光源
  pos: [58, -2]
  color: '#eaf2ff'
  intensity: 2.6
  out_of_frame: true
objects:
- id: tactic_screen
  name: 战术大屏
  spot: 训练馆
  material: 玻璃屏
  bbox: [32, 18, 55, 47]
  depth: 4.79
- id: review_bench
  name: 复盘长凳
  spot: 训练馆
  material: 皮革
  bbox: [34, 66, 50, 16]
  depth: 4.71
- id: lockers
  name: 储物柜
  spot: 训练馆
  material: 金属
  bbox: [0, 1, 15, 99]
  depth: 3.56
  clipped: 左下缘越出
- id: desk_row
  name: 五连训练桌
  spot: 训练馆
  material: 金属工位
  bbox: [15, 68, 69, 32]
  depth: 3.16
  clipped: 下缘越出
- id: logo_wall
  name: 队标墙板
  spot: 训练馆
  material: 亚克力灯板
  bbox: [86, 0, 14, 100]
  depth: 2.89
  clipped: 右上下缘越出
deco: 五台训练机屏幕亮着队标蓝,键盘声密如雨点,桌面耳机与能量饮料罐,战术屏定格复盘画面
atmosphere: 五台训练机屏幕亮着队标蓝,键盘声密如雨点——这里只认成绩不认解释
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
