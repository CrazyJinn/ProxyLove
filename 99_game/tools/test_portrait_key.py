"""portrait_key 单测：运行时键 = hexid(stand_id)（id 锚定，改名零漂移）。"""
from portrait_key import make_key
from snowflake_base62 import from_hexid


def test_make_key_is_hexid():
    k = make_key("PHSE4iftNQ")
    assert len(k) == 16 and all(c in "0123456789abcdef" for c in k)


def test_make_key_reversible():
    """键可逆解码回 stand_id（排查问题用）。"""
    assert from_hexid(make_key("PHSE4iftNQ")) == "PHSE4iftNQ"
    assert from_hexid(make_key("QZXoBBWJMg")) == "QZXoBBWJMg"


def test_make_key_case_insensitive_safe():
    """大小写变体 id（NTFS 撞名场景）→ 不同键（全小写 hex 不冲突）。"""
    k1, k2 = make_key("QZXoBBWJMG"), make_key("QZXoBBWJMg")
    assert k1 != k2
    assert k1.lower() == k1 and k2.lower() == k2


def test_make_key_unique_per_stand():
    """同角色同变体、不同着装 → 不同键（stand_id 唯一即键唯一）。"""
    assert make_key("PHSE4iftNQ") != make_key("PJajqyM6s4")
