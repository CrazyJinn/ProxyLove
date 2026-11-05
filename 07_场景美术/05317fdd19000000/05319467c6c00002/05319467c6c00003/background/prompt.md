游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 小酒馆-吧台卡座
scene_id: Re2PEUaYTr
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  back_wall: [1, 14, 98, 71]
  floor_material: 原木
  wall_material: 木质墙板
lights:
- name: 光源
  pos: [50, -12]
  color: '#ffd9a0'
  intensity: 2.3
  out_of_frame: true
- name: 光源
  pos: [50, 27]
  color: '#ffcf87'
  intensity: 1.2
objects:
- id: wall_art
  name: 酒标装饰画
  spot: 吧台区
  material: 布艺
  bbox: [78, 37, 15, 22]
  depth: 4.91
- id: booth_sofa
  name: 卡座沙发
  spot: 吧台区
  material: 皮革
  bbox: [0, 63, 10, 36]
  depth: 4.82
  clipped: 左缘越出
- id: bar_counter
  name: 吧台台体
  spot: 吧台区
  material: 原木
  bbox: [89, 58, 11, 40]
  depth: 4.77
  clipped: 右缘越出
- id: back_shelf
  name: 吧台酒架
  spot: 吧台区
  material: 原木
  bbox: [24, 21, 53, 39]
  depth: 4.4
- id: booth_table
  name: 卡座茶桌
  spot: 吧台区
  material: 原木
  bbox: [0, 72, 0, 28]
  depth: 4.38
  clipped: 左下缘越出
deco: 卡座桌上三五啤酒瓶与一壶白酒拼杯，花生毛豆小碟与揉皱的纸巾团，醉趴那侧压着空杯；吧台上倒扣的杯塔、切半的柠檬与擦杯布；窗边高脚凳上搭着件外套
atmosphere: 夜里的小酒馆一角，暖黄酒架灯带压着音量，玻璃杯碰响混着邻桌低笑声
time_of_day: 夜晚

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
