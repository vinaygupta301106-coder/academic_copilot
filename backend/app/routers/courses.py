from fastapi import APIRouter, HTTPException
from neo4j import GraphDatabase
from app.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

router = APIRouter(prefix="/api/v1/courses", tags=["Courses"])

def get_neo4j_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

@router.get("/")
def get_all_courses():
    """Fetch all courses available in the Knowledge Graph."""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            query = """
            MATCH (c:Course)
            RETURN c.code AS code, c.name AS name, c.credits AS credits, c.min_grade AS min_grade
            """
            result = session.run(query)
            courses = [record.data() for record in result]
            return {"courses": courses}
    finally:
        driver.close()

@router.get("/{course_code}/prerequisites")
def check_prerequisites(course_code: str):
    """Fetch all direct and indirect prerequisites for a specific course."""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            query = """
            MATCH (target:Course {code: $code})
            OPTIONAL MATCH (prereq:Course)-[:PREREQUISITE_FOR*1..3]->(target)
            RETURN target.code AS target_course, 
                   collect(DISTINCT prereq.code) AS required_prerequisites
            """
            result = session.run(query, code=course_code.upper()).single()
            if not result or not result["target_course"]:
                raise HTTPException(status_code=404, detail=f"Course '{course_code}' not found.")
            
            return {
                "course": result["target_course"],
                "prerequisites": result["required_prerequisites"]
            }
    finally:
        driver.close()