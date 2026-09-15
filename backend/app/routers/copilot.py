import os
import re
from datetime import date

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from neo4j import GraphDatabase

from app.security import inspect_ai_input, require_student_scope, require_session

from app.config import (
    MYSQL_DATABASE_URL,
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
    OLLAMA_MODEL,
)

try:
    import ollama
except ImportError:
    ollama = None

router = APIRouter(prefix="/api/v1/copilot", tags=["Academic Copilot"])
mysql_engine = create_engine(MYSQL_DATABASE_URL, pool_pre_ping=True)

DAILY_LIMIT = int(os.getenv("COPILOT_DAILY_LIMIT", "15"))


def get_neo4j_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))


class ChatRequest(BaseModel):
    user_id: int
    user_message: str
    target_track: str = "AI & Data Science"
    # Kept only for frontend compatibility. The backend does NOT trust this field.
    completed_courses: list[str] = []
    conversation_history: list[dict[str, str]] = []


class WhatIfRequest(BaseModel):
    user_id: int
    action: str = "take"  # take | skip
    course_codes: list[str] = []


def _course_snapshot(course, catalog, completed_set):
    by_code = {c["code"]: c for c in catalog}
    missing = [p for p in course["prereqs"] if p in by_code and p not in completed_set]
    return {
        "code": course["code"],
        "name": course["name"],
        "credits": course["credits"],
        "semester": course["semester"],
        "prerequisites": course["prereqs"],
        "missing_prerequisites": missing,
        "eligible": not missing and course["code"] not in completed_set,
        "already_completed": course["code"] in completed_set,
    }


def _what_if_simulation(catalog, completed, action, requested_codes):
    valid = {c["code"]: c for c in catalog}
    baseline = set(completed) & set(valid)
    requested = []
    invalid = []
    for raw in requested_codes:
        code = str(raw).strip().upper()
        if not code:
            continue
        if code in valid and code not in requested:
            requested.append(code)
        elif code not in valid and code not in invalid:
            invalid.append(code)

    if not requested:
        raise HTTPException(status_code=400, detail="Select at least one valid curriculum course for the simulation.")
    if action not in {"take", "skip"}:
        raise HTTPException(status_code=400, detail="Simulation action must be 'take' or 'skip'.")

    baseline_completed = set(baseline)
    baseline_completed_credits = sum(float(valid[c]["credits"] or 0) for c in baseline_completed)
    _, baseline_ready, baseline_locked = _audit(catalog, baseline_completed)
    baseline_ready_codes = {c["code"] for c in baseline_ready}

    simulated = set(baseline_completed)
    selected_results = []
    blocked = []

    if action == "skip":
        for code in requested:
            if code not in simulated:
                selected_results.append({**_course_snapshot(valid[code], catalog, simulated), "action_result": "not_completed"})
                continue
            simulated.remove(code)
            selected_results.append({**_course_snapshot(valid[code], catalog, simulated), "action_result": "removed_from_simulation"})
    else:
        # Apply eligible requested courses iteratively so a scenario such as
        # [MATH201, CS402] can model both being taken in sequence.
        remaining = list(requested)
        while remaining:
            progressed = False
            for code in list(remaining):
                course = valid[code]
                if code in simulated:
                    selected_results.append({**_course_snapshot(course, catalog, simulated), "action_result": "already_completed"})
                    remaining.remove(code)
                    progressed = True
                    continue
                missing = [p for p in course["prereqs"] if p in valid and p not in simulated]
                if not missing:
                    simulated.add(code)
                    selected_results.append({**_course_snapshot(course, catalog, simulated), "action_result": "added_to_simulation"})
                    remaining.remove(code)
                    progressed = True
            if not progressed:
                for code in remaining:
                    course = valid[code]
                    snap = _course_snapshot(course, catalog, simulated)
                    blocked.append(snap)
                    selected_results.append({**snap, "action_result": "blocked_by_prerequisites"})
                break

    _, simulated_ready, simulated_locked = _audit(catalog, simulated)
    simulated_ready_codes = {c["code"] for c in simulated_ready}
    simulated_locked_codes = {c["code"] for c in simulated_locked}

    newly_eligible = sorted(simulated_ready_codes - baseline_ready_codes)
    newly_locked = sorted(simulated_locked_codes - {c["code"] for c in baseline_locked})
    no_longer_eligible = sorted(baseline_ready_codes - simulated_ready_codes)

    simulated_credits = sum(float(valid[c]["credits"] or 0) for c in simulated)
    delta = simulated_credits - baseline_completed_credits

    return {
        "action": action,
        "requested_courses": [valid[c] for c in requested],
        "invalid_course_codes": invalid,
        "selected_results": selected_results,
        "blocked_courses": blocked,
        "baseline": {
            "completed_courses": sorted(baseline_completed),
            "eligible_courses": sorted(baseline_ready_codes),
            "credits": baseline_completed_credits,
        },
        "simulated": {
            "completed_courses": sorted(simulated),
            "eligible_courses": sorted(simulated_ready_codes),
            "locked_courses": sorted(simulated_locked_codes),
            "credits": simulated_credits,
        },
        "impact": {
            "newly_eligible": newly_eligible,
            "newly_locked": newly_locked,
            "no_longer_eligible": no_longer_eligible,
            "credit_delta": delta,
        },
        "simulation_only": True,
        "database_changed": False,
        "source": "Neo4j curriculum graph + MySQL student completion record",
    }


