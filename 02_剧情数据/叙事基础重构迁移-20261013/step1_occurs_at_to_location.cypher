MATCH (e:Event)-[r:occurs_at]->(sp:Spot {kind:'default'})-[:part_of]->(l:Location)
MERGE (e)-[r2:occurs_at]->(l) ON CREATE SET r2.detail = r.detail, r2.sync = false;
MATCH (e:Event)-[r:occurs_at]->(sp:Spot {kind:'zone'})-[:part_of]->(l:Location)
MERGE (e)-[r2:occurs_at]->(l) ON CREATE SET r2.detail = r.detail, r2.sync = false
MERGE (e)-[r3:anchored_at]->(sp) ON CREATE SET r3.detail = r.detail, r3.sync = false;
MATCH (e:Event)-[r:occurs_at]->(:Spot) DELETE r;
MATCH ()-[r:occurs_at]->() WHERE r.anchor IS NOT NULL REMOVE r.anchor;
