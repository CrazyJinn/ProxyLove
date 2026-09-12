extends Node
## 集中式剧本解释器。持有运行时状态，match op 分发指令。

signal line_ready(kind: String, payload: Dictionary)
signal portrait_changed(slots: Dictionary)
signal bg_changed(scene_name: String, time: String)
signal bgm_changed(track: String, mode: String, loop: bool)
signal choice_presented(options: Array)
signal ended(kind: String, title: String, cg: String)
signal chapter_finished()
signal scene_entered()

var _file: String = ""
var _chapter: Dictionary = {}
var _scenes: Array = []
var _scene_idx: int = 0
var _line_idx: int = 0
# 推进中标志：transition 行 await 播放期间为 true，advance() 入口忽略重入（防点击跳行）
var _advancing: bool = false
# 快进直通（由 Game 每帧同步：skip 激活或 Ctrl 按住）：transition 行不播不等直通
var skipping: bool = false
# 立绘槽状态：值为 {who, portrait} 或 null。say/show 写入，hide 清除。
var slots: Dictionary = {"left": null, "center": null, "right": null}

var _ChapterLoader = preload("res://scripts/data/ChapterLoader.gd")
var _loader

func _ready() -> void:
	_loader = _ChapterLoader.new()

func start(file: String, scene_id: String = "", label: String = "") -> void:
	# 重置立绘槽：每次 start 开局清空，避免跨章节/重开残留
	slots = {"left": null, "center": null, "right": null}
	# GUT 适配：测试用 .new() 创建、未入树时 _ready 不触发，此处兜底初始化
	if _loader == null:
		_loader = _ChapterLoader.new()
	# Web 端按需挂载该章资源包（桌面/首章为 no-op）。含 await 使本方法变 async：
	# 调用方（Game._ready）不 await 亦可——协程会自行继续到 _run_from_current 并发信号。
	await ChapterPackLoader.ensure_chapter(file)
	_file = file
	_chapter = _loader.load_chapter(file)
	if _chapter.is_empty():
		push_error("ScriptInterpreter: 无法加载章节 %s" % file)
		chapter_finished.emit()
		return
	_scenes = _chapter["scenes"]
	_scene_idx = 0
	if scene_id != "":
		_scene_idx = _find_scene_index(scene_id)
	_enter_scene_block()
	if label != "":
		var li := _find_label(label)
		if li >= 0:
			_line_idx = li
	_run_from_current()

func advance() -> void:
	if _advancing:
		return  # transition/床淡出等待中：忽略点击推进（等完自动继续），防跳行
	# 床在播（未自然播完）：推进前 1s 淡出——淡完才切下一句（字幕保持）；已播完直接切。
	# 快进（skipping）立即停床不等（skip 语义）；等待期 _advancing 挡重入。
	if AudioManager.has_active_beds():
		if skipping:
			AudioManager.stop_all_beds()  # skip 快进：立即停+清 dismissed（停点 reconcile 按剧本重起）
		else:
			_advancing = true
			AudioManager.stop_all_beds(1.0, true)  # 用户推进收床：淡出+记 dismissed（不复活）
			var t0 := Time.get_ticks_msec()
			while Time.get_ticks_msec() - t0 < 1000:
				if skipping:
					break  # 淡出中途 skip 激活：放行推进（床 tween 继续自毁渐弱）
				await get_tree().process_frame
			_advancing = false
	_line_idx += 1
	_run_from_current()

# 当前 scene-block 在 _scenes 中的下标，供 UI 侧（如 skip 判定跨段）读取
func current_scene_idx() -> int:
	return _scene_idx

# 停点床状态对齐：扫描当前块 行首→当前行 推导「此刻应在播的床」（bed+ 起 / bed- 止），
# 交 AudioManager.reconcile_beds 对齐（缺的起播、多的停）。skip 途中 bed 指令被忽略，
# skip/读档停在阻塞行时靠本函数恢复正确床状态（幂等——正常推进时床已对，调用无副作用）。
func _reconcile_beds() -> void:
	if _scene_idx >= len(_scenes):
		return
	var want: Dictionary = {}
	var lines: Array = _scenes[_scene_idx]["lines"]
	for i in range(min(_line_idx + 1, len(lines))):
		var l: Dictionary = lines[i]
		if l["op"] == "bed_start":
			want[l.get("bed", "")] = l.get("track", "")
		elif l["op"] == "bed_end":
			want.erase(l.get("bed", ""))
	AudioManager.reconcile_beds(want)

