MATCH (sp:Spot {kind:'default'})
WHERE NOT (sp)-[:realizes]->() AND coalesce(sp.dsl_path, '') = '' AND NOT ()-[:anchored_at]->(sp)
DETACH DELETE sp;
