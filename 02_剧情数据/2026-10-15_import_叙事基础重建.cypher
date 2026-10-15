// ═══ 叙事基础重建 2026-10-15 ═══
// 依据：02_剧情数据/2026-10-15_25_剧本ink_关系提取.md（人工审阅版）
// 决策：E5 起穿越后事件 involved 只挂宿主陈默；evt_relation 按新时间序重建；
//       wears/anchored_at 按旧→新映射回迁，E18 例外改连 林梦-居家慵懒着装
// 执行：python .claude/scripts/cypher_exec.py -f <本文件> --multi

// ── 0. 删除旧数据（用户已备份；DETACH 清掉 involved/occurs_at/link/leads_to/evt_relation/presents/option/wears/anchored_at）──
MATCH (n:Info) DETACH DELETE n;
MATCH (n:Choice) DETACH DELETE n;
MATCH (n:Event) DETACH DELETE n;

// ── 1. Event 节点 ×30（E6 为 BE 分支）──
UNWIND [
  {id:'RGcLQijx32', title:'陆择酒店醒来与顾盈道别', time:'2024-05-31 06:00:00', type:'交流', description:'开场=锚点−1天清晨；一夜情后道别，顾盈推荐街角咖啡店，陆择婉拒加微信，当天 10 点飞机'},
  {id:'RGcLQijx33', title:'陆择街角咖啡店买美式问大巴', time:'2024-05-31 06:00:00', type:'交流', description:'紧接酒店道别；牛奶未备好改美式，小夏告知机场大巴街对面 20 分钟一趟'},
  {id:'RGcLQijx34', title:'陆择被摩托车撞飞身亡', time:'2024-05-31 12:00:00', type:'转折', description:'路口人行横道抢行，被闯红灯摩托车撞飞，后脑着地，送医途中身亡'},
  {id:'RGcLQijx35', title:'伊芙宣判陆择下地狱并布置试炼', time:'2024-05-31 18:00:00', type:'转折', description:'灵魂夹缝；罪名伤害众多女孩感情；试炼=用特长拯救 6 个弱者、以其身份生活 30 天；结尾灵魂被吸入漩涡'},
  {id:'RGcLQijx36', title:'陈默跳江之夜陆择灵魂入体', time:'2024-06-01 22:00:00', type:'转折', description:'锚点时刻 Day 0；长江大桥护栏外侧；Choice 分叉：跳下去→BE／再想想→主线；翻回栏杆意识到身处他人身体'},
  {id:'RGcLQijx37', title:'陈默跳江身亡', time:'2024-06-01 22:00:00', type:'状态变化', description:'仅「跳下去」BE 分支；次日桥面摆满陌生人自发买来的奶茶和外卖', ending_kind:'BE'},
  {id:'RGcLQijx38', title:'陆择翻回栏杆接陈念来电', time:'2024-06-01 23:00:00', type:'交流', description:'陈念因留言警觉深夜来电；约定次日上门探望'},
  {id:'RGcLQijx39', title:'陆择翻转账记录删温蔓青联系方式', time:'2024-06-01 23:00:00', type:'行动', description:'回屋后翻手机：累计转账 66666 零回复；按下删除头像'},
  {id:'RGcLQijx3A', title:'陈念上门探望塞冰箱炖汤数落', time:'2024-06-02 09:00:00', type:'行动', description:'Day 1；两大袋菜塞满冰箱、炖排骨汤、检查燃气三遍、话痨式唠叨一小时+'},
  {id:'RGcLQijx3B', title:'陆择借陈默身份向陈念打听过去', time:'2024-06-02 09:00:00', type:'交流', description:'炖汤间隙问「姐，我以前……怎么样」；陈念讲述拼命代练、钱全给女人的过去'},
  {id:'RGcLQijx3C', title:'陈念临走碗底压现金三千叮嘱自爱', time:'2024-06-02 12:00:00', type:'行动', description:'压钱动作快得像做贼；「人首先要自爱」；脚步声下到半层停了停'},
  {id:'RGcLQijx3D', title:'陈默理发改造形象', time:'2024-06-03 09:00:00', type:'行动', description:'Day 2；从分手开始未打理；Tony 铲青打薄，承诺下月免费造型「看你重新开始」'},
  {id:'RGcLQijx3E', title:'陈默服装店置装花 680', time:'2024-06-03 09:00:00', type:'行动', description:'紧接理发；季棠搭配浅灰衬衫+深色直筒；休闲+运动两套刷卡 680；「最近想重新开始了」'},
  {id:'RGcLQijx3F', title:'陆择盘点陈默家底与到期订单', time:'2024-06-03 15:00:00', type:'行动', description:'余额 86.2；两单待交付一单次日到期；群规超时赔三倍踢群；「生存压力第一次有了形状」'},
  {id:'RGcLQijx3G', title:'陈默当晚上线完成代练单技惊四座', time:'2024-06-03 20:00:00', type:'行动', description:'前五分钟生涩→第六分钟肌肉记忆接管；35 分钟胜利结算；客户加钱再来一单；群友（林梦）惊呼「老陈你活的？」'},
  {id:'RGcLQijx3H', title:'林梦语音陪玩单美杜莎翻盘局', time:'2024-06-04 15:00:00', type:'行动', description:'Day 3；渡劫局 12 分送头、21 分跳刀、34 分卖鞋买圣剑开大暴走翻盘；赢后林梦聊半小时八卦，「你今天声音听起来精神多了」'},
  {id:'RGcLQijx3I', title:'陈默南滨路晨跑搭讪苏晓禾被教跑姿婉拒', time:'2024-06-05 06:30:00', type:'交流', description:'Day 4 清晨六点半；苏晓禾主动纠正跑姿四条；加微信被「老土的搭讪套路。下次吧」婉拒；并肩跑两百米'},
  {id:'RGcLQijx3J', title:'林梦午间来电报头条并投资 8600', time:'2024-06-06 12:00:00', type:'交流', description:'Day 5 厨房餐区吃饺子时；三分钟剪辑登游戏区头条；「本小姐投资你……十倍还我」；安排上门装机'},
  {id:'RGcLQijx3K', title:'陆择算人生账收拾屋子定三闹钟', time:'2024-06-06 18:00:00', type:'状态变化', description:'放弃追讨 66666；清外卖盒旧快递盒；定 6:30/6:40/6:50 三闹钟为再遇晨跑姑娘'},
  {id:'RGcLQijx3L', title:'陈默第三闹钟响出门晨跑采购', time:'2024-06-07 06:50:00', type:'行动', description:'Day 6；沿江溜达三公里；顺路买鸡蛋青菜（冰箱饺子吃完）'},
  {id:'RGcLQijx3M', title:'新设备到货上门装机调试', time:'2024-06-07 12:00:00', type:'行动', description:'林梦投资落地；中午到货调试至晚餐；晚餐自己下面卧蛋'},
  {id:'RGcLQijx3N', title:'陈默直播首秀峰值一万二', time:'2024-06-07 20:00:00', type:'行动', description:'开播十分钟六百人循头条而来；两小时峰值 12000；播三个多小时；弹幕「技术流主播」'},
  {id:'RGcLQijx3O', title:'沈暮雪私信邀约试训', time:'2024-06-07 23:00:00', type:'交流', description:'下播后平台私信；自介星耀电竞战队经理；「没有寒暄，没有客套」；约次日 15:00 电话联系'},
  {id:'RGcLQijx3P', title:'沈暮雪基地门口接陈默介绍流程', time:'2024-06-08 14:50:00', type:'交流', description:'Day 7 提前十分钟到；两轮制：五局 solo + 一局训练赛（江烈亲自下场）'},
  {id:'RGcLQijx3Q', title:'陈默试训五局 solo 全胜', time:'2024-06-08 15:00:00', type:'行动', description:'个人环节碾压；第三局后队员凑一起小声嘀咕'},
  {id:'RGcLQijx3R', title:'训练赛陈默顶撞江烈冲突中止', time:'2024-06-08 15:00:00', type:'转折', description:'一号位野区刷钱不参团不救五号位；顶撞「你当你是谁啊」；江烈「今天到此为止。回去等通知」'},
  {id:'RGcLQijx3S', title:'沈暮雪送行自承「考虑不周」', time:'2024-06-08 15:00:00', type:'交流', description:'「其实他说得有道理，比赛是五个人的」「今天的事，是我考虑不周」——与 E29 微信首句呼应'},
  {id:'RGcLQijx3T', title:'苏晓禾放慢半拍陪跑约后天见', time:'2024-06-09 06:00:00', type:'交流', description:'Day 8；跑姿已按四条改获确认；全程无话四公里、脚步声叠成同一节奏；「明天有雨，后天见」'},
  {id:'RGcLQijx3U', title:'沈暮雪微信致歉并约面谈', time:'2024-06-10 09:00:00', type:'交流', description:'Day 9 刚起床；「试训的事，是我考虑不周。但我依然觉得你很有潜力」；约翌日下午三点咖啡店'},
  {id:'RGcLQijx3V', title:'沈暮雪咖啡店面邀加入星耀二队', time:'2024-06-11 15:00:00', type:'交流', description:'Day 10；条件=训练表定下后不许迟到不接凌晨单；底薪+奖金；试用期按代练价、两月后签合同；陈默答应；加糖咖啡「天赋很高，别浪费了」'}
] AS row CREATE (e:Event) SET e = row;

