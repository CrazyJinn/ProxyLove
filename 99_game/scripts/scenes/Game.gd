extends Control
## 主游戏场景：背景层 + 立绘层 + 对话框 + 选项 + 历史 + 系统菜单 + 设置。
## 订阅 ScriptInterpreter 信号做渲染；玩家输入驱动解释器 advance/choose。

var _bg := TextureRect.new()
var _portraits = preload("res://scripts/ui/PortraitLayer.gd").new()
var _dialogue = preload("res://scripts/ui/DialogueBox.gd").new()
var _choice = preload("res://scripts/ui/ChoiceMenu.gd").new()
var _backlog = preload("res://scripts/ui/Backlog.gd").new()
var _menu = preload("res://scripts/ui/SystemMenu.gd").new()
var _settings = preload("res://scripts/ui/SettingsPanel.gd").new()
var _splash = preload("res://scripts/ui/SectionSplash.gd").new()
var _auto: bool = false
var _pending_scene := ""  # Day 过场遮盖期间延迟换的背景（covered/结束点应用）
var _pending_bgm: Dictionary = {}  # skip 快进期间暂存的段 BGM，停点柔和（fade）应用
var _pending_splash: Dictionary = {}  # skip 快进途中跨日的过场，停点（新段首句）再播
var _history: Array = []  # 已显示台词/旁白 {who, text, narrate}——逐句回看数据源
var _review_idx := -1  # 回看下标：-1=实时（最后一句），≥0=正显示 _history[_review_idx]
var _last_section := ""  # 最近一次写入 Backlog 的节标签（同节多段切换不重复插隔断）
var _auto_gap: float = AUTO_LINE_GAP  # 当前行 Auto 停留时长（line_ready 时按行类型更新）
var _ended: bool = false  # 本轮已进结局/章节结束（防 skip 越界）
var _auto_timer := Timer.new()
var _ctrl_held: bool = false  # Ctrl 按住快进状态
var _ctrl_acc: float = 0.0     # Ctrl 快进句末累加计时
var _skip_active: bool = false  # skip 快进中（异步 while 激活）
const CTRL_LINE_INTERVAL := 0.25  # Ctrl 快进：句末打完后自动翻页间隔（秒）
const AUTO_LINE_GAP := 1.0   # Auto：say 行语音播完后切句的停留间隔（秒）
const AUTO_NARRATE_BASE := 1.0       # Auto：旁白行基础停留（秒）
const AUTO_NARRATE_PER_CHAR := 0.06  # Auto：旁白行按字数追加的阅读时间（秒/字）
const AUTO_WAIT_POLL := 0.2  # Auto：未就绪（打字中/语音未播完）时的轮询间隔（秒）

func _ready() -> void:
	# 根 Control 默认 STOP 会吞掉穿透上来的鼠标点击，导致 _unhandled_input 收不到 advance（键盘不受影响）
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	# 等比裁切填充：背景图 1536×1024（3:2），expand 下视口普遍更高，默认 STRETCH
	# 会纵向拉变形，COVERED 保持比例裁上下。
	_bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	add_child(_bg)
	add_child(_portraits)
	add_child(_dialogue)
	add_child(_choice)
	add_child(_backlog)
	add_child(_menu)
	add_child(_settings)
	add_child(_splash)  # 最顶层：节间 Day 过场盖住对话框
	add_child(_auto_timer)
	_auto_timer.one_shot = true
	_auto_timer.timeout.connect(_auto_advance)
	# 纯展示层放行鼠标穿透到 _unhandled_input（推进对话）；按钮在 DialogueBox 内单独保留 STOP
	_bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_portraits.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_dialogue.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_wire_interpreter()
	_wire_ui()
	# 主场景根 Control 不会被 Window 自动铺满（实测恒为 0,0），手动设到视口尺寸，
	# 子层（_bg/PortraitLayer/DialogueBox 等 PRESET_FULL_RECT）才会正确铺满。
	var vp: Viewport = get_viewport()
	if vp != null:
		vp.size_changed.connect(_apply_layout)
	_apply_layout()
	# 进入起始章节（GameManager.start_new_game 可传参覆盖，默认 chapter00_序章/酒店）
	ScriptInterpreter.start(GameManager.start_chapter, GameManager.start_scene)

func _apply_layout() -> void:
	# 必须用 get_visible_rect()（逻辑坐标）：root viewport 的 size 是物理像素，
	# Web hidpi / expand 下两者不同（expand 逻辑宽恒为基准 1536，物理宽=innerW*dpr），
	# 直接赋给 Control 会随窗口形状产生 ±5~10% 错位，根比视口大时子层溢出裁切。
	var s: Vector2 = Vector2(1536, 1024)
	var vp: Viewport = get_viewport()
	if vp != null:
		var visible: Vector2 = vp.get_visible_rect().size
		if visible.x > 0.0:
			s = visible
	size = s

