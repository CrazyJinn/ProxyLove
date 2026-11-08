游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 林梦家-电竞房
scene_id: RLFwn8iZlJ
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [0, 62, 100, 38]
  back_wall: [0, 11, 50, 58]
  right_wall: [50, 0, 50, 100]
  ceiling: [0, 0, 100, 19]
  floor_material: 深色岩板
  wall_material: 乳胶漆
lights:
- name: 光源
  pos: [30, 46]
  color: '#a8c4e0'
  intensity: 2.4
- name: 光源
  pos: [46, 54]
  color: '#8f6fe8'
  intensity: 1.4
- name: 光源
  pos: [26, 36]
  color: '#5f7290'
  intensity: 1.2
objects:
- id: pc_tower
  name: RGB主机箱
  spot: 林梦家-电竞房
  material: 玻璃
  bbox: [44, 56, 4, 10]
  depth: 5.76
- id: w1
  name: 窗
  bbox: [9, 17, 32, 40]
  depth: 5.69
  kind: opening
  desc: 北墙大窗,深夜城市灯火
- id: wall_shelf
  name: 壁挂搁板
  spot: 林梦家-电竞房
  material: 木饰面
  bbox: [14, 31, 30, 7]
  depth: 5.53
- id: game_desk
  name: 电竞长桌
  spot: 林梦家-电竞房
  material: 金属
  bbox: [14, 53, 31, 18]
  depth: 5.43
- id: game_chair
  name: 电竞椅
  spot: 林梦家-电竞房
  material: 皮革
  bbox: [0, 47, 17, 30]
  depth: 4.95
  clipped: 左缘越出
- id: low_bench
  name: 窗侧矮榻
  spot: 林梦家-电竞房
  material: 布艺
  bbox: [47, 62, 20, 22]
  depth: 4.07
deco: 电竞长桌三屏阵列亮着，机甲风机械键盘和大鼠标垫，高背电竞椅停在桌前西端半转向像刚起身，耳机挂在支架上，外卖盒与空能量饮料罐堆在桌角，搁板上一排手办与联赛奖杯
atmosphere: 深夜电竞房被三屏冷光和机箱RGB灯带点亮，窗外一整面城市灯火，机械键盘声与排位音效在空旷大平层里回荡
time_of_day: 夜晚

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
