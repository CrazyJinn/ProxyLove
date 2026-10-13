MATCH (a)-[r:evt_relation {type:'因果'}]->(b)
MERGE (a)-[r2:leads_to]->(b) ON CREATE SET r2.detail = r.detail, r2.sync = false;
MATCH ()-[r:evt_relation {type:'因果'}]->() DELETE r;
MATCH (a)-[r:link {type:'因果'}]->(b)
MERGE (a)-[r2:leads_to]->(b) ON CREATE SET r2.detail = r.detail, r2.sync = false;
MATCH ()-[r:link {type:'因果'}]->() DELETE r;
