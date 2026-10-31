游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 康复中心
scene_id: RVaUJp92GH
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  back_wall: [2, 11, 96, 60]
  left_wall: [2, 11, 3, 60]
  right_wall: [95, 11, 3, 60]
  floor_material: 浅灰塑胶
  wall_material: 乳胶漆
lights:
- name: 光源
  pos: [50, -15]
  color: '#ffffff'
  intensity: 2.4
  out_of_frame: true
objects:
- id: w1
  name: 窗
  bbox: [26, 22, 27, 36]
  depth: 4.46
  kind: opening
  desc: 北墙大窗,上午阳光斜进训练大厅
- id: mirror_wall
  name: 训练区整面镜
  spot: 康复中心
  material: 镜面玻璃
  bbox: [26, 26, 57, 38]
  depth: 4.39
- id: pt_bed
  name: PT治疗床
  spot: 康复中心
  material: 皮革
  bbox: [0, 56, 12, 44]
  depth: 4.28
  clipped: 左下缘越出
- id: equip_rack
  name: 器械重墙架
  spot: 康复中心
  material: 金属
  bbox: [89, 12, 11, 88]
  depth: 4.21
  clipped: 右下缘越出
deco: 墙边卷立的瑜伽垫,架格上的弹力带与泡沫轴,前台一摞预约单与纸巾盒,饮水机旁一排纸杯
atmosphere: 上午阳光从北墙大窗斜进训练大厅,白光通亮,空气里消毒水混着橡胶垫的气味,器械偶尔发出轻微金属声
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
