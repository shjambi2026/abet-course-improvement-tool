import streamlit as st

def get_course_ai():
    if "course_ai" not in st.session_state:
        st.session_state["course_ai"] = {
            "digital_twin": {},
            "curriculum": {},
            "enhancement": {},
            "assessment": {},
            "attainment": {},
            "esr": {},
        }
    return st.session_state["course_ai"]