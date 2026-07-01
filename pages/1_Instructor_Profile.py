import streamlit as st

from services.storage_service import (
    load_instructor_profile,
    save_instructor_profile
)

st.title("👤 Instructor Profile")

# ----------------------------------------
# Load profile from CSV
# ----------------------------------------

profile = load_instructor_profile()

if profile is None:
    profile = {}

titles = ["Mrs.", "Mr.", "Dr.", "Prof."]

departments = [
    "Computer Science",
    "Information Technology",
    "Information Systems"
]

selected_title = st.selectbox(
    "Title",
    titles,
    index=titles.index(profile.get("title", "Dr."))
    if profile.get("title", "Dr.") in titles else 2
)

name = st.text_input(
    "Instructor Name *",
    profile.get("name", "")
)

department = st.selectbox(
    "Department *",
    departments,
    index=departments.index(profile.get("department", "Information Systems"))
    if profile.get("department", "Information Systems") in departments else 2
)

college = st.text_input(
    "College",
    profile.get(
        "college",
        "Faculty of Computing and Information Technology"
    )
)

university = st.text_input(
    "University",
    profile.get(
        "university",
        "King Abdulaziz University"
    )
)

button_text = (
    "Update Profile"
    if profile
    else "Create Profile"
)

if st.button(button_text):

    profile = {
        "title": selected_title,
        "name": name,
        "department": department,
        "college": college,
        "university": university
    }

    save_instructor_profile(profile)

    # Keep it in session for the current run
    st.session_state["instructor_profile"] = profile

    st.success("Instructor profile saved successfully.")

    st.rerun()