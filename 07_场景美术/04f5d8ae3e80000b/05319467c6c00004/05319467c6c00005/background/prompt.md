游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 路边摊-烧烤摊
scene_id: Re2PEUaYTt
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  ground: [0, 80, 87, 4]
  ground_desc: 摊区外城市街面，远处夜市灯火与人流的虚化延伸
  sky_desc: 夏夜深蓝天幕，薄云遮月
  floor_material: 沥青
lights:
- name: 光源
  pos: [51, 36]
  color: '#ffd9a0'
  intensity: 2.2
objects:
- id: prep_table
  name: 调料操作台
  spot: 路边摊-夜市摊区
  material: 塑胶
  bbox: [22, 50, 15, 12]
  depth: 7.52
- id: signboard
  name: 灯箱招牌
  spot: 路边摊-夜市摊区
  material: 玻璃
  bbox: [61, 37, 4, 12]
  depth: 7.47
  cname: 暖黄灯箱光
- id: grill_cart
  name: 烧烤炉车
  spot: 路边摊-夜市摊区
  material: 金属
  bbox: [41, 48, 21, 14]
  depth: 7.19
- id: stall_canopy
  name: 摊位遮棚
  spot: 路边摊-夜市摊区
  material: 布艺
  bbox: [29, 33, 36, 3]
  depth: 7.08
deco: 烤炉上码开的肉串淌着焦香油脂，铁皮盘里的烤韭菜和蒜蓉茄子，塑料方凳围坐的折叠桌上插着竹签的签桶和半卷卫生纸，冰镇啤酒瓶挂着水珠
atmosphere: 炭火气混着孜然辣椒面的浓香，油烟升腾里灯箱招牌暖黄光晃眼，夜市人声与滋滋烤肉声裹在一起
time_of_day: 夜晚

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
