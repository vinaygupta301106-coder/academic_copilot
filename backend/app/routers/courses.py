from fastapi import APIRouter, HTTPException, Query
from neo4j import GraphDatabase
from app.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
from app import curriculum

router = APIRouter(prefix="/api/v1/courses", tags=["Courses"])

def get_neo4j_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

@router.get("/")
def get_all_courses(department: str | None = Query(default=None)):
    """Fetch courses available in the curriculum and Knowledge Graph.
    If department is provided, returns courses for that department (Semesters 1-8).
    Otherwise returns the complete verified catalog.
    """
    if department:
        norm_dept = curriculum.normalize_department(department)
        courses = curriculum.get_curriculum(norm_dept)
        return {"department": norm_dept, "courses": courses}

    try:
        driver = get_neo4j_driver()
        try:
            with driver.session() as session:
                query = """
                MATCH (c:Course)
                OPTIONAL MATCH (prereq:Course)-[:PREREQUISITE_FOR]->(c)
                RETURN c.code AS code, c.name AS name, c.credits AS credits,
                       c.semester AS semester, c.department AS department, c.min_grade AS min_grade,
                       collect(DISTINCT prereq.code) AS prerequisites
                ORDER BY c.code
                """
                result = session.run(query)
                courses = [record.data() for record in result]
                if courses:
                    return {"courses": courses}
        finally:
            driver.close()
    except Exception:
        pass

    # Authoritative fallback
    return {"courses": curriculum.get_all_courses()}


@router.get("/departments")
def get_departments():
    """Return the 3 supported academic departments."""
    return {"departments": curriculum.get_departments()}


@router.get("/curriculum")
def get_curriculum(department: str | None = Query(default=None)):
    """Return full semester-wise curriculum (Semesters 1-8, 120 credits total)
    for the selected department.
    """
    dept = curriculum.normalize_department(department)
    courses = curriculum.get_curriculum(dept)
    by_semester = {}
    for sem in range(1, 9):
        sem_courses = [c for c in courses if int(c.get("semester") or 1) == sem]
        by_semester[f"semester_{sem}"] = {
            "semester": sem,
            "credits": sum(float(c.get("credits") or 0) for c in sem_courses),
            "courses": sem_courses,
        }
    return {
        "department": dept,
        "total_required_credits": curriculum.DEGREE_REQUIRED_CREDITS,
        "semesters": by_semester,
        "courses": courses,
    }


@router.get("/{course_code}/prerequisites")
def check_prerequisites(course_code: str):
    """Fetch direct and indirect prerequisites for a specific course."""
    code_upper = course_code.strip().upper()
    try:
        driver = get_neo4j_driver()
        try:
            with driver.session() as session:
                query = """
                MATCH (target:Course {code: $code})
                OPTIONAL MATCH (prereq:Course)-[:PREREQUISITE_FOR*1..4]->(target)
                RETURN target.code AS target_course,
                       collect(DISTINCT prereq.code) AS required_prerequisites
                """
                result = session.run(query, code=code_upper).single()
                if result and result["target_course"]:
                    return {
                        "course": result["target_course"],
                        "prerequisites": [str(p).upper() for p in (result["required_prerequisites"] or []) if p]
                    }
        finally:
            driver.close()
    except Exception:
        pass

    # Authoritative graph fallback
    course_data = curriculum.get_course(code_upper)
    if not course_data:
        raise HTTPException(status_code=404, detail=f"Course '{course_code}' not found.")

    # Trace transitive prerequisites
    visited = []
    to_visit = list(course_data.get("prerequisites", []))
    while to_visit:
        curr = to_visit.pop(0)
        if curr not in visited:
            visited.append(curr)
            parent = curriculum.get_course(curr)
            if parent:
                to_visit.extend(parent.get("prerequisites", []))

    return {
        "course": code_upper,
        "prerequisites": visited
    }
