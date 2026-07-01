
import streamlit as st


def colored_box(text, background, border, text_color="#111827"):
    st.markdown(
        f"""
        <div style="
            background-color:{background};
            border-left:6px solid {border};
            padding:14px 16px;
            border-radius:10px;
            margin-bottom:10px;
            color:{text_color};
        ">
            {text}
        </div>
        """,
        unsafe_allow_html=True,
    )


def improvement_box(text):
    colored_box(
        text,
        background="#f0ecf9",
        #f3e8ff",
        # border="#7e22ce",
        border="#f0ecf9",
        text_color="#2e1065",
    )


def observation_box(text):
    colored_box(
        text,
        background="#ffffff",
        #eff6ff",
        # border="#2563eb",
        border="#2e1065",
        text_color="#2e1065",
    )


def knowledge_box(text):
    colored_box(
        text,
        background="#f9fafb",
        border="#6b7280",
        text_color="#111827",
    )

