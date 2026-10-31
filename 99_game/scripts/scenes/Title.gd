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
	# 章节选择：清单读 chapter_packs.json（发布工具维护，随章自动增长）；
	# id 锚定（2026-10-31 起）键 = hexid(Chapter.id)，显示名取条目 meta 的 title、
	# 排序按 chapter_no（缺 meta 的条目回退键文本/字典序）；metadata 存 stem（真名）。
	# 默认选首章，「开始游戏」从所选章进入
	_chapter = OptionButton.new()
	for e in _chapter_entries():
		_chapter.add_item(e["title"])
		_chapter.set_item_metadata(_chapter.item_count - 1, e["stem"])
	if _chapter.item_count > 0:
		_chapter.select(0)
	_chapter.custom_minimum_size = Vector2(220, 40)
	# 章（左）/节（右）左右并排一行
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 16)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_child(_chapter)
	_vbox.add_child(row)
	# 小节选择：随所选章列出该章节（Section，block id 的 sNN 前缀归组），
	# 选中进该节首段；首项「从头开始」= 章首段；换章时联动刷新
	_scene = OptionButton.new()
	_scene.custom_minimum_size = Vector2(220, 40)
	row.add_child(_scene)
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

func _chapter_entries() -> Array:
	"""已发布章条目 [{stem, title, no}]（chapter_packs.json；chapter_no 排序，
	title 显示）；读不到时退回默认章。stem = hexid(Chapter.id)（章 JSON/pck 文件名主体）。"""
	var txt := FileAccess.get_file_as_string("res://data/chapter_packs.json")
	if txt != "":
		var packs = JSON.parse_string(txt)
		if packs is Dictionary and not packs.is_empty():
			var entries := []
			for k in packs.keys():
				var meta: Dictionary = packs[k] if packs[k] is Dictionary else {}
				entries.append({
					"stem": str(k),
					"title": str(meta.get("title", k)),
					"no": int(meta.get("chapter_no", 9999)),
				})
			entries.sort_custom(func(a, b): return a["no"] < b["no"])
			return entries
	return [{"stem": GameManager.start_chapter, "title": GameManager.start_chapter, "no": 0}]

func _on_chapter_selected(_index: int) -> void:
	_refresh_scene_options()

func _refresh_scene_options() -> void:
	# 按所选章重填小节下拉：节 = Section 粒度（项文本「节标题」——section_title 由
	# 发布链注入章 JSON；id 锚定后 block id 为雪花形无 sNN 前缀，_section_prefix 返回 ""
	# → 直接显示 section_title，无节标题才回退 block id 单列兜底）。
	# metadata 存该节首个 block id 供 start；首项「从头开始」metadata 空 = 章首段。
	# 段清单经 ChapterLoader 读章 JSON（透明解密加密剧本、带结构校验）；
	# 先 ensure_chapter（幂等；当前全量主包模式为 no-op）保证 Web 分包模式下章 JSON 可读。
	# 读不到（未发布段/解析失败）降级为仅「从头开始」，不阻断开局。
	_scene.clear()
	_scene.add_item("从头开始")
	_scene.set_item_metadata(0, "")
	_scene.select(0)
	if _chapter.item_count == 0:
		return
	var stem := str(_chapter.get_item_metadata(_chapter.selected))
	await ChapterPackLoader.ensure_chapter(stem)
	# await 后本节点可能已随切场景被释放（Web 分包下载耗时期间点开始/退出）
	if not is_instance_valid(_scene):
		return
	if _loader == null:
		_loader = preload("res://scripts/data/ChapterLoader.gd").new()
	var ch: Dictionary = _loader.load_chapter(stem)
	if ch.is_empty():
		return
	var seen := {}  # sNN 前缀 -> 已列（节内多 block 只列首项）
	for blk in ch["scenes"]:
		var sid: String = blk.get("id", "")
		if sid == "":
			continue
		var prefix := _section_prefix(sid)
		if prefix != "" and seen.has(prefix):
			continue  # 同节后续 block：从该节首段顺播，无需单列
		var label: String = blk.get("section_title", "")
		if label == "":
			label = sid if prefix == "" else prefix  # 无节标题：回退 block id / 节号
		elif prefix != "":
			label = "%s %s" % [prefix, label]  # id 锚定后 block id 为雪花形（prefix 恒空），显示纯节标题
		_scene.add_item(label)
		_scene.set_item_metadata(_scene.item_count - 1, sid)
		if prefix != "":
			seen[prefix] = true

# block id 的节前缀（s00/s01…）：id 形如 sNN_xxx；不合形态返回 ""（该 block 单列兜底）
func _section_prefix(sid: String) -> String:
	if sid.length() < 4 or sid[0] != "s" or not sid[1].is_valid_int() or not sid[2].is_valid_int() \
			or sid[3] != "_":
		return ""
	return sid.substr(0, 3)

func _on_start_pressed() -> void:
	if _chapter.item_count > 0:
		var stem := str(_chapter.get_item_metadata(_chapter.selected))
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
