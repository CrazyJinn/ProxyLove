extends Control
## 节间 Day 过场：黑屏渐入 → 「Day N」大字 + 节标题小字 → 渐出；期间由 Game 屏蔽推进。

signal finished()
signal covered()  # 黑幕全遮完成（fade-in 尾）：此刻换背景图不可见，随后淡出即新图渐显

const FADE_IN := 0.25
const HOLD := 0.9
const FADE_OUT := 0.35
enum State { HIDDEN, FADING_IN, HOLD, FADING_OUT }
var _state: int = State.HIDDEN
var _rect := ColorRect.new()
var _big := Label.new()  # 「Day N」/章标题（无日章）
var _small := Label.new()  # 节标题（小字，冷银灰与旁白同族）
var _tw: Tween = null

func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	_rect.color = Color.BLACK
	add_child(_rect)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 12)
	_big.add_theme_font_size_override("font_size", 64)
	_big.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_small.add_theme_font_size_override("font_size", 28)
	_small.add_theme_color_override("font_color", Color(0.66, 0.71, 0.80))
	_small.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(_big)
	box.add_child(_small)
	center.add_child(box)
	add_child(center)
	mouse_filter = Control.MOUSE_FILTER_STOP  # 吃点击=跳过；HIDDEN 时 visible=false 不拦截
	gui_input.connect(_on_gui)
	hide()

func is_active() -> bool:
	return _state != State.HIDDEN

func show_splash(big: String, small: String) -> void:
	if is_active():
		return  # 重入防御（换段连发时沿用当前过场即可）
	_big.text = big
	_small.text = small
	_small.visible = small != ""
	_rect.modulate.a = 0.0
	_big.modulate.a = 0.0
	_small.modulate.a = 0.0
	show()
	_state = State.FADING_IN
	_tw = create_tween()
	_tw.tween_property(_rect, "modulate:a", 1.0, FADE_IN)
	_tw.tween_callback(func():
		_state = State.HOLD
		covered.emit())
	_tw.tween_property(_big, "modulate:a", 1.0, 0.2)
	_tw.parallel().tween_property(_small, "modulate:a", 1.0, 0.2)
	_tw.tween_interval(HOLD)
	_tw.tween_callback(func(): _state = State.FADING_OUT)
	_tw.tween_property(_rect, "modulate:a", 0.0, FADE_OUT)
	_tw.parallel().tween_property(_big, "modulate:a", 0.0, FADE_OUT)
	_tw.parallel().tween_property(_small, "modulate:a", 0.0, FADE_OUT)
	_tw.tween_callback(_done)

# 点击/推进键跳过：快淡出收尾（不硬切，避免阅读中的突兀黑闪消失）
func skip() -> void:
	if not is_active():
		return
	if _tw:
		_tw.kill()
	_state = State.FADING_OUT
	_tw = create_tween()
	_tw.tween_property(_rect, "modulate:a", 0.0, 0.15)
	_tw.parallel().tween_property(_big, "modulate:a", 0.0, 0.15)
	_tw.parallel().tween_property(_small, "modulate:a", 0.0, 0.15)
	_tw.tween_callback(_done)

func _on_gui(ev: InputEvent) -> void:
	if ev is InputEventMouseButton and ev.pressed:
		skip()

func _done() -> void:
	_state = State.HIDDEN
	hide()
	finished.emit()
