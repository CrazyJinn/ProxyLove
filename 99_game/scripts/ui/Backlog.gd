extends Control
## 对话历史 Log。

const _sc := preload("res://scripts/ui/SpeakerColors.gd")  # 说话人配色（与对话框同口径）

var _panel := Panel.new()
var _label := RichTextLabel.new()
var _entries: Array = []

func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	_panel.offset_left = 100
	_panel.offset_right = -100
	_panel.offset_top = 80
	_panel.offset_bottom = -80
	add_child(_panel)
	_label.set_anchors_preset(Control.PRESET_FULL_RECT)
	_label.offset_left = 20
	_label.offset_right = -20
	_label.offset_top = 20
	_label.offset_bottom = -20
	_label.bbcode_enabled = true
	_label.scroll_following = true
	_panel.add_child(_label)
	# 点击面板任意处（含正文区）关闭；滚轮留给 RichTextLabel 自身滚动（不 accept）
	gui_input.connect(_on_click_close)
	_panel.gui_input.connect(_on_click_close)
	_label.gui_input.connect(_on_click_close)
	hide()

func _on_click_close(ev: InputEvent) -> void:
	if ev is InputEventMouseButton and ev.pressed \
			and ev.button_index != MOUSE_BUTTON_WHEEL_UP and ev.button_index != MOUSE_BUTTON_WHEEL_DOWN:
		visible = false

# 小节隔断行（居中 + 冷灰装饰线，前后留空行）：每进入新节由 Game 触发
func append_section(title: String) -> void:
	_entries.append("")
	_entries.append("[center][color=#8A97A8]──  %s  ──[/color][/center]" % title)
	_entries.append("")
	_label.text = "\n".join(_entries)

func append(who: String, text: String) -> void:
	# 整段一次性赋值（无打字机），bbcode 包裹安全；配色与对话框对齐：
	# say = 名牌+正文同角色色（名牌加粗），旁白 = 灰
	var line := ("[color=%s][b]%s[/b]：%s[/color]" % [_sc.hex_for(who), who, text]) if who != "" \
		else "[color=#%s]%s[/color]" % [_sc.NARRATE.to_html(false), text]
	_entries.append(line)
	_label.text = "\n".join(_entries)

func toggle() -> void:
	visible = not visible  # 切自身可见性，子 _panel 跟随父
