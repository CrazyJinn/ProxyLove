游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 八楼出租屋-电脑桌直播位-更新设备前
scene_id: QW77oRdOwS
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [0, 73, 100, 27]
  back_wall: [0, 0, 51, 100]
  right_wall: [51, 0, 49, 100]
  ceiling: [0, 0, 100, 15]
  floor_material: 原木地板
lights:
- name: 光源
  pos: [47, 56]
  color: '#bcd4f0'
  intensity: 2.2
objects:
- id: desk
  name: 旧电脑桌
  spot: 卧室
  material: 原木
  bbox: [35, 57, 23, 30]
  depth: 3.52
- id: w1
  name: 窗
  bbox: [5, 19, 30, 49]
  depth: 3.0
  kind: opening
  desc: 卧室旧窗，深夜窗外无光，窗帘半拉
- id: bed
  name: 单人床
  spot: 卧室
  material: 布艺软包
  bbox: [0, 80, 14, 20]
  depth: 2.36
  clipped: 左下缘越出
deco: 电脑桌上有一个老旧的显示器和主机,桌面上还凌乱的堆着一些垃圾和一桶吃剩的泡面
atmosphere: 旧设备堆出的深夜直播角,屏幕冷光是这间小屋唯一醒着的东西
time_of_day: 夜晚

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