func _wire_interpreter() -> void:
	ScriptInterpreter.line_ready.connect(_on_line_ready)
	ScriptInterpreter.portrait_changed.connect(_portraits.apply_slots)
	ScriptInterpreter.bg_changed.connect(_on_bg_changed)
	ScriptInterpreter.bgm_changed.connect(_on_bgm_changed)
	ScriptInterpreter.choice_presented.connect(_on_choice)
	ScriptInterpreter.scene_entered.connect(_on_scene_entered)
	ScriptInterpreter.splash_requested.connect(_on_splash)
	ScriptInterpreter.ended.connect(_on_ended)
	ScriptInterpreter.chapter_finished.connect(_on_chapter_finished)

func _wire_ui() -> void:
	_splash.covered.connect(_flush_pending_scene)  # 全遮点换图（不可见）
	_splash.finished.connect(_on_splash_finished)  # 兜底 flush 积压背景 + 放行解释器
	_choice.option_chosen.connect(ScriptInterpreter.choose)
	_dialogue.button_log.connect(_backlog.toggle)
	_dialogue.button_auto.connect(_toggle_auto)
	_dialogue.button_skip.connect(_skip)
	_dialogue.button_menu.connect(_toggle_menu)
	_menu.settings_requested.connect(_settings.show)
	_menu.title_requested.connect(GameManager.to_title)
	_menu.closed.connect(_menu.close)
	_menu.save_requested.connect(_quick_save)  # V1：存档按钮降级为 quick 存
	_menu.load_requested.connect(_quick_load)  # V1：读档按钮降级为 quick 读

func _toggle_menu() -> void:
	if _menu.visible:
		_menu.close()
	else:
		_menu.open()

func _on_line_ready(kind: String, payload: Dictionary) -> void:
	_auto_gap = _auto_gap_for(kind, payload.get("text", ""))
	_review_idx = -1  # 新句即回实时（回看中的推进已被挡，此处兜底）
	_history.append({"who": payload.get("who", ""), "text": payload.get("text", ""),
		"narrate": kind != "say"})
	if kind == "say":
		_dialogue.show_line(payload.get("who", ""), payload.get("text", ""), false)
		_backlog.append(payload.get("who", ""), payload.get("text", ""))
		AudioManager.play_voice(payload.get("voice", ""))
	else:  # narrate
		_dialogue.show_line("", payload.get("text", ""), true)
		_backlog.append("", payload.get("text", ""))
		AudioManager.play_voice("")  # 旁白不配音：仅停上一句对白尾音

func _on_bg_changed(scene_name: String, _time: String) -> void:
	# Day 过场遮盖期间延迟换图：黑幕全遮（covered）时换不可见，随后淡出 = 新背景从黑中渐显
	if _splash.is_active():
		_pending_scene = scene_name
		return
	_apply_bg(scene_name)

func _apply_bg(scene_name: String) -> void:
	var man = Engine.get_singleton("Manifest") if Engine.has_singleton("Manifest") else null
	var path: String = man.get_scene(scene_name) if man else ""
	if path != "" and ResourceLoader.exists(path):
		_bg.texture = load(path)
	else:
		var pg = preload("res://scripts/util/PlaceholderGen.gd").new()
		_bg.texture = pg.get_scene_image(scene_name)

func _flush_pending_scene() -> void:
	if _pending_scene != "":
		_apply_bg(_pending_scene)
		_pending_scene = ""

func _on_bgm_changed(track: String, mode: String, loop: bool) -> void:
	# skip 快进途中不逐段硬切歌（短时间反复切很刺耳），停点统一切最终段 BGM
	if _skip_active:
		_pending_bgm = {"track": track, "mode": mode, "loop": loop}
		return
	match mode:
		"play": AudioManager.play_bgm(track, loop)
		"stop": AudioManager.stop_bgm()
		"fade": AudioManager.fade_bgm(track, loop)

func _flush_pending_bgm() -> void:
	if _pending_bgm.is_empty() or _ended:
		_pending_bgm = {}
		return
	var b: Dictionary = _pending_bgm
	_pending_bgm = {}
	match b.get("mode", "play"):
		"stop": AudioManager.stop_bgm()
		_: AudioManager.fade_bgm(b.get("track", ""), b.get("loop", true))  # 停点柔和切

# 选择点前自动写 quick 槽（spec 5.3）
func _on_choice(options: Array) -> void:
	SaveManager.save_slot(SaveManager.QUICK, ScriptInterpreter.snapshot())
	_choice.show_options(options)

