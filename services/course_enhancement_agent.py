
from services.ai_service import ask_ai_json


def generate_course_enhancement_plan(
    course,
    digital_twin,
    curriculum_analysis,
    focus_areas,
    instructor_notes="",
):
    prompt = f"""
You are a Course Enhancement Advisor for an ABET-accredited Information Systems program.

Your task is to recommend practical course enhancements for the next offering.

Use ONLY the provided course context and knowledge.
Do not invent unsupported facts.
If evidence is limited, clearly state that the recommendation is based on available materials.

Course:
{course}

Course Digital Twin:
{digital_twin}

Curriculum Analysis:
{curriculum_analysis}

Selected Focus Areas:
{focus_areas}

Instructor Notes:
{instructor_notes}

Return ONLY valid JSON using this exact schema:

{{
  "content_enhancement": ["string"],
  "laboratory_enhancement": ["string"],
  "teaching_resources": ["string"],
  "teaching_strategies": ["string"],
  "ai_integration": ["string"],
  "assessment_enhancement": ["string"],
  "continuous_improvement_roadmap": {{
    "high_priority": ["string"],
    "medium_priority": ["string"],
    "low_priority": ["string"]
  }},
  "overall_observation": "string"
}}
"""

    return ask_ai_json(prompt)

