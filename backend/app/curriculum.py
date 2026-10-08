"""
authoritative curriculum definition for:
1. Information Technology
2. Computer Science
3. AI & Data Science

Degree requirement: exactly 120 credits across Semesters 1 through 8
(15 credits per semester x 8 semesters = 120 credits).
"""

from typing import Any

DEPARTMENTS = [
    "Information Technology",
    "Computer Science",
    "AI & Data Science",
]

DEGREE_REQUIRED_CREDITS = 120

def normalize_department(dept: str | None) -> str:
    if not dept:
        return "Computer Science"
    d = dept.strip().lower()
    if d in {"it", "information technology", "infotech"}:
        return "Information Technology"
    if d in {"cs", "computer science", "comp sci"}:
        return "Computer Science"
    if d in {"ai & data science", "ai", "data science", "aids", "ai & ds", "artificial intelligence"}:
        return "AI & Data Science"
    return "Computer Science"


CURRICULA: dict[str, list[dict[str, Any]]] = {
    "Computer Science": [
        # Semester 1 (15 credits)
        {"code": "CS101", "name": "Intro to Programming", "credits": 3, "semester": 1, "department": "Computer Science", "prerequisites": [], "min_grade": "C"},
        {"code": "MATH101", "name": "Calculus I", "credits": 4, "semester": 1, "department": "Computer Science", "prerequisites": [], "min_grade": "C"},
        {"code": "CS103", "name": "Digital Logic & Systems", "credits": 4, "semester": 1, "department": "Computer Science", "prerequisites": [], "min_grade": "C"},
        {"code": "ENGL101", "name": "Technical Communication", "credits": 4, "semester": 1, "department": "Computer Science", "prerequisites": [], "min_grade": "C"},

        # Semester 2 (15 credits)
        {"code": "CS102", "name": "Data Structures", "credits": 4, "semester": 2, "department": "Computer Science", "prerequisites": ["CS101"], "min_grade": "C"},
        {"code": "MATH201", "name": "Linear Algebra", "credits": 3, "semester": 2, "department": "Computer Science", "prerequisites": ["MATH101"], "min_grade": "C"},
        {"code": "CS104", "name": "Discrete Mathematics", "credits": 4, "semester": 2, "department": "Computer Science", "prerequisites": ["MATH101"], "min_grade": "C"},
        {"code": "PHYS101", "name": "Engineering Physics", "credits": 4, "semester": 2, "department": "Computer Science", "prerequisites": [], "min_grade": "C"},

        # Semester 3 (15 credits)
        {"code": "CS201", "name": "Algorithms", "credits": 4, "semester": 3, "department": "Computer Science", "prerequisites": ["CS102"], "min_grade": "C"},
        {"code": "CS202", "name": "Computer Organization & Architecture", "credits": 4, "semester": 3, "department": "Computer Science", "prerequisites": ["CS103"], "min_grade": "C"},
        {"code": "CS203", "name": "Object-Oriented Programming", "credits": 4, "semester": 3, "department": "Computer Science", "prerequisites": ["CS102"], "min_grade": "C"},
        {"code": "MATH202", "name": "Probability & Statistics", "credits": 3, "semester": 3, "department": "Computer Science", "prerequisites": ["MATH101"], "min_grade": "C"},

        # Semester 4 (15 credits)
        {"code": "CS301", "name": "Database Systems", "credits": 3, "semester": 4, "department": "Computer Science", "prerequisites": ["CS102"], "min_grade": "C"},
        {"code": "CS204", "name": "Operating Systems", "credits": 4, "semester": 4, "department": "Computer Science", "prerequisites": ["CS202"], "min_grade": "C"},
        {"code": "CS205", "name": "Computer Networks", "credits": 4, "semester": 4, "department": "Computer Science", "prerequisites": ["CS201"], "min_grade": "C"},
        {"code": "CS206", "name": "Software Engineering Principles", "credits": 4, "semester": 4, "department": "Computer Science", "prerequisites": ["CS203"], "min_grade": "C"},

        # Semester 5 (15 credits)
        {"code": "CS401", "name": "Artificial Intelligence", "credits": 4, "semester": 5, "department": "Computer Science", "prerequisites": ["CS301"], "min_grade": "B"},
        {"code": "CS302", "name": "Theory of Computation", "credits": 4, "semester": 5, "department": "Computer Science", "prerequisites": ["CS201"], "min_grade": "C"},
        {"code": "CS303", "name": "Web Technologies & Architecture", "credits": 4, "semester": 5, "department": "Computer Science", "prerequisites": ["CS301"], "min_grade": "C"},
        {"code": "CS304", "name": "Cybersecurity Fundamentals", "credits": 3, "semester": 5, "department": "Computer Science", "prerequisites": ["CS205"], "min_grade": "C"},

        # Semester 6 (15 credits)
        {"code": "CS402", "name": "Machine Learning", "credits": 4, "semester": 6, "department": "Computer Science", "prerequisites": ["CS301"], "min_grade": "B"},
        {"code": "CS305", "name": "Distributed Systems", "credits": 4, "semester": 6, "department": "Computer Science", "prerequisites": ["CS204"], "min_grade": "C"},
        {"code": "CS306", "name": "Cloud Computing Infrastructure", "credits": 4, "semester": 6, "department": "Computer Science", "prerequisites": ["CS205"], "min_grade": "C"},
        {"code": "CS307", "name": "Compiler Design", "credits": 3, "semester": 6, "department": "Computer Science", "prerequisites": ["CS302"], "min_grade": "C"},

        # Semester 7 (15 credits)
        {"code": "CS403", "name": "Deep Learning Systems", "credits": 4, "semester": 7, "department": "Computer Science", "prerequisites": ["CS402"], "min_grade": "C"},
        {"code": "CS404", "name": "Big Data Analytics", "credits": 4, "semester": 7, "department": "Computer Science", "prerequisites": ["CS301"], "min_grade": "C"},
        {"code": "CS405", "name": "Capstone Project I", "credits": 4, "semester": 7, "department": "Computer Science", "prerequisites": ["CS206"], "min_grade": "C"},
        {"code": "CS406", "name": "Mobile Application Development", "credits": 3, "semester": 7, "department": "Computer Science", "prerequisites": ["CS303"], "min_grade": "C"},

        # Semester 8 (15 credits)
        {"code": "CS407", "name": "Capstone Project II", "credits": 6, "semester": 8, "department": "Computer Science", "prerequisites": ["CS405"], "min_grade": "C"},
        {"code": "CS408", "name": "Ethics & Professional Practice", "credits": 3, "semester": 8, "department": "Computer Science", "prerequisites": [], "min_grade": "C"},
        {"code": "CS409", "name": "Information Security Management", "credits": 3, "semester": 8, "department": "Computer Science", "prerequisites": ["CS304"], "min_grade": "C"},
        {"code": "CS410", "name": "Natural Language Processing", "credits": 3, "semester": 8, "department": "Computer Science", "prerequisites": ["CS402"], "min_grade": "C"},
    ],

    "Information Technology": [
        # Semester 1 (15 credits)
        {"code": "CS101", "name": "Intro to Programming", "credits": 3, "semester": 1, "department": "Information Technology", "prerequisites": [], "min_grade": "C"},
        {"code": "MATH101", "name": "Calculus I", "credits": 4, "semester": 1, "department": "Information Technology", "prerequisites": [], "min_grade": "C"},
        {"code": "IT101", "name": "Information Technology Essentials", "credits": 4, "semester": 1, "department": "Information Technology", "prerequisites": [], "min_grade": "C"},
        {"code": "ENGL101", "name": "Technical Communication", "credits": 4, "semester": 1, "department": "Information Technology", "prerequisites": [], "min_grade": "C"},

        # Semester 2 (15 credits)
        {"code": "CS102", "name": "Data Structures", "credits": 4, "semester": 2, "department": "Information Technology", "prerequisites": ["CS101"], "min_grade": "C"},
        {"code": "MATH201", "name": "Linear Algebra", "credits": 3, "semester": 2, "department": "Information Technology", "prerequisites": ["MATH101"], "min_grade": "C"},
        {"code": "IT102", "name": "Computer Hardware & Systems", "credits": 4, "semester": 2, "department": "Information Technology", "prerequisites": [], "min_grade": "C"},
        {"code": "IT103", "name": "Web Design Fundamentals", "credits": 4, "semester": 2, "department": "Information Technology", "prerequisites": [], "min_grade": "C"},

        # Semester 3 (15 credits)
        {"code": "ADP", "name": "Application Development Programming", "credits": 4, "semester": 3, "department": "Information Technology", "prerequisites": ["CS102"], "min_grade": "C"},
        {"code": "CS201", "name": "Algorithms", "credits": 4, "semester": 3, "department": "Information Technology", "prerequisites": ["CS102"], "min_grade": "C"},
        {"code": "IT202", "name": "Networking Fundamentals", "credits": 4, "semester": 3, "department": "Information Technology", "prerequisites": ["IT101"], "min_grade": "C"},
        {"code": "MATH202", "name": "Probability & Statistics", "credits": 3, "semester": 3, "department": "Information Technology", "prerequisites": ["MATH101"], "min_grade": "C"},

        # Semester 4 (15 credits)
        {"code": "CS301", "name": "Database Systems", "credits": 3, "semester": 4, "department": "Information Technology", "prerequisites": ["CS102"], "min_grade": "C"},
        {"code": "ADVANCED JAVA", "name": "Advanced Java Programming", "credits": 4, "semester": 4, "department": "Information Technology", "prerequisites": ["ADP"], "min_grade": "C"},
        {"code": "IT203", "name": "System Administration & Linux", "credits": 4, "semester": 4, "department": "Information Technology", "prerequisites": ["IT102"], "min_grade": "C"},
        {"code": "IT205", "name": "Human-Computer Interaction", "credits": 4, "semester": 4, "department": "Information Technology", "prerequisites": [], "min_grade": "C"},

        # Semester 5 (15 credits)
        {"code": "NETWORK SECURITY", "name": "Network Security & Cryptography", "credits": 4, "semester": 5, "department": "Information Technology", "prerequisites": ["IT202"], "min_grade": "C"},
        {"code": "IT302", "name": "Enterprise Application Architecture", "credits": 4, "semester": 5, "department": "Information Technology", "prerequisites": ["ADVANCED JAVA"], "min_grade": "C"},
        {"code": "IT303", "name": "Database Administration & SQL", "credits": 4, "semester": 5, "department": "Information Technology", "prerequisites": ["CS301"], "min_grade": "C"},
        {"code": "IT304", "name": "IT Project Management", "credits": 3, "semester": 5, "department": "Information Technology", "prerequisites": [], "min_grade": "C"},

        # Semester 6 (15 credits)
        {"code": "IT305", "name": "Cloud Infrastructure & DevOps", "credits": 4, "semester": 6, "department": "Information Technology", "prerequisites": ["IT203"], "min_grade": "C"},
        {"code": "IT306", "name": "Mobile & Wireless Networks", "credits": 4, "semester": 6, "department": "Information Technology", "prerequisites": ["IT202"], "min_grade": "C"},
        {"code": "IT307", "name": "Web Services & REST APIs", "credits": 4, "semester": 6, "department": "Information Technology", "prerequisites": ["IT302"], "min_grade": "C"},
        {"code": "IT308", "name": "Information Storage Management", "credits": 3, "semester": 6, "department": "Information Technology", "prerequisites": ["CS301"], "min_grade": "C"},

        # Semester 7 (15 credits)
        {"code": "IT401", "name": "IT Capstone Project I", "credits": 4, "semester": 7, "department": "Information Technology", "prerequisites": ["IT304"], "min_grade": "C"},
        {"code": "IT402", "name": "Cyber Forensics & Incident Response", "credits": 4, "semester": 7, "department": "Information Technology", "prerequisites": ["NETWORK SECURITY"], "min_grade": "C"},
        {"code": "IT403", "name": "Virtualization & Cloud Security", "credits": 4, "semester": 7, "department": "Information Technology", "prerequisites": ["IT305"], "min_grade": "C"},
        {"code": "IT404", "name": "IT Governance & Compliance", "credits": 3, "semester": 7, "department": "Information Technology", "prerequisites": [], "min_grade": "C"},

        # Semester 8 (15 credits)
        {"code": "IT405", "name": "IT Capstone Project II", "credits": 6, "semester": 8, "department": "Information Technology", "prerequisites": ["IT401"], "min_grade": "C"},
        {"code": "IT406", "name": "Disaster Recovery & Business Continuity", "credits": 3, "semester": 8, "department": "Information Technology", "prerequisites": ["IT404"], "min_grade": "C"},
        {"code": "IT407", "name": "Internet of Things (IoT) Systems", "credits": 3, "semester": 8, "department": "Information Technology", "prerequisites": ["IT202"], "min_grade": "C"},
        {"code": "CS408", "name": "Ethics & Professional Practice", "credits": 3, "semester": 8, "department": "Information Technology", "prerequisites": [], "min_grade": "C"},
    ],

    "AI & Data Science": [
        # Semester 1 (15 credits)
        {"code": "CS101", "name": "Intro to Programming", "credits": 3, "semester": 1, "department": "AI & Data Science", "prerequisites": [], "min_grade": "C"},
        {"code": "MATH101", "name": "Calculus I", "credits": 4, "semester": 1, "department": "AI & Data Science", "prerequisites": [], "min_grade": "C"},
        {"code": "AI101", "name": "Foundations of AI", "credits": 4, "semester": 1, "department": "AI & Data Science", "prerequisites": [], "min_grade": "C"},
        {"code": "ENGL101", "name": "Technical Communication", "credits": 4, "semester": 1, "department": "AI & Data Science", "prerequisites": [], "min_grade": "C"},

        # Semester 2 (15 credits)
        {"code": "CS102", "name": "Data Structures", "credits": 4, "semester": 2, "department": "AI & Data Science", "prerequisites": ["CS101"], "min_grade": "C"},
        {"code": "MATH201", "name": "Linear Algebra", "credits": 3, "semester": 2, "department": "AI & Data Science", "prerequisites": ["MATH101"], "min_grade": "C"},
        {"code": "AI102", "name": "Python for Data Science", "credits": 4, "semester": 2, "department": "AI & Data Science", "prerequisites": ["CS101"], "min_grade": "C"},
        {"code": "MATH102", "name": "Discrete Math for AI", "credits": 4, "semester": 2, "department": "AI & Data Science", "prerequisites": ["MATH101"], "min_grade": "C"},

        # Semester 3 (15 credits)
        {"code": "CS201", "name": "Algorithms", "credits": 4, "semester": 3, "department": "AI & Data Science", "prerequisites": ["CS102"], "min_grade": "C"},
        {"code": "AI201", "name": "Probability & Statistics for Data Science", "credits": 4, "semester": 3, "department": "AI & Data Science", "prerequisites": ["MATH101"], "min_grade": "C"},
        {"code": "CS301", "name": "Database Systems", "credits": 3, "semester": 3, "department": "AI & Data Science", "prerequisites": ["CS102"], "min_grade": "C"},
        {"code": "AI202", "name": "Data Wrangling & Analysis", "credits": 4, "semester": 3, "department": "AI & Data Science", "prerequisites": ["AI102"], "min_grade": "C"},

        # Semester 4 (15 credits)
        {"code": "AI203", "name": "Statistical Machine Learning", "credits": 4, "semester": 4, "department": "AI & Data Science", "prerequisites": ["AI201", "MATH201"], "min_grade": "C"},
        {"code": "AI204", "name": "Optimization for AI", "credits": 4, "semester": 4, "department": "AI & Data Science", "prerequisites": ["MATH201"], "min_grade": "C"},
        {"code": "AI205", "name": "Data Visualization & Storytelling", "credits": 4, "semester": 4, "department": "AI & Data Science", "prerequisites": ["AI202"], "min_grade": "C"},
        {"code": "AI206", "name": "Big Data Structures", "credits": 3, "semester": 4, "department": "AI & Data Science", "prerequisites": ["CS102"], "min_grade": "C"},

        # Semester 5 (15 credits)
        {"code": "CS401", "name": "Artificial Intelligence", "credits": 4, "semester": 5, "department": "AI & Data Science", "prerequisites": ["CS301"], "min_grade": "B"},
        {"code": "AI301", "name": "Machine Learning Systems", "credits": 4, "semester": 5, "department": "AI & Data Science", "prerequisites": ["AI203"], "min_grade": "C"},
        {"code": "AI302", "name": "Deep Learning & Neural Networks", "credits": 4, "semester": 5, "department": "AI & Data Science", "prerequisites": ["AI204"], "min_grade": "C"},
        {"code": "AI303", "name": "Data Engineering & Pipelines", "credits": 3, "semester": 5, "department": "AI & Data Science", "prerequisites": ["CS301"], "min_grade": "C"},

        # Semester 6 (15 credits)
        {"code": "CS402", "name": "Machine Learning", "credits": 4, "semester": 6, "department": "AI & Data Science", "prerequisites": ["CS301"], "min_grade": "B"},
        {"code": "AI304", "name": "Computer Vision", "credits": 4, "semester": 6, "department": "AI & Data Science", "prerequisites": ["AI302"], "min_grade": "C"},
        {"code": "AI305", "name": "Natural Language Processing", "credits": 4, "semester": 6, "department": "AI & Data Science", "prerequisites": ["AI302"], "min_grade": "C"},
        {"code": "AI306", "name": "Big Data Processing Frameworks", "credits": 3, "semester": 6, "department": "AI & Data Science", "prerequisites": ["AI303"], "min_grade": "C"},

        # Semester 7 (15 credits)
        {"code": "AI401", "name": "AI & Data Science Capstone I", "credits": 4, "semester": 7, "department": "AI & Data Science", "prerequisites": ["AI301"], "min_grade": "C"},
        {"code": "AI402", "name": "Reinforcement Learning", "credits": 4, "semester": 7, "department": "AI & Data Science", "prerequisites": ["AI302"], "min_grade": "C"},
        {"code": "AI403", "name": "Generative AI & LLMs", "credits": 4, "semester": 7, "department": "AI & Data Science", "prerequisites": ["AI305"], "min_grade": "C"},
        {"code": "AI404", "name": "MLOps & Model Governance", "credits": 3, "semester": 7, "department": "AI & Data Science", "prerequisites": ["AI301"], "min_grade": "C"},

        # Semester 8 (15 credits)
        {"code": "AI405", "name": "AI & Data Science Capstone II", "credits": 6, "semester": 8, "department": "AI & Data Science", "prerequisites": ["AI401"], "min_grade": "C"},
        {"code": "AI406", "name": "Responsible AI & Ethics", "credits": 3, "semester": 8, "department": "AI & Data Science", "prerequisites": [], "min_grade": "C"},
        {"code": "AI407", "name": "Knowledge Graphs & Graph ML", "credits": 3, "semester": 8, "department": "AI & Data Science", "prerequisites": ["AI302"], "min_grade": "C"},
        {"code": "AI408", "name": "Time Series & Forecasting", "credits": 3, "semester": 8, "department": "AI & Data Science", "prerequisites": ["AI201"], "min_grade": "C"},
    ],
}


