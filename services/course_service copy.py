import re


def extract_sos_from_workbook(workbook):
    worksheet = workbook["Notes"]

    student_outcomes = []

    for row in worksheet.iter_rows(min_row=2, values_only=True):
        value = row[1]

        if value:
            text = str(value).strip()

            match = re.match(r"^([1-6])\.\s*(.*)", text)

            if match:
                so_number = match.group(1)
                description = match.group(2).strip()

                if so_number in ["1", "2", "3", "4", "5"]:
                    student_outcomes.append({
                        "SO": f"SO{so_number}",
                        "Description": description
                    })

                elif so_number == "6" and "[IS]" in description:
                    description = description.replace("[IS]", "").strip()
                    student_outcomes.append({
                        "SO": "SO6",
                        "Description": description
                    })

    return student_outcomes


def extract_clos_from_workbook(workbook):
    worksheet = workbook["ArticulationMatrix"]

    clos = []

    for row in worksheet.iter_rows(min_row=5, values_only=True):
        clo_number = row[0]
        clo_text = row[1]
        domain = row[2]
        so = row[3]

        if clo_number and clo_text:
            clos.append({
                "CLO": f"CLO{int(clo_number)}",
                "Description": str(clo_text).strip(),
                "Domain": str(domain).strip(),
                "SO": f"SO{int(so)}"
            })

    return clos


def _extract_assessment_so_map(workbook):
    worksheet = workbook["ArticulationMatrix"]

    assessment_columns = {
        19: "Quiz",
        20: "Exam",
        21: "Comprehensive Final Exam",
        22: "Project (Individual)",
        23: "Group Project",
        24: "Homework Assignments",
        25: "Graded Lab Work",
        26: "Lab Exam",
        27: "Student Work Portfolio",
        28: "Formal Presentation",
        29: "Essay Writing"
    }

    assessment_so_map = {}

    for assessment_name in assessment_columns.values():
        assessment_so_map[assessment_name] = []

    for row in worksheet.iter_rows(min_row=5, values_only=True):
        so = row[3]

        if so:
            so_id = "SO" + str(int(so))

            for col_index, assessment_name in assessment_columns.items():
                cell_value = row[col_index]

                if cell_value:
                    assessment_so_map[assessment_name].append(so_id)

    return assessment_so_map


def _extract_assessments_from_grade_distribution(workbook):
    worksheet = workbook["GradeDistribution"]

    assessments = []

    for row in worksheet.iter_rows(values_only=True):
        row_values = [value for value in row if value is not None]

        if len(row_values) >= 2:
            assessment_name = str(row_values[0]).strip()

            for value in row_values[1:]:
                if isinstance(value, (int, float)):
                    assessments.append({
                        "Assessment": assessment_name,
                        "Grade": float(value)
                    })
                    break

    # Remove invalid rows
    cleaned = []

    for item in assessments:
        name = item["Assessment"]

        if name.lower() not in [
            "assessment",
            "assessment tools",
            "student outcome",
            "total",
            "grade distribution"
        ]:
            cleaned.append(item)

    return cleaned


def _extract_assessment_so_distribution(workbook):
    worksheet = workbook["GradeDistribution"]

    assessments = []

    for row in worksheet.iter_rows(min_row=3, values_only=True):
        week = row[0]
        assessment_name = row[1]
        grade = row[2]

        if assessment_name is None or grade is None:
            continue

        so_distribution = {}

        so_columns = {
            3: "SO1",
            4: "SO2",
            5: "SO3",
            6: "SO4",
            7: "SO5",
            8: "SO6"
        }

        for col_index, so_id in so_columns.items():
            value = row[col_index]

            if isinstance(value, (int, float)) and value > 0:
                so_distribution[so_id] = float(value)

        assessments.append({
            "Week": week,
            "Assessment": str(assessment_name).strip(),
            "Grade": float(grade),
            "SO_Distribution": so_distribution
        })

    return assessments


def build_assessments(workbook):
    """
    Returns a list of assessment dictionaries used
    throughout the platform.

    [
        {
            "name": "Final Exam",
            "weight": 40,
            "sos": ["SO2"],
            "so_distribution": {"SO2":40}
        }
    ]
    """

    weights = extract_assessments_from_grade_distribution(workbook)
    so_map = extract_assessment_so_map(workbook)
    distribution = extract_assessment_so_distribution(workbook)

    assessments = []

    for item in weights:

        name = item["Assessment"]

        assessment = {
            "name": name,
            "weight": item["Grade"],
            "sos": sorted(
                list(
                    set(
                        so_map.get(name, [])
                    )
                )
            ),
            "so_distribution": {},
        }

        for d in distribution:

            if d["Assessment"] == name:
                assessment["so_distribution"] = d["SO_Distribution"]
                break

        assessments.append(assessment)

    return assessments
    