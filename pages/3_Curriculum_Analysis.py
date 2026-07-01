
from datetime import datetime
import streamlit as st

from services.curriculum_agent import analyze_curriculum
from services.ui_components import improvement_box, observation_box

# --------------------------------------------------
# Validate Session
# --------------------------------------------------

if "instructor_profile" not in st.session_state:
    st.warning("Please create your instructor profile first.")
    st.page_link("pages/1_Instructor_Profile.py", label="Go to Instructor Profile", icon="👤")
    st.stop()

if "current_course" not in st.session_state:
    st.warning("Please load a course in Course Workspace first.")
    st.page_link("pages/2_Course_Workspace.py", label="Go to Course Workspace", icon="📚")
    st.stop()

if "clos" not in st.session_state or not st.session_state.get("clos"):
    st.warning("Please upload/load an articulation matrix in Course Workspace first.")
    st.page_link("pages/2_Course_Workspace.py", label="Go to Course Workspace", icon="📚")
    st.stop()


# --------------------------------------------------
# Load Data
# --------------------------------------------------

course = st.session_state["current_course"]["profile"]
clos = st.session_state.get("clos", [])
student_outcomes = st.session_state.get("student_outcomes", [])
assessments = st.session_state.get("assessments", [])


# --------------------------------------------------
# Deterministic Bloom Engine
# --------------------------------------------------

BLOOM_LEVELS = {
    "list": "Remember",
    "define": "Remember",
    "describe": "Understand",
    "explain": "Understand",
    "identify": "Understand",
    "recognize": "Understand",
    "use": "Apply",
    "apply": "Apply",
    "communicate": "Apply",
    "articulate": "Analyze",
    "analyze": "Analyze",
    "compare": "Analyze",
    "evaluate": "Evaluate",
    "justify": "Evaluate",
    "create": "Create",
    "design": "Create",
    "develop": "Create",
}


def detect_bloom_level(clo_text):
    text = (clo_text or "").lower().strip()

    for verb, level in BLOOM_LEVELS.items():
        if text.startswith(verb):
            return level

    return "Unclear"


def calculate_so_coverage(clos):
    coverage = {}

    for clo in clos:
        so = clo.get("SO", "Unmapped")
        coverage[so] = coverage.get(so, 0) + 1

    return coverage


def calculate_bloom_distribution(clos):
    distribution = {}

    for clo in clos:
        bloom = detect_bloom_level(clo.get("Description", ""))
        distribution[bloom] = distribution.get(bloom, 0) + 1

    return distribution


