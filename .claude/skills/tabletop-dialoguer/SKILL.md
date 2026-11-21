---
name: tabletop-dialoguer
description: |
  跑团式节台词生成（DM 制 + 常驻角色 subagent，邮箱模式 inbox/outbox）：主 agent 任 DM，一个角色一个常驻 subagent，角色按自身三钉自由发挥、互相对话逐句推进直到 sub 内容演完；DM 只当裁判不导演。
  节级创作链第一环（chapter-novelist 已软删 2026-11-20，本 skill 为替代）：产出读者向台词草稿 跑团草稿.md（DM 旁白散文织入台词之间，每拍带【场景：地点·时间｜block <scene_block_id>】行 + 头部取材指纹），落盘 25_剧本/ch<NN>/sec<MM>/，交 chapter-dialoguer 打磨定稿；零图写入（status 推进归 dialoguer 唯一图写入）。
  在需要为某 Section 产台词草稿（plot-design 编排触发或用户直呼）时使用。argument-hint: <section_id>
argument-hint: <section_id>
arguments:
  - section_id
allowed-tools: Read, Bash, Write, Edit, delegate_task, terminal
---

# 跑团式台词生成（DM 制 · 常驻邮箱模式 · 按 Event 分批 + 事件后回收）

> 经 ch02 sec02 五轮实测：台词中位 17 字、真 silence 可触发、披露审验实弹两拦两成。派发粒度按 Event 分批，事件收束即回收实例。
> 生产定位：节级创作链第一环（小说段替代——chapter-novelist 已软删 2026-11-20）。产 跑团草稿.md 交 chapter-dialoguer 打磨定稿（草稿→台词.ink 两段式）；本 skill 零图写入——不改 Section.status、不写 script_path，图写入归 dialoguer 唯一图写入；不动存量 小说.md/台词.ink（存量节定稿链照旧）。

## 1. 架构与信息流

```
DM（主 agent，受限视角——一切图查询带时间上限，见 §6 样例库：
  │   结构查询 ≤ 本节末 / 动态查询 ≤ 本拍时刻；DM 与角色同样不知道未来，
  │   未来数据不进信封也不进 DM 判定依据）
  │ 四条合并查询（样例见 §6：开跑 Q1 骨架+Q2 静态包；每批 Q3 动态包+Q4 共同经历）：
  │   Q1 骨架：节结构+拍序（sub.start_time）+判定依据+场景锚+在场名单（→批划分）
  │   Q2 静态包：vibe/Lore/relation/LS（三钉+语境角色定义+对手关系口径素材）
  │   Q3 动态包：认知集白名单（forms 锚 ≤ cutoff，同 (角色,Info) 多条时间线全量返回——认知编年史）∪ at 区间（哨兵 开篇前/至今 特判）
  │   Q4 共同经历：UNWIND 角色组，size(ppl)=size(group) 图内交集（< cutoff）
  ▼
每 Event 一批常驻 subagent（delegate_task 派发，只含本 Event 在场角色；贯穿角色每 Event 新实例，前情由场景帧现查重组）
  │ 收信循环：poll inbox_N.txt → 按人设自由反应 → 追加 outbox_N.txt（<编号>|<JSON>）
  ▼
DM 逐手审验（串行铁律：一手一回传一手，严禁并行派发+预填历史）
  │ 判 sub 事实项演到 → 世界事件/旁白推进；未演到且僵住 → 下一拍
  ▼
汇编 跑团草稿.md（拍头旁白帧 + 逐手台词；文末附录 DM 判定/量化对照）——落盘 25_剧本/ch<NN>/sec<MM>/，零图写入（契约见 §7/§9）
```

角色权威状态永远在图（Character/Lore/LanguageStyle）；inbox/outbox 是单次会话的舞台便签，跨会话复用明确不做。

## 2. 生命周期与协议（单 Event 生命周期，收束即回收）

