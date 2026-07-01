
import os
from pathlib import Path
import streamlit as st

from services.storage_service import load_instructor_profile, load_courses
from services.platform_service import (
    instructor_display_name,
    calculate_course_readiness,
    generate_platform_insights,
)

st.set_page_config(
    page_title="Curriculum Intelligence Platform",
    page_icon="🎓",
    layout="wide",
)

# --------------------------------------------------
# Stable asset paths
# --------------------------------------------------
BASE_DIR = Path(__file__).parent
ASSET_DIR = BASE_DIR / "assets"

FCIT_LOGO = ASSET_DIR / "fcit_logo.png"
ABET_LOGO = ASSET_DIR / "abet_logo.png"

profile = load_instructor_profile()
if profile:
    st.session_state["instructor_profile"] = profile

# --------------------------------------------------
# Header
# --------------------------------------------------
# left, center, right = st.columns([1.3, 4, 1.3])

# with left:
#     st.image(str(FCIT_LOGO), use_container_width=True)

# with right:
#     st.image(str(ABET_LOGO), use_container_width=True)

left, center, right = st.columns([1.7, 4, 1.1])

with left:
    if FCIT_LOGO.exists():
        st.image(str(FCIT_LOGO), width=1800)

with center:
    st.markdown(
        """
        <div style="text-align:center;">
            <h1 style="margin-bottom:0;">Curriculum Intelligence Platform</h1>
            <p style="font-size:18px; margin-top:0; color:#345;">
                <em>An AI-powered faculty assistant for continuous course improvement and ABET accreditation.</em>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right:
    if ABET_LOGO.exists():
        st.image(str(ABET_LOGO), width=60)

st.divider()

# --------------------------------------------------
# Instructor Profile
# --------------------------------------------------
if "instructor_profile" not in st.session_state:
    st.warning("Please create your instructor profile before using the system.")
    st.page_link("pages/1_Instructor_Profile.py", label="Create Profile", icon="👤")
    st.stop()

profile = st.session_state["instructor_profile"]
name = instructor_display_name(profile)

st.markdown(f"### Welcome, {name}")
st.write(profile.get("department", "Information Systems Department"))

c1, c2 = st.columns(2)
with c1:
    st.info("**Academic Year:** 2025–2026")
with c2:
    st.info("**Semester:** Second Semester")

# --------------------------------------------------
# Courses
# --------------------------------------------------
courses = load_courses()
current_courses = [c for c in courses if c.get("status", "Current") == "Current"] or courses

st.markdown("## Your Courses")

if not current_courses:
    st.info("No courses have been added yet. Start by creating a course workspace.")
    st.page_link("pages/2_Course_Workspace.py", label="Go to Course Workspace", icon="📚")
else:
    cols = st.columns(2)
    for index, course in enumerate(current_courses):
        readiness = calculate_course_readiness(course)
        with cols[index % 2]:
            with st.container(border=True):
                st.markdown(f"### {course.get('course_code', '')} – {course.get('course_name', '')}")
                st.write("**Coordinator:**", course.get("coordinator") or "Not specified")
                st.write("**Instructor:**", course.get("instructor") or name)
                st.write("**Sections:**", course.get("sections") or "Not specified")
                st.progress(
                    readiness.get("overall", 0) / 100,
                    text=f"Course Readiness: {readiness.get('overall', 0)}%",
                )

                matrix_status = "Available" if course.get("matrix_file") else "Not available"
                st.write("**Curriculum Matrix:**", matrix_status)

                if course.get("last_opened"):
                    st.caption(f"Last opened: {course.get('last_opened')}")

                st.page_link("pages/2_Course_Workspace.py", label="Open Workspace", icon="📁")
                # st.page_link("pages/3_Course_Profile.py", label="View Course Profile", icon="📖")

# --------------------------------------------------
# Platform Statistics
# --------------------------------------------------
st.markdown("## Platform Statistics")

readiness_values = [calculate_course_readiness(c).get("overall", 0) for c in current_courses] or [0]

document_keys = [
    "syllabus_file",
    "matrix_file",
    "lab_syllabus_file",
    "slides_file",
    "assessments_file",
    "esr_file",
    "coordination_file",
]

def count_documents(course):
    total = 0
    for key in document_keys:
        value = course.get(key)
        if isinstance(value, list):
            total += len(value)
        elif value:
            total += 1
    return total

all_docs = sum(count_documents(course) for course in current_courses)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Courses", len(current_courses))
m2.metric("Average Readiness", f"{round(sum(readiness_values) / len(readiness_values))}%")
m3.metric("Knowledge Sources", all_docs)
m4.metric("Current Courses", len([c for c in current_courses if c.get("status", "Current") == "Current"]))

# --------------------------------------------------
# AI Insights
# --------------------------------------------------
st.markdown("## AI Insights")
for insight in generate_platform_insights(current_courses):
    st.write("💡", insight)

# # --------------------------------------------------
# # Knowledge Assistant Quick Access
# # --------------------------------------------------
# st.markdown("## Ask the Knowledge Assistant")
# question = st.text_input("Quick question", placeholder="Example: Summarize CPIS-351 or explain ABET SO4")

# if question:
#     st.info("Open the Knowledge Assistant page for a grounded answer using the course knowledge base.")
#     st.page_link("pages/10_Knowledge_Assistant.py", label="Open Knowledge Assistant", icon="💬")

# --------------------------------------------------
# Footer
# --------------------------------------------------

st.markdown("---")

st.markdown(
    """
    <div style="text-align:center; color:gray; font-size:0.9em;">
        AI-Powered Curriculum Intelligence & Accreditation Support System<br>
        Version 1.0<br>
        © 2026 Dr. Sahar Jambi<br>
        Information Systems Department<br>
        King Abdulaziz University
    </div>
    """,
    unsafe_allow_html=True,
)
