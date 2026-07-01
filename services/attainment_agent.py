from services.ai_service import ask_ai_json


def analyze_so_attainment(
    course,
    digital_twin,
    curriculum_analysis,
    enhancement_plan,
    attainment,
):
    prompt = f"""
You are an ABET accreditation expert helping an instructor interpret Student Outcome attainment results.

Use ONLY the supplied information.

Course:
{course}

Course Digital Twin:
{digital_twin}

Curriculum Analysis:
{curriculum_analysis}

Course Enhancement Plan:
{enhancement_plan}

Student Outcome Attainment:
{attainment}

Return ONLY valid JSON.

{{
    "assessment_based_evaluation":"string",

    "overall_observation":"string",

    "improvement_actions":[
        "string"
    ]
}}
"""

    return ask_ai_json(prompt)