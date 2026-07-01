from datetime import datetime


def _as_text(value):
    """
    Safely convert AI/user-generated values to text.
    Prevents join errors when an AI response returns a list instead of a string.
    """
    if value is None:
        return ""

    if isinstance(value, list):
        return "\n".join(str(item) for item in value)

    if isinstance(value, dict):
        return "\n".join(f"{key}: {val}" for key, val in value.items())

    return str(value)



def _sort_ids(values, prefix):
    def key(value):
        try:
            return int(str(value).replace(prefix, ""))
        except Exception:
            return 9999

    return sorted(values or [], key=key)


def _markdown_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join(["---" for _ in headers]) + "|")

    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")

    return "\n".join(_as_text(line) for line in lines)


def _course_header(course):
    return f"{course.get('course_code', '')} {course.get('course_name', '')}".strip()


def _academic_period(course):
    semester = course.get("semester", "")
    year = course.get("academic_year", "")
    return f"{semester} - {year}".strip(" -")


def generate_coordination_mom(
    course,
    course_structure=None,
    meeting_no="",
    meeting_date="",
    meeting_time="",
    attendees="",
    topics_discussed="",
    prepared_by="",
    next_meeting="",
    **kwargs,
):
    today = datetime.now().strftime("%Y-%m-%d")

    attendee_items = [
        line.strip()
        for line in str(attendees or "").splitlines()
        if line.strip()
    ] or [""]

    topic_items = [
        line.strip()
        for line in str(topics_discussed or kwargs.get("discussion_notes", "")).splitlines()
        if line.strip()
    ] or [""]

    lines = []
    lines.append("# FCIT Course Coordination Meeting")
    lines.append("")
    lines.append("## Meeting Minutes")
    lines.append("")
    lines.append(f"**FCIT Course Coordination Meeting – {_academic_period(course)}**")
    lines.append("")
    lines.append(f"**Course:** {_course_header(course)}")
    lines.append(f"**Section(s):** {course.get('sections', course.get('section', ''))}")
    lines.append("")
    lines.append(f"**Meeting #:** {meeting_no or '—'}")
    lines.append(f"**Date:** {meeting_date or today}")
    lines.append(f"**Time:** {meeting_time or '—'}")
    lines.append("")
    lines.append("## Attendance Names")
    lines.append(_markdown_table(["#", "Name"], [[i, name] for i, name in enumerate(attendee_items, start=1)]))
    lines.append("")
    lines.append("## Topics Discussed / Actions Taken / Points Agreed")
    lines.append(_markdown_table(["#", "Topic / Action / Point Agreed"], [[i, item] for i, item in enumerate(topic_items, start=1)]))
    lines.append("")
    lines.append(_markdown_table(["Prepared by", "Signature"], [[prepared_by or course.get("coordinator", course.get("instructor", "")), ""]]))
    lines.append("")
    lines.append(f"**Next meeting:** {next_meeting or '—'}")

    return "\n".join(_as_text(line) for line in lines)


