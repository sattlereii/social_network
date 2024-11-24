from neo4j import GraphDatabase
import os

def import_data():
    # Připojení k Neo4j
    uri = "bolt://neo4j:7687"
    driver = GraphDatabase.driver(uri, auth=("neo4j", "mypassword"))

    with driver.session() as session:
        # Import uživatelů
        session.run("""
            LOAD CSV WITH HEADERS FROM 'file:///data/users.csv' AS row
            MERGE (u:User {username: row.username})
            SET u.points = toInteger(row.points)
        """)

        # Import výzev
        session.run("""
            LOAD CSV WITH HEADERS FROM 'file:///data/challenges.csv' AS row
            MERGE (c:Challenge {id: row.id})
            SET c.name = row.name, c.description = row.description, 
                c.duration = toInteger(row.duration), c.created_by = row.created_by,
                c.created_at = row.created_at
        """)

        # Import relací
        session.run("""
            LOAD CSV WITH HEADERS FROM 'file:///data/relationships.csv' AS row
            MATCH (u:User {username: row.username})
            MATCH (c:Challenge {id: row.challenge_id})
            CALL apoc.create.relationship(u, row.relationship, {result: row.result}, c) YIELD rel
            RETURN rel
        """)

    driver.close()
    print("Data successfully imported.")
