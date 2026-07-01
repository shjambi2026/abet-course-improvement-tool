import json

from services.ai_service import ask_ai_json
from services.document_text_service import extract_text_from_file, extract_texts


KNOWLEDGE_PRIORITY = [
    "syllabus",
    "matrix",
    "lab_syllabus",
    "slides",
    "lab_files",
    "assessment_package",
    "esr",
    "coordination",
]


def _safe_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _clo_text(clos):
    if not clos:
        return "No CLOs available."

    lines = []
    for clo in clos:
        if isinstance(clo, dict):
            clo_id = clo.get("CLO", "CLO")
            desc = clo.get("Description", "")
            so = clo.get("SO", "")
            domain = clo.get("Domain", "")
            lines.append(f"{clo_id}: {desc} | SO: {so} | Domain: {domain}")
        else:
            lines.append(str(clo))

    return "\n".join(lines)


def _load_course_knowledge(course):

    syllabus_text = extract_text_from_file(course.get("syllabus_file"))

    lab_syllabus_text = extract_text_from_file(course.get("lab_syllabus_file"))

    slides_text = extract_texts(course.get("slides_file"))

    lab_files_text = extract_texts(course.get("lab_files"))

    assessment_text = extract_texts(course.get("assessments_file"))
    
    esr_text = extract_texts(course.get("esr_file"))

    coordination_text = extract_texts(course.get("coordination_file"))

    return {
        "syllabus": syllabus_text[:12000],
        "lab_syllabus": lab_syllabus_text[:6000],
        "slides": slides_text[:12000],
        "lab_files": "\n\n".join(lab_files_text)[:12000],
        "assessment_package": "\n\n".join(assessment_text)[:12000],
        "esr": "\n\n".join(esr_text)[:6000],
        "coordination": "\n\n".join(coordination_text)[:6000],
    }


def _empty_digital_twin():
    return {
        "course_summary": "Not generated yet.",
        "official_prerequisites": "Not generated yet.",
        "expected_student_background": "Not generated yet.",
        "recommended_instructor_background": "Not generated yet.",
        "key_topics": [],
        "software_tools": [],
        "recommended_teaching_strategies": [],
        "assessment_observations": [],
        "keywords": [],
        "source_note": "AI generation unavailable.",
    }


def build_course_digital_twin(course, clos=None):
    """
    Builds an AI-generated Course Digital Twin from uploaded knowledge sources.

    Uses:
    - Course syllabus
    - Lab syllabus
    - Previous ESR(s)
    - Coordination MOM(s)
    - Extracted CLOs
    """

    clos = clos or []
    docs = _load_course_knowledge(course)

    if not docs["syllabus"] and not clos:
        return _empty_digital_twin()

    prompt = f"""

You are a Course Knowledge Agent for an ABET-accredited Information Systems program.

Build a Course Digital Twin using ONLY the provided course information and knowledge sources.

Use every available knowledge source.

If multiple sources contain similar information, prefer the most specific and most recent one.

When historical documents such as ESRs or Coordination MOMs conflict with the current syllabus or articulation matrix,
treat the current syllabus and articulation matrix as authoritative.
Use historical documents only to enrich recommendations, teaching background, and continuous improvement observations.

Do not invent official facts that are not supported by the provided sources.
If a field cannot be determined, write "Not available from the provided sources."


Return ONLY valid JSON using this exact schema:
{{
  "course_summary": "string",
  "official_prerequisites": "string",
  "expected_student_background": "string",
  "recommended_instructor_background": "string",
  "key_topics": ["string"],
  "software_tools": ["string"],
  "recommended_teaching_strategies": ["string"],
  "assessment_observations": ["string"],
  "keywords": ["string"]
}}

Course information:
Course Code: {course.get("course_code", "")}
Course Name: {course.get("course_name", "")}
Department: {course.get("department", "")}
Academic Year: {course.get("academic_year", "")}
Semester: {course.get("semester", "")}

CLOs:
{_clo_text(clos)}

Course Syllabus
{docs["syllabus"]}

Lab Syllabus
{docs["lab_syllabus"]}

Teaching Slides
{docs["slides"]}

Lab Files
{docs["lab_files"]}

Assessment Package
{docs["assessment_package"]}

Previous ESR(s)
{docs["esr"]}

Coordination MOM(s)
{docs["coordination"]}
"""

    result = ask_ai_json(prompt)

    if not result:
        return _empty_digital_twin()

    return {
        "course_summary": result.get("course_summary", "Not available from the provided sources."),
        "official_prerequisites": result.get("official_prerequisites", "Not available from the provided sources."),
        "expected_student_background": result.get("expected_student_background", "Not available from the provided sources."),
        "recommended_instructor_background": result.get("recommended_instructor_background", "Not available from the provided sources."),
        "key_topics": result.get("key_topics", []),
        "software_tools": result.get("software_tools", []),
        "recommended_teaching_strategies": result.get("recommended_teaching_strategies", []),
        "assessment_observations": result.get("assessment_observations", []),
        "keywords": result.get("keywords", []),
        "source_note": "✨ AI generated from: Course Syllabus • CLOs • ESR(s) • Coordination MOM(s)",
    }