import json
from pathlib import Path
from validate_chapter import validate_chapter

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = str(ROOT / "data" / "剧本.schema.json")


def _valid_doc():
    return {"meta": {"chapter": 1, "title": "x", "requires": {"characters": [], "scenes": [], "portraits": []}},
            "scenes": [{"id": "s", "scene": "x", "lines": [{"op": "narrate", "text": "hi"}]}]}


def test_valid_chapter_passes(tmp_path):
    p = tmp_path / "ch.json"
    p.write_text(json.dumps(_valid_doc(), ensure_ascii=False), encoding="utf-8")
    ok, errors = validate_chapter(str(p), SCHEMA)
    assert ok, errors


def test_missing_op_field_fails(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps({"meta": {"chapter": 1, "title": "x"},
                    "scenes": [{"id": "s", "scene": "x", "lines": [{"text": "hi"}]}]},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    ok, errors = validate_chapter(str(bad), SCHEMA)
    assert not ok
    assert any("op" in e or "required" in e for e in errors)


def test_bad_ending_kind_fails(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps({"meta": {"chapter": 1, "title": "x"},
                    "scenes": [{"id": "s", "scene": "x",
                                "lines": [{"op": "ending", "kind": "XXX"}]}]},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    ok, _ = validate_chapter(str(bad), SCHEMA)
    assert not ok


def test_bed_lines_pass_validation(tmp_path):
    """bed_start（op/bed/track）/ bed_end（op/bed）合法文档过 schema。"""
    doc = _valid_doc()
    doc["scenes"][0]["lines"] = [
        {"op": "bed_start", "bed": "rain", "track": "bed-ch0-s01-B1"},
        {"op": "narrate", "text": "雨下起来。"},
        {"op": "bed_end", "bed": "rain"},
    ]
    p = tmp_path / "bed.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    ok, errors = validate_chapter(str(p), SCHEMA)
    assert ok, errors


def test_bed_lines_missing_required_fails(tmp_path):
    """bed_end 缺 bed / bed_start 缺 track 均不过校验。"""
    for bad_line in ({"op": "bed_end"}, {"op": "bed_start", "bed": "rain"}):
        doc = _valid_doc()
        doc["scenes"][0]["lines"] = [bad_line]
        p = tmp_path / "bad_bed.json"
        p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        ok, errors = validate_chapter(str(p), SCHEMA)
        assert not ok