// ── 2. Info 节点 ×80（事实层 kl=1 / 推断层 kl=3；content=依据原文或推理链）──
UNWIND [
  {id:'RGcLQijx3W', title:'陆择与顾盈发生一夜情', content:'sec00「昨夜的酒气还没散透」「昨晚你还挺厉害的」', knowledge_level:1},
  {id:'RGcLQijx3X', title:'陆择当天要赶 10 点的飞机离开', content:'sec00「等下还要赶飞机」「10点的飞机」', knowledge_level:1},
  {id:'RGcLQijx3Y', title:'顾盈向陆择推荐街角咖啡店', content:'sec00「街角有一家，拿铁还不错」', knowledge_level:1},
  {id:'RGcLQijx3Z', title:'陆择婉拒与顾盈加微信', content:'sec00「还是别了……我怕床受不了」', knowledge_level:1},
  {id:'RGcLQijx3a', title:'陆择被闯红灯摩托车撞倒送医途中身亡', content:'sec02 伊芙：「你被一辆闯红灯的摩托车撞倒，在送去医院的路上就没了呼吸」', knowledge_level:1},
  {id:'RGcLQijx3b', title:'伊芙自称天使持羊皮纸主持审判', content:'sec02「按你们凡间的说法，算是天使吧」「伊芙掏出了一张羊皮纸」', knowledge_level:1},
  {id:'RGcLQijx3c', title:'陆择被判下地狱罪名「伤害众多女孩感情」', content:'sec02「这上面写着：因为伤害众多女孩感情」', knowledge_level:1},
  {id:'RGcLQijx3d', title:'审判庭换了新审判官尺度收紧', content:'sec02「以前倒是还好，但是现在审判庭换了一个姐姐」', knowledge_level:1},
  {id:'RGcLQijx3e', title:'试炼条款：拯救 6 个弱者以其身份生活 30 天', content:'sec02「你的灵魂会穿越到弱者的身上，进入他的身体，以他的身份替他生活30天」', knowledge_level:1},
  {id:'RGcLQijx3f', title:'弱者定义：认真待感情却伤痕累累的人', content:'sec02「那些认真对待了感情，结果却落得伤痕累累的人」', knowledge_level:1},
  {id:'RGcLQijx3g', title:'陈默出事当晚曾给陈念留言', content:'sec00「刚才你给我的留言是什么意思，你老实交代，是不是出事了」', knowledge_level:1},
  {id:'RGcLQijx3h', title:'陈念是陈默的姐姐', content:'sec00 来电显示「姐姐」+陈念全段口吻', knowledge_level:1},
  {id:'RGcLQijx3i', title:'陈默累计转账温蔓青 66666 元对方零回复', content:'sec00「几百的，一千的，最大一笔一万……加起来，六万六千六百六十六。对方一条消息都没回过」', knowledge_level:1},
  {id:'RGcLQijx3j', title:'陆择删除了陈默手机里温蔓青的联系方式', content:'sec00「他的手指停在那个头像上，按下了删除」', knowledge_level:1},
  {id:'RGcLQijx3k', title:'温蔓青与陈默处对象两年从未登陈家门', content:'sec01「处了两年，她进过咱家一次门没有？过年妈喊她来吃饭，她说票不好买」', knowledge_level:1},
  {id:'RGcLQijx3l', title:'陈默两年一件外套穿两冬、钱全转温蔓青', content:'sec01「一件外套穿两个冬天，她倒好，包换得比手机壳还勤。图什么？图你会转钱！」', knowledge_level:1},
  {id:'RGcLQijx3m', title:'陈默童年被父亲罚站屋外不哭委屈自憋', content:'sec01 陈念口述「你爸罚你，你一声不吭站屋外，站到腿麻也不哭，还得是我去把你拉回来」', knowledge_level:1},
  {id:'RGcLQijx3n', title:'陈默以前拼命代练钱全给女人熬夜黑白颠倒', content:'sec01「一睁眼就是接单，饭都不好好吃……赚了钱干什么？全给了女人，自己啥都不留」', knowledge_level:1},
  {id:'RGcLQijx3o', title:'陈默冰箱空空长期外卖度日', content:'sec01「陈默！你冰箱里连根葱都没有！你天天吃什么？外卖？」', knowledge_level:1},
  {id:'RGcLQijx3p', title:'陈念临走在碗底压现金三千', content:'sec01「往碗底压了一沓现金，动作快得像做贼」+sec05「手头只有压在碗底的现金：三千」', knowledge_level:1},
  {id:'RGcLQijx3q', title:'接单群纪律：超时赔三倍踢群、警告两次移出通报', content:'sec02「接单不交付，赔三倍，踢出群」+群公告「交付超时=警告一次，警告两次=移出+全平台通报」', knowledge_level:1},
  {id:'RGcLQijx3r', title:'陈默余额 86.2 元、两单待交付一单次日到期', content:'sec02「两单待交付，一单明天到期。到期不交，三倍赔偿。他的余额是八十六块二」', knowledge_level:1},
  {id:'RGcLQijx3s', title:'陈默的手感是几千个夜晚熬出的肌肉记忆', content:'sec02「那不是他的技术。那是陈默熬夜熬出来的几千个夜晚，还寄居在这双手里」', knowledge_level:1},
  {id:'RGcLQijx3t', title:'陆择把任务理解为帮陈默找个女朋友', content:'sec02「拯救弱者四个字，他自行理解成了帮陈默找个漂亮女朋友。毕竟他自己最擅长的就是这个」', knowledge_level:1},
  {id:'RGcLQijx3u', title:'陈默分手后长期没打理自己', content:'sec02 Tony「你这头发……你多久没打理过自己了」+陈默「大概……从分手开始」', knowledge_level:1},
  {id:'RGcLQijx3v', title:'林梦的单是语音陪玩价高三成、两月惯例「不动号」', content:'sec03「陪玩，带语音。价格比普通代练单高三成」「不要动我号，就在我自己号上带我打」；林梦称「雇佣关系里唯一有人情味的一种」', knowledge_level:1},
  {id:'RGcLQijx3w', title:'陈默上次给林梦打得极差', content:'sec03「上次坑了我……十分钟挂机，二十分钟开送」', knowledge_level:1},
  {id:'RGcLQijx3x', title:'陈默自述「之前的我不太想活，现在想通了」', content:'sec03 语音原话「之前的我不太想活，现在想通了」', knowledge_level:1},
  {id:'RGcLQijx3y', title:'星耀一队队员与经理吵翻出走、一号位开天窗', content:'sec03 林梦八卦「星耀那个一队，有个队员跟经理吵翻了，拎着背包自顾自的跑了，下个比赛一号位估计得开天窗」', knowledge_level:1},
  {id:'RGcLQijx3z', title:'一队经理为女性三十不到、圈里称雪姐', content:'sec03「那经理是谁吗，女的，三十不到，据说很漂亮，圈里都叫她雪姐」', knowledge_level:1},
  {id:'RGcLQijx40', title:'某主播直播间哭事件掉 5 万粉', content:'sec03「上周直播间哭那事你看了没有？直接掉了5万粉！」', knowledge_level:1},
  {id:'RGcLQj1YB6', title:'美杜莎盘录像将被剪成视频并引起一人关注', content:'sec03 旁白「他不知道的是，这一盘的录像即将被人剪成视频，并引起了一个人的关注」', knowledge_level:1},
  {id:'RGcLQj1YB7', title:'林梦为跳刀道歉并说「你今天声音听起来精神多了」', content:'sec03「跳刀那件事，我错怪你了」「你今天声音听起来，精神多了」', knowledge_level:1},
  {id:'RGcLQj1YB8', title:'苏晓禾的跑姿四条口诀', content:'sec04「重心提起来……脚掌落地，肩膀沉下去，步频提上去，步幅收回来」', knowledge_level:1},
  {id:'RGcLQj1YB9', title:'苏晓禾婉拒加微信留「下次吧」余地', content:'sec04「老土的搭讪套路。下次吧，你自己再适应一下，我走啦拜拜」', knowledge_level:1},
  {id:'RGcLQj1YBA', title:'林梦剪的三分钟美杜莎视频登游戏区头条', content:'sec05「游戏区头条就是前天你那盘美杜莎……三分钟全是精华，跳刀圣剑暴走一秒没浪费」', knowledge_level:1},
  {id:'RGcLQj1YBB', title:'林梦出资 8600 设备款约定红了十倍偿还', content:'sec05「设备升级，钱我出」「本小姐投资你。等你以后红了，十倍还我」', knowledge_level:1},
  {id:'RGcLQj1YBC', title:'陈默经济账：平台抽两成、房租 1800 季付、现金 3000', content:'sec05「代练收入一单几十到几百，平台还抽两成。房租一千八，按季付」「压在碗底的现金：三千」', knowledge_level:1},
  {id:'RGcLQj1YBD', title:'陆择决定不向温蔓青追讨 66666', content:'sec05「要回来的话，得撕破脸……算了，送出去的钱如同泼出去的水」', knowledge_level:1},
  {id:'RGcLQj1YBE', title:'陆择定三闹钟为再遇晨跑姑娘', content:'sec05「收拾完，他给自己定了三个闹钟……想着明天晨跑再偶遇到那个有趣的姑娘」', knowledge_level:1},
  {id:'RGcLQj1YBF', title:'首播十分钟涌入六百人、两小时峰值 12000', content:'sec06「开播十分钟，直播间涌进来六百人——不少是循着那条头条视频摸进来的。两个小时后，峰值停在了一万二」', knowledge_level:1},
  {id:'RGcLQj1YBG', title:'直播不露脸、弹幕称声音好听技术强', content:'sec06 弹幕「主播声音好好听，技术还贼强」「不露脸好，技术流主播！」', knowledge_level:1},
  {id:'RGcLQj1YBH', title:'沈暮雪自介星耀经理、私信邀试训约次日 15:00', content:'sec06「你好，我是星耀电竞战队经理沈暮雪……有兴趣来我们战队试试吗？」「明天下午三点，打这个号码联系」', knowledge_level:1},
  {id:'RGcLQj1YBI', title:'江烈是星耀队长兼试训主考官', content:'sec07「江烈？——队长，也是你今天的主考官」', knowledge_level:1},
  {id:'RGcLQj1YBJ', title:'试训两轮制：五局 solo + 一局训练赛', content:'sec07「试训分两轮。第一轮个人，五局solo。第二轮跟队伍一起打一局训练赛，江烈亲自下场」', knowledge_level:1},
  {id:'RGcLQj1YBK', title:'试训冲突经过：一号位刷钱不救人顶撞江烈后被中止', content:'sec07「中路准备打团，你还在野区刷钱」「你当你是谁啊，在这指指点点的」「今天到此为止。回去等通知」', knowledge_level:1},
  {id:'RGcLQj1YBL', title:'沈暮雪表态「比赛是五个人的」「考虑不周」', content:'sec07「其实他说得有道理，比赛是五个人的」「今天的事，是我考虑不周」', knowledge_level:1},
  {id:'RGcLQj1YBM', title:'陈默把跑姿四条编成口诀无人盯也照练', content:'sec08「你不是给了四条嘛……我编成了口诀，跑步的时候在心里背」', knowledge_level:1},
  {id:'RGcLQj1YBN', title:'苏晓禾放慢半拍陪跑四公里约「后天见」', content:'sec08「她把配速放慢了半拍……刚好跟在他侧后方，陪他跑完了剩下的四公里」「明天有雨，后天见」', knowledge_level:1},
  {id:'RGcLQj1YBO', title:'苏晓禾确认他说「后天见」没用套路且记到了晚上', content:'sec08「这人说后天见的时候，没有用任何套路……这句最普通的，她记到了晚上」', knowledge_level:1},
  {id:'RGcLQj1YBP', title:'星耀新组二队：前两月线上训练、效果不好随时散伙', content:'sec09「新组建的。基地还在装修，前两个月线上训练，效果不好随时散伙」', knowledge_level:1},
  {id:'RGcLQj1YBQ', title:'二队条款：不许迟到不接凌晨单、底薪+奖金、试用两月后签合同', content:'sec09「训练表一旦定下，不许迟到、不许再接单到凌晨，有事得提前请假」「底薪加赛绩奖金」「合同等两个月之后签，现在算试用期，先按你代练的价格来算」', knowledge_level:1},
  {id:'RGcLQj1YBR', title:'沈暮雪顶着江烈的看法坚持邀约', content:'sec09「江烈对我有看法。——你试训的表现，对你有看法很正常。但这毕竟是新的队伍，他的看法没那么重要」', knowledge_level:1},
  {id:'RGcLQj1YBS', title:'沈暮雪不说明挖人原因', content:'sec09「那为什么顶着他挖我？——等你值得得到答案的时候，我自然会告诉你」', knowledge_level:1},
  {id:'RGcLQj1YBT', title:'沈暮雪替陈默咖啡加糖、临别「天赋很高别浪费了」', content:'sec09「端起来喝了一口，她细心的帮他加了糖，甜度刚好」「你天赋很高，别浪费了」', knowledge_level:1},
  {id:'RGcLQj1YBU', title:'陆择情场老手嘴甜会撩', content:'推理链：E1 台词「都好看，各有各的韵味」「嘴可真甜呀」→ 惯于应付女性、话术娴熟', knowledge_level:3},
  {id:'RGcLQj1YBV', title:'陆择一夜情不留联系及时止损', content:'推理链：I4 婉拒加微信 + E1「下次我怕床受不了」→ 不纠缠不承诺的行为模式', knowledge_level:3},
  {id:'RGcLQj1YBW', title:'伊芙业务生疏流程仓促', content:'推理链：E4「我看看接下来的流程」翻羊皮纸 +「糟糕要来不及了」→ 新手天使、流程仓促', knowledge_level:3},
  {id:'RGcLQj1YBX', title:'陆择生前情史劣迹斑斑', content:'推理链：I7 罪名伤害众多女孩感情 + I8 换审判官后判罪 → 渣男生前定性', knowledge_level:3},
  {id:'RGcLQj1YBY', title:'陆择孤独无亲辞世无人收尸', content:'推理链：E10 旁白「他陆择习惯了孤身一人，辞世的时候，怕是连个来收尸的人都没有」→ 孤家寡人背景', knowledge_level:3},
  {id:'RGcLQj1YBZ', title:'陈念刀子嘴豆腐心以唠叨投喂表达爱', content:'推理链：E9-E11 行为链（数落+塞冰箱+炖汤+压钱）→ 关爱以唠叨与投喂表达', knowledge_level:3},
  {id:'RGcLQj1YBa', title:'温蔓青对陈默无真心、索取型恋爱', content:'推理链：I15 两年不登门 + I16 只进不出勤换包 → 感情剥削', knowledge_level:3},
  {id:'RGcLQj1YBb', title:'陈默恋爱脑、账上自己永远排最后', content:'推理链：I13 饭钱八块转账六万六 + E19 旁白「这个人的账上，自己永远排在最后」→ 自我贬抑式付出', knowledge_level:3},
  {id:'RGcLQj1YBc', title:'陈默分手后陷入抑郁性自我忽视', content:'推理链：I25 分手后不打理 + I22 挂单六天 + I28 不想活 → 抑郁状态', knowledge_level:3},
  {id:'RGcLQj1YBd', title:'陈默恋爱失败后曾有轻生倾向', content:'推理链：I28「之前的我不太想活」+ E5 跳江 → 求死动机成立', knowledge_level:3},
  {id:'RGcLQj1YBe', title:'陆择第一步策略是改造宿主形象', content:'推理链：E12 理发 + E13 置装 + E14 旁白「第一步，先让自己像个人样」→ 为搭讪目标铺路', knowledge_level:3},
  {id:'RGcLQj1YBf', title:'Tony 善良有人情味', content:'推理链：E12「下个月我给你做个造型，不收费。就当……看你重新开始」→ 职业之外善意', knowledge_level:3},
  {id:'RGcLQj1YBg', title:'季棠专业懂行', content:'推理链：E13「你这种需求的，穿深色，人比衣服精神，才是真精神」→ 穿搭判断专业', knowledge_level:3},
  {id:'RGcLQj1YBh', title:'林梦孤独、把陪玩当陪伴', content:'推理链：E16 自顾自聊半小时八卦 + 旁白「她哪是有话说，就是不想下线」→ 寻求陪伴', knowledge_level:3},
  {id:'RGcLQj1YBi', title:'林梦家境优渥', content:'推理链：E18 出 8600 眼不眨「钱我出」+ 自称「本小姐」→ 经济从容', knowledge_level:3},
  {id:'RGcLQj1YBj', title:'苏晓禾性格爽利、拒绝不伤人', content:'推理链：E17「笑着，语气轻快，像躲开一张递过来的传单」→ 善意边界感', knowledge_level:3},
  {id:'RGcLQj1YBk', title:'陆择开始为陈默的人生负责', content:'推理链：E19 算人生账+收拾屋子+定闹钟 +「算的是陈默的人生账」→ 从借住者到经营者转变', knowledge_level:3},
  {id:'RGcLQj1YBl', title:'陆择借宿主身体走红心存酸涩', content:'推理链：E22 对黑屏发呆 +「这双手的主人，熬了那么多个夜晚，从没被这么多人这么关注过」→ 身份愧疚', knowledge_level:3},
  {id:'RGcLQj1YBm', title:'江烈团队至上、治队强势', content:'推理链：E26 冲突言行「五号位来得及吗」+ I47「比赛是五个人的」→ 理念与作风', knowledge_level:3},
  {id:'RGcLQj1YBn', title:'沈暮雪用人自主果断、事后自我复盘', content:'推理链：E23-E30 顶住江烈意见挖人 + 两次「考虑不周」→ 管理风格', knowledge_level:3},
  {id:'RGcLQj1YBo', title:'试训首秀以失败悬置', content:'推理链：E26「回去等通知」无下文 + E29 次日致歉挽回 → 首轮未通过但关系未断', knowledge_level:3},
  {id:'RGcLQj1YBp', title:'苏晓禾对陈默渐生好感与在意', content:'推理链：E28 主动放慢半拍陪跑 + I50「这句最普通的，她记到了晚上」→ 情感萌芽', knowledge_level:3},
  {id:'RGcLQj1YBq', title:'陈默与苏晓禾进入无言默契期', content:'推理链：E28「两副脚步声，一前一后，慢慢叠成了同一个节奏」→ 关系进展', knowledge_level:3},
  {id:'RGcLQj1YBr', title:'沈暮雪观察细致体贴', content:'推理链：I55 记得替他加糖、甜度刚好 → 细节洞察力', knowledge_level:3},
  {id:'RGcLQj1YBs', title:'星耀一队正处于动荡期', content:'推理链：I29 队员与经理吵翻出走、一号位开天窗 → 组织危机，为二队组建背景', knowledge_level:3}
] AS row CREATE (i:Info) SET i = row;