- 按 Event 分批派发：每批只 spawn 本 Event 在场角色；语境含角色定义（三钉/LS/台词纪律/内心轨规则）+ 驻留协议，只装本 Event 的 sub 序与场景帧（未来 Event 不进视野）。贯穿角色（如陈默）每 Event 一个全新实例——实例间零记忆连续性，前情由场景帧按当日现查的认知集重组（权威在图，跨会话/跨批复用明确不做）。
- 收信循环：`awk -F'|' '$1>已回最高编号' inbox_N.txt` → 回信追加 `outbox_N.txt`；**回信先于查信**——查到新信前必须已回完上一信全部手，严禁把旧信尾答攒到下一批（实测判例：跨拍延迟手 6 处，含 echo 签手）。
- 事件收束即回收四步：判完成（sub 事实项演到）→ 对本批全部实例投 `99|END`（编号大于各自已回最高编号）→ 收末手核 outbox 行数（实例自评只当索引，会漂）→ delegate_task stop 逐实例兜底（已优雅退场则 stop 为空操作），归档该 Event 段、README 记 delegation id 后再开下一批。
- **固定 `sleep 10`，禁自适应退避**（实测退避把节拍切换延迟拉到 2 分钟）。
- **END 信优先于一切超时**：每轮 poll 第一动作查 END；预算（总驻留 90 分钟）只对「无 END 收件」生效（实测有实例因预算抢跑错过 END）。
- 退出三通道：END 优雅退场（汇报演出史）> 预算自尽 > DM stop。
- 实例可弃、状态在文件；重 spawn+回灌 outbox 即复活。delegation/subagent ID 落盘到工位 README，否则续跑查不回。

## 3. 信封契约（DM → 角色）

信封只装三样，**永不装**：本手指令、别人的钉子、全局图数据、未来节拍、他人内心。**信息投放白名单 = 该角色认知集**（has_cognition→about 可达的 Info ∪ 自己 has_info 的 Lore，forms 锚事件不晚于本拍；封闭世界——无认知链=不知道。认知编年史：同 (角色, Info) 可有多条认知沿 forms 时间轴并存，Q3 全量返回时间线——信封投放**按拍时刻取最新有效态**，旧态（如已揭底的误信）只作 DM 理解认知演变的素材，不进白名单）——认知集之外的信息即使剧情需要也不经信封泄露（世界事件通道另议）。反向同理：**听者在拍时刻无有效认知链（forms ≤ 拍时刻）的 Info，本节不得经任何角色之口使其知情**——披露审验见 §5。

1. **场景帧**：开拍/转场时投递，**Markdown 结构化分块**（模板见下；逐块信息给全——分块比散文段更防要素遗漏）。六要素语义不变，格式上「我面对的是谁」与「我在之前做过什么」合并为对手块：

   ```
   【场景帧】<日期 时间>

   ## 你是谁
   <话顶身份，双轨角色含内在身份；可带 vibe 一句>

   ## 你在哪
   <at 区间覆盖本拍时刻（sub.start_time）的位置；语音场两端不同地是常态，照实写各端所在地>

   ## 你要干什么
   <本场景当场的事务，如「接这通电话」「把合同看完签掉」；不含未来节拍>
   <口径继承：拍点依据（Event/sub description）中的隐瞒/谎称/试探类意图必须显式下达且带口径本身，如「按你已跟他说过的口径，这就是家庭聚餐」——只给任务不给口径，角色会按自己的 KNOWS 直说，隐瞒戏必翻车；无此类意图则省略本行>

   ## <对手姓名>（<在场身份/头衔，只投 Q1 骨架（Event 语境/sub description）可见部分，不为 roster 常识造图数据>）
   - 关系：<relation 边口径，如亲姐姐/队友；无边=初见，照封闭世界直译「无交集/不熟」>
   - 你们发生过什么：<共同经历查询结果按时间摘要；交集为空=「无交集」>
   - <可选：对手此刻在场状态一句>

   ## 你现在知道什么
   - <认知集白名单逐条（认知编年史按拍时刻最新有效态）>
   ```

   多对手（语音频道/群场）每人一个对手块。对手**形象不进信封**——AppearanceStyle 在参考图流程下不保证填写、不可作事实源，外貌感知归 DM 旁白（读者向层）。**段位纪律**——认知态一律落「你现在知道什么」块、共同经历一律落对手块「发生过什么」，段位混装（认知写进对手块、认知块缺位）判违例退回重写。无机位/BGM/转场占位符（机位、BGM、氛围属汇编阶段的读者向创作，不是角色输入，用户裁决）；