def init_copilot_usage_storage():
    """Create persistent per-student daily Ollama usage tracking."""
    with mysql_engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS copilot_ai_usage (
                student_id INT NOT NULL,
                usage_date DATE NOT NULL,
                question_count INT NOT NULL DEFAULT 0,
                PRIMARY KEY (student_id, usage_date),
                CONSTRAINT fk_copilot_ai_usage_student
                    FOREIGN KEY (student_id) REFERENCES copilot_students(id)
                    ON DELETE CASCADE
            )
        """))


def _student(student_id: int):
    with mysql_engine.connect() as conn:
        row = conn.execute(text("""
            SELECT id, name, email, department, track, semester, role
            FROM copilot_students
            WHERE id = :id
        """), {"id": student_id}).mappings().first()
    return dict(row) if row else None


def _completed(student_id: int) -> list[str]:
    with mysql_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT course_code
            FROM copilot_student_courses
            WHERE student_id = :id AND status = 'completed'
            ORDER BY enrolled_at, course_code
        """), {"id": student_id}).scalars().all()
    return [str(x).upper() for x in rows]


def _usage_count(student_id: int) -> int:
    with mysql_engine.connect() as conn:
        value = conn.execute(text("""
            SELECT question_count
            FROM copilot_ai_usage
            WHERE student_id = :student_id AND usage_date = :usage_date
        """), {"student_id": student_id, "usage_date": date.today()}).scalar()
    return int(value or 0)


