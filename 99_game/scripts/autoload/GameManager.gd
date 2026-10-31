extends Node
## 全局流程 + 键位注册（代码注册 InputMap，替代 project.godot 手写 [input]）+ 场景切换。
## autoload: GameManager（首个 autoload，_ready 时注册 Manifest 单例与输入）。

class EndingData:
	static var kind: String = ""
	static var title: String = ""

func _ready() -> void:
	# 注册 Manifest 单例，供其他 autoload 与 UI 共用
	if not Engine.has_singleton("Manifest"):
		var m = preload("res://scripts/data/Manifest.gd").new()
		m.load_from_path("res://data/manifest.json")
		Engine.register_singleton("Manifest", m)
	_register_inputs()
	_apply_default_font()
	_apply_env_override()

func _apply_env_override() -> void:
	# 调试入口：环境变量覆盖起始章/段（headless 冒烟、桌面直进某章，免改代码/点 UI）。
	# 例：PROXYLOVE_CHAPTER=chapter01_新皮肤 godot --headless res://scenes/Game.tscn
	var ch := OS.get_environment("PROXYLOVE_CHAPTER")
	if ch != "":
		start_chapter = ch
	var sc := OS.get_environment("PROXYLOVE_SCENE")
	if sc != "":
		start_scene = sc
	if start_chapter == "":
		start_chapter = _default_chapter()  # chapter_packs 首章（PROXYLOVE_CHAPTER 可覆盖）

func _register_inputs() -> void:
	_add_action("advance", [KEY_SPACE, KEY_ENTER], [MOUSE_BUTTON_LEFT])
	_add_action("menu", [KEY_ESCAPE], [MOUSE_BUTTON_RIGHT])
	_add_action("quick_save", [KEY_F5], [])
	_add_action("quick_load", [KEY_F9], [])
	_add_action("log", [KEY_H], [])
	# 逐句回看：滚轮上/上键=上一条，滚轮下/下键=下一条（滚轮上不再开 Backlog，Backlog 由 H 开关）
	_add_action("review_prev", [KEY_UP], [MOUSE_BUTTON_WHEEL_UP])
	_add_action("review_next", [KEY_DOWN], [MOUSE_BUTTON_WHEEL_DOWN])
	_add_action("auto_play", [KEY_A], [])
	_add_action("skip", [KEY_S], [])

func _add_action(action_name: String, keycodes: Array, mouse_buttons: Array) -> void:
	if InputMap.has_action(action_name):
		return
	InputMap.add_action(action_name)
	for kc in keycodes:
		var e := InputEventKey.new()
		e.keycode = kc
		InputMap.action_add_event(action_name, e)
	for mb in mouse_buttons:
		var em := InputEventMouseButton.new()
		em.button_index = mb
		InputMap.action_add_event(action_name, em)

func _apply_default_font() -> void:
	# 桌面端有系统中文字体兜底；Web 端浏览器缺中文字体 → 中文乱码。
	# 固定路径加载内嵌字体设为 root theme 默认字体。
	# （不用 DirAccess 扫描：该 API 在 Web 端读 pck 不可靠——桌面正常但 Web 漏扫，字体设不上。）
	const FONT_PATH := "res://fonts/LXGWWenKai-Medium.ttf"
	if not ResourceLoader.exists(FONT_PATH):
		return
	var f := load(FONT_PATH) as Font
	if f == null:
		return
	var t := Theme.new()
	t.default_font = f
	get_tree().root.theme = t

## 起始章节配置（Game 场景 _ready 时读这两个值启动解释器）。
## start_new_game() 可传参覆盖（标题的章/小节下拉即经此传入）；start_scene 留空 = 章首段
## （scene-block id 随发布变，硬编码会漂移导致"找不到场景段"）。
## id 锚定（2026-10-31 起）：章 stem = hexid(Chapter.id)（16 位小写 hex），缺省值
## 运行时从 chapter_packs.json 取 chapter_no 最小章（不再硬编码章名）。
var start_chapter := ""
var start_scene := ""

func _default_chapter() -> String:
	## chapter_packs.json 中 chapter_no 最小的章 stem；读不到回退空串（启动报错可见）。
	var txt := FileAccess.get_file_as_string("res://data/chapter_packs.json")
	if txt != "":
		var packs = JSON.parse_string(txt)
		if packs is Dictionary and not packs.is_empty():
			var best_stem := ""
			var best_no := 999999
			for k in packs.keys():
				var meta: Dictionary = packs[k] if packs[k] is Dictionary else {}
				var no: int = int(meta.get("chapter_no", 9999))
				if no < best_no:
					best_no = no
					best_stem = str(k)
			if best_stem != "":
				return best_stem
	return ""

func start_new_game(chapter: String = "", scene: String = "") -> void:
	# Game 场景 _ready 时自行调 ScriptInterpreter.start，避免跨场景 call_deferred 时序问题
	if chapter != "":
		start_chapter = chapter
	# start_scene 无条件赋值（与 chapter 不同）：空 = 章首段。否则从某小节开过一轮后
	# 回标题再「从头开始」，这里会残留上一轮的段 id。
	start_scene = scene
	goto_scene("res://scenes/Game.tscn")

func to_title() -> void:
	goto_scene("res://scenes/Title.tscn")

func goto_ending(kind: String, title: String) -> void:
	EndingData.kind = kind
	EndingData.title = title
	goto_scene("res://scenes/Ending.tscn")

func goto_scene(path: String) -> void:
	get_tree().change_scene_to_file(path)
