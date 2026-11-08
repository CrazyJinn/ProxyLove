游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 康复中心-前台
scene_id: RsEFbSd21J
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  back_wall: [19, 29, 57, 35]
  floor_material: 浅灰塑胶
  wall_material: 乳胶漆
lights:
- name: 光源
  pos: [48, 17]
  color: '#ffffff'
  intensity: 2.4
- name: 光源
  pos: [49, 32]
  color: '#fdfbf4'
  intensity: 1.6
objects:
- id: water_dispenser
  name: 饮水机
  spot: 前台
  material: 金属
  bbox: [73, 52, 6, 14]
  depth: 6.65
- id: w_hall
  name: 窗
  bbox: [58, 40, 8, 23]
  depth: 6.44
  kind: opening
  desc: 北墙右段磨砂玻璃门,推开即训练大厅
- id: logo_wall
  name: 机构形象墙
  spot: 前台
  material: 金属
  bbox: [40, 37, 24, 15]
  depth: 6.17
- id: reception_counter
  name: 前台接待台
  spot: 前台
  material: 木饰面
  bbox: [22, 54, 27, 12]
  depth: 6.07
- id: leaflet_stand
  name: 宣传资料架
  spot: 前台
  material: 金属
  bbox: [0, 48, 10, 27]
  depth: 5.5
  clipped: 左缘越出
deco: 台面一摞预约单与登记笔，纸巾盒与会员卡架，宣传折页扇形摆开，候诊凳上摞着过刊杂志，画面无绿植盆栽与花艺
atmosphere: 上午的阳光透过玻璃门漫进前厅，接待台后机构标识安静立着，消毒水气味比训练大厅淡些
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