2. **新增可见历史**：他人言行转述 + 自己没说过的客观事实；「（沉默）」可见（写成「她没接话」）；
3. **供词**：客观现象，不给结论（写「你已经看出他是关系户」= 剥夺角色推理）。

**信封文案纪律**：类目名（新增可见历史/供词/世界事件）是 DM 的组装分类，**不进信封正文**——正文以世界向角色的呈现落笔：对手言行用转述句直接开场（「电话那头，姐姐连珠炮开口——」「频道里王昊把锅往外拨——」），客观现象用感官句（「你看见……」「你听到……」），世界事件直接写发生（「你还没走出大门，一个双手插兜的家伙晃到你跟前——」）；角色收信读到的是世界，不是标签。唯二例外：场景帧首行的【场景帧】标记（开拍/转场识别用）、违约退回令（元指令，明示「违约退回：」）。

**信封只抄图**：信封内一切事实（认知、共同经历、at、头衔、约定细节）以查询返回为唯一来源，DM 禁止顺手补写图中没有的推论、时间、地点。图料不足报缺口，宁缺勿编（判例：场景帧把「初期训练均为线上」补写成「今天起转线下」——图无此锚、且与当晚线上训练赛冲突，两批实例口径被带偏；信封写错 = 全线污染，比角色即兴危害大一个量级）。

## 4. 输出合同（角色 → DM）

```json
{"type": "line_action | line | action | silence", "line": "...", "action": "...", "inner": "（可选，默认省略）"}
```

- 外发 line 一句口语短句常规 5~25 字（实测中位 17、max 30，「演讲手」消失）；
- `inner` 仅限双轨角色（宿主灵魂，如陆择），默认省略——写了必须装「说不出但必须知道」的信息，与台词信息重复的判违例退回；非双轨角色语境直接写「无内心轨」；
- silence 合法且可见为「（沉默）」；纯 action 手合法；
- 纯中文，禁任何外文单词；违约退回重问。
- 披露违规（向拍时刻无有效认知链的听者**唯一可指认**地传递 Info）判违约退回——细则见 §5 披露审验。

## 5. DM 纪律：裁判不导演

