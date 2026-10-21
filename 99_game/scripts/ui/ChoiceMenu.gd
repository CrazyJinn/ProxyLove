extends Control
## 选项面板：半透明深色面板 + 自定义三态按钮 + 悬停高亮 + 入场淡入。

signal option_chosen(option: Dictionary)

const BTN_W := 360.0
const BTN_H := 60.0
const ACCENT := Color("#63E2F2")  # 悬停描边强调色（青蓝，同陆择/UI 主色）
var _panel := PanelContainer.new()
var _box := VBoxContainer.new()

func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE  # 面板放行穿透，按钮自会 STOP
	# 锚点居中 + 双向生长：选项数变化仍真正居中（替代旧手动 position 偏移）
	_panel.set_anchors_preset(Control.PRESET_CENTER)
	_panel.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_panel.grow_vertical = Control.GROW_DIRECTION_BOTH
	_panel.add_theme_stylebox_override("panel", _panel_style())
	_box.add_theme_constant_override("separation", 14)
	_panel.add_child(_box)
	add_child(_panel)
	hide()

func show_options(options: Array) -> void:
	for c in _box.get_children():
		c.queue_free()
	for opt in options:
		var b := Button.new()
		b.text = opt["label"]
		b.custom_minimum_size = Vector2(BTN_W, BTN_H)
		b.add_theme_font_size_override("font_size", 26)
		b.add_theme_color_override("font_color", Color("#E8EDF4"))
		b.add_theme_color_override("font_hover_color", Color.WHITE)
		b.add_theme_color_override("font_pressed_color", Color.WHITE)
		b.add_theme_stylebox_override("normal", _btn_style(Color(0.10, 0.12, 0.17, 0.88), Color(1, 1, 1, 0.10)))
		b.add_theme_stylebox_override("hover", _btn_style(Color(0.16, 0.24, 0.36, 0.95), ACCENT))
		b.add_theme_stylebox_override("pressed", _btn_style(Color(0.10, 0.16, 0.25, 0.95), ACCENT))
		b.add_theme_stylebox_override("focus", StyleBoxEmpty.new())  # 鼠标驱动，去焦点虚线框
		var o = opt  # 局部解耦，避免 lambda 捕获循环变量
		b.pressed.connect(func(): _on_chosen(o))
		_box.add_child(b)
	_panel.modulate.a = 0.0
	show()
	var tw := create_tween()  # 入场淡入
	tw.tween_property(_panel, "modulate:a", 1.0, 0.25)

func _on_chosen(opt: Dictionary) -> void:
	hide()
	option_chosen.emit(opt)

func _panel_style() -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = Color(0.04, 0.05, 0.09, 0.72)
	s.set_corner_radius_all(12)
	s.set_content_margin_all(24)
	return s

func _btn_style(bg: Color, border: Color) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.set_corner_radius_all(8)
	s.content_margin_left = 18
	s.content_margin_right = 18
	s.content_margin_top = 10
	s.content_margin_bottom = 10
	s.set_border_width_all(1)
	s.border_color = border
	return s
