游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 漫展会场-入口
scene_id: RkaSUg0DbF
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  ground_desc: 广场外城市街景与地铁口方向涌来的人流，远景虚化
  sky_desc: 晴朗午后天空，淡蓝少量云
  floor_material: 混凝土
lights:
- name: 光源
  pos: [71, -22]
  color: '#fff2dc'
  intensity: 2.2
  out_of_frame: true
objects:
- id: arch
  name: 主题拱门
  spot: 漫展会场-入口区
  material: 金属
  bbox: [30, 20, 40, 39]
  depth: 14.99
  cname: 漫展主题拱门
- id: gate_l
  name: 验票闸机·左
  spot: 漫展会场-入口区
  material: 金属
  bbox: [30, 53, 11, 8]
  depth: 13.04
- id: gate_r
  name: 验票闸机·右
  spot: 漫展会场-入口区
  material: 金属
  bbox: [59, 53, 11, 8]
  depth: 13.04
- id: gate_c
  name: 验票闸机·中
  spot: 漫展会场-入口区
  material: 金属
  bbox: [45, 53, 10, 8]
  depth: 12.64
- id: fence_l_far
  name: 排队围栏·左后
  spot: 漫展会场-入口区
  material: 金属
  bbox: [16, 53, 14, 13]
  depth: 11.42
- id: fence_r_far
  name: 排队围栏·右后
  spot: 漫展会场-入口区
  material: 金属
  bbox: [70, 53, 14, 13]
  depth: 11.42
- id: fence_l_near
  name: 排队围栏·左前
  spot: 漫展会场-入口区
  material: 金属
  bbox: [0, 56, 14, 44]
  depth: 6.8
  clipped: 左下缘越出
- id: fence_r_near
  name: 排队围栏·右前
  spot: 漫展会场-入口区
  material: 金属
  bbox: [86, 56, 14, 44]
  depth: 6.8
  clipped: 右下缘越出
deco: 蛇形围栏上的主题指示牌，地上荧光导向地贴与被踩皱的宣传单，闸机口递出的验票手环，林梦手里的墨镜与迷你挎包
atmosphere: 周日午后的漫展入口广场，人潮从地铁口方向涌来，主题拱门与彩旗立牌喧闹夺目，盛装coser与便装人流交错
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
