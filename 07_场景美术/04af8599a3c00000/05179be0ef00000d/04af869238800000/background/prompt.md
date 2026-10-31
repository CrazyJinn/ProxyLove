游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 灵魂夹缝
scene_id: OwNTDArnfs
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  ground: [0, 55, 100, 25]
  ground_desc: 静水湖面,铺展至天际,如镜映暮色
  sky_desc: 黄昏薄暮,对岸山林轮廓在薄雾中若隐若现
lights:
- name: 光源
  pos: [48, 40]
  color: '#f0a860'
  intensity: 2.2
objects:
- id: reeds_mid
  name: 芦苇丛中
  spot: 灵魂夹缝
  material: 芦苇
  bbox: [44, 49, 11, 7]
  depth: 16.67
- id: stones
  name: 浅滩卵石带
  spot: 灵魂夹缝
  material: 卵石
  bbox: [55, 54, 28, 6]
  depth: 13.91
- id: reeds_near
  name: 芦苇丛近
  spot: 灵魂夹缝
  material: 芦苇
  bbox: [54, 49, 14, 10]
  depth: 12.06
- id: cottage
  name: 原木茅草屋
  spot: 灵魂夹缝
  material: 原木茅草
  bbox: [100, 0, 0, 100]
  depth: 4.47
  clipped: 右上下缘越出
deco: 岸边芦苇摇曳,浅滩卵石错落,湖面静水如镜映着暮色,薄雾漫过对岸山林轮廓
atmosphere: 万物凝滞的死后过渡感,静水无声,静谧中透着淡淡哀伤与超然,时间仿佛不在此处流动
time_of_day: 黄昏

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