def _reserve_ai_question(student_id: int) -> tuple[bool, int]:
    """Atomically reserve one Ollama request if the daily limit has not been reached."""
    today = date.today()
    with mysql_engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO copilot_ai_usage (student_id, usage_date, question_count)
            VALUES (:student_id, :usage_date, 0)
            ON DUPLICATE KEY UPDATE question_count = question_count
        """), {"student_id": student_id, "usage_date": today})

        result = conn.execute(text("""
            UPDATE copilot_ai_usage
            SET question_count = question_count + 1
            WHERE student_id = :student_id
              AND usage_date = :usage_date
              AND question_count < :limit
        """), {
            "student_id": student_id,
            "usage_date": today,
            "limit": DAILY_LIMIT,
        })
        if result.rowcount != 1:
            count = conn.execute(text("""
                SELECT question_count FROM copilot_ai_usage
                WHERE student_id = :student_id AND usage_date = :usage_date
            """), {"student_id": student_id, "usage_date": today}).scalar()
            return False, int(count or 0)

        count = conn.execute(text("""
            SELECT question_count FROM copilot_ai_usage
            WHERE student_id = :student_id AND usage_date = :usage_date
        """), {"student_id": student_id, "usage_date": today}).scalar()
        return True, int(count or 0)


def _release_ai_question(student_id: int):
    """Give the reserved slot back if the Ollama request failed."""
    with mysql_engine.begin() as conn:
        conn.execute(text("""
            UPDATE copilot_ai_usage
            SET question_count = GREATEST(question_count - 1, 0)
            WHERE student_id = :student_id AND usage_date = :usage_date
        """), {"student_id": student_id, "usage_date": date.today()})


def build_catalog(track: str):
    """Return the verified course catalog and prerequisite graph for the selected track."""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            query = """
            MATCH (c:Course)
            OPTIONAL MATCH (t:Track {name: $track})<-[:BELONGS_TO_TRACK]-(tc:Course)
            WHERE tc IS NOT NULL AND tc.code = c.code
            OPTIONAL MATCH (prereq:Course)-[:PREREQUISITE_FOR]->(c)
            RETURN c.code AS code,
                   c.name AS name,
                   c.credits AS credits,
                   c.min_grade AS min_grade,
                   c.semester AS semester,
                   collect(DISTINCT prereq.code) AS prereqs
            ORDER BY c.code
            """
            rows = [record.data() for record in session.run(query, track=track)]
            # If the graph does not have track relationships, use the complete Course catalog.
            if not rows:
                rows = [record.data() for record in session.run("""
                    MATCH (c:Course)
                    OPTIONAL MATCH (prereq:Course)-[:PREREQUISITE_FOR]->(c)
                    RETURN c.code AS code, c.name AS name, c.credits AS credits,
                           c.min_grade AS min_grade, c.semester AS semester,
                           collect(DISTINCT prereq.code) AS prereqs
                    ORDER BY c.code
                """)]
            return rows
    finally:
        driver.close()


def _normalize_catalog(rows):
    catalog = []
    for row in rows:
        if not row.get("code"):
            continue
        catalog.append({
            "code": str(row["code"]).upper(),
            "name": row.get("name") or str(row["code"]),
            "credits": row.get("credits"),
            "min_grade": row.get("min_grade"),
            "semester": row.get("semester"),
            "prereqs": [str(p).upper() for p in (row.get("prereqs") or []) if p],
        })
    return catalog


def _audit(catalog, completed):
    completed_set = set(completed)
    valid_codes = {c["code"] for c in catalog}
    completed_valid = completed_set & valid_codes
    ready, locked = [], []
    for course in catalog:
        if course["code"] in completed_valid:
            continue
        missing = [p for p in course["prereqs"] if p in valid_codes and p not in completed_valid]
        item = {**course, "missing_prerequisites": missing}
        if not missing:
            ready.append(item)
        else:
            locked.append(item)
    return completed_valid, ready, locked


def _find_course(question: str, catalog):
    q = question.lower()
    # Prefer exact course code mentions.
    for c in catalog:
        if re.search(rf"\b{re.escape(c['code'].lower())}\b", q):
            return c
    # Then exact course-name phrase.
    for c in sorted(catalog, key=lambda x: len(str(x["name"])), reverse=True):
        name = str(c["name"]).strip().lower()
        if len(name) >= 4 and name in q:
            return c
    return None


def _find_courses(question: str, catalog):
    """Find every verified course explicitly mentioned in a question, preserving question order."""
    q = question.lower()
    found = []
    by_code = {c["code"]: c for c in catalog}

    # Course codes are the safest signal. Avoid matching the same code twice.
    for match in re.finditer(r"\b[A-Za-z]{2,}\d{2,4}\b", question):
        code = match.group(0).upper()
        if code in by_code and code not in {c["code"] for c in found}:
            found.append(by_code[code])

    # Also support exact verified course names.
    for c in sorted(catalog, key=lambda x: len(str(x["name"])), reverse=True):
        name = str(c["name"]).strip().lower()
        if len(name) >= 4 and name in q and c["code"] not in {x["code"] for x in found}:
            found.append(c)

    # Restore the order in which course names/codes appear in the user's question.
    def position(course):
        positions = []
        code_pos = q.find(course["code"].lower())
        if code_pos >= 0:
            positions.append(code_pos)
        name_pos = q.find(str(course["name"]).lower())
        if name_pos >= 0:
            positions.append(name_pos)
        return min(positions) if positions else 10**9

    return sorted(found, key=position)


def _comparison_answer(question, student, catalog, completed):
    """Give a verified, personalized comparison without asking Qwen to invent facts."""
    courses = _find_courses(question, catalog)
    if len(courses) < 2:
        return None

    completed_valid, ready, locked = _audit(catalog, completed)
    ready_codes = {c["code"] for c in ready}
    by_code = {c["code"]: c for c in catalog}

    lines = ["Here is a comparison based on your current curriculum and academic record:"]
    for c in courses:
        missing = [p for p in c["prereqs"] if p in by_code and p not in completed_valid]
        eligibility = "eligible now" if not missing and c["code"] not in completed_valid else (
            "already completed" if c["code"] in completed_valid else "not eligible yet"
        )
        prereqs = ", ".join(c["prereqs"]) if c["prereqs"] else "None"
        credits = c["credits"] if c["credits"] is not None else "not specified"
        semester = c["semester"] if c["semester"] is not None else "not specified"
        extra = f"; missing: {', '.join(missing)}" if missing else ""
        lines.append(
            f"- {c['code']} — {c['name']}: {eligibility}; {credits} credit(s); "
            f"semester {semester}; prerequisites: {prereqs}{extra}."
        )

    not_completed = [c for c in courses if c["code"] not in completed_valid]
    currently_eligible = [c for c in not_completed if c["code"] in ready_codes]

    # A recommendation is only made from objective, verified pathway criteria.
    if len(currently_eligible) == 1:
        winner = currently_eligible[0]
        recommendation = (
            f"Based on your current record, I would prioritize {winner['code']} — {winner['name']} "
            f"because it is currently eligible for you. This is a pathway recommendation, "
            f"not a claim that the course is universally better."
        )
    elif currently_eligible:
        same_semester = [c for c in currently_eligible if c.get("semester") == student.get("semester")]
        if len(same_semester) == 1:
            winner = same_semester[0]
            recommendation = (
                f"Based on your current record, {winner['code']} — {winner['name']} is the clearest "
                f"priority because it is currently eligible and matches your current semester. "
                f"The other eligible option(s) are also valid choices."
            )
        else:
            names = ", ".join(f"{c['code']} — {c['name']}" for c in currently_eligible)
            recommendation = (
                f"You are currently eligible for {names}. Your curriculum data does not define a "
                f"single universally better choice among them, so I would not invent one."
            )
    elif not_completed:
        nearest = sorted(not_completed, key=lambda c: len([p for p in c["prereqs"] if p not in completed_valid]))
        recommendation = (
            f"None of the compared courses is currently eligible based on the verified prerequisites. "
            f"The closest option by number of missing prerequisites is {nearest[0]['code']} — {nearest[0]['name']}."
        )
    else:
        recommendation = "All compared courses are already completed in your verified curriculum record."

    return "\n".join(lines) + "\n\n" + recommendation


def _course_status(course, catalog, completed):
    """Return verified personalized status for one course."""
    completed_valid, ready, locked = _audit(catalog, completed)
    by_code = {c["code"]: c for c in catalog}
    missing = [p for p in course["prereqs"] if p in by_code and p not in completed_valid]
    if course["code"] in completed_valid:
        status = "already completed"
    elif not missing:
        status = "currently eligible"
    else:
        status = "not currently eligible"
    return status, missing, completed_valid


def _course_info_answer(question, student, catalog, completed):
    """Answer open-ended questions about a recognized course from verified data."""
    courses = _find_courses(question, catalog)
    if len(courses) != 1:
        return None

    course = courses[0]
    q = question.lower().strip()
    status, missing, completed_valid = _course_status(course, catalog, completed)

    # These are intentionally broad so natural wording such as "what about MATH201?"
    # is treated as a course question even when it contains no predefined keyword.
    course_info_markers = [
        "what about", "tell me about", "about this course", "about the course",
        "what is", "what's", "details", "information", "info", "explain",
        "what happens if i take", "what happens if i choose", "if i take",
        "if i choose", "should i take", "should i choose", "is it good for me",
        "is this good for me", "useful for me", "worth taking"
    ]
    if not any(marker in q for marker in course_info_markers):
        # A bare course code/name is also a legitimate "tell me about this course" query.
        normalized = re.sub(r"[^a-z0-9]+", " ", q).strip()
        if normalized not in {
            course["code"].lower(),
            str(course["name"]).lower(),
            f"{course['code'].lower()} {str(course['name']).lower()}",
        }:
            return None

    by_code = {c["code"]: c for c in catalog}
    prereqs = ", ".join(
        f"{p} — {by_code[p]['name']}" if p in by_code else p
        for p in course["prereqs"]
    ) if course["prereqs"] else "None listed"
    credits = course["credits"] if course["credits"] is not None else "Not specified"
    semester = course["semester"] if course["semester"] is not None else "Not specified"

    lines = [
        f"**{course['code']} — {course['name']}**",
        f"• Credits: {credits}",
        f"• Curriculum semester: {semester}",
        f"• Prerequisites: {prereqs}",
        f"• Your current status: {status}."
    ]
    if missing:
        lines.append("• Missing prerequisites: " + ", ".join(missing) + ".")

    if any(x in q for x in ["what happens if", "if i take", "if i choose", "should i take", "should i choose", "is it good for me", "useful for me", "worth taking"]):
        if status == "currently eligible":
            lines.append(
                "Based on your verified academic record, choosing this course is currently possible. "
                "It will count as a curriculum course once completed."
            )
        elif status == "already completed":
            lines.append("You have already completed this curriculum course, so choosing it again is not needed in your current record.")
        else:
            lines.append(
                "You cannot currently take it under the verified prerequisite rules. "
                "Complete the missing prerequisite(s) first: " + ", ".join(missing) + "."
            )
    else:
        lines.append("These details come from your verified curriculum and current academic record.")
    return "\n".join(lines)


def _deterministic_answer(question, student, catalog, completed):
    """Answer fact-based questions without consuming an Ollama request."""
    q = question.lower().strip()
    completed_valid, ready, locked = _audit(catalog, completed)

    target = _find_course(question, catalog)
    asks_eligibility = any(x in q for x in [
        "eligible", "eligibility", "can i take", "can i enroll", "allowed to take"
    ])
    asks_missing = "missing prerequisite" in q or "missing prerequisites" in q or (
        "prerequisite" in q and any(x in q for x in ["missing", "need", "needed"])
    )
    asks_progress = any(x in q for x in [
        "my progress", "how am i progressing", "progress in my degree",
        "credits have i", "how many credits"
    ])
    asks_completed = "completed courses" in q or "courses have i completed" in q
    asks_next = "next semester" in q or "what should i take next" in q

    comparison_words = ["which is better", "which should i choose", "what should i choose", "which one should i take", "compare", "better out of", "which is best"]
    if any(x in q for x in comparison_words):
        comparison = _comparison_answer(question, student, catalog, completed)
        if comparison:
            return comparison

    if target and (asks_eligibility or asks_missing):
        missing = [p for p in target["prereqs"] if p not in completed_valid]
        if asks_missing:
            if missing:
                names = []
                by_code = {c["code"]: c for c in catalog}
                for code in missing:
                    names.append(f"{code} — {by_code.get(code, {}).get('name', code)}")
                return (
                    f"You are missing {len(missing)} prerequisite(s) for "
                    f"{target['code']} — {target['name']}: " + "; ".join(names) + "."
                )
            return f"You are not missing any listed prerequisites for {target['code']} — {target['name']}."
        if missing:
            return (
                f"No. You are currently not eligible for {target['code']} — {target['name']}. "
                f"Missing prerequisite(s): {', '.join(missing)}."
            )
        return f"Yes. You are currently eligible for {target['code']} — {target['name']}. All listed prerequisites are satisfied."

    if asks_completed:
        if not completed_valid:
            return "No completed courses from the current Neo4j curriculum are recorded for this student."
        by_code = {c["code"]: c for c in catalog}
        details = [f"{code} — {by_code[code]['name']}" for code in sorted(completed_valid)]
        return "Your completed curriculum courses are: " + "; ".join(details) + "."

    if asks_progress:
        by_code = {c["code"]: c for c in catalog}
        credits = sum(float(by_code[c]["credits"] or 0) for c in completed_valid if c in by_code)
        return (
            f"You have completed {len(completed_valid)} curriculum course(s) "
            f"for {credits:g} credits. Your current semester is {student['semester']}."
        )

    if asks_next:
        try:
            next_sem = int(student["semester"]) + 1
            eligible_next = [c for c in ready if c.get("semester") is not None and int(c["semester"]) == next_sem]
        except (TypeError, ValueError):
            next_sem = None
            eligible_next = []
        choices = eligible_next or ready
        if not choices:
            return "There are no currently eligible courses in the supplied curriculum."
        names = [f"{c['code']} — {c['name']}" for c in choices[:6]]
        qualifier = f"matching semester {next_sem}" if eligible_next else "currently eligible"
        return f"Based on your verified curriculum, the {qualifier} course options are: " + "; ".join(names) + "."

    # Any natural-language question that clearly points to one verified course gets
    # a verified course card before we ever fall through to the LLM.
    course_info = _course_info_answer(question, student, catalog, completed)
    if course_info:
        return course_info

    return None


def _asks_general_scope(question: str) -> bool:
    q = question.lower()
    return any(x in q for x in [
        "scope", "future", "career", "job", "jobs", "career path", "opportunities",
        "industry", "demand", "worth it", "useful", "salary", "pay"
    ])


def answer_with_ollama(system_prompt: str, user_message: str) -> str:
    if not ollama:
        raise RuntimeError("Ollama Python package is not installed.")
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        options={
            "num_gpu": 0,
            "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "250")),
            "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "2048")),
            "temperature": 0.1,
        },
        keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "5m"),
    )
    return response["message"]["content"].strip()


def _recommendation_engine(catalog, student, completed):
    """Build transparent, deterministic pathway recommendations from verified graph data.

    No LLM is used here and no student record is modified. Recommendations are based only on:
    - current eligibility from prerequisite rules
    - the student's current semester
    - newly eligible courses created by a one-course simulation
    - prerequisite bottlenecks shared by locked courses
    """
    completed_valid, ready, locked = _audit(catalog, completed)
    by_code = {c["code"]: c for c in catalog}
    ready_codes = {c["code"] for c in ready}
    current_semester = int(student.get("semester") or 1)

    recommendations = []
    for course in ready:
        simulated = set(completed_valid)
        simulated.add(course["code"])
        _, after_ready, _ = _audit(catalog, simulated)
        after_ready_codes = {c["code"] for c in after_ready}
        newly_unlocked = sorted(after_ready_codes - ready_codes - {course["code"]})

        semester = course.get("semester")
        try:
            semester_num = int(semester) if semester is not None else None
        except (TypeError, ValueError):
            semester_num = None
        semester_match = semester_num == current_semester
        semester_distance = abs(semester_num - current_semester) if semester_num is not None else 99

        reasons = ["currently eligible"]
        if semester_match:
            reasons.append(f"matches your current semester ({current_semester})")
        if newly_unlocked:
            reasons.append(f"can make {len(newly_unlocked)} additional course(s) eligible")

        # Transparent ranking: current-semester fit first, then pathway unlock impact,
        # then proximity to the student's semester. No subjective career/quality claim.
        rank_key = (
            0 if semester_match else 1,
            -len(newly_unlocked),
            semester_distance,
            course["code"],
        )
        recommendations.append({
            "code": course["code"],
            "name": course["name"],
            "credits": course["credits"],
            "semester": course["semester"],
            "prerequisites": course["prereqs"],
            "status": "eligible_now",
            "newly_eligible_after_selection": newly_unlocked,
            "unlock_count": len(newly_unlocked),
            "semester_match": semester_match,
            "reasons": reasons,
            "rank_key": rank_key,
        })

    recommendations.sort(key=lambda item: item["rank_key"])
    for index, item in enumerate(recommendations, start=1):
        item["rank"] = index
        item.pop("rank_key", None)
        if index == 1:
            item["priority"] = "Top priority"
        elif item["semester_match"]:
            item["priority"] = "Strong option"
        else:
            item["priority"] = "Available option"

    # Identify prerequisite bottlenecks: a missing prerequisite that blocks multiple
    # courses and is itself eligible to take now.
    blocker_counts = {}
    blocked_by = {}
    for course in locked:
        for prereq in course.get("missing_prerequisites", []):
            if prereq in by_code and prereq not in completed_valid:
                blocker_counts[prereq] = blocker_counts.get(prereq, 0) + 1
                blocked_by.setdefault(prereq, []).append(course["code"])

    blockers = []
    for code, count in blocker_counts.items():
        prereq_course = by_code[code]
        missing_for_prereq = [p for p in prereq_course["prereqs"] if p in by_code and p not in completed_valid]
        if not missing_for_prereq:
            blockers.append({
                "code": code,
                "name": prereq_course["name"],
                "credits": prereq_course["credits"],
                "semester": prereq_course["semester"],
                "blocked_course_codes": sorted(set(blocked_by[code])),
                "blocked_course_count": count,
                "eligible_now": code in ready_codes,
                "reason": (
                    f"Completing {code} can address a prerequisite shared by {count} course(s)."
                    if count > 1 else
                    f"Completing {code} addresses a prerequisite for {blocked_by[code][0]}."
                ),
            })
    blockers.sort(key=lambda x: (-x["blocked_course_count"], not x["eligible_now"], x["code"]))

    # If nothing is eligible, expose the closest prerequisite actions rather than an empty dashboard.
    if not recommendations:
        near_locked = sorted(
            locked,
            key=lambda c: (len(c.get("missing_prerequisites", [])), c["code"])
        )[:5]
        next_actions = [{
            "code": c["code"],
            "name": c["name"],
            "status": "blocked",
            "missing_prerequisites": c.get("missing_prerequisites", []),
            "reason": f"Complete prerequisite(s): {', '.join(c.get('missing_prerequisites', [])) or 'not specified'}.",
        } for c in near_locked]
    else:
        next_actions = []

    return {
        "student_id": student["id"],
        "student_name": student["name"],
        "current_semester": current_semester,
        "track": student["track"],
        "recommendations": recommendations[:8],
        "pathway_blockers": blockers[:8],
        "next_actions": next_actions,
        "methodology": [
            "Only courses that are currently eligible are recommended as immediate options.",
            "Current-semester courses are prioritized when semester data is available.",
            "Courses that unlock additional eligible courses receive higher pathway priority.",
            "Shared missing prerequisites are surfaced as pathway blockers.",
            "No career, salary, difficulty, or popularity claim is used in the ranking.",
        ],
        "source": "Neo4j curriculum graph + MySQL student completion record",
        "ai_used": False,
        "database_changed": False,
    }


@router.get("/recommendations/{user_id}")
def get_recommendations(user_id: int, x_demo_role: str | None = Header(default=None), x_demo_student_id: str | None = Header(default=None)):
    """Return transparent, personalized next-course recommendations without using the LLM."""
    try:
        require_student_scope(x_demo_role, x_demo_student_id, user_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    student = _student(user_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")
    try:
        catalog = _normalize_catalog(build_catalog(student["track"]))
        if not catalog:
            raise HTTPException(status_code=503, detail="No curriculum courses were found in Neo4j.")
        completed = _completed(user_id)
        return _recommendation_engine(catalog, student, completed)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation Engine Error: {str(e)}")


@router.post("/what-if")
def run_what_if(payload: WhatIfRequest, x_demo_role: str | None = Header(default=None), x_demo_student_id: str | None = Header(default=None)):
    """Run a hypothetical pathway simulation without changing the student's database record."""
    try:
        require_student_scope(x_demo_role, x_demo_student_id, payload.user_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    student = _student(payload.user_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")
    try:
        catalog = _normalize_catalog(build_catalog(student["track"]))
        if not catalog:
            raise HTTPException(status_code=503, detail="No curriculum courses were found in Neo4j.")
        completed = _completed(payload.user_id)
        result = _what_if_simulation(catalog, completed, payload.action.lower().strip(), payload.course_codes)
        result["user_id"] = payload.user_id
        result["student_name"] = student["name"]
        result["track"] = student["track"]
        result["semester"] = student["semester"]
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"What-If Simulation Error: {str(e)}")


@router.post("/chat")
def chat_with_copilot(payload: ChatRequest, x_demo_role: str | None = Header(default=None), x_demo_student_id: str | None = Header(default=None)):
    try:
        require_student_scope(x_demo_role, x_demo_student_id, payload.user_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    decision = inspect_ai_input(payload.user_message)
    if not decision.allowed:
        raise HTTPException(status_code=400, detail=decision.reason)

    student = _student(payload.user_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    try:
        catalog = _normalize_catalog(build_catalog(student["track"]))
        if not catalog:
            raise HTTPException(status_code=503, detail="No curriculum courses were found in Neo4j.")

        completed = _completed(payload.user_id)

        # Ignore legacy free-text/invalid completion records that are not real Neo4j course codes.
        completed_valid, ready, locked = _audit(catalog, completed)

        deterministic = _deterministic_answer(payload.user_message, student, catalog, completed)
        if deterministic:
            return {
                "user_id": payload.user_id,
                "user_message": payload.user_message,
                "copilot_response": deterministic,
                "llm_provider": "Academic Rules Engine",
                "ai_used": False,
                "usage_count": _usage_count(payload.user_id),
                "daily_limit": DAILY_LIMIT,
                "sources": [
                    {"source": "Neo4j curriculum knowledge graph", "scope": "Course catalog and prerequisite relationships"},
                    {"source": "MySQL student record", "scope": "Student profile and recorded completion status"},
                ],
            }

        allowed, usage_count = _reserve_ai_question(payload.user_id)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Daily AI question limit reached ({DAILY_LIMIT}/{DAILY_LIMIT}). It resets tomorrow."
            )

        by_code = {c["code"]: c for c in catalog}
        completed_details = [
            f"{code} — {by_code[code]['name']}"
            for code in sorted(completed_valid)
            if code in by_code
        ]

        mentioned_courses = _find_courses(payload.user_message, catalog)
        # For course-specific natural-language questions, send only the relevant
        # verified records to the small model. This dramatically reduces confusion.
        if mentioned_courses:
            context_courses = mentioned_courses
        else:
            context_courses = catalog

        catalog_details = []
        for c in context_courses:
            prereqs = ", ".join(c["prereqs"]) if c["prereqs"] else "None"
            status, missing, _ = _course_status(c, catalog, completed)
            catalog_details.append(
                f"{c['code']} — {c['name']} | credits: {c['credits']} | "
                f"semester: {c['semester'] if c['semester'] is not None else 'not specified'} | "
                f"prerequisites: {prereqs} | student status: {status}"
                + (f" | missing prerequisites: {', '.join(missing)}" if missing else "")
            )

        history_lines = []
        for item in payload.conversation_history[-6:]:
            role = str(item.get("role", "")).lower()
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                history_lines.append(f"{role}: {content[:800]}")

        if _asks_general_scope(payload.user_message):
            scope_rule = """
SCOPE/CAREER RULE:
The curriculum data does NOT establish salary, placement, demand, job outcomes, or
university-specific career claims. You may give a short GENERAL educational perspective
only when clearly labeled as general knowledge. Never claim that the university guarantees
or recommends a career outcome unless it is explicitly in the context.
"""
        else:
            scope_rule = """
Do not add unsupported career, salary, placement, difficulty, or popularity claims.
If the user asks for one, say the supplied curriculum data does not contain that information.
"""

        system_prompt = f"""
You are Academic Pathway Copilot for a university student.

PRIMARY RULE:
The verified curriculum data below is authoritative for university-specific facts.
Never invent or alter a course, course code, prerequisite, semester, credits, grade rule,
student detail, eligibility result, or academic policy.

{scope_rule}

If the question is about a course mentioned in the user's message, use the matching verified
course record below. Do not say that a course is "not in the curriculum" merely because it
is not currently eligible. Eligibility and curriculum membership are different things.

Student:
- Name: {student['name']}
- Department: {student['department']}
- Track: {student['track']}
- Current semester: {student['semester']}

Completed curriculum courses:
{chr(10).join('- ' + x for x in completed_details) if completed_details else '- None'}

Relevant verified course records:
{chr(10).join('- ' + x for x in catalog_details)}

Currently eligible courses:
{', '.join(c['code'] + ' — ' + c['name'] for c in ready) or 'None'}

Recent conversation (use only to resolve references such as "what about it"; current
verified course records remain authoritative):
{chr(10).join(history_lines) if history_lines else '- None'}

Answer directly and concisely. Separate verified curriculum facts from general educational
information. If the available data cannot support a university-specific claim, say so instead
of guessing.
"""
        try:
            response = answer_with_ollama(system_prompt, payload.user_message)
        except Exception:
            _release_ai_question(payload.user_id)
            raise

        return {
            "user_id": payload.user_id,
            "user_message": payload.user_message,
            "copilot_response": response,
            "llm_provider": "Ollama (Qwen 0.5B)",
            "ai_used": True,
            "usage_count": usage_count,
            "daily_limit": DAILY_LIMIT,
            "sources": [
                {"source": "Neo4j curriculum knowledge graph", "scope": "Verified course/prerequisite facts supplied to the model"},
                {"source": "MySQL student record", "scope": "Verified student profile and completion records"},
                {"source": "Ollama (Qwen 0.5B)", "scope": "Natural-language synthesis only; not an authority for university policy"},
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Copilot Error: {str(e)}")
