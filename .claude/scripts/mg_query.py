
import sys, json
from neo4j import GraphDatabase

def run(cypher):
    d = GraphDatabase.driver("bolt://localhost:7687", auth=None)
    with d.session() as s:
        return s.run(cypher).data()

if __name__ == "__main__":
    cypher = sys.stdin.read()
    try:
        print(json.dumps(run(cypher), ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"__error__": str(e)}, ensure_ascii=False))
