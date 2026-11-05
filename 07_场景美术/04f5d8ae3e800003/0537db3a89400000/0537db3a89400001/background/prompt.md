游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述；物件与地面/墙面可含 material 材质词，材质质感以该词为准。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 星耀电竞基地-经理办公室
scene_id: Rm85LQWh4T
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [13, 66, 87, 34]
  back_wall: [12, 27, 61, 43]
  right_wall: [72, 0, 28, 100]
  ceiling: [12, 0, 88, 30]
  floor_material: 深灰地毯
  wall_material: 吸音板
lights:
- name: 光源
  pos: [45, 12]
  color: '#f2ead8'
  intensity: 2.4
objects:
- id: window_n
  name: 窗
  bbox: [38, 32, 24, 23]
  depth: 4.82
  kind: opening
  desc: 北墙大窗,白纱帘滤进午后光
- id: wall_art
  name: 队标灯板画
  spot: 办公区
  material: 亚克力灯板
  bbox: [75, 34, 16, 23]
  depth: 4.76
- id: manager_desk
  name: 经理大班台
  spot: 办公区
  material: 原木
  bbox: [40, 58, 22, 15]
  depth: 4.55
- id: bookcase_w
  name: 书柜
  spot: 办公区
  material: 原木
  bbox: [0, 0, 0, 100]
  depth: 3.75
  clipped: 左上下缘越出
deco: 班台上摊开的二队合同与签字笔、保温杯与眼镜盒，书柜里码着战术手册与几座旧奖杯，东墙一对洽谈椅与小边几，门侧衣帽架
atmosphere: 白纱帘滤进来的午后光落在深色班台上，空气里飘着新打印合同的油墨味，静得能听见笔尖划纸
time_of_day: 白天

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
