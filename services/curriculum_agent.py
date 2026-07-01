from services.ai_service import ask_ai_json


def analyze_curriculum(course, clos, student_outcomes, assessments):
    prompt = f"""
You are an ABET curriculum expert.

Analyze the following curriculum information.

Course:
{course}

Course Learning Outcomes:
{clos}

Student Outcomes:
{student_outcomes}

Assessments:
{assessments}

Return ONLY valid JSON.

{{
  "bloom_analysis":[
      {{
          "clo":"CLO1",
          "level":"Analyze",
          "reason":"..."
      }}
  ],

  "so_coverage":[
      {{
          "so":"SO1",
          "coverage":"Strong",
          "observation":"..."
      }}
  ],

  "strengths":[
      "..."
  ],

  "gaps":[
      "..."
  ],

  "assessment_alignment":[
      {{
          "clo":"CLO1",
          "recommendation":"..."
      }}
  ],

  "improvement_actions":[
      "..."
  ],

  "overall_observation":"..."
}}
"""

    return ask_ai_json(prompt)