// ── 3. Choice 节点 ×1 ──
CREATE (ch:Choice {id:'RGcLQj1YBt', name:'跳江选择', description:'陈默身·陆择魂深夜立于长江大桥护栏外侧，意识到身处他人身体后的抉择：跳下去即 BE（次日桥面摆满奶茶外卖祭奠），再想想则翻回栏杆进入主线', time:'2024-06-01 22:00:00'});

// ── 4. involved ×55（决策：E5 穿越起陆择一律不挂，只挂宿主陈默+配角）──
UNWIND [
  {e:'RGcLQijx32', c:'陆择', r:'当事人'}, {e:'RGcLQijx32', c:'顾盈', r:'当事人'},
  {e:'RGcLQijx33', c:'陆择', r:'当事人'}, {e:'RGcLQijx33', c:'小夏', r:'店员'},
  {e:'RGcLQijx34', c:'陆择', r:'受害者'},
  {e:'RGcLQijx35', c:'陆择', r:'受审者'}, {e:'RGcLQijx35', c:'伊芙', r:'审判者'},
  {e:'RGcLQijx36', c:'陈默', r:'当事人'},
  {e:'RGcLQijx37', c:'陈默', r:'当事人'},
  {e:'RGcLQijx38', c:'陈默', r:'当事人'}, {e:'RGcLQijx38', c:'陈念', r:'当事人'},
  {e:'RGcLQijx39', c:'陈默', r:'当事人'},
  {e:'RGcLQijx3A', c:'陈默', r:'当事人'}, {e:'RGcLQijx3A', c:'陈念', r:'当事人'},
  {e:'RGcLQijx3B', c:'陈默', r:'当事人'}, {e:'RGcLQijx3B', c:'陈念', r:'当事人'},
  {e:'RGcLQijx3C', c:'陈默', r:'当事人'}, {e:'RGcLQijx3C', c:'陈念', r:'当事人'},
  {e:'RGcLQijx3D', c:'陈默', r:'当事人'}, {e:'RGcLQijx3D', c:'Tony', r:'理发师'},
  {e:'RGcLQijx3E', c:'陈默', r:'当事人'}, {e:'RGcLQijx3E', c:'季棠', r:'店员'},
  {e:'RGcLQijx3F', c:'陈默', r:'当事人'},
  {e:'RGcLQijx3G', c:'陈默', r:'当事人'}, {e:'RGcLQijx3G', c:'林梦', r:'群内围观'},
  {e:'RGcLQijx3H', c:'陈默', r:'当事人'}, {e:'RGcLQijx3H', c:'林梦', r:'雇主'},
  {e:'RGcLQijx3I', c:'陈默', r:'当事人'}, {e:'RGcLQijx3I', c:'苏晓禾', r:'当事人'},
  {e:'RGcLQijx3J', c:'陈默', r:'当事人'}, {e:'RGcLQijx3J', c:'林梦', r:'当事人'},
  {e:'RGcLQijx3K', c:'陈默', r:'当事人'},
  {e:'RGcLQijx3L', c:'陈默', r:'当事人'},
  {e:'RGcLQijx3M', c:'陈默', r:'当事人'},
  {e:'RGcLQijx3N', c:'陈默', r:'当事人'},
  {e:'RGcLQijx3O', c:'陈默', r:'当事人'}, {e:'RGcLQijx3O', c:'沈暮雪', r:'当事人'},
  {e:'RGcLQijx3P', c:'陈默', r:'当事人'}, {e:'RGcLQijx3P', c:'沈暮雪', r:'当事人'},
  {e:'RGcLQijx3Q', c:'陈默', r:'当事人'}, {e:'RGcLQijx3Q', c:'江烈', r:'主考官'}, {e:'RGcLQijx3Q', c:'沈暮雪', r:'旁观'},
  {e:'RGcLQijx3R', c:'陈默', r:'当事人'}, {e:'RGcLQijx3R', c:'江烈', r:'当事人'}, {e:'RGcLQijx3R', c:'沈暮雪', r:'旁观'},
  {e:'RGcLQijx3S', c:'陈默', r:'当事人'}, {e:'RGcLQijx3S', c:'沈暮雪', r:'当事人'},
  {e:'RGcLQijx3T', c:'陈默', r:'当事人'}, {e:'RGcLQijx3T', c:'苏晓禾', r:'当事人'},
  {e:'RGcLQijx3U', c:'陈默', r:'当事人'}, {e:'RGcLQijx3U', c:'沈暮雪', r:'当事人'},
  {e:'RGcLQijx3V', c:'陈默', r:'当事人'}, {e:'RGcLQijx3V', c:'沈暮雪', r:'当事人'}
] AS row
MATCH (ev:Event {id:row.e}) MATCH (c:Character {name:row.c})
MERGE (c)-[:involved {role:row.r}]->(ev);

