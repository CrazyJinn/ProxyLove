游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 vibe 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 游乐园
scene_id: S7lM3irKjJ
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  ground_desc: 园区外围绿化带与停车场
  sky_desc: 晴日蓝天,浮着几缕薄云
  floor_material: 混凝土
lights:
- name: 光源
  pos: [94, -17]
  color: '#fff2d8'
  intensity: 2.0
  out_of_frame: true
objects:
- id: ferris_wheel
  name: 摩天轮
  spot: 游乐园
  material: 金属
  bbox: [53, 27, 26, 30]
  depth: 17.3
  cname: 摩天轮轮廓
- id: snack_booth
  name: 小吃摊
  spot: 游乐园
  material: 金属
  bbox: [71, 42, 19, 18]
  depth: 14.04
- id: carousel
  name: 旋转木马
  spot: 游乐园
  material: 金属
  bbox: [0, 26, 41, 40]
  depth: 13.04
  cname: 旋转木马糖果色圆亭
  clipped: 左缘越出
- id: game_booth
  name: 游戏摊位
  spot: 游乐园
  material: 金属
  bbox: [74, 38, 26, 27]
  depth: 11.18
- id: walk_far
  name: 中央步道远段
  spot: 游乐园
  material: 混凝土
  bbox: [28, 59, 50, 5]
  depth: 10.62
- id: walk_mid
  name: 中央步道中段
  spot: 游乐园
  material: 混凝土
  bbox: [6, 64, 91, 14]
  depth: 6.5
- id: walk_near
  name: 中央步道近段
  spot: 游乐园
  material: 混凝土
  bbox: [0, 82, 100, 18]
  depth: 2.64
  clipped: 左右下缘越出
deco: 步道上空拉起的彩色三角旗;灯杆上束着的气球;推车式棉花糖摊;举着气球与糖葫芦的游客
vibe: 晴日上午的糖果色园区,阳光把游乐设施的漆色晒得发亮,假日人声与入园音乐混成一片暖闹
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
