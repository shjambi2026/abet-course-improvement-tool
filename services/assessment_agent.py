
from services.ai_service import ask_ai


def generate_assessment_item(
    course,
    digital_twin,
    clo,
    assessment_type,
    difficulty,
    number_of_items,
    additional_instructions="",
):
    prompt = f"""
You are an experienced university instructor and assessment designer for an ABET-accredited Information Systems program.

Generate high-quality assessment material using ONLY the provided course context.

Course:
{course}

Course Digital Twin:
{digital_twin}

Selected CLO:
{clo}

Assessment Type:
{assessment_type}

Difficulty:
{difficulty}

Number of Items:
{number_of_items}

Additional Instructor Instructions:
{additional_instructions}

Requirements:
- Align clearly with the selected CLO.
- Respect the Bloom level implied by the CLO.
- Include answer key or expected answer where appropriate.
- For rubrics, include criteria, performance levels, and marks.
- For projects or case studies, include scenario, tasks, deliverables, and grading guidance.
- Use clear academic language suitable for university students.

Return the assessment content in clean Markdown.
"""

    return ask_ai(prompt)