def get_departments() -> list[str]:
    return list(DEPARTMENTS)


def get_curriculum(department: str | None = None) -> list[dict[str, Any]]:
    dept = normalize_department(department)
    return [dict(c) for c in CURRICULA.get(dept, CURRICULA["Computer Science"])]


def get_course(code: str, department: str | None = None) -> dict[str, Any] | None:
    target = code.strip().upper()
    curriculum = get_curriculum(department)
    for c in curriculum:
        if c["code"].upper() == target:
            return dict(c)
    # Search across all curricula if not found in given department
    for dept_courses in CURRICULA.values():
        for c in dept_courses:
            if c["code"].upper() == target:
                return dict(c)
    return None


def get_all_courses() -> list[dict[str, Any]]:
    seen = set()
    combined = []
    for dept in DEPARTMENTS:
        for c in CURRICULA[dept]:
            if c["code"].upper() not in seen:
                seen.add(c["code"].upper())
                combined.append(dict(c))
    return combined


def calculate_progress(completed_codes: list[str], department: str | None = None) -> dict[str, Any]:
    curriculum = get_curriculum(department)
    curr_map = {c["code"].upper(): c for c in curriculum}

    unique_completed = set()
    completed_credits = 0.0
    semester_completed: dict[int, float] = {s: 0.0 for s in range(1, 9)}

    for code in completed_codes:
        upper = str(code).strip().upper()
        if upper in curr_map and upper not in unique_completed:
            unique_completed.add(upper)
            course = curr_map[upper]
            cr = float(course.get("credits") or 0)
            completed_credits += cr
            sem = int(course.get("semester") or 1)
            if sem in semester_completed:
                semester_completed[sem] += cr

    remaining_credits = max(0.0, DEGREE_REQUIRED_CREDITS - completed_credits)
    progress_percentage = min(100.0, round((completed_credits / DEGREE_REQUIRED_CREDITS) * 100, 1))

    return {
        "degree_required_credits": DEGREE_REQUIRED_CREDITS,
        "completed_credits": completed_credits,
        "remaining_credits": remaining_credits,
        "progress_percentage": progress_percentage,
        "completed_course_count": len(unique_completed),
        "semester_breakdown": semester_completed,
    }