- 不拆节拍点清单、不逐手下指令、不替角色决定做什么；开拍只投场景帧，行动动机全来自角色自己的钉子；
- 唯一推进杠杆 = **世界事件**（新人物入场/新信息到达/时间压力/旁白+事件打包），全场 4~6 次足够（实测 4 次，无僵死）；
- 判完成口径 = sub.description 事实项演到，**同一事实项允许不同演法**（例：「找由头挂断」被角色演成「当面缴械应下」= 放行并注记）；
- 唯一例外：事实项被角色跳过时，用世界结构把球递回去（判例：陆择想跳过读合同，不指令他读，而是让沈暮雪按自己的条款式性格测试「哪条是竞业？」）；
- **披露审验（用户裁决）**：认知层是只读运行时状态——「谁在何时知道什么」只能由图变更，跑团不得创造新知情者。逐手审验加一道披露检查：该手台词若向在场者传递其**拍时刻无有效认知链**（forms ≤ 拍时刻）的 Info，且内容**唯一可指认**该 Info（点名或可唯一定位，判例：「职业队要了我」⇒「陈默加入星耀二队」，拦），判违约——退回重演（退回理由只写「该信息本场不可对此人披露，换一手」，勿解释图结构），记作废样本；该台词不进可见历史、不转述对手、不进读者稿。豁免：inner 不外发不算；无听者独白不算；听者已持 KNOWS 态不拦。**误信态保护**：听者对某 Info 持偏差态（BELIEVES+title）时，任何角色台词不得唯一可指认地向其说破该 Info 的真相定性（判例：听者信「约的是家庭聚餐」时，「那是相亲！」四字即揭底）——提前揭底=抢跑编年史在未来事件 forms 锚上的揭底态，视同违约退回；揭底只能发生在 forms 锚定的揭底事件，跑团不得代跑。剧情上应有而图上漏建的披露会当场卡住——如实报缺口（设计端补 establishes+认知链），勿 runtime 补丁；错误前移到设计期是该裁决的预期效果；
- **拍点披露预检**：sub 事实项含披露/宣言/亮底类动作（「亮目标」「说出真相」「坦白」）时，开拍前先核该动作的目标听者对相关 Info 的认知链——听者无链且无拍内 forms 余地 = 该动作演到即违约，拍点被认知层卡死；如实报缺口（设计端补认知链或改拍点），勿归因于角色钉子触发权重、勿现场导演补救（判例：拍3「沈暮雪亮目标」三窗口未演到被误判为钉子权重不足，真因是听者陈默对该 Info 无链——演到反而违约，坑6 的宣言变体）；
- **涌现事实治理**：角色自由发挥产生的新世界事实，逐手过一道对照——a. **新人物**：图中无此 Character = 图外编造，违约退回（判例：陈念「妈做饭」，现查图上无父母角色，退回重演干净）；b. **时间冲突**：涌现的约定/事件时间与本节拍时刻（Q1 骨架）或**直接因果链邻居时刻**（审验豁免见 §6）撞车/错改 = 冲突，DM 以世界事件通道纠偏（改期 / 让角色自己发现撞车），勿放任（判例：图上锚定 06-14 中午的饭局被演成「今晚六点半家宴」——既撞本节当晚 19:30 训练赛，又错改 `leads_to` 下游揭底事件锚定的日期，沿 leads_to 一跳现查即可拿到正确时间锚当场纠偏）；c. **无冲突的物流级细节**（宿舍 B 栋、泡面）放行注记。
- 串行铁律机械化保留：一手一回传一手，早期三连事故的根因。
- 每拍收束后在汇编里写 **DM 判定**（哪些事实项以何种演法覆盖、自由发挥分叉、放行理由）。

## 6. DM 查询样例库（合并版：开跑 2 条 + 每批 2 条，抄改 cutoff/名单即用）

> **DM 受限视角原则**：时间上限写在 cypher 的 WHERE 里，不做 LLM 侧裁剪——DM 与角色同样不知道未来。合并查询各支路的 WHERE cutoff 各自保留、批外角色在 WHERE 过滤，合并不放大视野。动态 cutoff 一律以 `sub.start_time` 为准，Event 时间仅作参考——拍内锚定（如「沈暮雪目标认知 forms 10:30」在 sub=10:45 的初见王昊拍是否可见）只有 sub 时间判得准。教训保留：共同经历不过滤时间，06-18 踢人事件被误当 sec02 前史。样例值取自 ch2 sec02（2024-06-12）。
>
> **审验豁免（直接因果链）**：涌现事实治理（§5-b）需要时间锚时，允许沿 `leads_to` 查本拍 Event 的直接因果邻居（一跳，含未来 Event）的 start_time/end_time/title——查询结果**仅用于冲突判定**，禁止进入信封投放、叙事决策与旁白；豁免只服务审验不服务叙事，DM 的叙事视野仍不知未来（判例：拍1 涌现「今晚六点半家宴」，沿 leads_to 现查下游揭底事件锚定 06-14 12:00 → 当场判错改、纠偏改期，而角色与叙事线对 06-14 仍一无所知）。