# 场景段头自动写 quick 槽（spec 5.3）
func _on_scene_entered() -> void:
	SaveManager.save_slot(SaveManager.QUICK, ScriptInterpreter.snapshot())
	AudioManager.stop_voice()  # 段切换清场，避免上段尾音漏进新段
	# Backlog 小节隔断：节（sNN）变化才插——同节内多段切换不重复
	var st := ScriptInterpreter.current_section_label()
	if st != "" and st != _last_section:
		_backlog.append_section(st)
		_last_section = st

# 节间 Day 过场：day=-1（无日章，如序章）显示章标题大字、不显节标题。
# skip 只跳文本阅读：跨日过场暂存到停点（新段首句）再播；Ctrl 按住快进则不播（逐句直通语义）。
func _on_splash(day: int, sec_title: String) -> void:
	if _skip_active:
		_pending_splash = {"day": day, "title": sec_title}
		return
	if _ctrl_held:
		return
	_show_splash(day, sec_title)

func _show_splash(day: int, sec_title: String) -> void:
	ScriptInterpreter.ui_holding = true  # 挂起解释器：台词/音床等过场结束再开始（黑幕下不偷跑）
	var big := ("Day %d" % day) if day >= 0 else ScriptInterpreter.chapter_title()
	var small := sec_title if day >= 0 else ""
	_splash.show_splash(big, small)

func _on_splash_finished() -> void:
	_flush_pending_scene()
	ScriptInterpreter.ui_holding = false  # 放行解释器（自然播完/被跳过两路径都经 _done）

func _on_ended(kind: String, title: String, _cg: String) -> void:
	_ended = true
	AudioManager.stop_voice()
	GameManager.goto_ending(kind, title)

func _on_chapter_finished() -> void:
	_ended = true
	AudioManager.stop_voice()
	GameManager.to_title()

func _unhandled_input(event: InputEvent) -> void:
	if _splash.is_active():
		# 过场期间响应推进/S（=跳过过场）与菜单，其余（log/快进/自动）压后
		if event.is_action_pressed("advance") or event.is_action_pressed("skip"):
			_splash.skip()
		if not event.is_action_pressed("menu"):
			return
	if event.is_action_pressed("menu"):
		_toggle_menu()
		return
	if event.is_action_pressed("log"):
		_exit_review()  # 回看与历史面板互斥：开面板先回实时
		_backlog.toggle()
		return
	if event.is_action_pressed("quick_save"):
		_quick_save()
		return
	if event.is_action_pressed("quick_load"):
		_quick_load()
		return
	if event.is_action_pressed("auto_play"):
		_toggle_auto()
		return
	if event.is_action_pressed("skip"):
		_skip()
		return
	if _choice.visible or _menu.visible or _backlog.visible:
		return
	# 逐句回看：上/下（含滚轮）只在无弹层时可用
	if event.is_action_pressed("review_prev"):
		_review_step(-1)
		return
	if event.is_action_pressed("review_next"):
		_review_step(1)
		return
	if event.is_action_pressed("advance"):
		_advance()

func _advance() -> void:
	if _splash.is_active():
		_splash.skip()
		return
	if _review_idx >= 0:
		_exit_review()  # 回看中推进 = 退出回看恢复当前句（不推剧情）
		return
	if _dialogue.is_typing():
		_dialogue.finish_typing()
		return
	ScriptInterpreter.advance()

# 逐句回看：dir=-1 上一条 / +1 下一条。实时态（-1）按上→倒数第二句；
# 下一条滚到最新句再按 → 退出回看回实时。立绘/背景不回退（仅文本回看）。
func _review_step(dir: int) -> void:
	if _history.is_empty() or _splash.is_active():
		return
	if dir < 0:
		_review_idx = (_history.size() - 2) if _review_idx < 0 else (_review_idx - 1)
		_review_idx = maxi(_review_idx, 0)
	else:
		if _review_idx < 0:
			return  # 已在实时
		_review_idx += 1
		if _review_idx >= _history.size() - 1:
			_exit_review()
			return
	_show_review()

func _show_review() -> void:
	var h: Dictionary = _history[_review_idx]
	_dialogue.show_line(h.get("who", ""), h.get("text", ""), h.get("narrate", true))
	_dialogue.finish_typing()  # 历史句整句直显，不打字

func _exit_review() -> void:
	if _review_idx < 0:
		return
	_review_idx = -1
	if not _history.is_empty():  # 恢复当前（最新）句，整句直显
		var h: Dictionary = _history[_history.size() - 1]
		_dialogue.show_line(h.get("who", ""), h.get("text", ""), h.get("narrate", true))
		_dialogue.finish_typing()

func _toggle_auto() -> void:
	_auto = not _auto
	if _auto:
		_auto_timer.start(_auto_gap)

