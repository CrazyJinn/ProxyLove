extends RefCounted
## 台词说话人配色表：名牌与正文同色，旁白冷银灰；未知角色按名字哈希兜底。
## 色表纯运行时约定（男冷女暖），不写入图数据库、不进发布数据链。

const NARRATE := Color(0.66, 0.71, 0.80)  # 旁白灰（原 DialogueBox.COLOR_NARRATE 迁入）

# 男 = 冷色（青蓝/靛蓝/青绿/冷紫），女 = 暖色（粉/橙/黄/珊瑚/洋红/暖棕）。
# 双轨同身体：陆择（内心）亮青蓝 ↔ 陈默（对外）靛蓝，靠色相阶差 + 名牌文字区分。
const COLORS := {
	"陆择": Color("#63E2F2"),   # 亮青蓝（男主/内心轨）
	"陈默": Color("#7C9EFF"),   # 靛蓝（宿主/对外轨）
	"顾盈": Color("#FF85B3"),   # 玫粉
	"陈念": Color("#FFD873"),   # 暖黄（姐姐）
	"小夏": Color("#FF9E80"),   # 珊瑚
	"伊芙": Color("#FFEBC2"),   # 杏白金（天使）
	"季棠": Color("#E88BC7"),   # 洋红
	"林梦": Color("#FFB35C"),   # 亮橙
	"苏晓禾": Color("#E3BE94"), # 暖棕
	"沈暮雪": Color("#FFC9DE"), # 冰粉
	"江烈": Color("#B39DFF"),   # 冷紫
	"Tony": Color("#5EDCC0"),   # 青绿
	"温蔓青": Color("#FF7A6E"), # 西瓜红
}

static func color_for(who: String) -> Color:
	if who == "":
		return NARRATE
	return COLORS.get(who, _hash_color(who))

# 未知角色哈希兜底：String.hash() 跨运行稳定；HSL 固定 S/V 只轮转 H，落在柔和明度带
static func _hash_color(who: String) -> Color:
	var h: int = int(who.hash()) % 360
	if h < 0:
		h += 360
	return Color.from_hsv(float(h) / 360.0, 0.45, 0.92)

# Backlog 的 bbcode 用（RichTextLabel 的 [color=] 接受 #RRGGBB）
static func hex_for(who: String) -> String:
	return "#" + color_for(who).to_html(false)