def build_curriculum_report(course, clos, so_coverage, bloom_distribution, analysis):
    lines = []

    lines.append("# Curriculum Intelligence Summary")
    lines.append("")
    lines.append(f"Course: {course.get('course_code', '')} – {course.get('course_name', '')}")
    lines.append(f"Academic Year: {course.get('academic_year', '')}")
    lines.append(f"Semester: {course.get('semester', '')}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("")

    lines.append("## SO Coverage")
    total_clos = len(clos)
    for so, count in so_coverage.items():
        percentage = round((count / total_clos) * 100, 2) if total_clos else 0
        lines.append(f"- {so}: {count} CLO(s), {percentage}%")

    lines.append("")
    lines.append("## Bloom Distribution")
    for bloom, count in bloom_distribution.items():
        lines.append(f"- {bloom}: {count} CLO(s)")

    if analysis:
        lines.append("")
        lines.append("## Curriculum Strengths")
        for item in analysis.get("strengths", []):
            lines.append(f"- {item}")

        lines.append("")
        lines.append("## Curriculum Gaps")
        for item in analysis.get("gaps", []):
            lines.append(f"- {item}")

        lines.append("")
        lines.append("## Assessment Alignment")
        for item in analysis.get("assessment_alignment", []):
            lines.append(f"- {item.get('clo', 'CLO')}: {item.get('recommendation', '')}")

        lines.append("")
        lines.append("## Improvement Actions")
        for item in analysis.get("improvement_actions", []):
            lines.append(f"- {item}")

        lines.append("")
        lines.append("## Overall AI Observation")
        lines.append(analysis.get("overall_observation", ""))

    return "\n".join(lines)


# --------------------------------------------------
# Page Header
# --------------------------------------------------

st.title("🧠 Curriculum Analysis")

st.write(
    "Analyze CLO–SO mapping, Bloom distribution, SO coverage, assessment alignment, "
    "and curriculum improvement opportunities."
)

st.markdown(f"## {course.get('course_code', '')} – {course.get('course_name', '')}")


# --------------------------------------------------
# Quick Statistics
# --------------------------------------------------

st.markdown("---")

m1, m2, m3 = st.columns(3)
m1.metric("CLOs", len(clos))
m2.metric("Student Outcomes", len(student_outcomes))
m3.metric("Assessments", len(assessments))


# --------------------------------------------------
# Deterministic Analysis
# --------------------------------------------------

st.markdown("---")
st.markdown("## CLO–SO Mapping")

for clo in clos:
    with st.container(border=True):
        st.markdown(f"**{clo.get('CLO', 'CLO')}**")
        st.write(clo.get("Description", ""))
        st.markdown(f"**Mapped SO:** {clo.get('SO', 'Not specified')}")


st.markdown("---")
st.markdown("## SO Coverage")

so_coverage = calculate_so_coverage(clos)
total_clos = len(clos)

for so, count in so_coverage.items():
    percentage = round((count / total_clos) * 100, 2) if total_clos else 0

    with st.container(border=True):
        c1, c2 = st.columns(2)
        c1.metric("Student Outcome", so)
        c2.metric("Mapped CLOs", count)
        st.markdown(f"**{percentage}% of CLOs**")

st.caption("📊 Calculated from: Articulation Matrix • CLO–SO Mapping")


st.markdown("---")
st.markdown("## Bloom Analysis")

for clo in clos:
    bloom = detect_bloom_level(clo.get("Description", ""))

    with st.container(border=True):
        st.markdown(f"**{clo.get('CLO', 'CLO')}**")
        st.write(clo.get("Description", ""))
        st.markdown(f"**📊 Detected Bloom Level:** {bloom}")


st.markdown("---")
st.markdown("## Bloom Distribution")

bloom_distribution = calculate_bloom_distribution(clos)
bloom_cols = st.columns(len(bloom_distribution) if bloom_distribution else 1)

for idx, (bloom, count) in enumerate(bloom_distribution.items()):
    with bloom_cols[idx]:
        st.metric(bloom, count)

st.caption("📊 Calculated from: CLO action verbs")


# --------------------------------------------------
# AI Curriculum Analysis
# --------------------------------------------------

st.markdown("---")
st.markdown("## AI Curriculum Insights")

if st.button("✨ Generate AI Curriculum Analysis", type="primary"):
    with st.spinner("AI is analyzing the curriculum..."):
        try:
            analysis = analyze_curriculum(
                course=course,
                clos=clos,
                student_outcomes=student_outcomes,
                assessments=assessments,
            )

            st.session_state["curriculum_analysis"] = analysis

        except Exception as e:
            st.error("AI curriculum analysis could not be generated.")
            st.caption(str(e))

analysis = st.session_state.get("curriculum_analysis", {})

if analysis:
    st.markdown("### Curriculum Strengths")
    for item in analysis.get("strengths", []):
        st.success(item)

    st.markdown("### Curriculum Gaps")
    for item in analysis.get("gaps", []):
        st.warning(item)

    st.markdown("### Assessment Alignment")
    for item in analysis.get("assessment_alignment", []):
        st.info(
            f"**{item.get('clo', 'CLO')}** — "
            f"{item.get('recommendation', '')}"
        )

    st.markdown("### Recommended Improvement Actions")
    for item in analysis.get("improvement_actions", []):
        improvement_box(item)

    st.markdown("### Overall AI Observation")
    observation_box(analysis.get("overall_observation", ""))

    st.caption(
        "✨ AI generated from: Articulation Matrix • CLOs • Student Outcomes • Assessment Structure"
    )
else:
    st.info("Click **Generate AI Curriculum Analysis** to produce AI-based curriculum insights.")


# --------------------------------------------------
# Download Summary
# --------------------------------------------------

if analysis:
    # st.markdown("---")
    # st.markdown("## Download Full Report")
    st.caption(
        "Curriculum Intelligence combines deterministic accreditation-friendly calculations "
        "with AI-generated expert interpretation."
    )

    report_text = build_curriculum_report(
        course,
        clos,
        so_coverage,
        bloom_distribution,
        analysis,
    )

    course_code = course.get("course_code", "Course").replace(" ", "")
    academic_year = course.get("academic_year", "").replace("/", "-").replace(" ", "")
    semester = course.get("semester", "").replace(" ", "")
    today = datetime.now().strftime("%Y-%m-%d")

    filename = (
        f"CurriculumAnalysis_"
        f"{course_code}_"
        f"{academic_year}_"
        f"{semester}_"
        f"{today}.md"
    )

    st.download_button(
        label="📥 Download Curriculum Intelligence Report",
        data=report_text.encode("utf-8"),
        file_name=filename,
        mime="text/markdown",
    )


# --------------------------------------------------
# Footer
# --------------------------------------------------

st.markdown("---")
st.caption(
    "Curriculum Intelligence combines deterministic accreditation-friendly calculations "
    "with AI-generated expert interpretation."
)