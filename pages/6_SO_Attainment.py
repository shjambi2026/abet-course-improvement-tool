from datetime import datetime
from io import BytesIO
import json
import os
import streamlit as st

from services.attainment_service import (
    calculate_so_attainment_from_raw_workbook,
    build_so_attainment_report,
)
from services.attainment_template_service import generate_so_attainment_template
from services.attainment_agent import analyze_so_attainment
from services.course_knowledge_agent import build_course_digital_twin
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

if "course_structure" not in st.session_state:
    st.warning("Please load a course with an articulation matrix in Course Workspace first.")
    st.page_link("pages/2_Course_Workspace.py", label="Go to Course Workspace", icon="📚")
    st.stop()


# --------------------------------------------------
# Load Data
# --------------------------------------------------

course = st.session_state["current_course"]["profile"]
course_structure = st.session_state.get("course_structure", {})
clos = course_structure.get("clos", [])
student_outcomes = course_structure.get("student_outcomes", [])

all_assessments = course_structure.get(
    "assessment_instances",
    course_structure.get("assessments", []),
)

so_assessments = [
    assessment
    for assessment in all_assessments
    if assessment.get("assessing_so", False)
]

digital_twin = build_course_digital_twin(course, clos=clos)


# --------------------------------------------------
# Helper Functions
# --------------------------------------------------

def clean_filename_text(value):
    return (
        str(value or "")
        .replace("/", "-")
        .replace("\\", "-")
        .replace(" ", "")
        .replace(":", "")
        .replace("•", "-")
    )


def sort_so_ids(values):
    def key(value):
        try:
            return int(str(value).replace("SO", ""))
        except Exception:
            return 9999

    return sorted(values or [], key=key)


def sort_clo_ids(values):
    def key(value):
        try:
            return int(str(value).replace("CLO", ""))
        except Exception:
            return 9999

    return sorted(values or [], key=key)


def format_so_distribution(assessment):
    distribution = assessment.get("so_distribution", {})

    if distribution:
        items = sorted(
            distribution.items(),
            key=lambda item: int(str(item[0]).replace("SO", "")),
        )
        return ", ".join(f"{so} ({value:g}%)" for so, value in items)

    sos = sort_so_ids(assessment.get("assessed_sos", assessment.get("sos", [])))
    return ", ".join(sos) if sos else "—"


def format_assessment_label(assessment):
    week = assessment.get("week", "")
    name = assessment.get("name", "Assessment")
    so_text = format_so_distribution(assessment)
    return f"Week {week} • {name} • {so_text}"


def get_assessment_id(assessment):
    return assessment.get("id") or clean_filename_text(assessment.get("name", "Assessment"))


def get_assessed_sos(assessment):
    distribution = assessment.get("so_distribution", {})
    if distribution:
        return sort_so_ids(distribution.keys())

    return sort_so_ids(assessment.get("assessed_sos", assessment.get("sos", [])))


def generate_template_file(course, assessment):
    try:
        return generate_so_attainment_template(
            course=course,
            assessment=assessment,
        )
    except TypeError:
        return generate_so_attainment_template(
            course=course,
            assessment_name=assessment.get("name", "Assessment"),
            assessed_sos=get_assessed_sos(assessment),
        )


def calculate_combined_so_attainment(saved_results):
    weighted_totals = {}
    weight_totals = {}

    for record in saved_results.values():
        assessment = record.get("assessment", {})
        attainment = record.get("attainment", {})
        summary = attainment.get("summary", [])

        course_weight = assessment.get("course_weight", assessment.get("weight", 0))
        so_distribution = assessment.get("so_distribution", {})

        attainment_by_so = {
            item.get("so"): item.get("attainment_percent", 0)
            for item in summary
        }

        for so, distribution_percent in so_distribution.items():
            if so not in attainment_by_so:
                continue

            weight = course_weight * (distribution_percent / 100)

            weighted_totals[so] = weighted_totals.get(so, 0) + (
                attainment_by_so[so] * weight
            )
            weight_totals[so] = weight_totals.get(so, 0) + weight

    combined_summary = []

    for so in sort_so_ids(weighted_totals.keys()):
        total_weight = weight_totals.get(so, 0)

        attainment_percent = (
            round(weighted_totals[so] / total_weight, 2)
            if total_weight
            else 0
        )

        combined_summary.append(
            {
                "so": so,
                "combined_weight": round(total_weight, 2),
                "attainment_percent": attainment_percent,
                "target_percent": 65,
                "target_met": "Yes" if attainment_percent >= 65 else "No",
            }
        )

    return {
        "summary": combined_summary,
        "statistics": {
            "assessed_sos": len(combined_summary),
            "average_attainment": round(
                sum(item["attainment_percent"] for item in combined_summary) / len(combined_summary),
                2,
            )
            if combined_summary
            else 0,
            "sos_met_target": sum(
                1 for item in combined_summary if item.get("target_met") == "Yes"
            ),
        },
        "source": "Combined saved SO-assessment results",
    }


