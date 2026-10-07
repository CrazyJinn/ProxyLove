extends Control
## 标题/主菜单。

var _bg: ColorRect
var _center: CenterContainer
var _vbox: VBoxContainer
var _chapter: OptionButton
var _scene: OptionButton
var _start: Button
var _quit: Button
var _loader = null  # ChapterLoader（懒建），读章 JSON 列小节

func _ready() -> void:
	_bg = ColorRect.new()
	_bg.color = Color(0.05, 0.05, 0.08, 1.0)
	add_child(_bg)
	# CenterContainer 的 rect 被手动铺满视口后，会自动把内容（VBox）整体居中。
	_center = CenterContainer.new()
	add_child(_center)
	_vbox = VBoxContainer.new()
	_vbox.add_theme_constant_override("separation", 24)
	_center.add_child(_vbox)
	var title := Label.new()
	title.text = "代恋"
	title.add_theme_font_size_override("font_size", 72)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_vbox.add_child(title)
	# 章节选择：stem 清单读 chapter_packs.json 键（发布工具维护，随章自动增长）；
	# 排序后默认选首章，「开始游戏」从所选章进入
	_chapter = OptionButton.new()
	for stem in _chapter_stems():
		_chapter.add_item(stem)
	if _chapter.item_count > 0:
		_chapter.select(0)
	_chapter.custom_minimum_size = Vector2(160, 40)
	_chapter.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	_vbox.add_child(_chapter)
	# 小节选择：随所选章列出该章场景段（scene-block id，即发布侧的分节），
	# 首项「从头开始」= 章首段；换章时联动刷新
	_scene = OptionButton.new()
	_scene.custom_minimum_size = Vector2(160, 40)
	_scene.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	_vbox.add_child(_scene)
	_chapter.item_selected.connect(_on_chapter_selected)
	_refresh_scene_options()
	_start = Button.new()
	_start.text = "开始游戏"
	_start.custom_minimum_size = Vector2(160, 50)
	_start.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	_start.pressed.connect(_on_start_pressed)
	_vbox.add_child(_start)
	_quit = Button.new()
	_quit.text = "退出"
	_quit.custom_minimum_size = Vector2(160, 50)
	_quit.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	_quit.pressed.connect(get_tree().quit)
	_vbox.add_child(_quit)
	# 主场景根 Control 的 size 不会被 Window 自动铺满（实测恒为 0,0），
	# 改为监听视口尺寸、手动铺满 bg/center，规避根节点锚点不生效的问题。
	var vp: Viewport = get_viewport()
	if vp != null:
		vp.size_changed.connect(_apply_layout)
	_apply_layout()

func _apply_layout() -> void:
	# 用 get_visible_rect()（逻辑坐标）而非 vp.size（物理像素），同 Game.gd 注释。
	var s: Vector2 = Vector2(1536, 1024)
	var vp: Viewport = get_viewport()
	if vp != null:
		var visible: Vector2 = vp.get_visible_rect().size
		if visible.x > 0.0:
			s = visible
	_bg.size = s
	_center.size = s
	_log_layout("apply")

func _chapter_stems() -> Array:
	"""已发布章 stem 清单（chapter_packs.json 键，章号排序）；读不到时退回默认章。"""
	var txt := FileAccess.get_file_as_string("res://data/chapter_packs.json")
	if txt != "":
		var packs = JSON.parse_string(txt)
		if packs is Dictionary and not packs.is_empty():
			var stems := (packs.keys() as Array).duplicate()
			stems.sort()  # chapterNN_ 前缀字典序 = 章号序
			return stems
	return [GameManager.start_chapter]

func _on_chapter_selected(_index: int) -> void:
	_refresh_scene_options()

func _refresh_scene_options() -> void:
	# 按所选章重填小节下拉：项文本 = scene-block id（章内唯一、自带序号，如 s01_咖啡店），
	# metadata 存同名 id 供 start；首项「从头开始」metadata 空 = 章首段。
	# 段清单经 ChapterLoader 读章 JSON（透明解密加密剧本、带结构校验）；
	# 先 ensure_chapter（幂等；当前全量主包模式为 no-op）保证 Web 分包模式下章 JSON 可读。
	# 读不到（未发布段/解析失败）降级为仅「从头开始」，不阻断开局。
	_scene.clear()
	_scene.add_item("从头开始")
	_scene.set_item_metadata(0, "")
	_scene.select(0)
	if _chapter.item_count == 0:
		return
	var stem := _chapter.get_item_text(_chapter.selected)
	await ChapterPackLoader.ensure_chapter(stem)
	# await 后本节点可能已随切场景被释放（Web 分包下载耗时期间点开始/退出）
	if not is_instance_valid(_scene):
		return
	if _loader == null:
		_loader = preload("res://scripts/data/ChapterLoader.gd").new()
	var ch: Dictionary = _loader.load_chapter(stem)
	if ch.is_empty():
		return
	for blk in ch["scenes"]:
		var sid: String = blk.get("id", "")
		if sid == "":
			continue
		_scene.add_item(sid)
		_scene.set_item_metadata(_scene.item_count - 1, sid)

func _on_start_pressed() -> void:
	if _chapter.item_count > 0:
		var stem := _chapter.get_item_text(_chapter.selected)
		# 选中项 metadata 即起始段 id（首项空 = 章首段）
		var scene_id: String = str(_scene.get_item_metadata(_scene.selected)) if _scene.item_count > 0 else ""
		GameManager.start_new_game(stem, scene_id)
	else:
		GameManager.start_new_game()

func _log_layout(tag: String) -> void:
	var vp: Vector2 = Vector2.ZERO
	var v: Viewport = get_viewport()
	if v != null:
		vp = v.get_visible_rect().size
	print("[Title:%s] viewport=%s | self=%s bg=%s center=%s vbox=%s" % [tag, vp, size, _bg.size, _center.size, _vbox.size])
	print("[Title:%s]   start.global=%s | quit.global=%s" % [tag, _start.global_position, _quit.global_position])
