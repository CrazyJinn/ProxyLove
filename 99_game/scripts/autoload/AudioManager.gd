extends Node
## 集中式音频管理器。BGM 播放/停止/切轨、转场音效（transition/sfx 点状）、氛围声景
## （ambience，旧章 JSON 兼容）、音床（bed，区间循环）、语音播放、音量设置。
# Demo 无真实音频文件，所有路径走 Manifest 取值；资源缺失时 push_warning 并静默跳过，不阻塞管线。

var _bgm: AudioStreamPlayer = null
var _transition_player: AudioStreamPlayer = null
var _ambience_player: AudioStreamPlayer = null
var _voice_player: AudioStreamPlayer = null
var _beds: Dictionary = {}  # bed id -> {"player": AudioStreamPlayer, "track": String}
var _beds_dismissed: Dictionary = {}  # bed id -> true：用户推进收掉的床（本区间不再自动起播——
#   防 reconcile 按剧本区间复活；区间结束/换段/读档时清除，同 id 未来区间可再起）
var _bgm_loop: bool = true
var _bgm_user_db: float = 0.0  # 用户设置的 BGM 音量（SettingsPanel 加载时写入）

# BGM 通道基础衰减（默认混音：BGM 相对听感减半，语音/音效优先）。用户音量设置叠加其上。
const BGM_BASE_GAIN_DB := -10.0
const BED_TAIL_FADE := 2.0  # 床自然收尾：尾部 N 秒程序淡出（播完硬截断会突兀）

func _ready() -> void:
	_bgm = AudioStreamPlayer.new()
	_bgm.volume_db = BGM_BASE_GAIN_DB
	_transition_player = AudioStreamPlayer.new()
	_ambience_player = AudioStreamPlayer.new()
	_voice_player = AudioStreamPlayer.new()
	add_child(_bgm)
	add_child(_transition_player)
	add_child(_ambience_player)
	add_child(_voice_player)

func play_bgm(track: String, loop: bool = true) -> void:
	var path: String = _manifest().get_bgm(track) if _manifest() else ""
	if path == "" or not ResourceLoader.exists(path):
		push_warning("AudioManager: BGM 资源缺失 %s" % track)
		return
	_bgm.stream = load(path)
	_bgm_loop = loop
	_bgm.play()

func stop_bgm() -> void:
	_bgm.stop()

func fade_bgm(track: String, loop: bool = true) -> void:
	# V1：简化为切换播放目标轨道（无真实淡入淡出）
	play_bgm(track, loop)

## 转场音效（一次性短事件，1~2s 实录）。返回流时长（秒）；0 = 资源缺失/失败。
## 调用方（ScriptInterpreter）据此 await 播完再推进下一行——音效与台词不叠播。
func play_transition(track: String) -> float:
	var path: String = _manifest().get_sfx(track) if _manifest() else ""
	if path == "" or not ResourceLoader.exists(path):
		push_warning("AudioManager: 转场音效资源缺失 %s" % track)
		return 0.0
	var stream: AudioStream = load(path)
	_transition_player.stream = stream
	_transition_player.play()
	return stream.get_length() if stream else 0.0

## 氛围声景（挂 narrate 行，随旁白同出）。产物为 ~5s 带淡出的一次性片段——**播放一次
## 自然结束，不循环、不阻塞台词**（区别于 transition 转场音效的「等播完再推进」）。
## 同 track 已在播则不重启（防同段短间隔重复触发）；换 track 原地替换。
## 场景块切换由调用方 stop_ambience（打断残留长声景）。
func play_ambience(track: String) -> void:
	if _ambience_player.playing and track == _ambience_player.get_meta("track", ""):
		return  # 同声景在播：不重启（避免句间反复起播）
	var path: String = _manifest().get_sfx(track) if _manifest() else ""
	if path == "" or not ResourceLoader.exists(path):
		push_warning("AudioManager: 氛围声景资源缺失 %s" % track)
		return
	_ambience_player.stream = load(path)
	_ambience_player.set_meta("track", track)
	_ambience_player.play()

func stop_ambience() -> void:
	_ambience_player.stop()

func stop_transition() -> void:
	_transition_player.stop()  # skip 激活时弃播正在等待的 sfx（跳过语义，不等播完）

## 音床（bed+ 起 / bed- 止的区间声景，**一次性播放不循环**）。同床同曲在播 → 忽略
## （防重）；换曲 → 重载。结束淡出由 stop_bed(fade_s) 程序做（Tween 音量到 -60dB 后
## 自毁）——用户推进时未播完的床由 ScriptInterpreter.advance 淡出 1s 再切句。
## 音量走 sfx 通道；生命周期由调用方收口（换段/章末/读档 stop_all_beds 立即停，
## 停点由 ScriptInterpreter._reconcile_beds 按剧本位置对齐恢复——读档后床继续）。
func play_bed(bed: String, track: String) -> void:
	if bed == "":
		return
	if _beds.has(bed) and _beds[bed].get("track", "") == track \
			and _beds[bed]["player"].playing:
		return
	var path: String = _manifest().get_sfx(track) if _manifest() else ""
	if path == "" or not ResourceLoader.exists(path):
		push_warning("AudioManager: 音床资源缺失 %s" % track)
		return
	stop_bed(bed)
	var p := AudioStreamPlayer.new()
	p.stream = load(path)
	p.finished.connect(_bed_finished.bind(bed))  # 播完自然结束 → 出册（下次推进直接切句）
	add_child(p)
	p.play()
	_beds[bed] = {"player": p, "track": track}
	# 自然收尾：尾部 N 秒程序淡出（产物无尾部淡出，硬截断突兀）——到点时床仍在册且
	# 同曲才执行（用户提前推进已杀床/同床换曲则跳过），统一走 stop_bed 出册+tween 自毁。
	var dur: float = p.stream.get_length() if p.stream else 0.0
	if dur > BED_TAIL_FADE:
		var tail_at: float = dur - BED_TAIL_FADE
		get_tree().create_timer(tail_at).timeout.connect(func():
			var info: Dictionary = _beds.get(bed, {})
			if not info.is_empty() and info.get("track", "") == track:
				stop_bed(bed, BED_TAIL_FADE))