// ── 5. occurs_at ×30（Event→Location，一跳）──
UNWIND [
  {e:'RGcLQijx32', l:'酒店'}, {e:'RGcLQijx33', l:'街角咖啡店'}, {e:'RGcLQijx34', l:'马路'}, {e:'RGcLQijx35', l:'灵魂夹缝'},
  {e:'RGcLQijx36', l:'长江大桥'}, {e:'RGcLQijx37', l:'长江大桥'}, {e:'RGcLQijx38', l:'长江大桥'}, {e:'RGcLQijx39', l:'八楼出租屋'},
  {e:'RGcLQijx3A', l:'八楼出租屋'}, {e:'RGcLQijx3B', l:'八楼出租屋'}, {e:'RGcLQijx3C', l:'八楼出租屋'},
  {e:'RGcLQijx3D', l:'理发店'}, {e:'RGcLQijx3E', l:'服装店'}, {e:'RGcLQijx3F', l:'八楼出租屋'}, {e:'RGcLQijx3G', l:'八楼出租屋'},
  {e:'RGcLQijx3H', l:'八楼出租屋'}, {e:'RGcLQijx3I', l:'南滨路'}, {e:'RGcLQijx3J', l:'八楼出租屋'}, {e:'RGcLQijx3K', l:'八楼出租屋'},
  {e:'RGcLQijx3L', l:'南滨路'}, {e:'RGcLQijx3M', l:'八楼出租屋'}, {e:'RGcLQijx3N', l:'八楼出租屋'}, {e:'RGcLQijx3O', l:'八楼出租屋'},
  {e:'RGcLQijx3P', l:'星耀电竞基地'}, {e:'RGcLQijx3Q', l:'星耀电竞基地'}, {e:'RGcLQijx3R', l:'星耀电竞基地'}, {e:'RGcLQijx3S', l:'星耀电竞基地'},
  {e:'RGcLQijx3T', l:'南滨路'}, {e:'RGcLQijx3U', l:'八楼出租屋'}, {e:'RGcLQijx3V', l:'连锁咖啡店'}
] AS row
MATCH (ev:Event {id:row.e}) MATCH (l:Location {name:row.l})
MERGE (ev)-[:occurs_at]->(l);

