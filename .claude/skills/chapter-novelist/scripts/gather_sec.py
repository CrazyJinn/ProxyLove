# 通用素材圈定脚本：按 section_id 圈 Event+sub+scene+语感+Hook/Lore（供剔除标注）
import sys, json, subprocess
from neo4j import GraphDatabase
SEC = sys.argv[1]
d = GraphDatabase.driver('bolt://localhost:7687', auth=None)
out = {'section': SEC, 'events': [], 'info': []}
with d.session() as s:
    evs = s.run("""MATCH (sec:Section {id:$s})-[:includes]->(e:Event)
        OPTIONAL MATCH (e)-[:occurs_at]->(l:Location)
        WITH e, l.name AS loc
        OPTIONAL MATCH (c:Character)-[:involved]->(e)
        WITH e, loc, collect(c.name) AS cs
        RETURN e.id AS id, e.time AS t, e.title AS ti, e.description AS de, loc, cs ORDER BY e.time""", s=SEC).data()
    for r in evs:
        subs = s.run("""MATCH (:Event {id:$i})-[:refines]->(sub:SubEvent)
            OPTIONAL MATCH (sub)-[:anchored_at]->(sc:Scene)
            RETURN sub.id AS sid, sub.title AS st, sub.time AS stime, sub.description AS sde, sc.id AS scid, sc.name AS scn, sc.time_of_day AS tod ORDER BY stime""", i=r['id']).data()
        out['events'].append({**r, 'subs': subs})
    for r in s.run("""MATCH (sec:Section {id:$s})-[:includes]->(e:Event)
        MATCH (e)-[:reveals]->(info:Hook) RETURN info.id AS id, info.title AS ti, info.content AS c""", s=SEC).data() if False else []:
        pass
    # Hook：节内事件揭示的 Hook（若有 reveals 关联）
    for r in s.run("""MATCH (sec:Section {id:$s})-[:includes]->(e:Event)
        OPTIONAL MATCH (e)-[:reveals]->(info:Hook)
        WITH DISTINCT info WHERE info IS NOT NULL
        RETURN info.id AS id, info.title AS ti""", s=SEC).data():
        out['info'].append(r)
    chars = s.run("""MATCH (sec:Section {id:$s})-[:includes]->(e:Event)<-[:involved]-(host:Character)
        MATCH (c:Character) WHERE c = host OR (c)-[:relation {type:'控制'}]->(host)
        WITH DISTINCT c RETURN c.name AS n, c.description AS de, c.character_tags AS tg""", s=SEC).data()
    out['chars'] = chars
p = f".tmp/novelist/{SEC}_materials.json"
json.dump(out, open(p, 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