def update_combined_attainment_state():
    saved_results = st.session_state.get("so_attainment_results", {})

    if saved_results:
        combined_attainment = calculate_combined_so_attainment(saved_results)

        st.session_state["combined_so_attainment"] = combined_attainment
        st.session_state.setdefault("course_evidence", {})
        st.session_state["course_evidence"]["so_attainment_results"] = saved_results
        st.session_state["course_evidence"]["combined_so_attainment"] = combined_attainment
    else:
        st.session_state["combined_so_attainment"] = {}
        if "course_evidence" in st.session_state:
            st.session_state["course_evidence"]["so_attainment_results"] = {}
            st.session_state["course_evidence"]["combined_so_attainment"] = {}


def render_markdown_table(headers, rows):
    header = "| " + " | ".join(headers) + " |\n"
    separator = "|" + "|".join(["---" for _ in headers]) + "|\n"
    body = "\n".join("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    st.markdown(header + separator + body)



UPLOAD_FOLDER = "so_attainment_uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def safe_file_part(value):
    return (
        str(value or "")
        .replace("/", "-")
        .replace("\\", "-")
        .replace(" ", "_")
        .replace(":", "")
        .replace("•", "-")
    )


def course_upload_folder(course):
    course_id = course.get("course_id") or clean_filename_text(
        f"{course.get('course_code', 'Course')}_{course.get('academic_year', '')}_{course.get('semester', '')}"
    )
    folder = os.path.join(UPLOAD_FOLDER, safe_file_part(course_id))
    os.makedirs(folder, exist_ok=True)
    return folder


def saved_marks_paths(course, assessment_id):
    folder = course_upload_folder(course)
    safe_id = safe_file_part(assessment_id)
    return (
        os.path.join(folder, f"{safe_id}.xlsx"),
        os.path.join(folder, f"{safe_id}.json"),
    )


def save_uploaded_marks_workbook(course, assessment_id, uploaded_filename, uploaded_bytes, uploaded_at):
    xlsx_path, meta_path = saved_marks_paths(course, assessment_id)

    with open(xlsx_path, "wb") as f:
        f.write(uploaded_bytes)

    metadata = {
        "assessment_id": assessment_id,
        "uploaded_filename": uploaded_filename,
        "uploaded_at": uploaded_at,
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def delete_uploaded_marks_workbook(course, assessment_id):
    xlsx_path, meta_path = saved_marks_paths(course, assessment_id)

    for path in [xlsx_path, meta_path]:
        if os.path.exists(path):
            os.remove(path)


def load_persisted_attainment_results(course, so_assessments):
    results = {}

    for assessment in so_assessments:
        aid = get_assessment_id(assessment)
        xlsx_path, meta_path = saved_marks_paths(course, aid)

        if not os.path.exists(xlsx_path):
            continue

        try:
            with open(xlsx_path, "rb") as f:
                uploaded_bytes = f.read()

            metadata = {}

            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

            attainment = calculate_so_attainment_from_raw_workbook(
                BytesIO(uploaded_bytes)
            )

            results[aid] = {
                "assessment": assessment,
                "attainment": attainment,
                "uploaded_at": metadata.get("uploaded_at", ""),
                "uploaded_filename": metadata.get("uploaded_filename", f"{aid}.xlsx"),
                "uploaded_bytes": uploaded_bytes,
            }

        except Exception:
            # Skip corrupted or incompatible files; the user can re-upload.
            continue

    return results



# --------------------------------------------------
# Page Header
# --------------------------------------------------

st.title("📊 Student Outcome Attainment")

st.write(
    "Download an assessment-specific marks workbook, upload completed student SO marks, "
    "calculate SO attainment, and save the results for the EOS Report."
)

st.markdown(f"## {course.get('course_code', '')} – {course.get('course_name', '')}")


# --------------------------------------------------
# Initialize State
# --------------------------------------------------

persisted_results = load_persisted_attainment_results(course, so_assessments)

if "so_attainment_results" not in st.session_state:
    st.session_state["so_attainment_results"] = persisted_results
else:
    # Reload files from disk so saved attainment appears whenever the system loads.
    st.session_state["so_attainment_results"].update(persisted_results)

if "so_attainment_ai_results" not in st.session_state:
    st.session_state["so_attainment_ai_results"] = {}

update_combined_attainment_state()


# --------------------------------------------------
# Step 1: Select SO Assessment
# --------------------------------------------------

st.markdown("---")
st.markdown("## 1️⃣ Select SO Assessment")

if not so_assessments:
    st.warning(
        "No SO-assessing assessments were detected. Please check the Articulation Matrix and GradeDistribution sheets."
    )
    st.stop()

assessment = st.selectbox(
    "Assessment",
    so_assessments,
    format_func=format_assessment_label,
)

assessment_id = get_assessment_id(assessment)
assessment_name = assessment.get("name", "Assessment")
assessed_sos = get_assessed_sos(assessment)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Week", assessment.get("week", ""))
c2.metric("Type", assessment.get("type", "Assessment"))
c3.metric("Weight (%)", f"{assessment.get('course_weight', assessment.get('weight', 0)):g}")
c4.metric("SO Assessment", "Yes" if assessment.get("assessing_so") else "No")

st.markdown("**Assessment:** " + assessment_name)
st.markdown("**CLOs:** " + (", ".join(sort_clo_ids(assessment.get("clos", []))) or "—"))
st.markdown("**SO Mapping (Distribution):** " + format_so_distribution(assessment))

st.caption(
    "The downloaded Excel workbook should be filled with Program, Section, Student ID, maximum marks, "
    "and the marks earned for each assessed Student Outcome, then uploaded back to this page."
)


# --------------------------------------------------
# Step 2: Download Marks Workbook Template
# --------------------------------------------------

st.markdown("---")
st.markdown("## 2️⃣ Download Marks Workbook Template")

template_file = generate_template_file(course, assessment)

course_code = clean_filename_text(course.get("course_code", "Course"))
academic_year = clean_filename_text(course.get("academic_year", ""))
semester = clean_filename_text(course.get("semester", ""))
assessment_label = clean_filename_text(assessment_name)
today = datetime.now().strftime("%Y-%m-%d")

template_filename = (
    f"SO_Marks_Template_"
    f"{assessment_label}_"
    f"{course_code}_"
    f"{academic_year}_"
    f"{semester}_"
    f"{today}.xlsx"
)

st.download_button(
    label="📥 Download SO Marks Template",
    data=template_file,
    file_name=template_filename,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.info(
    "Use this workbook to enter Program, Section, Student ID, maximum marks, and SO-specific marks for this assessment."
)


# --------------------------------------------------
# Step 3: Upload Completed Workbook
# --------------------------------------------------

st.markdown("---")
st.markdown("## 3️⃣ Upload and Calculate Completed Marks Workbook")

upload_widget_key = f"upload_{assessment_id}_{st.session_state.get('upload_reset_counter', 0)}"

uploaded_workbook = st.file_uploader(
    "Upload completed SO marks workbook",
    type=["xlsx"],
    key=upload_widget_key,
)

if uploaded_workbook:
    st.caption(f"Uploaded file: {uploaded_workbook.name}")

if uploaded_workbook:
    try:
        uploaded_bytes = uploaded_workbook.getvalue()
        attainment = calculate_so_attainment_from_raw_workbook(uploaded_workbook)

        save_uploaded_marks_workbook(
            course=course,
            assessment_id=assessment_id,
            uploaded_filename=uploaded_workbook.name,
            uploaded_bytes=uploaded_bytes,
            uploaded_at=today,
        )

        st.session_state["so_attainment_results"][assessment_id] = {
            "assessment": assessment,
            "attainment": attainment,
            "uploaded_at": today,
            "uploaded_filename": uploaded_workbook.name,
            "uploaded_bytes": uploaded_bytes,
        }

        if assessment_id in st.session_state["so_attainment_ai_results"]:
            del st.session_state["so_attainment_ai_results"][assessment_id]

        update_combined_attainment_state()

        # Show the latest uploaded result in Section 4.
        st.session_state["selected_attainment_summary_id"] = assessment_id

        # Compatibility with earlier pages.
        st.session_state["so_attainment"] = attainment
        st.session_state["so_attainment_ai"] = {}

        st.success(f"SO attainment calculated and saved for {assessment_name}.")

    except Exception as e:
        st.error("Could not calculate SO attainment from the uploaded workbook.")
        st.caption(str(e))
        st.stop()


saved_results = st.session_state.get("so_attainment_results", {})
current_record = saved_results.get(assessment_id, {})
attainment = current_record.get("attainment", {})
attainment_ai = st.session_state["so_attainment_ai_results"].get(assessment_id, {})


# --------------------------------------------------
# Step 4: Display Assessment Results
# --------------------------------------------------

saved_results = st.session_state.get("so_attainment_results", {})

if saved_results:
    st.markdown("---")
    st.markdown("## 4️⃣ Assessment-Level Attainment Summary")

    saved_assessment_ids = list(saved_results.keys())

    selected_default = st.session_state.get("selected_attainment_summary_id")

    if selected_default not in saved_assessment_ids:
        selected_default = saved_assessment_ids[-1]

    selected_index = saved_assessment_ids.index(selected_default)

    selected_summary_id = st.selectbox(
        "Select uploaded assessment result",
        saved_assessment_ids,
        index=selected_index,
        format_func=lambda aid: saved_results[aid].get("assessment", {}).get("name", aid),
        key="selected_attainment_summary_id",
    )

    summary_record = saved_results[selected_summary_id]
    summary_assessment = summary_record.get("assessment", {})
    summary_assessment_name = summary_assessment.get("name", selected_summary_id)
    summary_attainment = summary_record.get("attainment", {})

    st.markdown(f"**Assessment:** {summary_assessment_name}")

    summary = summary_attainment.get("summary", [])
    statistics = summary_attainment.get("statistics", {})

    m1, m2, m3 = st.columns(3)
    m1.metric("Assessed SOs", statistics.get("assessed_sos", 0))
    m2.metric("SOs Meeting Target", statistics.get("sos_met_target", 0))
    m3.metric("Average Attainment", f"{statistics.get('average_attainment', 0)}%")

    rows = []

    for item in summary:
        rows.append(
            [
                item.get("so", ""),
                item.get("students_assessed", 0),
                item.get("students_attained", 0),
                f"{item.get('attainment_percent', 0)}%",
                item.get("target_met", "No"),
            ]
        )

    render_markdown_table(
        ["SO", "Students Assessed", "Students Attained", "Attainment", "Target Met"],
        rows,
    )

    for item in summary:
        st.progress(
            min(item.get("attainment_percent", 0) / 100, 1.0),
            text=f"{item.get('so', '')}: {item.get('attainment_percent', 0)}%",
        )

    st.caption(
        "Student pass threshold is 65% of maximum marks; SO attainment target is 65% of assessed students."
    )


    if summary_record.get("uploaded_bytes"):

        # ---------- First row ----------
        st.download_button(
            label="📥 Download Uploaded Marks Workbook",
            data=summary_record["uploaded_bytes"],
            file_name=summary_record.get(
                "uploaded_filename",
                f"{clean_filename_text(summary_assessment_name)}_uploaded_marks.xlsx",
            ),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=False,
            key=f"download_uploaded_summary_{selected_summary_id}",
        )

        # ---------- Second row ----------
        if st.button(
            "🗑️ Delete Uploaded Workbook",
            type="secondary",
            use_container_width=False,
            key=f"delete_summary_{selected_summary_id}",
            ):

            delete_uploaded_marks_workbook(course, selected_summary_id)

            if selected_summary_id in st.session_state["so_attainment_results"]:
                del st.session_state["so_attainment_results"][selected_summary_id]

            if selected_summary_id in st.session_state["so_attainment_ai_results"]:
                del st.session_state["so_attainment_ai_results"][selected_summary_id]

            st.session_state["so_attainment"] = {}
            st.session_state["so_attainment_ai"] = {}
            st.session_state["upload_reset_counter"] = (
                st.session_state.get("upload_reset_counter", 0) + 1
            )

            update_combined_attainment_state()

            remaining = list(st.session_state["so_attainment_results"].keys())

            if remaining:
                st.session_state["selected_attainment_summary_id"] = remaining[-1]
            else:
                st.session_state.pop("selected_attainment_summary_id", None)

            st.success(
                "The uploaded workbook has been deleted and the attainment results have been recalculated."
            )

            st.rerun()

else:
    st.info("No uploaded marks workbook is saved yet.")


# --------------------------------------------------
# Step 5: Saved Results and Combined Course SO Attainment
# --------------------------------------------------

st.markdown("---")
st.markdown("## 5️⃣ Saved Attainment Results")

if saved_results:
    saved_rows = []

    for aid, record in saved_results.items():
        a = record.get("assessment", {})
        saved_rows.append(
            [
                a.get("week", ""),
                a.get("name", ""),
                f"{a.get('course_weight', a.get('weight', 0)):g}",
                format_so_distribution(a),
                record.get("uploaded_filename", ""),
            ]
        )

    render_markdown_table(
        ["Week", "Assessment", "Weight (%)", "SO Mapping (Distribution)", "Uploaded File"],
        saved_rows,
    )

    update_combined_attainment_state()
    combined_attainment = st.session_state.get("combined_so_attainment", {})

    st.markdown("### Combined Course SO Attainment")

    combined_summary = combined_attainment.get("summary", [])

    if combined_summary:
        combined_rows = []

        for item in combined_summary:
            combined_rows.append(
                [
                    item.get("so", ""),
                    f"{item.get('combined_weight', 0):g}",
                    f"{item.get('attainment_percent', 0)}%",
                    item.get("target_met", "No"),
                ]
            )

        render_markdown_table(
            ["SO", "Combined Weight", "Combined Attainment", "Target Met"],
            combined_rows,
        )

        for item in combined_summary:
            st.progress(
                min(item.get("attainment_percent", 0) / 100, 1.0),
                text=f"{item.get('so', '')}: {item.get('attainment_percent', 0)}%",
            )

        st.success("Combined SO attainment is saved and ready for the EOS Report.")
    else:
        st.info("Upload marks for at least one SO-assessing assessment to build combined attainment.")

else:
    st.info("No SO attainment results have been saved yet. Upload a completed workbook to begin.")


# --------------------------------------------------
# Step 6: Generated Attainment Insights
# --------------------------------------------------

st.markdown("---")
st.markdown("## 6️⃣ Generated Attainment Insights")

if attainment:
    if st.button("✨ Generate Attainment Insights", type="primary"):
        with st.spinner("AI is interpreting attainment results..."):
            try:
                curriculum = st.session_state.get("curriculum_analysis", {})
                enhancement = st.session_state.get("course_enhancement_plan", {})

                attainment_ai = analyze_so_attainment(
                    course=course,
                    digital_twin=digital_twin,
                    curriculum_analysis=curriculum,
                    enhancement_plan=enhancement,
                    attainment=attainment,
                )

                st.session_state["so_attainment_ai_results"][assessment_id] = attainment_ai
                st.session_state["so_attainment_ai"] = attainment_ai

            except Exception as e:
                st.error("AI attainment insights could not be generated.")
                st.caption(str(e))

    attainment_ai = st.session_state["so_attainment_ai_results"].get(assessment_id, {})

    if attainment_ai:
        st.markdown("### Assessment-Based Evaluation")
        observation_box(attainment_ai.get("assessment_based_evaluation", ""))

        st.markdown("### Recommended Improvement Actions")
        for item in attainment_ai.get("improvement_actions", []):
            improvement_box(item)

        st.markdown("### Overall AI Observation")
        observation_box(attainment_ai.get("overall_observation", ""))

        st.caption(
            "AI generated from: Course Digital Twin • Curriculum Analysis • Course Enhancement • Student Outcome Attainment"
        )

        st.markdown("### Download Assessment Attainment Report")

        report_text = build_so_attainment_report(
            course,
            attainment,
            attainment_ai,
        )

        report_filename = (
            f"SO_Attainment_Report_"
            f"{assessment_label}_"
            f"{course_code}_"
            f"{academic_year}_"
            f"{semester}_"
            f"{today}.md"
        )

        st.download_button(
            label="📥 Download Assessment SO Attainment Report",
            data=report_text.encode("utf-8"),
            file_name=report_filename,
            mime="text/markdown",
        )
    else:
        st.info("Click **Generate Attainment Insights** after reviewing the calculated attainment results.")
else:
    st.info("Upload and calculate marks first, then generate attainment insights.")