// ── 6. evt_relation{先后} ×29（主线时间序 28 + E5→E6 分支）──
UNWIND [
  {a:'RGcLQijx32', b:'RGcLQijx33'}, {a:'RGcLQijx33', b:'RGcLQijx34'}, {a:'RGcLQijx34', b:'RGcLQijx35'}, {a:'RGcLQijx35', b:'RGcLQijx36'},
  {a:'RGcLQijx36', b:'RGcLQijx38'}, {a:'RGcLQijx38', b:'RGcLQijx39'}, {a:'RGcLQijx39', b:'RGcLQijx3A'}, {a:'RGcLQijx3A', b:'RGcLQijx3B'}, {a:'RGcLQijx3B', b:'RGcLQijx3C'},
  {a:'RGcLQijx3C', b:'RGcLQijx3D'}, {a:'RGcLQijx3D', b:'RGcLQijx3E'}, {a:'RGcLQijx3E', b:'RGcLQijx3F'}, {a:'RGcLQijx3F', b:'RGcLQijx3G'}, {a:'RGcLQijx3G', b:'RGcLQijx3H'},
  {a:'RGcLQijx3H', b:'RGcLQijx3I'}, {a:'RGcLQijx3I', b:'RGcLQijx3J'}, {a:'RGcLQijx3J', b:'RGcLQijx3K'}, {a:'RGcLQijx3K', b:'RGcLQijx3L'}, {a:'RGcLQijx3L', b:'RGcLQijx3M'},
  {a:'RGcLQijx3M', b:'RGcLQijx3N'}, {a:'RGcLQijx3N', b:'RGcLQijx3O'}, {a:'RGcLQijx3O', b:'RGcLQijx3P'}, {a:'RGcLQijx3P', b:'RGcLQijx3Q'}, {a:'RGcLQijx3Q', b:'RGcLQijx3R'},
  {a:'RGcLQijx3R', b:'RGcLQijx3S'}, {a:'RGcLQijx3S', b:'RGcLQijx3T'}, {a:'RGcLQijx3T', b:'RGcLQijx3U'}, {a:'RGcLQijx3U', b:'RGcLQijx3V'},
  {a:'RGcLQijx36', b:'RGcLQijx37'}
] AS row
MATCH (x:Event {id:row.a}) MATCH (y:Event {id:row.b})
MERGE (x)-[:evt_relation {type:'先后'}]->(y);

// ── 7. presents / option（E5 呈现跳江选择；跳下去→E6(BE)、再想想→E7 主线）──
MATCH (e5:Event {id:'RGcLQijx36'}) MATCH (ch:Choice {id:'RGcLQj1YBt'})
MERGE (e5)-[:presents]->(ch);
MATCH (ch:Choice {id:'RGcLQj1YBt'}) MATCH (e6:Event {id:'RGcLQijx37'})
MERGE (ch)-[:option {label:'跳下去', leads_to_ending:true}]->(e6);
MATCH (ch:Choice {id:'RGcLQj1YBt'}) MATCH (e7:Event {id:'RGcLQijx38'})
MERGE (ch)-[:option {label:'再想想'}]->(e7);

// ── 8. wears ×20（回迁；E18 例外改连 林梦-居家慵懒着装）──
UNWIND [
  {e:'RGcLQijx32', c:'顾盈-酒店晨离着装'}, {e:'RGcLQijx32', c:'陆择-赤裸上身'},
  {e:'RGcLQijx33', c:'小夏-咖啡店店员工作服'},
  {e:'RGcLQijx34', c:'陆择-商务休闲着装'},
  {e:'RGcLQijx35', c:'伊芙-天使灵魂引路人着装'}, {e:'RGcLQijx35', c:'陆择-麻衣苦行'},
  {e:'RGcLQijx36', c:'陈默-居家颓废着装'},
  {e:'RGcLQijx37', c:'陈默-居家颓废着装'},
  {e:'RGcLQijx3A', c:'陈念-探望休闲着装'},
  {e:'RGcLQijx3D', c:'Tony-前卫手艺人着装'},
  {e:'RGcLQijx3E', c:'陈默-廉价休闲新装'}, {e:'RGcLQijx3E', c:'季棠-店员清爽工作装'},
  {e:'RGcLQijx3H', c:'林梦-休闲电竞私服'},
  {e:'RGcLQijx3I', c:'苏晓禾-晨跑运动装'}, {e:'RGcLQijx3I', c:'陈默-晨跑运动装'},
  {e:'RGcLQijx3J', c:'林梦-居家慵懒着装'},
  {e:'RGcLQijx3R', c:'江烈-星耀队服训练着装'},
  {e:'RGcLQijx3T', c:'苏晓禾-晨跑运动装'}, {e:'RGcLQijx3T', c:'陈默-晨跑运动装'}
] AS row
MATCH (ev:Event {id:row.e}) MATCH (cs:CostumeStyle {name:row.c})
MERGE (ev)-[:wears]->(cs);

