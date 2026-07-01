import re


# ==========================================================
# Constants
# ==========================================================

# Column indexes are zero-based because openpyxl returns row tuples.
ASSESSMENT_COLUMNS = {
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
    29: "Essay Writing",
}

ASSESSMENT_TYPES = {
    "Quiz": "Quiz",
    "Exam": "Exam",
    "Comprehensive Final Exam": "Final Exam",
    "Project (Individual)": "Project",
    "Group Project": "Project",
    "Homework Assignments": "Assignment",
    "Graded Lab Work": "Lab",
    "Lab Exam": "Lab Exam",
    "Student Work Portfolio": "Portfolio",
    "Formal Presentation": "Presentation",
    "Essay Writing": "Essay",
}

INVALID_ASSESSMENT_NAMES = {
    "assessment",
    "assessment tools",
    "student outcome",
    "total",
    "grade distribution",
}


# ==========================================================
# Public API
# ==========================================================

def extract_course_structure(workbook):
    """
    Extract structured curriculum knowledge from the articulation matrix workbook.

    GradeDistribution is the source of truth for:
    - assessment instance names
    - week
    - course weight
    - SO distribution percentages

    ArticulationMatrix enriches assessment instances with:
    - CLO coverage
    - CLO-to-SO mapping
    - whether the assessment is officially used for SO assessment

    Returns
    -------
    dict
    """

    clos = _extract_clos(workbook)
    student_outcomes = _extract_sos(workbook)
    assessment_instances = _build_assessments(workbook)

    assessed_sos = sorted(
        {
            so
            for assessment in assessment_instances
            if assessment.get("assessing_so")
            for so in assessment.get("assessed_sos", [])
        },
        key=_id_sort_key,
    )

    total_course_weight = round(
        sum(a.get("course_weight", 0) for a in assessment_instances),
        2,
    )

    return {
        "clos": clos,
        "student_outcomes": student_outcomes,
        "assessment_instances": assessment_instances,

        # Temporary compatibility with existing pages.
        "assessments": assessment_instances,

        "statistics": {
            "num_clos": len(clos),
            "num_sos": len(student_outcomes),
            "num_assessment_instances": len(assessment_instances),
            "num_assessments": len(assessment_instances),
            "num_so_assessments": sum(1 for a in assessment_instances if a.get("assessing_so")),
            "num_non_so_assessments": sum(1 for a in assessment_instances if not a.get("assessing_so")),
            "total_course_weight": total_course_weight,
            "assessed_sos": assessed_sos,
        },
    }


def build_assessment_so_map(assessment_instances):
    """
    Compatibility helper.

    Returns:
        {
            "Group Project": ["SO2", "SO3"],
            "Comprehensive Final Exam": ["SO2"]
        }
    """

    mapping = {}

    for assessment in assessment_instances or []:
        name = assessment.get("name", "")
        sos = assessment.get("assessed_sos", [])

        if name:
            mapping[name] = sos

    return mapping


# ==========================================================
# Backward-compatible public wrappers
# ==========================================================

def extract_sos_from_workbook(workbook):
    return _extract_sos(workbook)


def extract_clos_from_workbook(workbook):
    return _extract_clos(workbook)


def extract_assessment_so_map(workbook):
    return build_assessment_so_map(_build_assessments(workbook))


def extract_assessment_so_distribution(workbook):
    return _build_assessments(workbook)


# ==========================================================
# CLO and SO Extraction
# ==========================================================

def _extract_sos(workbook):
    worksheet = workbook["Notes"]

    student_outcomes = []

    for row in worksheet.iter_rows(min_row=2, values_only=True):
        value = row[1]

        if not value:
            continue

        text = str(value).strip()
        match = re.match(r"^([1-6])\.\s*(.*)", text)

        if not match:
            continue

        so_number = match.group(1)
        description = match.group(2).strip()

        if so_number in ["1", "2", "3", "4", "5"]:
            student_outcomes.append(
                {
                    "SO": f"SO{so_number}",
                    "Description": description,
                }
            )

        elif so_number == "6" and "[IS]" in description:
            description = description.replace("[IS]", "").strip()
            student_outcomes.append(
                {
                    "SO": "SO6",
                    "Description": description,
                }
            )

    return student_outcomes


