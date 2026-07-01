
import os
import shutil
import warnings
import streamlit as st
import openpyxl

from services.course_service import extract_course_structure
from services.storage_service import (
    load_instructor_profile,
    load_courses,
    save_course,
    update_course,
    generate_course_id,
    update_last_opened,
)
from services.platform_service import (
    instructor_display_name,
    calculate_course_readiness,
    format_timestamp,
)
from services.course_knowledge_agent import build_course_digital_twin

warnings.filterwarnings("ignore", message="Cannot parse header or footer so it will be ignored")

MATRIX_FOLDER = "articulation_matrix"
DOCUMENT_FOLDER = "course_documents"
os.makedirs(MATRIX_FOLDER, exist_ok=True)
os.makedirs(DOCUMENT_FOLDER, exist_ok=True)

instructor_profile = load_instructor_profile()
if not instructor_profile:
    st.warning("Please create your instructor profile first.")
    st.page_link("pages/1_Instructor_Profile.py", label="Go to Instructor Profile", icon="👤")
    st.stop()

st.session_state["instructor_profile"] = instructor_profile
instructor_name = instructor_display_name(instructor_profile)

department_options = ["Computer Science", "Information Technology", "Information Systems"]
semester_options = ["First Semester", "Second Semester"]
status_options = ["Current", "Archived"]


def safe_filename(course_id, label, uploaded_file):
    ext = os.path.splitext(uploaded_file.name)[1]
    clean_label = label.replace(" ", "_").lower()
    return f"{course_id}_{clean_label}{ext}"


def save_uploaded_document(course_id, label, uploaded_file):
    if uploaded_file is None:
        return ""
    filename = safe_filename(course_id, label, uploaded_file)
    path = os.path.join(DOCUMENT_FOLDER, filename)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return filename