# 内部：进入场景段时套用 scene + bgm，从 line 0 起
func _enter_scene_block() -> void:
	_line_idx = 0
	# 换段清场：新 scene-block = 空舞台，避免上一段立绘残留（各段起手会重建在场角色）
	slots = {"left": null, "center": null, "right": null}
	portrait_changed.emit(_snapshot())
	var blk: Dictionary = _scenes[_scene_idx]
	bg_changed.emit(blk.get("scene", ""), blk.get("time", ""))
	if blk.has("bgm"):
		var b: Dictionary = blk["bgm"]
		bgm_changed.emit(b.get("track", ""), b.get("mode", "play"), b.get("loop", true))
	AudioManager.stop_ambience()  # 换段清场：上一段氛围声景停止（新段 narrate.ambience 重新起）
	AudioManager.stop_all_beds()  # 换段清场：上一段音床停止（方言保证 bed± 同块，此处兜底）
	scene_entered.emit()

# 从当前 line 起推进：即时指令自动递进，阻塞/终止停下
func _run_from_current() -> void:
	while true:
		if _scene_idx >= len(_scenes):
			AudioManager.stop_ambience()
			AudioManager.stop_all_beds()
			chapter_finished.emit()
			return
		var blk: Dictionary = _scenes[_scene_idx]
		var lines: Array = blk["lines"]
		if _line_idx >= len(lines):
			# 当前段执行完：顺序推进到下一段（套用其 scene+bgm）；末段完则章节结束。
			# jump/choice 用于分支跳转，直线衔接靠 scenes[] 顺序，无需每段尾显式 jump。
			_scene_idx += 1
			if _scene_idx >= len(_scenes):
				AudioManager.stop_ambience()
				AudioManager.stop_all_beds()
				chapter_finished.emit()
				return
			_enter_scene_block()
			continue
		var line: Dictionary = lines[_line_idx]
		var op: String = line["op"]
		match op:
			"say":
				_set_slot(line.get("pos", "left"), line.get("who", ""), line.get("portrait", ""))
				portrait_changed.emit(_snapshot())
				_reconcile_beds()
				line_ready.emit("say", line)
				return  # 阻塞
			"narrate":
				if line.has("ambience") and line["ambience"] != "" and not skipping:
					AudioManager.play_ambience(line["ambience"])  # 声景随旁白同出（一次播放不阻塞）
				_reconcile_beds()
				line_ready.emit("narrate", line)
				return  # 阻塞
			"choice":
				_reconcile_beds()
				choice_presented.emit(line["options"])
				return  # 阻塞
			"ending":
				_reconcile_beds()
				ended.emit(line.get("kind", "NE"), line.get("title", ""), line.get("cg", ""))
				return  # 终止
			"label":
				_line_idx += 1
				continue
			"show", "hide":
				_apply_portrait(line)
				_line_idx += 1
				continue
			"bg":
				bg_changed.emit(line.get("scene", ""), line.get("time", ""))
				_line_idx += 1
				continue
			"bgm":
				bgm_changed.emit(line.get("track", ""), line.get("mode", "play"), line.get("loop", true))
				_line_idx += 1
				continue
			"transition":
				# 点状音效（方言 v3 的 sfx:）：播完（+0.15s 间隔）再推进下一行——与台词语音不叠播。
				# 等待期间 advance() 被 _advancing 挡住（点击不跳行）；上限 5s 防异常长文件。
				# 每帧轮询 skipping：skip 在 sfx 播放中途激活 → 立即弃播直通（旧一次性
				# timer 会挂满时长，skip 协程被 _advancing 挡住干等——「skip 跳不过 sfx」）。
				if not skipping:
					var dur: float = AudioManager.play_transition(line.get("track", ""))
					if dur > 0.0 and get_tree() != null:
						_advancing = true
						var total_ms := int(minf(dur + 0.15, 5.0) * 1000.0)
						var t0 := Time.get_ticks_msec()
						while Time.get_ticks_msec() - t0 < total_ms:
							if skipping:
								AudioManager.stop_transition()
								break
							await get_tree().process_frame
						_advancing = false
				_line_idx += 1
				continue
			"bed_start":
				# 音床起：一次性声景随行起播（不循环，尾部 2s 程序淡出自然收尾），不阻塞推进；
				# 快进（skipping）不起新床——skip 停点由 _reconcile_beds 对齐当前应播床状态。
				# 未播完时用户推进 → 1s 淡出后切句（advance 内处理）。
				if not skipping:
					AudioManager.play_bed(line.get("bed", ""), line.get("track", ""))
				_line_idx += 1
				continue
			"bed_end":
				# 音床止：兜底停止（正常情况下床早已被 advance 的推进淡出/自然播完出册；
				# 此处覆盖 bed+ 与 bed- 之间无阻塞行的极短区间——自动递进链不走 advance）
				AudioManager.stop_bed(line.get("bed", ""), 1.0)
				_line_idx += 1
				continue
			"jump":
				_do_jump(line)
				continue  # _do_jump 已重定位 _scene_idx/_line_idx，继续推进
			_:
				push_error("ScriptInterpreter: 未知 op %s" % op)
				_line_idx += 1