**Q1 骨架查询（开跑一次）**——节结构+sub 序+场景锚+在场名单，产出批划分表（每 Event 在场角色→spawn 名单）与拍序（拍序与「本拍时刻」以 `sub.start_time` 为准——SubEvent 自带拍级时刻比 Event 细：签约落笔 sub=10:20（Event=10:00）、初见王昊 sub=10:45 与荣誉墙共享 Event 10:30，只有 sub 时间分得出先后）

```cypher
MATCH (s:Section {title:'全败首日'})-[:includes]->(e:Event)
OPTIONAL MATCH (e)<-[:involved]-(c:Character)
WITH e, collect(DISTINCT c.name) AS ppl
OPTIONAL MATCH (e)-[:refines]->(sub:SubEvent)
OPTIONAL MATCH (sub)-[:anchored_at]->(scn:Scene)
RETURN e.start_time AS evt_st, e.title AS evt, ppl,
       sub.start_time AS st, sub.title AS sub, sub.description AS basis, scn.name AS scene, scn.id AS scene_id
ORDER BY st
```

**Q2 角色静态包（开跑一次）**——vibe/priority/Lore/relation/LS 一次取齐（三钉组装素材+语境角色定义段+场景帧「我面对的是谁」的关系口径，全节不漂；图料不足报缺口勿编造）

```cypher
MATCH (c:Character) WHERE c.name IN ['陈默','陆择','陈念','沈暮雪','王昊','李想']
OPTIONAL MATCH (c)-[:has_info]->(l:Lore)
WITH c, collect({title:l.title, kl:l.knowledge_level}) AS lores
OPTIONAL MATCH (c)-[r:relation]->(o:Character)
WITH c, lores, collect({other:o.name, type:r.type, st:r.start_time, et:r.end_time}) AS rels
OPTIONAL MATCH (c)-[:has_voice_style]->(ls:LanguageStyle)
RETURN c.name AS who, c.vibe AS vibe, c.priority AS prio, lores, rels, ls.speech_style AS ls
```

**Q3 Event 动态包（每批一次，UNION 归一列式）**——认知集+所在地合并；逐角色「现在知道什么」白名单，兼出 speaker 独有 Info 集（披露审验 hold 表素材）。**hold 表前置**：每批开拍前由 Q3 素材建本批 hold 表——批内每对 (speaker, 听者) × 每条 Info 两条判定线：听者无链 → speaker 不可对其披露该 Info；听者持偏差态（BELIEVES+title）→ speaker 不可说破真相定性（§5 误信态保护）；逐手审验按表执行（v7 实测前置 hold 表全程零违约）。认知编年史：同 (角色,Info) 多条认知（如误信态+揭底态）按上款全量返回——`since` 列即时间线；**信封白名单取拍时刻最新有效态**（多行供 DM 理解认知演变，不聚合）

```cypher
MATCH (c:Character)-[:has_cognition]->(cg:Cognition)-[:about]->(i:Info)
MATCH (ke:Event)-[:forms]->(cg)
WHERE c.name IN ['陈默','沈暮雪','王昊'] AND ke.start_time <= '<本Event末拍时刻>'
RETURN 'cog' AS kind, c.name AS who, i.title AS item, cg.type AS att, coalesce(cg.title,'') AS believed, ke.start_time AS since
UNION
MATCH (c:Character)-[r:at]->(l:Location)
WHERE c.name IN ['陈默','沈暮雪','王昊'] AND (r.start_time <= '<本Event末拍时刻>' OR r.start_time='开篇前')
  AND (r.end_time >= '<本Event末拍时刻>' OR r.end_time='至今')
RETURN 'at' AS kind, c.name AS who, l.name AS item, r.type AS att, '' AS believed, r.start_time AS since
```

**Q4 共同经历 UNWIND（每批一次）**——批内全部所需角色组的交集一条出；`size(ppl)=size(group)` 即交集判定，留在图内（group 列表=本批实际同场的角色组：二人对+全体，k=4 时非空子集至多 11 个；空结果=封闭世界正确答案，不是查询写错）

