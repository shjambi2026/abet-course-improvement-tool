import os
import csv
from datetime import datetime

DATA_FOLDER = "data"

INSTRUCTOR_FILE = os.path.join(
    DATA_FOLDER,
    "instructor_profile.csv"
)

COURSE_FILE = os.path.join(
    DATA_FOLDER,
    "course_profiles.csv"
)

INSTRUCTOR_FIELDS = [
    "title",
    "name",
    "department",
    "college",
    "university"
]

COURSE_FIELDS = [
    "course_id",
    "department",
    "academic_year",
    "semester",
    "course_code",
    "course_name",
    "course_description",
    "course_type",
    "level",
    "track",
    "prerequisites",
    "teaching_background",
    "instructor",
    "coordinator",
    "sections",
    "syllabus_file",
    "matrix_file",
    "lab_syllabus_file",
    "slides_file",
    "labs_file",
    "assessments_file",
    "rubrics_file",
    "esr_file",
    "coordination_file",
    "status",
    "last_opened"
]


def initialize_storage():
    os.makedirs(DATA_FOLDER, exist_ok=True)

    if not os.path.exists(INSTRUCTOR_FILE):
        with open(INSTRUCTOR_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=INSTRUCTOR_FIELDS)
            writer.writeheader()

    if not os.path.exists(COURSE_FILE):
        with open(COURSE_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COURSE_FIELDS)
            writer.writeheader()


def load_instructor_profile():
    initialize_storage()

    with open(INSTRUCTOR_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if rows:
        return rows[0]

    return None


def save_instructor_profile(profile):
    initialize_storage()

    with open(INSTRUCTOR_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=INSTRUCTOR_FIELDS)
        writer.writeheader()
        writer.writerow(profile)


def instructor_profile_exists():
    profile = load_instructor_profile()
    return profile is not None


def load_courses():
    initialize_storage()

    with open(COURSE_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        courses = []
        for row in reader:
            for field in COURSE_FIELDS:
                row.setdefault(field, "")
            courses.append(row)
        return courses


def normalize_course(course):
    normalized = {}
    for field in COURSE_FIELDS:
        normalized[field] = course.get(field, "")
    return normalized


def save_courses(courses):
    initialize_storage()

    normalized_courses = [normalize_course(course) for course in courses]

    with open(COURSE_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COURSE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(normalized_courses)


def generate_course_id(course_code, academic_year, semester):
    clean_code = course_code.replace("-", "").replace(" ", "")
    clean_year = academic_year.replace("-", "_").replace(" ", "")
    clean_semester = semester.replace(" ", "")

    return clean_code + "_" + clean_year + "_" + clean_semester


def save_course(course):
    courses = load_courses()

    updated = False

    for index, existing_course in enumerate(courses):
        if existing_course["course_id"] == course["course_id"]:
            courses[index] = course
            updated = True
            break

    if not updated:
        courses.append(course)

    save_courses(courses)


def get_course(course_id):
    courses = load_courses()

    for course in courses:
        if course["course_id"] == course_id:
            return course

    return None


def update_last_opened(course_id):
    courses = load_courses()

    for course in courses:
        if course["course_id"] == course_id:
            course["last_opened"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            break

    save_courses(courses)


def update_course(old_course_id, updated_course):
    courses = load_courses()

    updated_courses = []

    for course in courses:
        if course["course_id"] == old_course_id:
            updated_courses.append(updated_course)
        elif course["course_id"] != updated_course["course_id"]:
            updated_courses.append(course)

    save_courses(updated_courses)