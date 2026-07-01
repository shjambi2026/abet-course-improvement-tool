def get_course_catalog_info(course_code):
    code = (course_code or "").strip().upper()


    return catalog.get(code, {
        "course_description": "",
        "course_type": "",
        "track": "",
        "level": "",
        "official_prerequisites": "",
        "student_background": "",
        "teaching_background": ""
    })