func _bed_finished(bed: String) -> void:
	# 一次性播放：自然播完即出册自毁（has_active_beds 转 false → 推进时无需淡出等待）。
	# 正常情况下尾部淡出 timer 先到（stop_bed 出册+自毁），此处只兜异常时序。
	var info: Dictionary = _beds.get(bed, {})
	if info.is_empty():
		return
	_beds.erase(bed)
	if is_instance_valid(info["player"]):
		info["player"].queue_free()

## 对齐当前应播床状态（skip/读档停点用）：want = {bed_id: track}。
## 缺的起播、多的立即停、同床换曲重载——skip 途中 bed 指令被忽略，停点靠本函数对齐。
## **用户推进收掉的床（_beds_dismissed）不复活**——推进即收是用户显式意图，优先于
## 剧本区间；区间结束（want 不含）时解除 dismissed，同 id 未来区间可再起。
func reconcile_beds(want: Dictionary) -> void:
	for bed in _beds.keys().duplicate():
		if not want.has(bed):
			stop_bed(bed)
	for bed in _beds_dismissed.keys().duplicate():
		if not want.has(bed):
			_beds_dismissed.erase(bed)  # 区间结束：解除，未来同 id 区间可自动起播
	for bed in want:
		if _beds_dismissed.has(bed):
			continue
		play_bed(bed, want[bed])  # 同床同曲在播 → 内部防重忽略；换曲/缺失 → 起播

func has_active_beds() -> bool:
	return not _beds.is_empty()

func stop_bed(bed: String, fade_s: float = 0.0) -> void:
	## fade_s>0：Tween 音量淡出后自毁（推进未播完的床 / bed_end 行用 1.0）；
	## 缺省 0 立即停（换段/读档/章末快切语义）。
	## 开始淡出即从 _beds 出册——防「淡出中紧跟 bed+ 同床同曲」被 play_bed 防重逻辑忽略、
	## 淡出完成后静音的边缘 case（方言允许 bed- 后紧接 bed+ 同 id 再起）。
	var info: Dictionary = _beds.get(bed, {})
	if info.is_empty():
		return
	_beds.erase(bed)
	var p: AudioStreamPlayer = info["player"]
	if not is_instance_valid(p):
		return
	if fade_s > 0.0:
		var tw := create_tween()
		tw.tween_property(p, "volume_db", -60.0, fade_s)
		tw.finished.connect(func():
			p.stop()
			p.queue_free())
	else:
		p.stop()
		p.queue_free()

## 批量停床。dismiss=true（用户推进收床）：被停的床记入 dismissed，reconcile 不再按
## 剧本区间复活；立即停路径（skip/换段/读档/章末）顺带清空 dismissed（全局重置，
## 停点 reconcile 可按剧本位置重新起播——skip 到达新进度应有床）。
func stop_all_beds(fade_s: float = 0.0, dismiss: bool = false) -> void:
	for bed in _beds.keys().duplicate():
		if dismiss:
			_beds_dismissed[bed] = true
		stop_bed(bed, fade_s)
	if not dismiss:
		_beds_dismissed.clear()

func play_voice(key: String) -> void:
	# 首行无条件 stop：任一新 say 都自动停上一句，覆盖点击/Auto/Skip/Ctrl 所有推进路径
	_voice_player.stop()
	if key == "":
		return  # narrate / 无 voice 字段：仅停旧音不播放
	var path: String = _manifest().get_voice(key) if _manifest() else ""
	if path == "" or not ResourceLoader.exists(path):
		push_warning("AudioManager: VOICE 资源缺失 %s" % key)
		return
	_voice_player.stream = load(path)
	_voice_player.play()

func stop_voice() -> void:
	_voice_player.stop()

## 当前句语音是否仍在播（Auto 模式据此等播完再切句；narrate/资源缺失恒 false）。
func is_voice_playing() -> bool:
	return _voice_player.playing

func set_volume(channel: String, value_db: float) -> void:
	match channel:
		"bgm":
			_bgm_user_db = value_db
			_bgm.volume_db = BGM_BASE_GAIN_DB + value_db  # 用户值叠加通道基础衰减
		"sfx":
			_transition_player.volume_db = value_db
			_ambience_player.volume_db = value_db
			for info: Dictionary in _beds.values():
				info["player"].volume_db = value_db  # 床播放器动态建，须遍历同步
		"voice": _voice_player.volume_db = value_db

func _manifest():
	return Engine.get_singleton("Manifest") if Engine.has_singleton("Manifest") else null
