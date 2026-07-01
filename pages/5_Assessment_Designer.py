
import streamlit as st
from datetime import datetime
from services.course_knowledge_agent import build_course_digital_twin
from services.assessment_agent import generate_assessment_item


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
course_structure = st.session_state.get(
    "course_structure",
    {
        "clos": [],
        "assessments": [],
        "student_outcomes": [],
        "statistics": {},
    },
)
clos = course_structure.get("clos", [])
assessments = course_structure.get("assessments", [])

digital_twin = build_course_digital_twin(course, clos=clos)


# --------------------------------------------------
# Page Header
# --------------------------------------------------

st.title("📝 Assessment Designer")

st.write(
    "Generate high-quality assessment materials aligned with Course Learning Outcomes, "
    "Bloom’s Taxonomy, ABET Student Outcomes, and the Course Digital Twin."
)

st.markdown(f"## {course.get('course_code', '')} – {course.get('course_name', '')}")

if not clos:
    st.info(
        "No CLOs are available for this course yet. "
        "Please upload/load the articulation matrix in Course Workspace, then return to Assessment Designer."
    )
    st.page_link("pages/2_Course_Workspace.py", label="Go to Course Workspace", icon="📚")
    st.stop()


# --------------------------------------------------
# Select CLO and Settings
# --------------------------------------------------

st.markdown("---")
st.markdown("## Assessment Setup")

assessment = None
if assessments:
    assessment = st.selectbox("Assessment", assessments, format_func=lambda a: a["name"])
    c1,c2,c3=st.columns(3)
    c1.metric("Type", assessment.get("type",""))
    c2.metric("Weight", f"{assessment.get('weight',0)}%")
    c3.metric("Student Outcomes", ", ".join(assessment.get("sos",[])) or "-")


clo_options = [
    f"{clo.get('CLO', 'CLO')} - {clo.get('Description', '')}"
    for clo in clos
]

selected_clo_text = st.selectbox("Select CLO", clo_options)
selected_index = clo_options.index(selected_clo_text)
selected_clo = clos[selected_index]

left, right = st.columns(2)

with left:
    st.write("**Selected CLO:**", selected_clo.get("CLO", ""))
    st.write("**Description:**", selected_clo.get("Description", ""))
    st.write("**Mapped SO:**", selected_clo.get("SO", "Not specified"))

with right:
    assessment_type = st.selectbox(
        "Assessment Type",
        [
            "MCQ",
            "True / False",
            "Short Answer",
            "Essay",
            "Scenario-Based Question",
            "Case Study",
            "Programming Task",
            "Lab Exercise",
            "Project",
            "Presentation",
            "Rubric",
        ],
    )

    difficulty = st.selectbox(
        "Difficulty",
        ["Easy", "Moderate", "Challenging"],
        index=1,
    )

    number_of_items = st.slider(
        "Number of Items",
        min_value=1,
        max_value=10,
        value=3,
    )

additional_instructions = st.text_area(
    "Additional Instructor Instructions (Optional)",
    placeholder="Example: Include a healthcare case study, provide answer key, avoid coding, align with project work...",
    height=120,
)


# --------------------------------------------------
# Generate Assessment
# --------------------------------------------------

st.markdown("---")

if "generated_assessment" not in st.session_state:
    st.session_state["generated_assessment"] = ""

if st.button("✨ Generate Assessment", type="primary"):
    with st.spinner("Generating assessment material with AI..."):
        generated = generate_assessment_item(
            course=course,
            digital_twin=digital_twin,
            clo=selected_clo,
            assessment_type=assessment_type,
            difficulty=difficulty,
            number_of_items=number_of_items,
            additional_instructions=additional_instructions,
        )

        st.session_state["generated_assessment"] = generated or ""


# --------------------------------------------------
# Output
# --------------------------------------------------

st.markdown("## Generated Assessment")

if st.session_state["generated_assessment"]:
    edited_item = st.text_area(
        "Review and edit generated assessment",
        value=st.session_state["generated_assessment"],
        height=700,
    )

    st.caption(
        "✨ AI generated from: Course Digital Twin • Selected CLO • Assessment Type • Instructor Instructions"
    )

    course_code = course.get("course_code", "Course").replace(" ", "")
    academic_year = course.get("academic_year", "").replace("/", "-").replace(" ", "")
    semester = course.get("semester", "").replace(" ", "")
    clo_id = selected_clo.get("CLO", "CLO")
    assessment_name = assessment_type.replace(" / ", "_").replace(" ", "_")
    difficulty_name = difficulty.replace(" ", "")
    today = datetime.now().strftime("%Y-%m-%d")

    filename = (
        f"Assessment_"
        f"{(assessment or {}).get('name','Assessment').replace(' ','_')}_"
        f"{course_code}_"
        f"{assessment_name}_"
        f"{clo_id}_"
        f"{difficulty_name}_"
        f"{academic_year}_"
        f"{semester}_"
        f"{today}.md"
    )

    st.download_button(
        label="📥 Download Assessment",
        data=edited_item.encode("utf-8"),
        file_name=filename,
        mime="text/markdown",
    )

else:
    st.info("Select the assessment settings and click **Generate Assessment**.")
    

# --------------------------------------------------
# Footer
# --------------------------------------------------

st.markdown("---")

