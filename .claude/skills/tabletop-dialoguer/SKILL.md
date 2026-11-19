---
name: tabletop-dialoguer
description: |
  跑团式节台词生成（DM 制 + 常驻角色 subagent，邮箱模式 inbox/outbox）：主 agent 任 DM，一个角色一个常驻 subagent，角色按自身三钉自由发挥、互相对话逐句推进直到 sub 内容演完；DM 只当裁判不导演。
  产出读者向台词草稿（DM 旁白散文织入台词之间，带机位/BGM 占位符的汇编 md），试验阶段只落 scratch、零图写入；是 chapter-dialoguer 的候选替代/补充，未接入生产链。
  在需要为某 Section 生成台词草稿、或对比跑团产出与 chapter-dialoguer 定稿质量时使用。argument-hint: <section_id>
argument-hint: <section_id>
arguments:
  - section_id
allowed-tools: Read, Bash, Write, Edit, delegate_task, terminal
---

# 跑团式台词生成（DM 制 · 常驻邮箱模式 · v3 协议）

> 经 ch02 sec02 三轮实测验证：v3 53 手零作废、台词中位 17 字、真 silence 可触发。
> 试验定位：产出只落会话 scratch，不改 Section.status、不写 script_path、不覆盖 25_剧本 定稿、不动 chapter-novelist / chapter-dialoguer。转生产需另出方案另行批准。

## 1. 架构与信息流

```
DM（主 agent，独占全量图数据）
  │ 开拍查询：Section→includes→Event→refines→SubEvent（sub.description=判定依据；机位=sub 的 anchored_at Scene，occurs_at 只是事件地点足迹）
  │ 人物所在地查询：各在拍角色覆盖事件 start_time 的 at 区间（多条覆盖取最短、哨兵 开篇前/至今 特判）——远程在场事件（电话/连麦）对端由此得出，不默认同机位
  │ 认知集查询（时间在 cypher 的 WHERE 中控制，勿 LLM 自行裁剪）：
  │   MATCH (c:Character {id:'<角色id>'})-[:has_cognition]->(cg:Cognition)-[:about]->(i:Info)
  │   MATCH (ke:Event)-[:forms]->(cg) WHERE ke.start_time <= '<本拍时刻>'
  │   RETURN i.title, i.knowledge_level
  │   UNION MATCH (c:Character {id:'<角色id>'})-[:has_info]->(l:Lore) RETURN l.title
  │ 共同经历查询：(Character)-[:involved]→(Event)，按时间过滤
  ▼
每角色一个常驻 subagent（delegate_task 派发，全场一次）
  │ 收信循环：poll inbox_N.txt → 按人设自由反应 → 追加 outbox_N.txt（<编号>|<JSON>）
  ▼
DM 逐手审验（串行铁律：一手一回传一手，严禁并行派发+预填历史）
  │ 判 sub 事实项演到 → 世界事件/旁白推进；未演到且僵住 → 下一拍
  ▼
汇编 md（拍头旁白帧 + 逐手台词 + DM 判定 + 量化对照）——只落 scratch
```

角色权威状态永远在图（Character/Lore/LanguageStyle）；inbox/outbox 是单次会话的舞台便签，跨会话复用明确不做。

## 2. 生命周期与协议（v3）

- 派发即驻留：语境含角色定义（三钉/LS/台词纪律/内心轨规则）+ 驻留协议，然后全场不重复派发该角色。
- 收信循环：`awk -F'|' '$1>已回最高编号' inbox_N.txt` → 回信追加 `outbox_N.txt`。
- **固定 `sleep 10`，禁自适应退避**（v2 实测退避把节拍切换延迟拉到 2 分钟）。
- **END 信优先于一切超时**：每轮 poll 第一动作查 END；预算（总驻留 90 分钟）只对「无 END 收件」生效（v2 王昊因预算抢跑错过 END）。
- 退出三通道：END 优雅退场（汇报演出史）> 预算自尽 > DM stop。
- 实例可弃、状态在文件；重 spawn+回灌 outbox 即复活。delegation/subagent ID 落盘到工位 README，否则续跑查不回。

## 3. 信封契约（DM → 角色）

信封只装三样，**永不装**：本手指令、别人的钉子、全局图数据、未来节拍、他人内心。**信息投放白名单 = 该角色认知集**（has_cognition→about 可达的 Info ∪ 自己 has_info 的 Lore，forms 锚事件不晚于本拍；封闭世界——无认知链=不知道）——认知集之外的信息即使剧情需要也不经信封泄露（世界事件通道另议）。

1. **场景帧**：开拍/转场时，含【旁白·机位：…】【BGM：待定·…】【转场：…】【你所在：…】占位符（机位取自图 sub 的 anchored_at，各角色所在取覆盖事件 start_time 的 at 区间——语音场对端与机位端不同地是常态，照实分开写，不手写散文）；
2. **新增可见历史**：他人言行转述 + 自己没说过的客观事实；「（沉默）」可见；
3. **供词**：客观现象，不给结论（写「你已经看出他是关系户」= 剥夺角色推理）。

## 4. 输出合同（角色 → DM）

```json
{"type": "line_action | line | action | silence", "line": "...", "action": "...", "inner": "（可选，默认省略）"}
```