def _extract_clos(workbook):
    worksheet = workbook["ArticulationMatrix"]

    clos = []

    for row in worksheet.iter_rows(min_row=5, values_only=True):
        clo_number = row[0]
        clo_text = row[1]
        domain = row[2]
        so = row[3]

        if clo_number and clo_text:
            clos.append(
                {
                    "CLO": f"CLO{int(clo_number)}",
                    "Description": str(clo_text).strip(),
                    "Domain": str(domain).strip() if domain else "",
                    "SO": f"SO{int(so)}" if so else "",
                }
            )

    return clos


# ==========================================================
# Assessment Extraction
# ==========================================================

def _build_assessments(workbook):
    assessment_instances = _extract_assessments_from_grade_distribution(workbook)
    assessment_instances = _enrich_assessments_from_articulation_matrix(
        workbook,
        assessment_instances,
    )

    return assessment_instances


def _extract_assessments_from_grade_distribution(workbook):
    """
    GradeDistribution is the master list of assessment instances.
    """

    if "GradeDistribution" not in workbook.sheetnames:
        return []

    worksheet = workbook["GradeDistribution"]

    instances = []

    for row in worksheet.iter_rows(min_row=3, values_only=True):
        week = _safe_row_value(row, 0)
        assessment_name = _safe_row_value(row, 1)
        course_weight = _safe_row_value(row, 2)

        if assessment_name is None or course_weight is None:
            continue

        if not isinstance(course_weight, (int, float)):
            continue

        name = str(assessment_name).strip()

        if not name or name.lower() in INVALID_ASSESSMENT_NAMES:
            continue

        base_name, assessment_no = _split_assessment_name(name)
        so_distribution = _extract_grade_distribution_so_distribution(row)

        instance = {
            "id": _make_assessment_id(base_name, assessment_no),
            "name": name,
            "base_name": base_name,
            "assessment_no": assessment_no,
            "week": _normalize_week(week),
            "type": _detect_assessment_type(base_name),
            "course_weight": float(course_weight),

            # Compatibility alias for older pages.
            "weight": float(course_weight),

            "clos": [],
            "mapped_sos": [],
            "assessing_so": False,
            "assessed_sos": sorted(so_distribution.keys(), key=_id_sort_key),

            # Compatibility alias. For display, prefer mapped_sos or assessed_sos
            # depending on the purpose.
            "sos": sorted(so_distribution.keys(), key=_id_sort_key),

            "so_distribution": so_distribution,
            "matrix_row": None,
            "matrix_rows": [],
        }

        instances.append(instance)

    instances.sort(
        key=lambda item: (
            _week_sort_key(item.get("week")),
            item.get("name", ""),
        )
    )

    return instances


def _enrich_assessments_from_articulation_matrix(workbook, instances):
    if "ArticulationMatrix" not in workbook.sheetnames:
        return instances

    worksheet = workbook["ArticulationMatrix"]
    assessing_so_col = _find_assessing_so_column(worksheet)

    by_key = {
        (_normalize_week_key(a.get("week")), _normalize_assessment_name(a.get("base_name"))): a
        for a in instances
    }

    for excel_row_number, row in enumerate(
        worksheet.iter_rows(min_row=5, values_only=True),
        start=5,
    ):
        clo_number = _safe_row_value(row, 0)
        mapped_so = _safe_row_value(row, 3)

        if not clo_number:
            continue

        clo_id = f"CLO{int(clo_number)}"
        mapped_so_id = f"SO{int(mapped_so)}" if mapped_so else ""

        assessing_so_value = _safe_row_value(row, assessing_so_col)
        assessing_so = _is_truthy_assessing_so(assessing_so_value)

        for col_index, base_name in ASSESSMENT_COLUMNS.items():
            week_value = _safe_row_value(row, col_index)

            if not week_value:
                continue

            key = (
                _normalize_week_key(week_value),
                _normalize_assessment_name(base_name),
            )

            instance = by_key.get(key)

            if instance is None:
                # If the workbook has an articulation entry without a matching
                # GradeDistribution row, skip it. GradeDistribution is the master
                # list of assessment instances.
                continue

            _append_unique(instance["clos"], clo_id)

            if mapped_so_id:
                _append_unique(instance["mapped_sos"], mapped_so_id)

            if assessing_so:
                instance["assessing_so"] = True

                if instance.get("so_distribution"):
                    for so_id in instance["so_distribution"].keys():
                        _append_unique(instance["assessed_sos"], so_id)
                elif mapped_so_id:
                    _append_unique(instance["assessed_sos"], mapped_so_id)
                    instance["so_distribution"] = {mapped_so_id: 100.0}

            instance["matrix_rows"].append(excel_row_number)

    for instance in instances:
        instance["clos"] = _sort_ids(instance.get("clos", []), "CLO")
        instance["mapped_sos"] = _sort_ids(instance.get("mapped_sos", []), "SO")
        instance["assessed_sos"] = _sort_ids(instance.get("assessed_sos", []), "SO")

        # Compatibility alias:
        # Keep all related SOs here so older pages still show mappings.
        instance["sos"] = instance["mapped_sos"] or instance["assessed_sos"]

        if instance["matrix_rows"]:
            instance["matrix_row"] = min(instance["matrix_rows"])

    return instances