def generate_assessment_cover_sheet(
    course,
    assessment,
    assessment_date="",
    duration="",
    total_marks=30,
    section="",
    program="IS",
    notes="",
    **kwargs,
):
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        total_marks = float(total_marks)
    except Exception:
        total_marks = 30.0

    section = section or course.get("sections", course.get("section", ""))
    program = program or "IS"

    distribution = assessment.get("so_distribution", {})
    so_rows = []

    if distribution:
        for so, percent in sorted(
            distribution.items(),
            key=lambda item: int(str(item[0]).replace("SO", "")),
        ):
            max_marks = round(total_marks * (float(percent) / 100), 2)
            so_rows.append([so, f"{max_marks:g}"])
    else:
        for so in _sort_ids(assessment.get("assessed_sos", assessment.get("sos", [])), "SO"):
            so_rows.append([so, ""])

    lines = []
    lines.append("# Assessment Cover Sheet")
    lines.append("")
    lines.append("**Kingdom of Saudi Arabia**")
    lines.append("")
    lines.append("**King Abdulaziz University**")
    lines.append("")
    lines.append("**Faculty of Computing and Information Technology**")
    lines.append("")
    lines.append(f"**{course.get('department', 'Information Systems Department')}**")
    lines.append("")
    lines.append(f"## {_course_header(course)}")
    lines.append("")
    lines.append(f"**{_academic_period(course)}**")
    lines.append("")
    lines.append(f"**Type of Assessment:** {assessment.get('name', '')}")
    lines.append("")
    lines.append(f"**Coordinator(s):** {course.get('coordinator', '')}    **Instructor:** {course.get('instructor', '')}")
    lines.append("")
    lines.append(f"**Total Marks for this Assessment:** {total_marks:g}")
    lines.append("")
    lines.append("## Student Information")
    lines.append("")
    lines.append("**Student Name:** ______________________________")
    lines.append("")
    lines.append("**Student ID:** ________________________________")
    lines.append("")
    lines.append(f"**Section:** {section}    **Program:** {program}")
    lines.append("")
    lines.append(f"**Total Obtained Marks:** __________ out of {total_marks:g}")
    lines.append("")
    lines.append(f"**Duration:** {duration or '—'}")
    lines.append("")
    lines.append(f"**Assessment Date:** {assessment_date or today}")
    lines.append("")
    lines.append("## Student Outcomes (SO) – Maximum Marks Contributed by this Assessment")

    if so_rows:
        total_so_marks = sum(
            float(str(row[1]).replace(",", ""))
            for row in so_rows
            if str(row[1]).strip()
        )
        lines.append(
            _markdown_table(
                ["Student Outcome", "Maximum Marks"],
                so_rows + [["Total (SO)", f"{total_so_marks:g}"]],
            )
        )
    else:
        lines.append("No SO maximum marks were detected for this assessment.")

    if notes:
        lines.append("")
        lines.append("## Notes")
        lines.append(notes)

    return "\n".join(_as_text(line) for line in lines)


def generate_eos_report(
    course,
    course_structure,
    combined_so_attainment=None,
    assessment_based_evaluation="",
    subjective_evaluation="",
    course_improvement="",
    instructor_reflection="",
    improvement_actions="",
    **kwargs,
):
    today = datetime.now().strftime("%A, %B %d, %Y")

    if not subjective_evaluation:
        subjective_evaluation = instructor_reflection

    if not course_improvement:
        course_improvement = improvement_actions

    lines = []
    lines.append("# Information Systems Department")
    lines.append("")
    lines.append("# End of Semester Course Evaluation Report")
    lines.append("")
    lines.append(f"## {_course_header(course)}")
    lines.append("")
    lines.append(f"**{_academic_period(course)}**")
    lines.append("")
    lines.append(f"**Section:** {course.get('sections', course.get('section', ''))}")

    if course.get("number_of_students"):
        lines.append(f"**Number of Students:** {course.get('number_of_students')}")

    lines.append(f"**Instructor:** {course.get('instructor', '')}")
    lines.append("")
    lines.append("## SO Attainment Summary")

    if combined_so_attainment and combined_so_attainment.get("summary"):
        rows = []

        for item in combined_so_attainment.get("summary", []):
            rows.append(
                [
                    item.get("so", ""),
                    item.get("students_assessed", "—"),
                    item.get("students_attained", "—"),
                    f"{item.get('attainment_percent', 0)}%",
                    item.get("target_met", "No"),
                ]
            )

        lines.append(
            _markdown_table(
                ["Student outcome", "Students assessed", "Students attained", "Attainment", "Target met"],
                rows,
            )
        )
        lines.append("")
        lines.append("Student pass threshold: 65% of max points; SO attainment target: 65% of assessed students.")
    else:
        lines.append("SO attainment results were not available.")

    lines.append("")
    lines.append("## Assessment-Based Evaluation")
    lines.append(_as_text(assessment_based_evaluation) or "No assessment-based evaluation was entered.")
    lines.append("")
    lines.append("## Subjective Evaluation")
    lines.append(_as_text(subjective_evaluation) or "No subjective evaluation was entered.")
    lines.append("")
    lines.append("## Course Improvement")
    lines.append(_as_text(course_improvement) or "No course improvement actions were entered.")
    lines.append("")
    lines.append(f"Report Date: {today}")

    return "\n".join(_as_text(line) for line in lines)