def save_uploaded_documents(course_id, label, uploaded_files):
    if not uploaded_files:
        return []
    saved_files = []
    for index, uploaded_file in enumerate(uploaded_files, start=1):
        filename = safe_filename(course_id, f"{label}_{index}", uploaded_file)
        path = os.path.join(DOCUMENT_FOLDER, filename)
        with open(path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        saved_files.append(filename)
    return saved_files


def normalize_file_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    return [value]


def file_display(value):
    files = normalize_file_list(value)
    if not files:
        return "No file uploaded"
    return ", ".join(files)


def has_file(value):
    return len(normalize_file_list(value)) > 0


def empty_course_structure():
    return {
        "clos": [],
        "student_outcomes": [],
        "assessments": [],
        "statistics": {
            "num_clos": 0,
            "num_sos": 0,
            "num_assessments": 0,
        },
    }


def load_matrix(file_path):
    workbook = openpyxl.load_workbook(file_path, data_only=True)
    course_structure = extract_course_structure(workbook)

    return {
        "workbook": workbook,
        "course_structure": course_structure,
        "student_outcomes": course_structure.get("student_outcomes", []),
        "clos": course_structure.get("clos", []),
        "assessments": course_structure.get("assessments", []),
        "assessment_so_map": build_assessment_so_map(course_structure.get("assessments", [])),
    }


def empty_matrix_data():
    course_structure = empty_course_structure()

    return {
        "workbook": None,
        "course_structure": course_structure,
        "student_outcomes": [],
        "clos": [],
        "assessments": [],
        "assessment_so_map": {},
    }


def build_assessment_so_map(assessments):
    assessment_so_map = {}

    for assessment in assessments:
        name = assessment.get("name", "Assessment")
        assessment_so_map[name] = assessment.get("sos", [])

    return assessment_so_map


def matrix_data_for_course(course):
    matrix_file = course.get("matrix_file", "")
    if not matrix_file:
        return empty_matrix_data()

    path = os.path.join(MATRIX_FOLDER, matrix_file)
    if not os.path.exists(path):
        return empty_matrix_data()

    return load_matrix(path)


def build_current_course(course_profile, matrix_data=None):
    matrix_data = matrix_data or empty_matrix_data()
    course_structure = matrix_data.get("course_structure", empty_course_structure())

    st.session_state["current_course"] = {
        "profile": course_profile,
        "course_structure": course_structure,
        "student_outcomes": course_structure.get("student_outcomes", []),
        "clos": course_structure.get("clos", []),
        "assessments": course_structure.get("assessments", []),
        "assessment_so_map": matrix_data.get("assessment_so_map", {}),
    }

    st.session_state["current_course_id"] = course_profile["course_id"]
    st.session_state["course_profile"] = course_profile
    st.session_state["course_structure"] = course_structure

    # Temporary compatibility for existing pages
    st.session_state["student_outcomes"] = course_structure.get("student_outcomes", [])
    st.session_state["clos"] = course_structure.get("clos", [])
    st.session_state["assessments"] = course_structure.get("assessments", [])
    st.session_state["assessment_so_map"] = matrix_data.get("assessment_so_map", {})
    st.session_state["num_clos"] = course_structure.get("statistics", {}).get("num_clos", 0)
    st.session_state["num_sos"] = course_structure.get("statistics", {}).get("num_sos", 0)




def show_course_structure(course_structure):
    st.markdown("### Extracted Course Structure")

    stats = course_structure.get("statistics", {})

    c1, c2, c3 = st.columns(3)
    c1.metric("CLOs", stats.get("num_clos", 0))
    c2.metric("Student Outcomes", stats.get("num_sos", 0))
    c3.metric(
        "Assessment Instances",
        stats.get("num_assessment_instances", stats.get("num_assessments", 0)),
    )

    assessments = course_structure.get(
        "assessment_instances",
        course_structure.get("assessments", []),
    )

    if not assessments:
        st.info("No assessments were extracted from the articulation matrix.")
        return

    st.markdown("### Assessment Summary")

    total_weight = stats.get(
        "total_course_weight",
        round(sum(a.get("course_weight", 0) for a in assessments), 2),
    )

    so_assessments = sum(1 for a in assessments if a.get("assessing_so"))
    non_so_assessments = len(assessments) - so_assessments

    assessed_sos = sorted(
        {
            so
            for a in assessments
            if a.get("assessing_so")
            for so in a.get("assessed_sos", [])
        },
        key=lambda x: int(str(x).replace("SO", "")),
    )

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Assessment Instances", len(assessments))
    s2.metric("SO Assessments", so_assessments)
    s3.metric("Non-SO Assessments", non_so_assessments)
    s4.metric("Total Weight", f"{total_weight}%")

    st.caption(
        "Assessed SOs: "
        + (", ".join(assessed_sos) if assessed_sos else "None detected")
    )

    st.markdown("### Assessment Structure")

    def sort_clos(values):
        return sorted(
            values,
            key=lambda x: int(str(x).replace("CLO", "")),
        )

    def sort_sos(values):
        return sorted(
            values,
            key=lambda x: int(str(x).replace("SO", "")),
        )

    def compress_ids(values, prefix):
        values = sort_clos(values) if prefix == "CLO" else sort_sos(values)

        nums = []
        for value in values:
            try:
                nums.append(int(str(value).replace(prefix, "")))
            except Exception:
                pass

        if not nums:
            return "—"

        ranges = []
        start = prev = nums[0]

        for num in nums[1:]:
            if num == prev + 1:
                prev = num
            else:
                if start == prev:
                    ranges.append(f"{prefix}{start}")
                else:
                    ranges.append(f"{prefix}{start}–{prefix}{prev}")
                start = prev = num

        if start == prev:
            ranges.append(f"{prefix}{start}")
        else:
            ranges.append(f"{prefix}{start}–{prefix}{prev}")

        return ", ".join(ranges)

    def format_so_mapping(assessment):
        if assessment.get("assessing_so"):
            distribution = assessment.get("so_distribution", {})

            if distribution:
                items = sorted(
                    distribution.items(),
                    key=lambda item: int(str(item[0]).replace("SO", "")),
                )

                return ", ".join(
                    f"{so} ({value:g}%)"
                    for so, value in items
                )

            sos = assessment.get("assessed_sos", [])
            return ", ".join(sort_sos(sos)) if sos else "—"

        mapped_sos = assessment.get("mapped_sos", assessment.get("sos", []))
        return ", ".join(sort_sos(mapped_sos)) if mapped_sos else "—"

    header = "| Week | Assessment | Type | Weight (%) | CLOs | SO Assessment | SO Mapping (Distribution) |\n"
    header += "|:---:|---|:---:|:---:|---|:---:|---|\n"

    rows = []

    for a in assessments:
        week = a.get("week", "")
        name = a.get("name", "")
        assessment_type = a.get("type", "")
        weight = a.get("course_weight", a.get("weight", 0))
        clos = compress_ids(a.get("clos", []), "CLO")
        so_assessment = "✓" if a.get("assessing_so") else "✗"
        so_mapping = format_so_mapping(a)

        rows.append(
            f"| {week} | {name} | {assessment_type} | {weight:g} | {clos} | {so_assessment} | {so_mapping} |"
        )

    st.markdown(header + "\n".join(rows))

def copy_existing_matrix_if_course_id_changed(old_course_id, new_course_id, profile, updated_course):
    if not profile.get("matrix_file") or old_course_id == new_course_id:
        return

    old_path = os.path.join(MATRIX_FOLDER, profile["matrix_file"])
    new_matrix_file = new_course_id + os.path.splitext(profile["matrix_file"])[1]
    new_path = os.path.join(MATRIX_FOLDER, new_matrix_file)

    if os.path.exists(old_path):
        shutil.copy(old_path, new_path)

    updated_course["matrix_file"] = new_matrix_file


def show_course_readiness(course):
    readiness = calculate_course_readiness(course)

    st.markdown("### Overall Readiness")
    st.progress(readiness.get("overall", 0) / 100, text=f"{readiness.get('overall', 0)}%")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Essential", f"{readiness.get('essential', 0)}%")
    c2.metric("Accreditation", f"{readiness.get('accreditation', 0)}%")
    c3.metric("Teaching", f"{readiness.get('teaching', 0)}%")
    c4.metric("Assessment", f"{readiness.get('assessment', 0)}%")

    st.markdown("### Readiness Notes")

    notes = []

    if has_file(course.get("syllabus_file")):
        notes.append("Course syllabus is available and will serve as the main course knowledge source.")
    else:
        notes.append("Course syllabus has not been uploaded yet. It is the main source for course knowledge.")

    if has_file(course.get("matrix_file")):
        notes.append("Articulation matrix is available and can support curriculum intelligence and accreditation analysis.")
    else:
        notes.append("Articulation matrix is not available. This is acceptable for courses where the matrix has not yet been prepared.")

    if has_file(course.get("lab_syllabus_file")):
        notes.append("Lab syllabus is available and can support analysis of practical learning activities.")
    else:
        notes.append("Lab syllabus is optional and not currently available.")

    if has_file(course.get("slides_file")):
        notes.append("Teaching slides are available and can support teaching improvement and assessment generation.")
    else:
        notes.append("Teaching slides are not currently available.")

    if has_file(course.get("labs_file")):
        notes.append("Lab file is available and can support teaching improvement and assessment generation.")
    else:
        notes.append("Lab file is not currently available.")

    if has_file(course.get("assessments_file")):
        notes.append("Assessment package file(s) are available. The system can later classify them into quizzes, assignments, projects, exams, and rubrics.")
    else:
        notes.append("Assessment package is not currently available.")

    if has_file(course.get("esr_file")):
        notes.append("Previous ESR file(s) are available and will be used as the main historical source for previous achievement and improvement memory.")
    else:
        notes.append("Previous ESR is not currently available. Historical achievement analysis will be limited until it is added.")

    if has_file(course.get("coordination_file")):
        notes.append("Previous Coordination MOM(s) are available and can support continuity of course coordination decisions.")
    else:
        notes.append("Previous Coordination MOM(s) are optional and not currently available.")

    for note in notes:
        st.info(note)


st.title("📚 Course Workspace")
st.write(
    "Manage course information and knowledge sources that power the Course Digital Twin. "
    "AI-enriched fields such as course description, required/elective status, track, level, prerequisites, "
    "and required teaching background will be generated later from the FCIT catalog, syllabus, and course resources."
)


st.markdown("## New Course")

with st.expander("Add a new course"):
    st.markdown("### Course Information")

    new_department = st.selectbox("Department *", department_options, index=2, key="new_department")
    new_academic_year = st.text_input("Academic Year *", "2025-2026", key="new_academic_year")
    new_semester = st.selectbox("Semester *", semester_options, index=1, key="new_semester")
    new_course_code = st.text_input("Course Code *", "", key="new_course_code")
    new_course_name = st.text_input("Course Name *", "", key="new_course_name")
    new_sections = st.text_input("Section(s) *", "", key="new_sections")
    new_coordinator = st.text_input("Coordinator", instructor_name, key="new_coordinator")
    st.text_input("Instructor", instructor_name, disabled=True, key="new_instructor_display")
    new_status = st.selectbox("Status *", status_options, index=0, key="new_status")

    st.markdown("### Essential Knowledge Sources")
    new_syllabus = st.file_uploader("Course Syllabus", type=["pdf", "docx", "txt"], key="new_syllabus")
    new_matrix = st.file_uploader("Articulation Matrix", type=["xlsx", "xls", "xlsm"], key="new_matrix")
    new_lab_syllabus = st.file_uploader("Lab Syllabus", type=["pdf", "docx", "txt"], key="new_lab_syllabus")
    new_slides = st.file_uploader("Teaching Slides", type=["pdf", "pptx", "zip"], key="new_slides")
    new_labs = st.file_uploader("Lab File", type=["zip", "pdf", "docx", "txt", "ipynb", "py", "xlsx", "csv"], key="new_labs")

    st.markdown("### Assessment Resources")
    new_assessment_package = st.file_uploader(
        "Add Assessment Package",
        type=["zip", "pdf", "docx", "pptx", "xlsx"],
        accept_multiple_files=True,
        key="new_assessment_package",
    )

    st.markdown("### Continuous Improvement Knowledge")
    has_previous_esr = st.checkbox("Do you have a previous ESR to add?", key="new_has_previous_esr")
    new_esr = []
    if has_previous_esr:
        new_esr = st.file_uploader(
            "Add Previous ESR",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="new_previous_esr",
        )

    has_previous_coordination = st.checkbox(
        "Do you have previous Coordination MOM(s) to add?",
        key="new_has_previous_coordination",
    )
    new_coordination = []
    if has_previous_coordination:
        new_coordination = st.file_uploader(
            "Add Previous Coordination MOM(s)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="new_previous_coordination",
        )

    add_course = st.button("Add Course")

if add_course:
    if not new_course_code or not new_course_name or not new_academic_year or not new_sections:
        st.warning("Please complete all required course information fields.")
    else:
        course_id = generate_course_id(new_course_code, new_academic_year, new_semester)

        matrix_filename = ""
        if new_matrix is not None:
            matrix_filename = course_id + os.path.splitext(new_matrix.name)[1]
            with open(os.path.join(MATRIX_FOLDER, matrix_filename), "wb") as f:
                f.write(new_matrix.getbuffer())

        new_course_profile = {
            "course_id": course_id,
            "department": new_department,
            "academic_year": new_academic_year,
            "semester": new_semester,
            "course_code": new_course_code,
            "course_name": new_course_name,
            "instructor": instructor_name,
            "coordinator": new_coordinator,
            "sections": new_sections,
            "status": new_status,

            "course_description": "",
            "course_type": "",
            "level": "",
            "track": "",
            "prerequisites": "",
            "teaching_background": "",

            "syllabus_file": save_uploaded_document(course_id, "syllabus", new_syllabus) if new_syllabus else "",
            "matrix_file": matrix_filename,
            "lab_syllabus_file": save_uploaded_document(course_id, "lab_syllabus", new_lab_syllabus) if new_lab_syllabus else "",
            "slides_file": save_uploaded_document(course_id, "slides", new_slides) if new_slides else "",
            "labs_file": save_uploaded_document(course_id, "labs", new_labs) if new_labs else "",
            "assessments_file": save_uploaded_documents(course_id, "assessment_package", new_assessment_package)
            
            if new_assessment_package else [],
            "esr_file": save_uploaded_documents(course_id, "previous_esr", new_esr) if new_esr else [],
            "coordination_file": save_uploaded_documents(course_id, "coordination_meeting", new_coordination)
            
            if new_coordination else [],
            "rubrics_file": "",
            "last_opened": "",
        }

        save_course(new_course_profile)
        build_current_course(new_course_profile, matrix_data_for_course(new_course_profile))
        update_last_opened(course_id)

        st.session_state["course_added_message"] = "Course added successfully."
        st.session_state["selected_course_id"] = course_id
        st.rerun()


st.divider()
st.markdown("## Saved Courses")

all_courses = load_courses()
selected_course = None
load_saved = False

if all_courses:
    course_labels = [
        f"{c.get('course_code','')} - {c.get('course_name','')} "
        f"({c.get('semester','')}, {c.get('academic_year','')}) [{c.get('sections','')}]"
        for c in all_courses
    ]

    default_selected_index = next(
        (
            i
            for i, c in enumerate(all_courses)
            if c.get("course_id") == st.session_state.get("selected_course_id")
        ),
        0,
    )

    selected_index = st.selectbox(
        "Select saved course",
        range(len(course_labels)),
        index=default_selected_index,
        format_func=lambda i: course_labels[i],
    )

    selected_course = all_courses[selected_index]
    load_saved = st.button("Load Selected Course")
else:
    st.info("No saved courses found.")

if load_saved and selected_course:
    matrix_data = matrix_data_for_course(selected_course)
    update_last_opened(selected_course["course_id"])
    build_current_course(selected_course, matrix_data)
    st.success("Course loaded successfully.")
    st.rerun()


if "current_course" not in st.session_state:
    st.info("Add a new course or load a saved course to begin.")
    st.stop()

profile = st.session_state["current_course"]["profile"]

if "course_added_message" in st.session_state:
    st.success(st.session_state.pop("course_added_message"))

if "course_update_message" in st.session_state:
    st.success(st.session_state["course_update_message"])
    del st.session_state["course_update_message"]

st.divider()
st.markdown("## Loaded Course")
st.markdown(f"### {profile.get('course_code', '')} – {profile.get('course_name', '')}")

tab_info, tab_insights, tab_sources, tab_structure, tab_readiness = st.tabs(
    [
        "📋 Course Information",
        "💡 Course Insights",
        "📚 Knowledge Sources",
        "📋 Course Structure",
        "📈 Course Readiness",
    ]
)


with tab_info:
    st.markdown("### Course Information")

    with st.form("update_course_info_form"):
        update_department = st.selectbox(
            "Department *",
            department_options,
            index=department_options.index(profile.get("department", "Information Systems"))
            if profile.get("department", "Information Systems") in department_options else 2,
        )

        update_academic_year = st.text_input("Academic Year *", profile.get("academic_year", ""))
        update_semester = st.selectbox(
            "Semester *",
            semester_options,
            index=semester_options.index(profile.get("semester", "Second Semester"))
            if profile.get("semester", "Second Semester") in semester_options else 1,
        )

        update_course_code = st.text_input("Course Code *", profile.get("course_code", ""))
        update_course_name = st.text_input("Course Name *", profile.get("course_name", ""))
        update_sections = st.text_input("Section(s) *", profile.get("sections", ""))
        update_coordinator = st.text_input("Coordinator", profile.get("coordinator", ""))
        st.text_input("Instructor", profile.get("instructor") or instructor_name, disabled=True)

        update_status = st.selectbox(
            "Status *",
            status_options,
            index=0 if profile.get("status", "Current") == "Current" else 1,
        )

        update_info_button = st.form_submit_button("Update Course Information")

    if update_info_button:
        if not update_course_code or not update_course_name or not update_academic_year or not update_sections:
            st.warning("Please complete all required course fields.")
        else:
            old_course_id = profile["course_id"]
            new_course_id = generate_course_id(update_course_code, update_academic_year, update_semester)

            updated_course = profile.copy()
            updated_course.update(
                {
                    "course_id": new_course_id,
                    "department": update_department,
                    "academic_year": update_academic_year,
                    "semester": update_semester,
                    "course_code": update_course_code,
                    "course_name": update_course_name,
                    "sections": update_sections,
                    "coordinator": update_coordinator,
                    "instructor": profile.get("instructor") or instructor_name,
                    "status": update_status,
                }
            )

            copy_existing_matrix_if_course_id_changed(old_course_id, new_course_id, profile, updated_course)

            update_course(old_course_id, updated_course)
            build_current_course(updated_course, matrix_data_for_course(updated_course))
            update_last_opened(updated_course["course_id"])

            st.session_state["course_update_message"] = "Course information updated successfully."
            st.rerun()



with tab_insights:
    st.markdown("### Course Insights")

    course_structure = st.session_state.get("course_structure", empty_course_structure())
    clos = course_structure.get("clos", st.session_state.get("clos", []))

    try:
        digital_twin = build_course_digital_twin(profile, clos=clos)
    except Exception:
        digital_twin = {}

    course_summary = digital_twin.get("course_summary", "Not generated yet.")
    official_prereq = digital_twin.get("official_prerequisites", "Not generated yet.")
    student_background = digital_twin.get("expected_student_background", "Not generated yet.")
    instructor_background = digital_twin.get("recommended_instructor_background", "Not generated yet.")
    source_note = digital_twin.get("source_note", "✨ AI generated from: Course Knowledge Base")

    with st.container(border=True):
        st.markdown("#### 📚 AI Course Summary")
        st.write(course_summary)
        st.caption(source_note)

    with st.container(border=True):
        st.markdown("#### 📖 Official Prerequisite(s)")
        st.write(official_prereq)
        st.caption("📄 Extracted from: Course Syllabus")

    with st.container(border=True):
        st.markdown("#### 👨‍🎓 Expected Student Background")
        st.write(student_background)
        st.caption("✨ AI generated from: Official Prerequisite(s) • Course Syllabus • CLOs")

    with st.container(border=True):
        st.markdown("#### 👩‍🏫 Recommended Instructor Background")
        st.write(instructor_background)
        st.caption("✨ AI generated from: Course Syllabus • CLOs • Teaching Materials")


with tab_sources:
    st.markdown("### Knowledge Sources")
    st.write(
        "Each knowledge source below shows the current file(s), explains how AI will use it, "
        "and allows you to upload, replace, or add files."
    )

    with st.form("update_knowledge_sources_form"):
        st.markdown("#### Essential Knowledge Sources")

        with st.container(border=True):
            st.markdown("**📘 Course Syllabus**")
            st.write(f"Current file(s): {file_display(profile.get('syllabus_file'))}")
            st.caption("Used by AI to generate course description, infer course context, identify topics, and support course-related questions.")
            syllabus_file = st.file_uploader(
                "Upload / Replace Course Syllabus",
                type=["pdf", "docx", "txt"],
                key="update_syllabus",
            )

        with st.container(border=True):
            st.markdown("**📊 Articulation Matrix**")
            st.write(f"Current file(s): {file_display(profile.get('matrix_file'))}")
            st.caption("Used by AI to analyze CLO–SO mapping, Bloom levels, assessment alignment, and accreditation evidence.")
            replacement_matrix = st.file_uploader(
                "Upload / Replace Articulation Matrix",
                type=["xlsx", "xls", "xlsm"],
                key="current_replacement_matrix",
            )

        with st.container(border=True):
            st.markdown("**🧪 Lab Syllabus**")
            st.write(f"Current file(s): {file_display(profile.get('lab_syllabus_file'))}")
            st.caption("Used by AI to understand practical activities, lab learning outcomes, and required teaching preparation.")
            lab_syllabus_file = st.file_uploader(
                "Upload / Replace Lab Syllabus",
                type=["pdf", "docx", "txt"],
                key="update_lab_syllabus",
            )

        with st.container(border=True):
            st.markdown("**📑 Teaching Slides**")
            st.write(f"Current file(s): {file_display(profile.get('slides_file'))}")
            st.caption("Used by AI to review topics, suggest teaching improvements, and generate aligned assessments.")
            slides_file = st.file_uploader(
                "Upload / Replace Teaching Slides",
                type=["pdf", "pptx", "zip"],
                key="update_slides",
            )

        with st.container(border=True):
            st.markdown("**🧪 Lab File**")
            st.write(f"Current file: {file_display(profile.get('labs_file'))}")
            st.caption("Used by AI to understand lab activities, exercises, datasets, notebooks, and practical learning tasks.")
            labs_file = st.file_uploader(
                "Upload / Replace Lab File",
                type=["zip", "pdf", "docx", "txt", "ipynb", "py", "xlsx", "csv"],
                key="update_lab_files",
            )

        st.markdown("#### Assessment Resources")

        with st.container(border=True):
            st.markdown("**📝 Assessment Package**")
            st.write(f"Current file(s): {file_display(profile.get('assessments_file'))}")
            st.caption("Used by AI to classify assessments, identify assessment types, review alignment, and generate new assessment items.")
            assessments_files = st.file_uploader(
                "Add Assessment Package",
                type=["zip", "pdf", "docx", "pptx", "xlsx"],
                accept_multiple_files=True,
                key="update_assessment_package",
            )

        st.markdown("#### Continuous Improvement Knowledge")

        with st.container(border=True):
            st.markdown("**📈 Previous ESR**")
            st.write(f"Current file(s): {file_display(profile.get('esr_file'))}")
            st.caption("Used by AI to understand previous student achievement, instructor reflections, and improvement actions.")
            esr_files = st.file_uploader(
                "Add Previous ESR",
                type=["pdf", "docx", "txt"],
                accept_multiple_files=True,
                key="update_esr",
            )

        with st.container(border=True):
            st.markdown("**👥 Previous Coordination MOM(s)**")
            st.write(f"Current file(s): {file_display(profile.get('coordination_file'))}")
            st.caption("Used by AI to understand previous coordination decisions, agreed actions, and governance notes.")
            coordination_files = st.file_uploader(
                "Add Previous Coordination MOM(s)",
                type=["pdf", "docx", "txt"],
                accept_multiple_files=True,
                key="update_coordination",
            )

        update_sources_button = st.form_submit_button("Update Knowledge Sources")

    if update_sources_button:
        old_course_id = profile["course_id"]
        updated_course = profile.copy()

        single_upload_map = {
            "syllabus_file": ("syllabus", syllabus_file),
            "lab_syllabus_file": ("lab_syllabus", lab_syllabus_file),
            "slides_file": ("slides", slides_file),
            "labs_file": ("labs", labs_file),
        }

        for field, (label, uploaded) in single_upload_map.items():
            if uploaded is not None:
                updated_course[field] = save_uploaded_document(updated_course["course_id"], label, uploaded)

        if assessments_files:
            existing = normalize_file_list(updated_course.get("assessments_file"))
            new_files = save_uploaded_documents(updated_course["course_id"], "assessment_package", assessments_files)
            updated_course["assessments_file"] = existing + new_files

        if esr_files:
            existing = normalize_file_list(updated_course.get("esr_file"))
            new_files = save_uploaded_documents(updated_course["course_id"], "previous_esr", esr_files)
            updated_course["esr_file"] = existing + new_files

        if coordination_files:
            existing = normalize_file_list(updated_course.get("coordination_file"))
            new_files = save_uploaded_documents(updated_course["course_id"], "coordination_meeting", coordination_files)
            updated_course["coordination_file"] = existing + new_files

        if replacement_matrix is not None:
            new_matrix_file = updated_course["course_id"] + os.path.splitext(replacement_matrix.name)[1]
            with open(os.path.join(MATRIX_FOLDER, new_matrix_file), "wb") as f:
                f.write(replacement_matrix.getbuffer())
            updated_course["matrix_file"] = new_matrix_file
        else:
            copy_existing_matrix_if_course_id_changed(
                old_course_id,
                updated_course["course_id"],
                profile,
                updated_course,
            )

        update_course(old_course_id, updated_course)
        build_current_course(updated_course, matrix_data_for_course(updated_course))
        update_last_opened(updated_course["course_id"])

        st.session_state["course_update_message"] = "Knowledge sources updated successfully."
        st.rerun()


with tab_structure:
    course_structure = st.session_state.get("course_structure", empty_course_structure())
    show_course_structure(course_structure)


with tab_readiness:
    show_course_readiness(profile)

    st.markdown("### Recent Activity")
    st.caption(f"Current session updated: {format_timestamp()}")


