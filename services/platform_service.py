import os
from datetime import datetime

DOCUMENT_CATEGORIES = {
    "syllabus_file": "Syllabus",
    "matrix_file": "Articulation Matrix",
    "esr_file": "End-of-Semester Report",
    "coordination_file": "Coordination Meeting Report",
    "slides_file": "Slides",
    "labs_file": "Lab Files",
    "assessments_file": "Assessment Files",
    # "rubrics_file": "Rubrics",
}

ESSENTIAL_KEYS = ["syllabus_file"]
ACCREDITATION_KEYS = ["matrix_file", "esr_file", "coordination_file"]
TEACHING_KEYS = ["slides_file", "labs_file"]
# ASSESSMENT_KEYS = ["assessments_file", "rubrics_file"]
ASSESSMENT_KEYS = ["assessments_file"]


def safe_int(value, default=0):
    try:
        return int(float(value))
    except Exception:
        return default


def instructor_display_name(profile):
    if not profile:
        return "Faculty Member"
    return (profile.get("title", "") + " " + profile.get("name", "")).strip() or "Faculty Member"


def get_document_status(course):
    status = []
    for key, label in DOCUMENT_CATEGORIES.items():
        value = course.get(key, "") if course else ""
        status.append({
            "key": key,
            "label": label,
            "available": bool(str(value).strip()),
            "file": value
        })
    return status


def readiness_by_keys(course, keys):
    if not keys:
        return 0
    available = 0
    for key in keys:
        if course and str(course.get(key, "")).strip():
            available += 1
    return round((available / len(keys)) * 100)


def calculate_course_readiness(course):
    if not course:
        return {
            "overall": 0,
            "essential": 0,
            "accreditation": 0,
            "teaching": 0,
            "assessment": 0,
        }
    essential = readiness_by_keys(course, ESSENTIAL_KEYS)
    accreditation = readiness_by_keys(course, ACCREDITATION_KEYS)
    teaching = readiness_by_keys(course, TEACHING_KEYS)
    assessment = readiness_by_keys(course, ASSESSMENT_KEYS)
    overall = round((essential * 0.30) + (accreditation * 0.30) + (teaching * 0.20) + (assessment * 0.20))
    return {
        "overall": overall,
        "essential": essential,
        "accreditation": accreditation,
        "teaching": teaching,
        "assessment": assessment,
    }


def missing_documents(course):
    return [item["label"] for item in get_document_status(course) if not item["available"]]


def get_course_attention_items(course):
    if not course:
        return []
    items = []
    docs = {item["key"]: item["available"] for item in get_document_status(course)}
    if not docs.get("syllabus_file"):
        items.append("Upload the course syllabus to complete the course profile.")
    if not docs.get("matrix_file"):
        items.append("Upload the articulation matrix when available to enable CLO–SO and Bloom analysis.")
    if not docs.get("esr_file"):
        items.append("Generate or upload the End-of-Semester Report.")
    if not docs.get("coordination_file"):
        items.append("Generate the Coordination Meeting Report for accreditation documentation.")
    # if not docs.get("rubrics_file"):
    #     items.append("Upload or generate rubrics for major assessments.")
    return items[:6]


def build_course_ai_summary(course, clos=None, sos=None, attainment=None):
    if not course:
        return "No course is currently loaded."
    code = course.get("course_code", "This course")
    name = course.get("course_name", "")
    level_note = course.get("level", "") or "the assigned undergraduate level"
    course_type = course.get("course_type", "") or "required/elective status not specified"
    readiness = calculate_course_readiness(course)["overall"]
    clo_count = len(clos or [])
    so_count = len(sos or [])
    missing = missing_documents(course)
    missing_text = ", ".join(missing[:3]) if missing else "no critical missing documents"
    return (
        f"{code} – {name} is a {course_type.lower()} course at {level_note}. "
        f"The current course readiness score is {readiness}%. "
        f"The available curriculum data includes {clo_count} CLOs and {so_count} mapped student outcomes. "
        f"The main documentation items needing attention are: {missing_text}. "
        f"Before teaching or coordinating the course, the instructor should review the syllabus, articulation matrix, previous ESR findings, SO attainment results, and any pending coordination meeting actions."
    )


def generate_platform_insights(courses):
    insights = []
    for course in courses:
        code = course.get("course_code", "Course")
        readiness = calculate_course_readiness(course)["overall"]
        if readiness < 70:
            insights.append(f"{code} has incomplete course documentation and should be reviewed before the next offering.")
        if not course.get("esr_file"):
            insights.append(f"{code} does not yet have an ESR document recorded.")
        if not course.get("coordination_file"):
            insights.append(f"{code} is missing the Coordination Meeting Report required for course-level accreditation documentation.")
        if course.get("matrix_file"):
            insights.append(f"{code} has curriculum mapping data")
            # insights.append(f"{code} has curriculum mapping data, but rubrics are not yet recorded for assessment evidence.")
    if not insights:
        insights.append("All saved courses have strong initial documentation coverage. Continue updating ESRs, attainment, and improvement actions each semester.")
    return insights[:5]


def format_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M")