```cypher
UNWIND [['陈默','沈暮雪'],['陈默','王昊'],['沈暮雪','王昊'],['陈默','沈暮雪','王昊']] AS group
MATCH (c:Character)-[:involved]->(e:Event)
WHERE c.name IN group AND e.start_time < '<本Event首拍时刻>'
WITH group, e, collect(DISTINCT c.name) AS ppl
WHERE size(ppl) = size(group)
RETURN group, e.start_time AS st, e.title AS evt
ORDER BY st
```

每个角色实例只知道自己认知集内的事实；**封闭世界认知，无例外**——无 has_cognition 链=不知道，involved 不推导知情（「参与即知情」已废止）；漏建认知条目=角色被误判无知，发现缺口在汇报中报，不在投放侧补丁；**角色不知道的信息不投、也不允许角色引用**（confabulation 与 improvisation 的分界线：有钉子时的自由发挥是特性，无钉子时的编造是事故）；
- 注入纪律：**注入与语境只写「你知道」清单，禁写「你不知道」负面清单**——封闭世界靠省略表达，认知集没列的即不知道；负面清单反而把事实的存在性泄露给实例（判例：陈念语境「你不知道：他直播走红、加入星耀二队」）；①亲历者各拿各版本的记忆（同一事件，不同角色记得不同侧面）；②**宿主/灵魂归属检查**：宿主入住前形成的认知（has_cognition 链且 forms 锚事件早于入住）与宿主名下 Lore，灵魂没有记忆（陆择的认知集=陆择自己的认知链，不含宿主前史认知）——投前必查入住时间线；③只供事实不供感受；
- 已知局限：注入被角色吸收（气质相容）但未必显式引用；显式唤起需要更强的世界事件触发，待验证。

## 7. 汇编（交付物——跑团草稿.md）

交付稿是**读者向台词草稿**，不是会议实录；落盘 `25_剧本/ch<NN>/sec<MM>/跑团草稿.md`（与 台词.ink 同目录，编号目录）：

- **头部取材指纹块**（fingerprint.py gen `--target tabletop` 产，dialoguer 入场 check 同源自检——圈定与命令见 §9）；
- 每拍以 `## 拍N 标题` + `【场景：地点·时间｜block <scene_block_id>】` 行开头——**block id 即拓扑契约**（= 所写机位的 Scene 节点 id，Q1 现查 `scene_id`；同机位多拍重复用同一 id，dialoguer 据此把拍合并为 ink 场景块，段边界由拍序承载——契约语义同旧小说.md 的 `###` 场景段标题）；
- **DM 旁白 = 写给读者的小说式叙述散文**（场景过渡、环境氛围、时间跳跃桥接），以引用段落织在台词行之间，时序必须正确（返工判例：门铃旁白曾被错排在进门戏之后）；机位、BGM、氛围是汇编阶段的读者向创作，不进角色信封；旁白只在转场和必要桥接处写，不逐手刷屏；
- 台词行 `角色：「line」（action）（内心：…）`；silence 写作「（沉默）」，或并入旁白叙述；
- 文末附内部附录（不属草稿本体，dialoguer 打磨时剥离）：DM 判定逐拍记录 + 量化表（总手/行长中位/silence/inner 占比/作废数，对照前轮）+ 机制发现清单。

## 8. 已知坑（实测）