// ── 9. anchored_at ×27（Event→Spot 场景归组回迁）──
UNWIND [
  {e:'RGcLQijx32', s:'酒店-客房'},
  {e:'RGcLQijx33', s:'街角咖啡店-点餐台'},
  {e:'RGcLQijx34', s:'马路-路口'},
  {e:'RGcLQijx36', s:'长江大桥-护栏段'}, {e:'RGcLQijx37', s:'长江大桥-护栏段'}, {e:'RGcLQijx38', s:'长江大桥-护栏段'},
  {e:'RGcLQijx39', s:'八楼出租屋-床铺区'},
  {e:'RGcLQijx3A', s:'八楼出租屋-厨房餐区'}, {e:'RGcLQijx3B', s:'八楼出租屋-厨房餐区'},
  {e:'RGcLQijx3C', s:'八楼出租屋-进门处'},
  {e:'RGcLQijx3D', s:'理发店-剪发区'},
  {e:'RGcLQijx3F', s:'八楼出租屋-床铺区'},
  {e:'RGcLQijx3G', s:'八楼出租屋-电脑桌区'}, {e:'RGcLQijx3H', s:'八楼出租屋-电脑桌区'},
  {e:'RGcLQijx3I', s:'南滨路-滨江步道'},
  {e:'RGcLQijx3J', s:'八楼出租屋-厨房餐区'},
  {e:'RGcLQijx3K', s:'八楼出租屋-电脑桌区'},
  {e:'RGcLQijx3L', s:'南滨路-滨江步道'},
  {e:'RGcLQijx3N', s:'八楼出租屋-电脑桌区'}, {e:'RGcLQijx3O', s:'八楼出租屋-电脑桌区'},
  {e:'RGcLQijx3Q', s:'星耀电竞基地-训练馆'}, {e:'RGcLQijx3R', s:'星耀电竞基地-训练馆'},
  {e:'RGcLQijx3T', s:'南滨路-滨江步道'},
  {e:'RGcLQijx3U', s:'八楼出租屋-床铺区'},
  {e:'RGcLQijx3V', s:'连锁咖啡店-座位区'}
] AS row
MATCH (ev:Event {id:row.e}) MATCH (s:Spot {name:row.s})
MERGE (ev)-[:anchored_at]->(s);

// ── 10. link：Character→Info（146 条，type=涉及）──
UNWIND [
  {i:'RGcLQijx3W', c:'陆择'}, {i:'RGcLQijx3W', c:'顾盈'},
  {i:'RGcLQijx3X', c:'陆择'},
  {i:'RGcLQijx3Y', c:'顾盈'}, {i:'RGcLQijx3Y', c:'陆择'},
  {i:'RGcLQijx3Z', c:'陆择'}, {i:'RGcLQijx3Z', c:'顾盈'},
  {i:'RGcLQijx3a', c:'陆择'},
  {i:'RGcLQijx3b', c:'伊芙'}, {i:'RGcLQijx3b', c:'陆择'},
  {i:'RGcLQijx3c', c:'陆择'}, {i:'RGcLQijx3c', c:'伊芙'},
  {i:'RGcLQijx3d', c:'伊芙'},
  {i:'RGcLQijx3e', c:'陆择'}, {i:'RGcLQijx3e', c:'伊芙'},
  {i:'RGcLQijx3f', c:'陆择'},
  {i:'RGcLQijx3g', c:'陈默'}, {i:'RGcLQijx3g', c:'陈念'},
  {i:'RGcLQijx3h', c:'陈念'}, {i:'RGcLQijx3h', c:'陈默'},
  {i:'RGcLQijx3i', c:'陈默'}, {i:'RGcLQijx3i', c:'温蔓青'},
  {i:'RGcLQijx3j', c:'陆择'}, {i:'RGcLQijx3j', c:'温蔓青'},
  {i:'RGcLQijx3k', c:'温蔓青'}, {i:'RGcLQijx3k', c:'陈默'}, {i:'RGcLQijx3k', c:'陈念'},
  {i:'RGcLQijx3l', c:'陈默'}, {i:'RGcLQijx3l', c:'温蔓青'}, {i:'RGcLQijx3l', c:'陈念'},
  {i:'RGcLQijx3m', c:'陈默'}, {i:'RGcLQijx3m', c:'陈念'},
  {i:'RGcLQijx3n', c:'陈默'}, {i:'RGcLQijx3n', c:'陈念'},
  {i:'RGcLQijx3o', c:'陈默'}, {i:'RGcLQijx3o', c:'陈念'},
  {i:'RGcLQijx3p', c:'陈念'}, {i:'RGcLQijx3p', c:'陈默'},
  {i:'RGcLQijx3q', c:'陈默'}, {i:'RGcLQijx3q', c:'林梦'},
  {i:'RGcLQijx3r', c:'陈默'},
  {i:'RGcLQijx3s', c:'陈默'}, {i:'RGcLQijx3s', c:'陆择'},
  {i:'RGcLQijx3t', c:'陆择'},
  {i:'RGcLQijx3u', c:'陈默'}, {i:'RGcLQijx3u', c:'Tony'},
  {i:'RGcLQijx3v', c:'林梦'}, {i:'RGcLQijx3v', c:'陈默'},
  {i:'RGcLQijx3w', c:'陈默'}, {i:'RGcLQijx3w', c:'林梦'},
  {i:'RGcLQijx3x', c:'陈默'}, {i:'RGcLQijx3x', c:'林梦'},
  {i:'RGcLQijx3y', c:'林梦'}, {i:'RGcLQijx3y', c:'沈暮雪'},
  {i:'RGcLQijx3z', c:'林梦'}, {i:'RGcLQijx3z', c:'沈暮雪'},
  {i:'RGcLQijx40', c:'林梦'},
  {i:'RGcLQj1YB6', c:'陈默'}, {i:'RGcLQj1YB6', c:'林梦'}, {i:'RGcLQj1YB6', c:'沈暮雪'},
  {i:'RGcLQj1YB7', c:'林梦'}, {i:'RGcLQj1YB7', c:'陈默'},
  {i:'RGcLQj1YB8', c:'苏晓禾'}, {i:'RGcLQj1YB8', c:'陈默'},
  {i:'RGcLQj1YB9', c:'苏晓禾'}, {i:'RGcLQj1YB9', c:'陈默'},
  {i:'RGcLQj1YBA', c:'林梦'}, {i:'RGcLQj1YBA', c:'陈默'},
  {i:'RGcLQj1YBB', c:'林梦'}, {i:'RGcLQj1YBB', c:'陈默'},
  {i:'RGcLQj1YBC', c:'陈默'},
  {i:'RGcLQj1YBD', c:'陆择'}, {i:'RGcLQj1YBD', c:'温蔓青'},
  {i:'RGcLQj1YBE', c:'陆择'}, {i:'RGcLQj1YBE', c:'苏晓禾'},
  {i:'RGcLQj1YBF', c:'陈默'}, {i:'RGcLQj1YBF', c:'林梦'},
  {i:'RGcLQj1YBG', c:'陈默'},
  {i:'RGcLQj1YBH', c:'沈暮雪'}, {i:'RGcLQj1YBH', c:'陈默'},
  {i:'RGcLQj1YBI', c:'江烈'}, {i:'RGcLQj1YBI', c:'沈暮雪'},
  {i:'RGcLQj1YBJ', c:'沈暮雪'}, {i:'RGcLQj1YBJ', c:'江烈'}, {i:'RGcLQj1YBJ', c:'陈默'},
  {i:'RGcLQj1YBK', c:'江烈'}, {i:'RGcLQj1YBK', c:'陈默'}, {i:'RGcLQj1YBK', c:'沈暮雪'},
  {i:'RGcLQj1YBL', c:'沈暮雪'}, {i:'RGcLQj1YBL', c:'江烈'}, {i:'RGcLQj1YBL', c:'陈默'},
  {i:'RGcLQj1YBM', c:'陈默'}, {i:'RGcLQj1YBM', c:'苏晓禾'},
  {i:'RGcLQj1YBN', c:'苏晓禾'}, {i:'RGcLQj1YBN', c:'陈默'},
  {i:'RGcLQj1YBO', c:'苏晓禾'}, {i:'RGcLQj1YBO', c:'陈默'},
  {i:'RGcLQj1YBP', c:'沈暮雪'}, {i:'RGcLQj1YBP', c:'陈默'},
  {i:'RGcLQj1YBQ', c:'沈暮雪'}, {i:'RGcLQj1YBQ', c:'陈默'},
  {i:'RGcLQj1YBR', c:'沈暮雪'}, {i:'RGcLQj1YBR', c:'江烈'}, {i:'RGcLQj1YBR', c:'陈默'},
  {i:'RGcLQj1YBS', c:'沈暮雪'}, {i:'RGcLQj1YBS', c:'陈默'},
  {i:'RGcLQj1YBT', c:'沈暮雪'}, {i:'RGcLQj1YBT', c:'陈默'},
  {i:'RGcLQj1YBU', c:'陆择'}, {i:'RGcLQj1YBU', c:'顾盈'},
  {i:'RGcLQj1YBV', c:'陆择'},
  {i:'RGcLQj1YBW', c:'伊芙'},
  {i:'RGcLQj1YBX', c:'陆择'},
  {i:'RGcLQj1YBY', c:'陆择'},
  {i:'RGcLQj1YBZ', c:'陈念'}, {i:'RGcLQj1YBZ', c:'陈默'},
  {i:'RGcLQj1YBa', c:'温蔓青'}, {i:'RGcLQj1YBa', c:'陈默'},
  {i:'RGcLQj1YBb', c:'陈默'}, {i:'RGcLQj1YBb', c:'温蔓青'},
  {i:'RGcLQj1YBc', c:'陈默'},
  {i:'RGcLQj1YBd', c:'陈默'},
  {i:'RGcLQj1YBe', c:'陆择'},
  {i:'RGcLQj1YBf', c:'Tony'},
  {i:'RGcLQj1YBg', c:'季棠'},
  {i:'RGcLQj1YBh', c:'林梦'}, {i:'RGcLQj1YBh', c:'陈默'},
  {i:'RGcLQj1YBi', c:'林梦'},
  {i:'RGcLQj1YBj', c:'苏晓禾'},
  {i:'RGcLQj1YBk', c:'陆择'}, {i:'RGcLQj1YBk', c:'陈默'},
  {i:'RGcLQj1YBl', c:'陆择'}, {i:'RGcLQj1YBl', c:'陈默'},
  {i:'RGcLQj1YBm', c:'江烈'},
  {i:'RGcLQj1YBn', c:'沈暮雪'}, {i:'RGcLQj1YBn', c:'江烈'},
  {i:'RGcLQj1YBo', c:'陈默'}, {i:'RGcLQj1YBo', c:'沈暮雪'}, {i:'RGcLQj1YBo', c:'江烈'},
  {i:'RGcLQj1YBp', c:'苏晓禾'}, {i:'RGcLQj1YBp', c:'陈默'},
  {i:'RGcLQj1YBq', c:'陈默'}, {i:'RGcLQj1YBq', c:'苏晓禾'},
  {i:'RGcLQj1YBr', c:'沈暮雪'},
  {i:'RGcLQj1YBs', c:'沈暮雪'}, {i:'RGcLQj1YBs', c:'江烈'}
] AS row
MATCH (info:Info {id:row.i}) MATCH (c:Character {name:row.c})
MERGE (c)-[:link {type:'涉及'}]->(info);

