游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 酒店-客房
scene_id: OiZR8tKjLc
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [0, 73, 100, 27]
  back_wall: [41, 0, 59, 100]
  left_wall: [0, 0, 42, 100]
  ceiling: [0, 0, 100, 16]
  floor_material: 地毯
  wall_material: 乳胶漆
lights:
- name: 光源
  pos: [64, 33]
  color: '#f2e2c4'
  intensity: 2.0
objects:
- id: w1
  name: 窗
  bbox: [57, 15, 40, 56]
  depth: 3.38
  kind: opening
  desc: 落地大窗,清晨城市天光,窗帘半拉
- id: bed
  name: 双人床
  spot: 客房
  material: 布艺
  bbox: [14, 61, 51, 39]
  depth: 3.26
  clipped: 下缘越出
- id: nightstand
  name: 床头柜
  spot: 客房
  material: 木饰面
  bbox: [0, 77, 14, 23]
  depth: 2.94
  clipped: 左下缘越出
- id: door
  name: 入户门
  bbox: [0, 677, -41, -577]
  depth: 0.65
  kind: opening
  clipped: 左下缘越出
deco: 床品凌乱皱褶,地毯上散落昨晚的衣物,床头两只水杯,窗帘半拉,晨光斜切进来
atmosphere: 宿醉后的尴尬清晨,空气中残留着昨夜的暧昧与局促
time_of_day: 清晨

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