# 立绘累积：show/hide 维护槽并发 portrait_changed；say 的立绘在 _run_from_current 里直接 _set_slot
func _apply_portrait(line: Dictionary) -> void:
	var op: String = line["op"]
	if op == "show":
		_set_slot(line.get("pos", "left"), line.get("who", ""), line.get("portrait", ""))
		portrait_changed.emit(_snapshot())
	elif op == "hide":
		_clear_slot_by_who(line.get("who", ""))
		portrait_changed.emit(_snapshot())

func _set_slot(pos: String, who: String, portrait: String) -> void:
	if slots.has(pos):
		slots[pos] = {"who": who, "portrait": portrait}

func _clear_slot_by_who(who: String) -> void:
	for k in slots.keys():
		if slots[k] != null and slots[k].get("who", "") == who:
			slots[k] = null

func _snapshot() -> Dictionary:
	return slots.duplicate(true)

func _do_jump(line: Dictionary) -> void:
	# 仅重定位指令指针，不推进；由 _run_from_current 的 while continue 自然走到新位置
	resolve_target(line.get("to", ""), line.get("scene", ""), line.get("file", ""))

# 玩家选定选项后由 UI 调用。option 含 to/scene/file（与 jump 共用 resolve_target）。
func choose(option: Dictionary) -> void:
	if not resolve_target(option.get("to", ""), option.get("scene", ""), option.get("file", "")):
		push_error("ScriptInterpreter: 选项目标无法定位 %s" % str(option))
		chapter_finished.emit()
		return
	_run_from_current()

# 重定位指令指针（file→scene→to 三层）。返回 false 表示定位失败。
func resolve_target(to: String, scene: String, file: String) -> bool:
	# file：跨章节切换并缓存
	if file != "":
		var new_chapter: Dictionary = _loader.load_chapter(file)
		if new_chapter.is_empty():
			push_error("ScriptInterpreter: 跨章节文件不存在 %s" % file)
			return false
		_file = file
		_chapter = new_chapter
		_scenes = new_chapter["scenes"]
		_scene_idx = 0
		_line_idx = 0  # 跨章节从头（spec：file=跨章节文件从头）；若后续有 scene/to 会覆盖
	# scene：本/新章节内定位段（_enter_scene_block 重置 _line_idx=0 并发 bg/bgm）
	if scene != "":
		_scene_idx = _find_scene_index(scene)
		_enter_scene_block()
	# to：段内 label 定位
	if to != "":
		var li := _find_label(to)
		if li < 0:
			return false
		_line_idx = li
	return true

func _find_scene_index(scene_id: String) -> int:
	for i in len(_scenes):
		if _scenes[i].get("id", "") == scene_id:
			return i
	push_error("ScriptInterpreter: 找不到场景段 %s" % scene_id)
	return 0

func _find_label(name: String) -> int:
	var lines: Array = _scenes[_scene_idx]["lines"]
	for i in len(lines):
		if lines[i].get("op") == "label" and lines[i].get("name") == name:
			return i
	push_error("ScriptInterpreter: 找不到 label %s" % name)
	return -1

# 存档快照：V1 无变量无 flag，状态 = 文件/段/指针/槽。供 SaveManager 持久化。
func snapshot() -> Dictionary:
	var blk: Dictionary = _scenes[_scene_idx] if _scene_idx < len(_scenes) else {}
	return {
		"file": _file,
		"scene_id": blk.get("id", ""),
		"line_idx": _line_idx,
		"slots": slots.duplicate(true),
		"bg": "", "bgm": ""
	}

# 从快照恢复运行时状态，套用当前段视觉并从 line_idx 继续执行。
func restore(snapshot_data: Dictionary) -> void:
	if _loader == null:
		_loader = _ChapterLoader.new()
	slots = snapshot_data.get("slots", {"left": null, "center": null, "right": null})
	var file: String = snapshot_data.get("file", "")
	var scene_id: String = snapshot_data.get("scene_id", "")
	var line_idx: int = int(snapshot_data.get("line_idx", 0))
	await ChapterPackLoader.ensure_chapter(file)
	_chapter = _loader.load_chapter(file)
	if _chapter.is_empty():
		push_error("ScriptInterpreter: restore 无法加载 %s" % file)
		chapter_finished.emit()
		return
	_file = file
	_scenes = _chapter["scenes"]
	_scene_idx = _find_scene_index(scene_id) if scene_id != "" else 0
	_line_idx = line_idx
	AudioManager.stop_ambience()  # 清旧档残留声景（恢复点之后的 narrate.ambience 会重新起）
	AudioManager.stop_all_beds()  # 清旧档残床（恢复点之后的 bed_start 会重新起；之前的床不恢复）
	# 套用当前段的视觉（scene+bgm+立绘），但不重置 line_idx
	var blk: Dictionary = _scenes[_scene_idx]
	bg_changed.emit(blk.get("scene", ""), blk.get("time", ""))
	if blk.has("bgm"):
		var b: Dictionary = blk["bgm"]
		bgm_changed.emit(b.get("track", ""), b.get("mode", "play"), b.get("loop", true))
	portrait_changed.emit(_snapshot())
	_run_from_current()