# ==========================================================
# Display / Parsing Helpers
# ==========================================================

def _extract_grade_distribution_so_distribution(row):
    """
    GradeDistribution columns:
    A = Week
    B = Assessment Tool
    C = Weight (%)
    D:I = %SO 1 ... %SO 6
    """

    distribution = {}

    for index in range(1, 7):
        col_index = 2 + index  # SO1 starts at zero-based index 3.
        value = _safe_row_value(row, col_index)

        if isinstance(value, (int, float)) and value > 0:
            distribution[f"SO{index}"] = float(value)

    return distribution


def _split_assessment_name(name):
    """
    Examples:
    - Graded Lab Work 1 -> ("Graded Lab Work", 1)
    - Homework Assignments 2 -> ("Homework Assignments", 2)
    - Group Project -> ("Group Project", 1)
    """

    text = str(name or "").strip()
    match = re.match(r"^(.*?)(?:\s+(\d+))?$", text)

    if not match:
        return text, 1

    base_name = match.group(1).strip()
    assessment_no = int(match.group(2)) if match.group(2) else 1

    return base_name, assessment_no


def _detect_assessment_type(base_name):
    return ASSESSMENT_TYPES.get(base_name, "Assessment")


def _make_assessment_id(base_name, assessment_no):
    prefix = _assessment_id_prefix(base_name)
    return f"{prefix}-{assessment_no:02d}"


def _assessment_id_prefix(base_name):
    mapping = {
        "Quiz": "QUIZ",
        "Exam": "EXAM",
        "Comprehensive Final Exam": "FINAL",
        "Project (Individual)": "PROJ",
        "Group Project": "GPROJ",
        "Homework Assignments": "HW",
        "Graded Lab Work": "LAB",
        "Lab Exam": "LABEX",
        "Student Work Portfolio": "PORT",
        "Formal Presentation": "PRES",
        "Essay Writing": "ESSAY",
    }

    return mapping.get(base_name, _slug(base_name).upper()[:8] or "ASSESS")


def _find_assessing_so_column(worksheet):
    for row in worksheet.iter_rows(min_row=1, max_row=4):
        for cell in row:
            text = _normalize_text(cell.value)

            if "assessing" in text and "so" in text:
                return cell.column - 1

    # Known layout fallback.
    return 4


# ==========================================================
# Generic Helpers
# ==========================================================

def _append_unique(items, value):
    if value and value not in items:
        items.append(value)


def _sort_ids(values, prefix):
    def key(value):
        text = str(value).replace(prefix, "")
        try:
            return int(text)
        except Exception:
            return 9999

    return sorted(values, key=key)


def _id_sort_key(value):
    text = str(value or "")
    match = re.search(r"(\d+)", text)

    if match:
        return int(match.group(1))

    return 9999


def _safe_row_value(row, index):
    if index is None:
        return None

    if index < 0 or index >= len(row):
        return None

    return row[index]


def _normalize_week(value):
    if value is None:
        return ""

    if isinstance(value, float) and value.is_integer():
        return int(value)

    return value


def _normalize_week_key(value):
    value = _normalize_week(value)
    return str(value).strip()


def _week_sort_key(value):
    if isinstance(value, (int, float)):
        return float(value)

    try:
        return float(value)
    except Exception:
        return 9999


def _is_truthy_assessing_so(value):
    if value is None:
        return False

    if isinstance(value, (int, float)):
        return value > 0

    text = str(value).strip().lower()

    if not text:
        return False

    return text not in [
        "no",
        "n",
        "false",
        "0",
        "-",
        "none",
        "not assessed",
    ]


def _normalize_assessment_name(value):
    return str(value or "").strip().lower()


def _normalize_text(value):
    if value is None:
        return ""

    return str(value).strip().lower().replace("_", " ")


def _slug(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")