1. 语音场（电话/连麦）角色会产出面对面动作（「转过椅子正对陈默」）——根治法=场景帧写明各角色所在（at 区间，语音两端不同地），语音场开场帧固定加「你已戴耳机坐定，上一场已结束」（实测复盘首手仍带前场走动动作，该句前移预防）；合同「语音场禁身体朝向对方、禁眼神接触」保留为兜底，DM 接受台词、剔除动作歧义；
2. 真 silence 的触发条件是「在场但非话事中心」的结构位置，硬造不出来；
3. 双开拍帧同时投两个实例会让两人同时出首手——开场帧只投一人，另一人等轮转；
4. 角色自由发挥会改戏的结构（电话→上门、skip→被测试），这是特性不是事故，判完成口径容得住；
5. delegation 结果只在轮次结束回传，工位文件才是实时进度——用 outbox 增量收割，勿等汇报。
6. **拍点动机检查查认知层，不是查散文**（判例：ch02 sec02「她提介绍对象」12 手未演）：Event/SubEvent.description 散文写得再全也进不了信封——三钉组装阶段逐拍点检查该动机在出场角色认知集（Q3 查询结果＋Lore）中有无承载，无承载 → 开拍前报缺口。根因定性＝动机链写错层：该落 Cognition 的事实留在 Event 散文里（存量普查：Info description 空置 21/21，本例拍点事件 forms 认知 0 条）。修复走生产端「事件散文中的角色意图/念头须同步落 Cognition（forms 锚＝来源事件）」（分界契约见 [Schema/剧情/Info.md](../../00_init/Schema/剧情/Info.md)），存量走建议链补认知后重跑；勿指望角色自发，勿现场导演补救。另：时间压力型递球只催出既有最要紧项，催不开新话题——私议程话题往往连对端钩子也不存在。
7. **涌现披露制造图外知情者**（判例：拍1 陈默被「游戏打多久」逼急，即兴抛出「星耀电竞二队要了我，今天上午签约」，陈念当场知情——图上该 Info 五个知情者无陈念、08:30 事件 establishes 全空）：根因=披露行为原本无治理，存量认知+自由发挥随时可说出口。已裁决：认知层只读，披露审验进 §5 逐手审验（唯一可指认即拦、违约退回重演）；漏建披露上报设计端补图（编年史下＝追加 Cognition 条目，forms 锚该场次事件），勿现场补救。
8. **任务口径断线 → 误信提前揭底**（判例：批1 图上 Event 写「以家庭聚餐为名约出门」，信封任务段却写成「把替他安排好的事说出口」——陈念实例按摊牌口径+自身 KNOWS 直说「那是相亲！」，陈默误信态当场被炸，而批2-4 信封照编年史仍投「你当它是家庭聚餐」，演出与图正面冲突）：根因=隐瞒/谎称类意图只活在 Event description 里、没进信封任务段——**角色意图不进信封=对角色不存在**。双闸修复：场景帧「我要干什么」口径继承（§3）+ 披露审验误信态保护（§5）；清单式核对=开拍前把拍点依据里的意图动词（瞒/谎称/试探/摊牌）逐个过一遍任务段。
9. **对手信息段位错置**（判例：批4 王昊信封「中单李想是你老队友」塞进「之前」段，而共同经历查询该对为空——「老队友」的真实依据是 Lore 同队身份而非共同事件）：根因=「与对手的关系」无正式信封位，DM 只能往「之前」段塞。修复=场景帧第六要素「我面对的是谁」（§3）；对手形象不进信封（AppearanceStyle 在参考图流程下不保证填写，不可作事实源），外貌感知归 DM 旁白。
10. **当事人自我事实无认知链**（判例：陈默不在「首播走红/美杜莎录像/技术顶尖/江烈冲突/加入二队」五条 Info 的知情者名单中——封闭世界字面下他不知道自己走红）：Q3 白名单不含当事人的自我事实，实测靠 Q4 共同经历+场景帧偶然补位未穿帮，但非共同经历的自我的事（如上头条）任何通路都够不着。发现此类缺口报设计端补链（forms 锚各自事件），勿在投放侧补丁。
11. **拍点披露与认知层矛盾**（判例：拍3「沈暮雪亮目标」三个相容窗口均未演到，被误归因为「钉子/LS 触发权重不足」，真因=听者陈默对「沈暮雪的目标」无认知链——宣言句演到即违反披露审验，角色和 DM 双方都被认知层正确地拦住了）：修复=开拍前拍点披露预检（§5），缺口报设计端补链或改拍点；此类「演不到」先查认知层再谈钉子权重，与坑6「先查图再断言认知缺口」同源。