- 外发 line 一句口语短句常规 5~25 字（v3 实测中位 17、max 30，「演讲手」消失）；
- `inner` 仅限双轨角色（宿主灵魂，如陆择），默认省略——写了必须装「说不出但必须知道」的信息，与台词信息重复的判违例退回；非双轨角色语境直接写「无内心轨」；
- silence 合法且可见为「（沉默）」；纯 action 手合法；
- 纯中文，禁任何外文单词；违约退回重问。

## 5. DM 纪律：裁判不导演

- 不拆节拍点清单、不逐手下指令、不替角色决定做什么；开拍只投场景帧，行动动机全来自角色自己的钉子；
- 唯一推进杠杆 = **世界事件**（新人物入场/新信息到达/时间压力/旁白+事件打包），全场 4~6 次足够（v3 实测 4 次，无僵死）；
- 判完成口径 = sub.description 事实项演到，**同一事实项允许不同演法**（例：「找由头挂断」被角色演成「当面缴械应下」= 放行并注记）；
- 唯一例外：事实项被角色跳过时，用世界结构把球递回去（v3 判例：陆择想跳过读合同，不指令他读，而是让沈暮雪按自己的条款式性格测试「哪条是竞业？」）；
- 串行铁律机械化保留：一手一回传一手，v1 三连事故的根因。
- 每拍收束后在汇编里写 **DM 判定**（哪些事实项以何种演法覆盖、自由发挥分叉、放行理由）。

## 6. 共同经历与认知集（开拍前查询）

- 共同经历查询：`(Character)-[:involved]→(Event)`，取当拍在场角色集合交集，**按剧情时间过滤（只投本节之前的事件）**——v3 实测把 06-18 的「踢人事件」误当 sec02 前史，靠时间过滤剔除；
- 认知集查询（**cypher 语句如下，时间在查询中控制**，不凭记忆手抄清单）：
  ```cypher
  MATCH (c:Character {id:'<角色id>'})-[:has_cognition]->(cg:Cognition)-[:about]->(i:Info)
  MATCH (ke:Event)-[:forms]->(cg)
  WHERE ke.start_time <= '<本拍时刻>'
  RETURN 'info' AS kind, i.title AS title, i.knowledge_level AS kl, cg.type AS attitude, coalesce(cg.title,'') AS believed, ke.start_time AS since
  UNION
  MATCH (c:Character {id:'<角色id>'})-[:has_info]->(l:Lore)
  RETURN 'lore' AS kind, l.title AS title, l.knowledge_level AS kl, '' AS since
  ```
  每个角色实例只知道自己认知集内的事实；**封闭世界认知，无例外**——无 has_cognition 链=不知道，involved 不推导知情（「参与即知情」已废止）；漏建认知条目=角色被误判无知，发现缺口在汇报中报，不在投放侧补丁；防剧透由 `WHERE ke.start_time <= 本拍时刻`（forms 锚事件）兜住；**角色不知道的信息不投、也不允许角色引用**（confabulation 与 improvisation 的分界线：有钉子时的自由发挥是特性，无钉子时的编造是事故）；认知条目带 type 与偏差 title（believed 非空=该角色信的是另一个命题，注入时照所信命题而非 Info 本体）；
- 注入纪律：①亲历者各拿各版本的记忆（同一事件，不同角色记得不同侧面）；②**宿主/灵魂归属检查**：宿主入住前形成的认知（has_cognition 链且 forms 锚事件早于入住）与宿主名下 Lore，灵魂没有记忆（陆择的认知集=陆择自己的认知链，不含宿主前史认知）——投前必查入住时间线；③只供事实不供感受；
- 已知局限：注入被角色吸收（气质相容）但未必显式引用；显式唤起需要更强的世界事件触发，待验证。

## 7. 汇编（交付物）

交付稿是**读者向台词草稿**，不是会议实录：

- 每拍以 `## 拍N 标题` + `【场景 …|BGM 待定：…】` 占位符行开头；
- **DM 旁白 = 写给读者的小说式叙述散文**（场景过渡、环境氛围、时间跳跃桥接），以引用段落织在台词行之间，时序必须正确（v3 返工点：门铃旁白曾被错排在进门戏之后）；信封里的【机位/BGM】帧只是给实例的舞台指示，不是读者旁白——旁白由 DM 在汇编阶段从帧素材展开创作，只在转场和必要桥接处写，不逐手刷屏；
- 台词行 `角色：「line」（action）（内心：…）`；silence 写作「（沉默）」，或并入旁白叙述；
- 文末附内部附录（不属草稿本体）：DM 判定逐拍记录 + 量化表（总手/行长中位/silence/inner 占比/作废数，对照前轮）+ 机制发现清单。

## 8. 已知坑（实测）

1. 语音场（电话/连麦）角色会产出面对面动作（「转过椅子正对陈默」）——根治法=场景帧写明各角色所在（at 区间，对端与机位端不同地）；合同「语音场禁身体朝向对方、禁眼神接触」保留为兜底，DM 接受台词、剔除动作歧义；
2. 真 silence 的触发条件是「在场但非话事中心」的结构位置，硬造不出来；
3. 双开拍帧同时投两个实例会让两人同时出首手——开场帧只投一人，另一人等轮转；
4. 角色自由发挥会改戏的结构（电话→上门、skip→被测试），这是特性不是事故，判完成口径容得住；
5. delegation 结果只在轮次结束回传，工位文件才是实时进度——用 outbox 增量收割，勿等汇报。