// ── 10b. link：Location→Info（34 条）──
UNWIND [
  {i:'RGcLQijx3W', l:'酒店'}, {i:'RGcLQijx3X', l:'酒店'}, {i:'RGcLQijx3a', l:'马路'},
  {i:'RGcLQijx3b', l:'灵魂夹缝'}, {i:'RGcLQijx3c', l:'灵魂夹缝'}, {i:'RGcLQijx3d', l:'灵魂夹缝'}, {i:'RGcLQijx3e', l:'灵魂夹缝'}, {i:'RGcLQijx3f', l:'灵魂夹缝'},
  {i:'RGcLQijx3i', l:'八楼出租屋'}, {i:'RGcLQijx3j', l:'八楼出租屋'}, {i:'RGcLQijx3o', l:'八楼出租屋'}, {i:'RGcLQijx3p', l:'八楼出租屋'}, {i:'RGcLQijx3r', l:'八楼出租屋'},
  {i:'RGcLQj1YB8', l:'南滨路'}, {i:'RGcLQj1YB9', l:'南滨路'},
  {i:'RGcLQj1YBC', l:'八楼出租屋'}, {i:'RGcLQj1YBF', l:'八楼出租屋'}, {i:'RGcLQj1YBG', l:'八楼出租屋'},
  {i:'RGcLQj1YBK', l:'星耀电竞基地'}, {i:'RGcLQj1YBL', l:'星耀电竞基地'},
  {i:'RGcLQj1YBM', l:'南滨路'}, {i:'RGcLQj1YBN', l:'南滨路'}, {i:'RGcLQj1YBO', l:'南滨路'},
  {i:'RGcLQj1YBT', l:'连锁咖啡店'}, {i:'RGcLQj1YBW', l:'灵魂夹缝'}, {i:'RGcLQj1YBZ', l:'八楼出租屋'}, {i:'RGcLQj1YBj', l:'南滨路'},
  {i:'RGcLQj1YBk', l:'八楼出租屋'}, {i:'RGcLQj1YBl', l:'八楼出租屋'}, {i:'RGcLQj1YBm', l:'星耀电竞基地'}, {i:'RGcLQj1YBo', l:'星耀电竞基地'},
  {i:'RGcLQj1YBp', l:'南滨路'}, {i:'RGcLQj1YBq', l:'南滨路'}, {i:'RGcLQj1YBr', l:'连锁咖啡店'}
] AS row
MATCH (info:Info {id:row.i}) MATCH (l:Location {name:row.l})
MERGE (l)-[:link {type:'涉及'}]->(info);

