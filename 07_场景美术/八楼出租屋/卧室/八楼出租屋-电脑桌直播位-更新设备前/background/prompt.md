游戏对话背景图。

以下 YAML 描述一张游戏场景背景图的画幅布局：坐标百分比，原点=画幅左上角，x 向右、y 向下（图像像素坐标系）；objects 的 bbox [x,y,w,h] 为物件包围盒左上角位置与宽高，列表由远及近（遮挡序）；room_regions 为房间/环境结构的画面区域；lights 为光源位置与颜色（out_of_frame 表示光源在画外但光照有效）；time_of_day 为时段；deco 与 atmosphere 为氛围与细节描述。请严格按此布局生成图片：物件位置/大小/颜色以 YAML 为准，场景无角色。

scene_name: 八楼出租屋-电脑桌直播位-更新设备前
scene_id: QW77oRdOwS
canvas: 百分比布局（原点=画幅左上角，x 向右、y 向下；depth=距相机米数，列表由远及近=遮挡序）
room_regions:
  floor: [0, 66, 100, 34]
  back_wall: [0, 0, 54, 100]
  right_wall: [54, 0, 46, 100]
  ceiling: [0, 0, 100, 6]
lights:
- name: 光源
  pos: [50, 49]
  color: '#bcd4f0'
  intensity: 2.2
objects:
- id: desk
  name: 旧电脑桌
  spot: 卧室
  bbox: [38, 51, 23, 30]
  depth: 3.4
- id: w1
  name: 窗
  bbox: [7, 9, 31, 52]
  depth: 2.84
  kind: opening
  desc: 卧室旧窗（窗墙居中，窗左是床、窗右是电脑桌），深夜窗外无光，窗帘半拉
- id: bed
  name: 单人床
  spot: 卧室
  bbox: [0, 74, 26, 26]
  depth: 2.14
  clipped: 左下缘越出
deco: 桌上一台旧显示器亮着（屏面朝房内），老式动圈麦克风支在杂乱桌面，乱线、外卖盒与空能量饮料罐沿桌沿堆叠；桌前一把旧办公椅，背对镜头；画面左侧床头堆着旧抱枕与缠乱的充电线
atmosphere: 旧设备堆出的深夜直播角，屏幕冷光是这间小屋唯一醒着的东西，局促里透着独居主播的专注，晴天
time_of_day: ''

油画风格，大色块平涂，忽略细节，冷色调，明亮通透，手绘厚涂质感，游戏美术，无角色，图面无描述性文字。
