import streamlit as st

from services.platform_service import build_course_ai_summary, get_document_status

try:
    from services.course_rag_service import (
        build_course_rag_chunks,
        retrieve_relevant_chunks,
        answer_course_question,
    )
except Exception:
    build_course_rag_chunks = None
    retrieve_relevant_chunks = None
    answer_course_question = None


# --------------------------------------------------
# Validate Session
# --------------------------------------------------

if "instructor_profile" not in st.session_state:
    st.warning("Please create your instructor profile first.")
    st.page_link("pages/1_Instructor_Profile.py", label="Go to Instructor Profile", icon="👤")
    st.stop()


# --------------------------------------------------
# Load Current Course
# --------------------------------------------------

course = st.session_state.get("current_course", {}).get("profile", {})
course_structure = st.session_state.get(
    "course_structure",
    st.session_state.get("current_course", {}).get("course_structure", {}),
)

clos = course_structure.get("clos", st.session_state.get("clos", []))
sos = course_structure.get("student_outcomes", st.session_state.get("student_outcomes", []))
assessments = course_structure.get(
    "assessment_instances",
    course_structure.get("assessments", st.session_state.get("assessments", [])),
)


# --------------------------------------------------
# Page Header
# --------------------------------------------------

st.title("💬 Knowledge Assistant")

st.write(
    "Ask questions grounded in the current course profile, uploaded documents, "
    "articulation matrix, assessment structure, SO attainment results, and generated course evidence."
)

if not course:
    st.info("Load a course from Course Workspace to ask course-specific questions.")
    st.stop()

st.markdown(f"### Active Course: {course.get('course_code','')} – {course.get('course_name','')}")
st.info(build_course_ai_summary(course, clos=clos, sos=sos))


# --------------------------------------------------
# Build RAG Knowledge Base
# --------------------------------------------------

rag_ready = (
    build_course_rag_chunks is not None
    and retrieve_relevant_chunks is not None
    and answer_course_question is not None
)

if not rag_ready:
    st.warning(
        "Course RAG service is not available. Please add `course_rag_service.py` to the services folder."
    )
    st.stop()

chunks = build_course_rag_chunks(course, course_structure)

with st.expander("📚 Knowledge Sources", expanded=False):
    st.metric("Knowledge Chunks", len(chunks))

    sources = sorted(set(chunk.get("source", "Course Knowledge") for chunk in chunks))

    if sources:
        st.markdown("**Available sources:**")
        for source in sources[:30]:
            st.write(f"- {source}")

        if len(sources) > 30:
            st.caption(f"...and {len(sources) - 30} more sources.")
    else:
        st.info("No course knowledge chunks were created yet.")

    st.markdown("**Document status:**")
    for item in get_document_status(course):
        mark = "✅ Available" if item["available"] else "⚪ Missing"
        st.write(f"- {item['label']}: {mark}")


# --------------------------------------------------
# Suggested Questions
# --------------------------------------------------

st.markdown("### Suggested Questions")

suggestions = [
    "Summarize this course.",
    "Which assessments contribute to SO attainment?",
    "Which CLOs map to SO2?",
    "Compare the SO-assessing assessments.",
    "Suggest EOS improvement actions.",
    "What evidence is missing for this course?",
]

cols = st.columns(2)

for index, suggestion in enumerate(suggestions):
    with cols[index % 2]:
        if st.button(suggestion, key=f"rag_suggestion_{index}"):
            st.session_state["knowledge_question"] = suggestion


# --------------------------------------------------
# Conversation State
# --------------------------------------------------

if "knowledge_history" not in st.session_state:
    st.session_state["knowledge_history"] = []


# --------------------------------------------------
# Ask Question
# --------------------------------------------------

st.markdown("---")

question = st.text_area(
    "Ask a question",
    value=st.session_state.get("knowledge_question", ""),
    placeholder="Example: Which assessments evaluate SO2? What should I improve next semester?",
    height=100,
)

if st.button("Ask", type="primary"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Searching course knowledge and generating an answer..."):
            try:
                result = answer_course_question(
                    course=course,
                    course_structure=course_structure,
                    query=question,
                    conversation_history=st.session_state["knowledge_history"],
                )

                answer = result.get("answer", "")
                sources_used = result.get("used_sources", [])
                follow_up = result.get("follow_up_suggestion", "")

                st.session_state["knowledge_history"].append(
                    {
                        "question": question,
                        "answer": answer,
                        "sources": sources_used,
                        "follow_up": follow_up,
                    }
                )

                st.session_state["knowledge_question"] = ""

            except Exception as e:
                st.error("Could not generate an answer.")
                st.caption(str(e))


# --------------------------------------------------
# Conversation Display
# --------------------------------------------------

history = st.session_state.get("knowledge_history", [])

if history:
    st.markdown("## Conversation")

    for item in reversed(history):
        with st.container(border=True):
            st.markdown(f"**You asked:** {item.get('question', '')}")
            st.write(item.get("answer", ""))

            if item.get("sources"):
                st.caption("Sources: " + ", ".join(item.get("sources", [])))

            if item.get("follow_up"):
                st.caption("Follow-up suggestion: " + item.get("follow_up", ""))

else:
    st.info("Ask a question to begin.")


# --------------------------------------------------
# Retrieval Preview
# --------------------------------------------------

with st.expander("🔎 Retrieval Preview", expanded=False):
    preview_query = question or st.session_state.get("knowledge_question", "")

    if preview_query:
        retrieved = retrieve_relevant_chunks(preview_query, chunks, top_k=5)

        if retrieved:
            for chunk in retrieved:
                st.markdown(f"**Source:** {chunk.get('source', '')}")
                st.caption(chunk.get("text", "")[:700] + "...")
        else:
            st.info("No matching course evidence was retrieved yet.")
    else:
        st.caption("Enter a question to preview the retrieved course evidence.")


st.caption("Course RAG v1 uses lightweight local retrieval over structured course data and uploaded course evidence.")