# Auto 停留时长：say 行有语音兜底（等播完再停 AUTO_LINE_GAP）；旁白无语音，按字数给阅读时间
func _auto_gap_for(kind: String, text: String) -> float:
	if kind == "say":
		return AUTO_LINE_GAP
	return AUTO_NARRATE_BASE + text.length() * AUTO_NARRATE_PER_CHAR

func _auto_advance() -> void:
	if not _auto:
		return
	# 等语音播完才切句（narrate/资源缺失时 playing=false，纯按停留时长推进）；
	# 打字中/菜单开着同样只轮询不推进。advance 同步发 line_ready，_auto_gap 已是新行值
	if not _dialogue.is_typing() and not AudioManager.is_voice_playing() \
			and not _choice.visible and not _menu.visible and not _splash.is_active() \
			and _review_idx < 0:
		ScriptInterpreter.advance()
		_auto_timer.start(_auto_gap)
	else:
		_auto_timer.start(AUTO_WAIT_POLL)

func _skip() -> void:
	# 跳过 = 推进到下一个 scene-block 首句；遇 choice/menu/ending/章末必停。
	# 每帧推一句（异步）：transition 行的 await 会挂起协程，若同帧同步循环推进
	# 会被 _advancing 挡住而 _line_idx 不动 → 同帧无限空转死循环——必须让帧流动。
	# 快进期间解释器 skipping=true（_process 每帧同步），transition 行不播不等直通。
	if _skip_active:
		return  # 防重入：S 键 / 对话框 skip 按钮并发会叠协程
	_exit_review()  # 回看中开 skip：先回实时（skip 推进语义）
	AudioManager.stop_voice()  # skip 立即静音，不等下一句自覆盖
	if _splash.is_active():
		_splash.skip()  # 过场播放中开 skip：先收掉过场（快进语义）
	_skip_active = true
	var start := ScriptInterpreter.current_scene_idx()
	# is_inside_tree()：协程 await 恢复时本节点可能已被摘树（菜单回标题等不设 _ended 的
	# 切场景路径）——循环就此退出，不推进已不渲染的场景
	while not _ended and is_inside_tree() and not _choice.visible and not _menu.visible:
		if ScriptInterpreter.current_scene_idx() != start:
			break  # 已跨段，停在新段首句
		if _dialogue.is_typing():
			_dialogue.finish_typing()
		else:
			ScriptInterpreter.advance()
		if _ended or not is_inside_tree():
			break  # advance 同步链内已章末/ending 切场景（本节点 queue_free/摘树）——
			# 协程就此终止。不得再 await：挂到帧末节点销毁后协程会在已亡节点上恢复，
			# get_tree() 报 "data.tree is null"（Game.gd 老 211 行报错的根因）。
		await get_tree().process_frame
	_skip_active = false
	_flush_pending_bgm()  # 停点统一切最终段 BGM（fade 柔和），途中不逐段硬切
	# 停点跨了日：Day 过场照常播（skip 只跳文本，时间定位信息保留）
	if not _pending_splash.is_empty() and not _ended and is_inside_tree():
		var s: Dictionary = _pending_splash
		_pending_splash = {}
		_show_splash(s["day"], s["title"])

func _process(delta: float) -> void:
	# Ctrl 按住 = 打字机 2× 速 + 句末自动翻页（松开恢复手动）
	# 每帧同步快进标志：skip 或 Ctrl 期间解释器 transition 行不播不等（直通）
	ScriptInterpreter.skipping = _skip_active or _ctrl_held
	var ctrl := Input.is_key_pressed(KEY_CTRL)
	if ctrl != _ctrl_held:
		_ctrl_held = ctrl
		_dialogue.set_fast(ctrl)
		_ctrl_acc = 0.0
	if not ctrl or _ended or _choice.visible or _menu.visible:
		return
	if _splash.is_active():
		_splash.skip()  # Ctrl 快进遇上过场：跳过（快进语义），本帧不推句
		return
	if _review_idx >= 0:
		return  # 回看中 Ctrl 不推剧情（导航优先）
	if _dialogue.is_typing():
		return  # 等 2× 速打字机自己打完
	_ctrl_acc += delta
	if _ctrl_acc >= CTRL_LINE_INTERVAL:
		_ctrl_acc = 0.0
		ScriptInterpreter.advance()

func _quick_save() -> void:
	SaveManager.save_slot(SaveManager.QUICK, ScriptInterpreter.snapshot())

func _quick_load() -> void:
	var snap = SaveManager.load_slot(SaveManager.QUICK)
	if snap.is_empty():
		return
	_history.clear()  # 清史防「未来句」泄露（回看数据从恢复点当前句重建）
	_review_idx = -1
	ScriptInterpreter.restore(snap)