// ── 10c. link：Event→Info（87 条，顺带关联）──
UNWIND [
  {i:'RGcLQijx3W', e:'RGcLQijx32'}, {i:'RGcLQijx3X', e:'RGcLQijx32'}, {i:'RGcLQijx3Y', e:'RGcLQijx32'}, {i:'RGcLQijx3Z', e:'RGcLQijx32'},
  {i:'RGcLQijx3a', e:'RGcLQijx34'},
  {i:'RGcLQijx3b', e:'RGcLQijx35'}, {i:'RGcLQijx3c', e:'RGcLQijx35'}, {i:'RGcLQijx3d', e:'RGcLQijx35'}, {i:'RGcLQijx3e', e:'RGcLQijx35'}, {i:'RGcLQijx3f', e:'RGcLQijx35'},
  {i:'RGcLQijx3g', e:'RGcLQijx36'}, {i:'RGcLQijx3g', e:'RGcLQijx38'},
  {i:'RGcLQijx3h', e:'RGcLQijx38'},
  {i:'RGcLQijx3i', e:'RGcLQijx39'}, {i:'RGcLQijx3j', e:'RGcLQijx39'},
  {i:'RGcLQijx3k', e:'RGcLQijx3A'}, {i:'RGcLQijx3l', e:'RGcLQijx3A'},
  {i:'RGcLQijx3m', e:'RGcLQijx3B'}, {i:'RGcLQijx3n', e:'RGcLQijx3B'},
  {i:'RGcLQijx3o', e:'RGcLQijx3A'}, {i:'RGcLQijx3p', e:'RGcLQijx3C'},
  {i:'RGcLQijx3q', e:'RGcLQijx3F'}, {i:'RGcLQijx3r', e:'RGcLQijx3F'},
  {i:'RGcLQijx3s', e:'RGcLQijx3G'},
  {i:'RGcLQijx3t', e:'RGcLQijx3D'}, {i:'RGcLQijx3t', e:'RGcLQijx3I'},
  {i:'RGcLQijx3u', e:'RGcLQijx3D'},
  {i:'RGcLQijx3v', e:'RGcLQijx3H'}, {i:'RGcLQijx3w', e:'RGcLQijx3H'}, {i:'RGcLQijx3x', e:'RGcLQijx3H'}, {i:'RGcLQijx3y', e:'RGcLQijx3H'}, {i:'RGcLQijx3z', e:'RGcLQijx3H'}, {i:'RGcLQijx40', e:'RGcLQijx3H'},
  {i:'RGcLQj1YB6', e:'RGcLQijx3H'}, {i:'RGcLQj1YB7', e:'RGcLQijx3H'},
  {i:'RGcLQj1YB8', e:'RGcLQijx3I'}, {i:'RGcLQj1YB9', e:'RGcLQijx3I'},
  {i:'RGcLQj1YBA', e:'RGcLQijx3J'}, {i:'RGcLQj1YBB', e:'RGcLQijx3J'},
  {i:'RGcLQj1YBC', e:'RGcLQijx3K'}, {i:'RGcLQj1YBD', e:'RGcLQijx3K'}, {i:'RGcLQj1YBE', e:'RGcLQijx3K'},
  {i:'RGcLQj1YBF', e:'RGcLQijx3N'}, {i:'RGcLQj1YBG', e:'RGcLQijx3N'},
  {i:'RGcLQj1YBH', e:'RGcLQijx3O'},
  {i:'RGcLQj1YBI', e:'RGcLQijx3P'}, {i:'RGcLQj1YBJ', e:'RGcLQijx3P'},
  {i:'RGcLQj1YBK', e:'RGcLQijx3R'}, {i:'RGcLQj1YBL', e:'RGcLQijx3S'},
  {i:'RGcLQj1YBM', e:'RGcLQijx3T'}, {i:'RGcLQj1YBN', e:'RGcLQijx3T'}, {i:'RGcLQj1YBO', e:'RGcLQijx3T'},
  {i:'RGcLQj1YBP', e:'RGcLQijx3V'}, {i:'RGcLQj1YBQ', e:'RGcLQijx3V'}, {i:'RGcLQj1YBR', e:'RGcLQijx3V'}, {i:'RGcLQj1YBS', e:'RGcLQijx3V'}, {i:'RGcLQj1YBT', e:'RGcLQijx3V'},
  {i:'RGcLQj1YBU', e:'RGcLQijx32'}, {i:'RGcLQj1YBV', e:'RGcLQijx32'},
  {i:'RGcLQj1YBW', e:'RGcLQijx35'}, {i:'RGcLQj1YBX', e:'RGcLQijx35'},
  {i:'RGcLQj1YBY', e:'RGcLQijx3B'},
  {i:'RGcLQj1YBZ', e:'RGcLQijx3A'}, {i:'RGcLQj1YBZ', e:'RGcLQijx3C'},
  {i:'RGcLQj1YBa', e:'RGcLQijx3A'},
  {i:'RGcLQj1YBb', e:'RGcLQijx39'},
  {i:'RGcLQj1YBc', e:'RGcLQijx3D'},
  {i:'RGcLQj1YBd', e:'RGcLQijx36'},
  {i:'RGcLQj1YBe', e:'RGcLQijx3D'}, {i:'RGcLQj1YBe', e:'RGcLQijx3E'},
  {i:'RGcLQj1YBf', e:'RGcLQijx3D'},
  {i:'RGcLQj1YBg', e:'RGcLQijx3E'},
  {i:'RGcLQj1YBh', e:'RGcLQijx3H'},
  {i:'RGcLQj1YBi', e:'RGcLQijx3J'},
  {i:'RGcLQj1YBj', e:'RGcLQijx3I'},
  {i:'RGcLQj1YBk', e:'RGcLQijx3K'},
  {i:'RGcLQj1YBl', e:'RGcLQijx3N'},
  {i:'RGcLQj1YBm', e:'RGcLQijx3R'},
  {i:'RGcLQj1YBn', e:'RGcLQijx3O'}, {i:'RGcLQj1YBn', e:'RGcLQijx3S'}, {i:'RGcLQj1YBn', e:'RGcLQijx3V'},
  {i:'RGcLQj1YBo', e:'RGcLQijx3R'},
  {i:'RGcLQj1YBp', e:'RGcLQijx3T'}, {i:'RGcLQj1YBq', e:'RGcLQijx3T'},
  {i:'RGcLQj1YBr', e:'RGcLQijx3V'},
  {i:'RGcLQj1YBs', e:'RGcLQijx3H'}
] AS row
MATCH (info:Info {id:row.i}) MATCH (ev:Event {id:row.e})
MERGE (ev)-[:link {type:'涉及'}]->(info);

// ── 11. leads_to 因果链 ×22（四向全通，detail=因果语境）──
UNWIND [
  {a:'RGcLQijx32', b:'RGcLQijx33', d:'顾盈推荐街角咖啡店，陆择顺路去买'},
  {a:'RGcLQijx34', b:'RGcLQijx35', d:'死亡后灵魂进入审判流程'},
  {a:'RGcLQijx35', b:'RGcLQijx36', d:'试炼任务启动，灵魂被漩涡送入第一个宿主'},
  {a:'RGcLQijx3g', b:'RGcLQijx38', d:'留言引发陈念警觉，深夜来电追问'},
  {a:'RGcLQijx38', b:'RGcLQijx3A', d:'电话中约定「明天你给我在家待着，我过去看你」'},
  {a:'RGcLQijx3t', b:'RGcLQijx3D', d:'策略第一步「先让自己像个人样」'},
  {a:'RGcLQijx3t', b:'RGcLQijx3E', d:'同一策略的置装环节'},
  {a:'RGcLQijx3t', b:'RGcLQijx3I', d:'目标导向选晨练场景物色对象'},
  {a:'RGcLQijx3F', b:'RGcLQijx3G', d:'到期单不交赔三倍，被迫当晚上线'},
  {a:'RGcLQijx3G', b:'RGcLQijx3H', d:'林梦群内围观「老陈你活的？」后次日抱着最后信任下单（网名=林梦）'},
  {a:'RGcLQijx3H', b:'RGcLQj1YB6', d:'高光局具备传播性'},
  {a:'RGcLQijx3H', b:'RGcLQijx3J', d:'林梦亲手剪辑该局上头条，乘热度催开播并出资'},
  {a:'RGcLQj1YBA', b:'RGcLQijx3N', d:'头条视频为首播引流'},
  {a:'RGcLQijx3J', b:'RGcLQijx3M', d:'投资落地为设备升级'},
  {a:'RGcLQijx3M', b:'RGcLQijx3N', d:'设备就绪才具备开播条件'},
  {a:'RGcLQijx3N', b:'RGcLQijx3O', d:'视频与直播热度引来星耀经理关注'},
  {a:'RGcLQijx3O', b:'RGcLQijx3P', d:'私信约定次日赴基地试训'},
  {a:'RGcLQijx3R', b:'RGcLQijx3U', d:'冲突「回去等通知」后沈暮雪主动挽回'},
  {a:'RGcLQijx3U', b:'RGcLQijx3V', d:'面谈落地为二队邀约'},
  {a:'RGcLQijx3I', b:'RGcLQijx3T', d:'教的跑姿被照练执行，再遇时获认可'},
  {a:'RGcLQijx3K', b:'RGcLQijx3L', d:'三闹钟机制驱动次日早起晨跑'},
  {a:'RGcLQijx3L', b:'RGcLQijx3T', d:'坚持同路线晨跑才有了老地方再遇'}
] AS row
MATCH (x) WHERE (x:Event OR x:Info) AND x.id = row.a
MATCH (y) WHERE (y:Event OR y:Info) AND y.id = row.b
MERGE (x)-[:leads_to {detail:row.d}]->(y);
