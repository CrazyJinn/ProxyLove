游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 林梦家
scene_id: RLFwn8iZlJ
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [0, 62, 100, 38]
  back_wall: [54, 0, 46, 99]
  left_wall: [0, 21, 54, 52]
  ceiling: [0, 0, 100, 33]
  floor_material: 浅色大板砖
  wall_material: 乳胶漆
lights:
- name: 光源
  pos: [38, 40]
  color: '#9fb8d8'
  intensity: 1.8
- name: 光源
  pos: [76, 7]
  color: '#ffd9a8'
  intensity: 0.9
objects:
- id: work_desk
  name: 剪辑工作站长桌
  spot: 林梦家
  material: 木饰面
  bbox: [35, 55, 22, 13]
  depth: 8.06
- id: w1
  name: 窗
  bbox: [11, 27, 39, 38]
  depth: 7.73
  kind: opening
  desc: 整面落地窗,夜景城市光
- id: low_board
  name: 电视矮柜
  spot: 林梦家
  material: 木饰面
  bbox: [74, 62, 26, 17]
  depth: 6.78
  clipped: 右缘越出
- id: coffee_table
  name: 长茶几
  spot: 林梦家
  material: 木饰面
  bbox: [38, 65, 19, 16]
  depth: 5.19
- id: sofa
  name: 客厅组合沙发
  spot: 林梦家
  material: 布艺
  bbox: [27, 59, 33, 33]
  depth: 4.85
- id: dining_table
  name: 餐桌
  spot: 林梦家
  material: 岩板
  bbox: [84, 83, 16, 17]
  depth: 2.44
  clipped: 右下缘越出
deco: 剪辑长桌双显示器亮着,耳机挂在支架上,外卖盒与奶茶杯,落地窗外城市夜景
atmosphere: 空荡大平层只剩屏幕光与城市光,剪辑声与外卖盒陪伴的独居夜晚
time_of_day: 夜晚

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
