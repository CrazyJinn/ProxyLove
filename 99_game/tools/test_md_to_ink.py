"""md→ink 一次性迁移器（00_init/migration/2026-09-02_台词md转ink.py）单测——不连 Neo4j。

锁定两件事：
  ① 合成样例（全行型）转换输出 == 手写 golden ink（转换器是退役历史工具，golden 冻结其输出；
     SYNTH 产物含 v1 单行式结局，方言 v2 解析器按设计拒绝——故不进解析锚）；
  ② 已退役（方言 v3，2026-09-03）：签名锚断言删除——锚对象（转换产物 ink）含
     环境音内嵌语法，v3 解析器按设计废止拒绝，且存量文件已迁移为 sfx/bed 行型，
     保真义务随迁移终结。保留 golden/map_target/garbage 用例冻结转换器历史行为。
在 99_game/tools 下跑：python -m pytest test_md_to_ink.py -v
"""
import importlib.util
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "section-voice-publisher" / "scripts"))
import script_splitter as sp  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "md_to_ink", ROOT / "00_init" / "migration" / "2026-09-02_台词md转ink.py")
md_to_ink = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(md_to_ink)


def _convert(tmp_path, name, md_text):
    md = tmp_path / name
    md.write_text(md_text, encoding="utf-8")
    ink_text = md_to_ink.convert_file(md)
    ink = tmp_path / (name.rsplit(".", 1)[0] + ".ink")
    ink.write_text(ink_text, encoding="utf-8")
    return ink


# ── 真实 fixture（2026-09-02 迁移时的 3 个 台词.md 全文）──

SEC00 = """# 酒店醒来

## s00_酒店 酒店-客房（清晨）

旁白:清晨，一缕阳光从窗帘的缝隙钻进来。
旁白:昨夜的酒气还没散透。外套歪在椅背上，两只杯子空在床头，谁也没打算收拾。
旁白:浴室传来哗哗的水声。【环境音:浴室洗澡的声音】
旁白:顾盈的身影透过磨砂玻璃，若隐若现。
旁白:陆择朦胧地睁开眼睛，摇了摇头，想尽快从宿醉中清醒过来。
旁白:水声停了，一阵窸窸窣窣之后，顾盈推开门走了出来。
旁白:白衬衫松松垮垮地罩在她身上，发梢还滴着水。
顾盈:哟，醒这么早？
陆择:哎……没办法，等下还要赶飞机。
陆择:这不是我的衬衫嘛。
顾盈:这儿乱七八糟的，随手抓到了这件。
陆择:别说，你穿着还挺好看。
顾盈:和不穿比呢？
陆择:都好看，各有各的韵味。
顾盈:哼，嘴可真甜呀。
旁白:顾盈对着镜子擦头发。
顾盈:没看出来，昨晚你还挺厉害的。要不加个微信？
陆择:还是别了，昨晚地动山摇的，下次我怕床受不了。
旁白:顾盈耸了耸肩，没再坚持。
旁白:顾盈开始化妆。
陆择:这附近有咖啡店么？
顾盈:怎么，想请我喝咖啡？
陆择:我倒是想，可是等不及你化妆了，10点的飞机。
顾盈:街角有一家，拿铁还不错。
陆择:谢啦。
旁白:顾盈换回自己裙子，对着镜子继续上妆。
旁白:陆择穿戴整齐，推门而出。
旁白:门在身后合上。房间里，吹风机的声音很快响了起来。
"""

SEC01 = """# 骤雨车祸

## s01_咖啡店 街角咖啡店-点餐台（清晨）

旁白:街角的咖啡店。刚开门的清晨，店里没有顾客，咖啡机吐着蒸汽，暖黄的灯光落在空着的座位上。
环境音:推门时门口的风铃清脆作响
小夏:欢迎光临，请问想喝点什么。
陆择:来一杯拿铁，打包。
小夏:抱歉，我们刚开门，牛奶还没备好——美式可以么？
陆择:行吧，看在你这么可爱的份上。
旁白:小夏耳根一红，低下头去。
小夏:您的美式。
陆择:请问，机场大巴在哪儿坐？
小夏:就在街对面，20分钟一趟。
旁白:陆择道了声谢，拎着打包杯走到门口。

## s01_路口 马路-路口（白天）

旁白:天突然暗了下来，接着淅淅沥沥地落起雨来。【环境音:雨点骤然砸落，越来越密】
旁白:雨点砸在湿滑的沥青路面上，积水洼里晃着破碎的霓虹。
旁白:陆择推开咖啡店的门，一股湿冷的水汽扑面而来。
陆择:什么鬼天气。
旁白:陆择低声骂了一句，把衣领竖了起来。
旁白:远处一辆摩托车发出了巨大的轰鸣。【环境音:远处摩托引擎轰鸣，加速逼近】
旁白:人行横道的绿灯开始倒计时。
旁白:陆择加快脚步小跑起来，想抢在红灯之前冲过马路。
旁白:摩托车轰鸣着冲了出来。
旁白:陆择被重重地撞飞了出去，后脑勺磕在马路牙子上。
旁白:所有声音在同一瞬间被抽空。
"""