## 9. 指纹圈定与落盘契约（跑团草稿.md 的素材自检）

跑团草稿头部取材指纹与 chapter-dialoguer 入场自检**同源同契约**（fingerprint.py 生成与自检一套脚本杜绝双入口不一致；素材 JSON 形状是机器契约——与旧小说链共用）。汇编落盘前两步：

```bash
# 1) 圈定素材（一条 UNION，输出即素材 JSON；<本节末> 现场替换为节最末成员事件 end_time）
python .claude/scripts/cypher_exec.py -c "<下述圈定查询>" --json > .tmp/novelist/<sec_id>_materials.json
# 2) 指纹头生成（--ids 只圈实际取用的素材子集，info/lore 可带强度后缀 id:E/id:S；产出置于草稿首）
python .claude/scripts/fingerprint.py gen --in .tmp/novelist/<sec_id>_materials.json --ids <id[,id:S…]> --at <chNN/secMM> --target tabletop
```

圈定查询（机器契约：**显式字段罗列 + null 对齐**，fingerprint.py 按行形状 kind/id/title/… 解析，不做整节点直返；Event 沿 includes 直连成员；**Info** 走本节 involved 角色认知集内事件性事实——含 `relation{type:控制}` 控制跳（控制者认知流入宿主），`ke.start_time ≤ 本节末`（forms 锚）防未来认知剧透；**Lore** 走本节 involved 角色 has_info 固有设定，含同款控制跳）：

```cypher
MATCH (sec:Section {id:'<sec_id>'})-[:includes]->(e:Event)
RETURN 'event' AS kind, e.id AS id, e.title AS title, e.start_time AS start_time, e.type AS type,
       e.description AS description, e.ending_kind AS ending_kind, e.condition AS condition,
       null AS content, null AS knowledge_level
UNION
MATCH (sec:Section {id:'<sec_id>'})-[:includes]->(e2:Event)
MATCH (src:Character)-[:has_cognition]->(cg:Cognition)-[:about]->(i:Info)
MATCH (ke:Event)-[:forms]->(cg)
WHERE ((src)-[:involved]->(e2)
       OR (src)-[:relation {type:'控制'}]->(:Character)-[:involved]->(e2))
  AND ke.start_time <= '<本节最末成员事件的 end_time，现场替换>'
RETURN DISTINCT 'info' AS kind, i.id AS id, i.title AS title, null AS start_time, null AS type,
       null AS description, null AS ending_kind, null AS condition,
       i.content AS content, i.knowledge_level AS knowledge_level
UNION
MATCH (sec:Section {id:'<sec_id>'})-[:includes]->(e2:Event)
MATCH (src:Character)-[:has_info]->(l:Lore)
WHERE (src)-[:involved]->(e2)
   OR (src)-[:relation {type:'控制'}]->(:Character)-[:involved]->(e2)
RETURN DISTINCT 'lore' AS kind, l.id AS id, l.title AS title, null AS start_time, null AS type,
       null AS description, null AS ending_kind, null AS condition,
       l.content AS content, l.knowledge_level AS knowledge_level
```

- **freshness 裁量（DM 旁白专用）**：圈定含 info/lore 行时跑 `fingerprint.py freshness --in … --at <chNN/secMM> --root 25_剧本`，按 `allow` 档位（explicit 正面/侧面均可、side 只可侧面折射、blocked 禁释放）裁量 **DM 旁白与读者向细节**的信息释放；角色台词不受此限（认知投放按 §3 白名单，角色重复提自己知道的事是真实感的一部分）。
- **stale 语义**：草稿头部指纹与当前图素材不一致（dialoguer 侧 `fingerprint.py check` exit 1）→ dialoguer 停止报 stale，回退本 skill 重跑（重跑覆盖旧草稿；该节定稿链作废由 plot-design 编排触发，本 skill 零图写入不变）。
