
from datetime import datetime
import streamlit as st

from services.course_knowledge_agent import build_course_digital_twin
from services.course_enhancement_agent import generate_course_enhancement_plan
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


# --------------------------------------------------
# Load Data
# --------------------------------------------------

course = st.session_state["current_course"]["profile"]
clos = st.session_state.get("clos", [])
digital_twin = build_course_digital_twin(course, clos=clos)
curriculum_analysis = st.session_state.get("curriculum_analysis", {})


# --------------------------------------------------
# Helper
# --------------------------------------------------

def show_list(title, items):
    st.markdown(f"### {title}")
    if not items:
        st.caption("No recommendations generated.")
        return

    for item in items:
        improvement_box(item)


def build_enhancement_report(course, plan):
    lines = []

    lines.append("# Course Enhancement Intelligence Report")
    lines.append("")
    lines.append(f"Course: {course.get('course_code', '')} – {course.get('course_name', '')}")
    lines.append(f"Academic Year: {course.get('academic_year', '')}")
    lines.append(f"Semester: {course.get('semester', '')}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("")

    sections = [
        ("Content Enhancement", "content_enhancement"),
        ("Laboratory Enhancement", "laboratory_enhancement"),
        ("Teaching Resources", "teaching_resources"),
        ("Teaching Strategies", "teaching_strategies"),
        ("AI Integration Opportunities", "ai_integration"),
        ("Assessment Enhancement", "assessment_enhancement"),
    ]

    for heading, key in sections:
        lines.append(f"## {heading}")
        for item in plan.get(key, []):
            lines.append(f"- {item}")
        lines.append("")

    roadmap = plan.get("continuous_improvement_roadmap", {})

    lines.append("## Continuous Improvement Roadmap")
    lines.append("")
    lines.append("### High Priority")
    for item in roadmap.get("high_priority", []):
        lines.append(f"- {item}")

    lines.append("")
    lines.append("### Medium Priority")
    for item in roadmap.get("medium_priority", []):
        lines.append(f"- {item}")

    lines.append("")
    lines.append("### Low Priority")
    for item in roadmap.get("low_priority", []):
        lines.append(f"- {item}")

    lines.append("")
    lines.append("## Overall Observation")
    lines.append(plan.get("overall_observation", ""))

    return "\n".join(lines)


# --------------------------------------------------
# Page Header
# --------------------------------------------------

st.title("🚀 Course Enhancement")

st.write(
    "Generate practical recommendations to improve course content, labs, resources, "
    "teaching strategies, AI integration, assessments, and continuous improvement planning."
)

st.markdown(f"## {course.get('course_code', '')} – {course.get('course_name', '')}")


# --------------------------------------------------
# Enhancement Setup
# --------------------------------------------------

# st.markdown("---")
# st.markdown("## Enhancement Setup")

# focus_options = [
#     "Course Content",
#     "Laboratory",
#     "Teaching Resources",
#     "Teaching Strategies",
#     "AI Integration",
#     "Assessments",
#     "Continuous Improvement",
# ]

# focus_areas = st.multiselect(
#     "Enhancement Focus Areas",
#     focus_options,
#     default=focus_options,
# )

# instructor_notes = st.text_area(
#     "Instructor Notes (Optional)",
#     placeholder="Example: Students struggled with UML sequence diagrams, or I want to add more real-world case studies.",
#     height=120,
# )

# --------------------------------------------------
# Enhancement Setup
# --------------------------------------------------

st.markdown("---")
st.markdown("## Enhancement Setup")

focus_options = [
    "Course Content",
    "Laboratory",
    "Teaching Resources",
    "Teaching Strategies",
    "AI Integration",
    "Assessments",
    "Continuous Improvement",
]

st.markdown("**Enhancement Focus Areas**")

col1, col2 = st.columns(2)

selected_focus = []

for i, option in enumerate(focus_options):
    with (col1 if i % 2 == 0 else col2):
        if st.checkbox(option, value=True, key=f"focus_{option}"):
            selected_focus.append(option)

focus_areas = selected_focus

instructor_notes = st.text_area(
    "Instructor Notes (Optional)",
    placeholder=(
        "Example: Students struggled with UML sequence diagrams, "
        "or I want to add more real-world case studies."
    ),
    height=120,
)

# --------------------------------------------------
# Generate
# --------------------------------------------------

if "course_enhancement_plan" not in st.session_state:
    st.session_state["course_enhancement_plan"] = {}

st.markdown("---")

if st.button("✨ Generate Course Enhancement Plan", type="primary"):
    with st.spinner("AI is generating the course enhancement plan..."):
        try:
            plan = generate_course_enhancement_plan(
                course=course,
                digital_twin=digital_twin,
                curriculum_analysis=curriculum_analysis,
                focus_areas=focus_areas,
                instructor_notes=instructor_notes,
            )

            st.session_state["course_enhancement_plan"] = plan

        except Exception as e:
            st.error("Course enhancement plan could not be generated.")
            st.caption(str(e))


plan = st.session_state.get("course_enhancement_plan", {})


# --------------------------------------------------
# Results
# --------------------------------------------------

if plan:
    st.markdown("## Course Enhancement Plan")

    show_list("📘 Content Enhancement", plan.get("content_enhancement", []))
    show_list("🧪 Laboratory Enhancement", plan.get("laboratory_enhancement", []))
    show_list("📖 Teaching Resources", plan.get("teaching_resources", []))
    show_list("🎓 Teaching Strategies", plan.get("teaching_strategies", []))
    show_list("🤖 AI Integration Opportunities", plan.get("ai_integration", []))
    show_list("📝 Assessment Enhancement", plan.get("assessment_enhancement", []))

    st.markdown("### 🔄 Continuous Improvement Roadmap")

    roadmap = plan.get("continuous_improvement_roadmap", {})

    st.markdown("#### High Priority")
    for item in roadmap.get("high_priority", []):
        improvement_box(item)

    st.markdown("#### Medium Priority")
    for item in roadmap.get("medium_priority", []):
        st.info(item)

    st.markdown("#### Low Priority")
    for item in roadmap.get("low_priority", []):
        st.success(item)

    st.markdown("### Overall AI Observation")
    observation_box(plan.get("overall_observation", ""))

    st.caption(
        "✨ AI generated from: Course Digital Twin • Curriculum Intelligence • Course Knowledge Base • Instructor Notes"
    )

    # --------------------------------------------------
    # Download
    # --------------------------------------------------

    st.markdown("---")
    st.markdown("## Download Report")

    report_text = build_enhancement_report(course, plan)

    course_code = course.get("course_code", "Course").replace(" ", "")
    academic_year = course.get("academic_year", "").replace("/", "-").replace(" ", "")
    semester = course.get("semester", "").replace(" ", "")
    today = datetime.now().strftime("%Y-%m-%d")

    filename = (
        f"CourseEnhancement_"
        f"{course_code}_"
        f"{academic_year}_"
        f"{semester}_"
        f"{today}.md"
    )

    st.download_button(
        label="📥 Download Course Enhancement Report",
        data=report_text.encode("utf-8"),
        file_name=filename,
        mime="text/markdown",
    )

else:
    st.info("Select focus areas and click **Generate Course Enhancement Plan**.")


# --------------------------------------------------
# Footer
# --------------------------------------------------

st.markdown("---")
st.caption(
    "Course Enhancement Intelligence helps instructors improve course content, resources, labs, "
    "teaching strategies, assessments, and continuous improvement planning using the Course Digital Twin."
)