SEC02 = """# 夹缝试炼

## s02_夹缝 灵魂夹缝-夹缝空间（黄昏）

旁白:这里像一座荒废的神庙——断裂的列柱沿着石板路排向远方，尽头隐在细雾里。
旁白:暮光停在将暗未暗的时刻，不再往下沉。四下安静得没有风，也没有回声。
陆择:这……是哪？
伊芙:这是你意识里的世界
陆择:你是谁
伊芙:按你们凡间的说法，算是天使吧
陆择:我……这是死了么？
伊芙:嗯，你被一辆闯红灯的摩托车撞倒，在送去医院的路上就没了呼吸
旁白:陆择瞪大了双眼，一脸不可置信地看着眼前的女孩。
伊芙:嗯……我看看接下来的流程
旁白:伊芙掏出了一张羊皮纸。
伊芙:你要下地狱！
陆择:为什么，我可没做过什么伤天害理的事
伊芙:呃……这上面写着：因为伤害众多女孩感情
陆择:这就得下地狱啦？
伊芙:以前倒是还好，但是现在审判庭换了一个姐姐。不过你还有一个机会拯救自己
陆择:什么机会
伊芙:用你的特长去拯救6个弱者
伊芙:你的灵魂会穿越到弱者的身上，进入他的身体，以他的身份替他生活30天。
伊芙:至于什么样的人算弱者——对于你的特长来说，是那些认真对待了感情，结果却落得伤痕累累的人。
陆择:拯救了他们，对我有什么好处
伊芙:好处是……糟糕要来不及了!
旁白:陆择突然眼前一花，感觉被吸入了一个巨大的漩涡。
"""

# ── 合成样例：全行型覆盖（选择两去向 + 裸名去向 + 分支 + 结局 + 转场 + 内嵌氛围）──

SYNTH = """# 试炼

## s03_天台 学校-天台（黄昏）

环境音:天台铁门被推开时的生锈铰链声
陆择:站住！
旁白:风很大。【环境音:天台风声呼啸】

**选择**
- 跳下去 → 结局:BE
- 转身离开 → 分支:离开
- 喊她的名字 → 名字

**分支:离开**

陆择:再见。

**结局**:TE——独自离开
"""

SYNTH_GOLDEN = """// 试炼

=== s03_天台 学校-天台（黄昏）

环境音:天台铁门被推开时的生锈铰链声
陆择:站住！
旁白:风很大。【环境音:天台风声呼啸】

* 跳下去 -> END # ending: BE
* 转身离开 -> 离开
* 喊她的名字 -> 名字

= 离开

陆择:再见。

-> END # ending: TE——独自离开
"""


def test_convert_golden_synthetic(tmp_path):
    md = tmp_path / "台词.md"
    md.write_text(SYNTH, encoding="utf-8")
    assert md_to_ink.convert_file(md) == SYNTH_GOLDEN


def test_convert_real_files_rows_deep_equal(tmp_path):
    """3 个真实 md：parse_ink(转换产物) == parse_md(原文) 深相等——行文本逐字保真。
    md 时代解析器删除后本用例自动跳过（签名锚用例承接）。"""
    if not hasattr(sp, "parse_md"):
        import pytest
        pytest.skip("parse_md 已删除（md 时代结束），保真由签名锚用例锁定")
    for i, md_text in enumerate([SEC00, SEC01, SEC02]):
        md = tmp_path / f"sec{i}.md"
        md.write_text(md_text, encoding="utf-8")
        ink_text = md_to_ink.convert_file(md)
        ink = tmp_path / f"sec{i}.ink"
        ink.write_text(ink_text, encoding="utf-8")
        assert sp.parse_ink(ink) == sp.parse_md(md), f"sec{i} 转换后行模型漂移"


def test_map_target():
    f = md_to_ink._map_target
    assert f("分支:起床") == "起床"
    assert f("场景:s01_路口") == "s01_路口"
    assert f("结局:BE") == "END # ending: BE"
    assert f("名字") == "名字"


def test_garbage_line_passes_through_but_parse_ink_rejects(tmp_path):
    """转换器对未识别内容行原样拷贝（保真优先），防线在解析器：parse_ink 拒绝。"""
    assert md_to_ink.convert_line("%%怪行%%", 1, "x.md", [False]) == "%%怪行%%"
    ink = tmp_path / "台词.ink"
    ink.write_text("=== s0 场（早）\n%%怪行%%\n", encoding="utf-8")
    with pytest.raises(ValueError, match="第 2 行"):
        sp.parse_ink(ink)
