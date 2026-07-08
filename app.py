from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, Response
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = "dev-only-change-me"  # needed for flash messages; replace before deploying

# --- Placeholder data (will move to the database once models are wired up) ---

SCHOOL_NAME = "School name"

# Fill these in with your real school details — they show in the report card
# footer and header. Leave any field blank to omit it from the printed card.
SCHOOL_INFO = {
    "type": "Primary School",     # subtitle shown under the school name, e.g. "International Primary School"
    "address": "",                # e.g. "Nakasamba Close Plot 10, Entebbe, Uganda"
    "phone": "",
    "email": "",
    "website": "",
    "reg_no": "",                 # e.g. a Ministry of Education registration number
    "logo_path": "images /Screenshot 2026-07-08 at 07.47.18.png",              # e.g. "images/logo.png" once you add a real logo file under static/images/
}

NAV_ITEMS = [
    {"label": "Home", "endpoint": "home"},
    {"label": "Profiles", "endpoint": "profiles"},
    {"label": "Academics", "endpoint": "academics"},
    {"label": "Grades", "endpoint": "grades"},
    {"label": "Attendance", "endpoint": "attendance"},
    {"label": "Reports", "endpoint": "reports"},
]

TERMS = [
    {"id": 1, "name": "Term 1, 2026", "start": date(2026, 2, 3), "end": date(2026, 5, 8)},
    {"id": 2, "name": "Term 2, 2026", "start": date(2026, 5, 25), "end": date(2026, 8, 14)},
    {"id": 3, "name": "Term 3, 2026", "start": date(2026, 9, 7), "end": date(2026, 12, 4)},
]

QUICK_ACTIONS = [
    {"icon": "ti-report", "title": "Enter grades", "subtitle": "Primary 5 — Maths", "endpoint": "grades"},
    {"icon": "ti-clipboard-check", "title": "Take attendance", "subtitle": "3 classes pending", "endpoint": "attendance"},
    {"icon": "ti-file-text", "title": "Generate report", "subtitle": "End of term", "endpoint": "reports"},
]

EVENT_RECORDS = [
    {"id": 1, "name": "Mid-term exams begin", "start_date": "14-07-2026", "end_date": "18-07-2026", "audience": "Whole school", "teacher": "Taaka Beatrice"},
    {"id": 2, "name": "Parents meeting", "start_date": "18-07-2026", "end_date": "18-07-2026", "audience": "Whole school", "teacher": "Support R"},
]

# --- Classes ---
#
# Placeholder list of classes offered by the school. This is the hook point for
# Academics > Classes: once that module exists, replace this with a real lookup
# (e.g. get_classes_for_term(current_term)) and everything downstream — the
# student filter dropdown, enrollment, etc. — keeps working unchanged.
CLASSES = [
    "Primary 1",
    "Primary 2",
    "Primary 3",
    "Primary 4",
    "Primary 5",
    "Primary 6",
    "Primary 7",
]

# --- Status rules ---
#
# Staff status is driven by account activity, not enrollment:
#   - "Active"                    -> the account has been created AND the person has logged in at least once
#   - "Account not activated yet" -> the account exists but they haven't logged in yet
#
# Student status is driven by enrollment, and will be set automatically once the
# Academics > Enrollment flow exists:
#   - "Active"   -> currently enrolled in a class for the current term
#   - "Inactive" -> not currently enrolled (never enrolled, withdrawn, or not yet promoted/re-enrolled)
#
# Both lists below store the raw facts (account_created / has_logged_in, enrolled_class)
# rather than a hardcoded status string, and status is computed with the functions below.
# That's the hook point: once real enrollment records exist, swap `enrolled_class` for a
# real lookup against the current term's class assignments and this logic doesn't change.

STAFF = [
    {"id": 1, "name": "Jackson Dance", "email": "jackson.dance@school.org", "phone": "", "role": "teacher", "account_created": True, "has_logged_in": False, "created_on": "21-04-2026"},
    {"id": 2, "name": "Elvin Ndoli", "email": "elvin.ndoli@school.org", "phone": "", "role": "teacher", "account_created": True, "has_logged_in": True, "created_on": "09-03-2026"},
    {"id": 3, "name": "Uwimana D'amour", "email": "uwimana.damour@school.org", "phone": "", "role": "teacher", "account_created": True, "has_logged_in": True, "created_on": "16-02-2026"},
    {"id": 4, "name": "Ishimwe Joselyne", "email": "ishimwe.joselyne@school.org", "phone": "", "role": "teacher", "account_created": True, "has_logged_in": True, "created_on": "10-07-2025"},
    {"id": 5, "name": "Raymond Gakwaya", "email": "raymond.gakwaya@school.org", "phone": "", "role": "teacher", "account_created": True, "has_logged_in": True, "created_on": "04-02-2026"},
    {"id": 6, "name": "Eddy Sheja", "email": "eddy.sheja@school.org", "phone": "", "role": "teacher", "account_created": True, "has_logged_in": True, "created_on": "08-12-2025"},
    {"id": 7, "name": "Dushime Alipe", "email": "dushime.alipe@school.org", "phone": "", "role": "teacher", "account_created": True, "has_logged_in": True, "created_on": "11-04-2025"},
    {"id": 8, "name": "Support R", "email": "support.r@school.org", "phone": "", "role": "admin", "account_created": True, "has_logged_in": True, "created_on": "04-09-2025"},
    {"id": 9, "name": "Rene Mucyo", "email": "rene.mucyo@school.org", "phone": "", "role": "teacher", "account_created": True, "has_logged_in": False, "created_on": "14-10-2025"},
]

STUDENTS = [
    {"id": 1, "registration_number": "STU-2026-001", "name": "Nabirye Grace", "lin": "", "date_of_birth": "2015-03-12", "enrolled_class": "Primary 5", "created_on": "12-01-2026"},
    {"id": 2, "registration_number": "STU-2026-002", "name": "Okello Brian", "lin": "UG-LIN-88213", "date_of_birth": "2016-07-01", "enrolled_class": "Primary 3", "created_on": "12-01-2026"},
    {"id": 3, "registration_number": "STU-2026-003", "name": "Achen Mercy", "lin": "", "date_of_birth": "2014-11-23", "enrolled_class": "", "created_on": "03-02-2026"},
    {"id": 4, "registration_number": "STU-2026-004", "name": "Kato Emmanuel", "lin": "UG-LIN-90042", "date_of_birth": "2015-01-09", "enrolled_class": "Primary 4", "created_on": "20-01-2026"},
]

ACADEMIC_CLASSES = [
    {"id": 1, "name": "Primary 1", "teacher": "Jackson Dance"},
    {"id": 2, "name": "Primary 2", "teacher": "Elvin Ndoli"},
    {"id": 3, "name": "Primary 3", "teacher": "Uwimana D'amour"},
    {"id": 4, "name": "Primary 4", "teacher": "Ishimwe Joselyne"},
    {"id": 5, "name": "Primary 5", "teacher": "Raymond Gakwaya"},
    {"id": 6, "name": "Primary 6", "teacher": "Eddy Sheja"},
    {"id": 7, "name": "Primary 7", "teacher": "Dushime Alipe"},
]

SUBJECTS = [
    {"id": 1, "name": "Mathematics", "class_name": "Primary 5", "maximum_mark": 100, "is_compulsory": True, "teacher": "Raymond Gakwaya"},
    {"id": 2, "name": "English", "class_name": "Primary 4", "maximum_mark": 100, "is_compulsory": True, "teacher": "Ishimwe Joselyne"},
    {"id": 3, "name": "Science", "class_name": "Primary 3", "maximum_mark": 100, "is_compulsory": True, "teacher": "Uwimana D'amour"},
    {"id": 4, "name": "French", "class_name": "Primary 3", "maximum_mark": 100, "is_compulsory": False, "teacher": "Uwimana D'amour"},
]

ENROLLMENTS = [
    {"id": 1, "date": "12-01-2026", "class_name": "Primary 5", "description": "Primary 5 enrollment", "student_ids": [1], "status": "Enrolled"},
    {"id": 2, "date": "12-01-2026", "class_name": "Primary 3", "description": "Primary 3 enrollment", "student_ids": [2], "status": "Enrolled"},
    {"id": 3, "date": "20-01-2026", "class_name": "Primary 4", "description": "Primary 4 enrollment", "student_ids": [4], "status": "Enrolled"},
]

PROMOTION_DECISIONS = {}

# "Other subject" used to be a selectable assessment type here. It's no longer
# needed as a choice: whether an assessment is marks-graded or letter-graded
# is now derived automatically from the subject's own "is_compulsory" flag
# (see is_other_subject_assessment). Staff just pick the real assessment
# period below for every subject, compulsory or not.
ASSESSMENT_TYPES = [
    "B.O.T.",
    "Mid",
    "E.O.T Internal",
    "E.O.T External",
]

GRADING_ASSESSMENTS = [
    {"id": 1, "date": "01-05-2026", "class_name": "Primary 5", "subject": "Mathematics", "subject_id": 1, "assessment_type": "Mid", "maximum": 100},
    {"id": 2, "date": "01-05-2026", "class_name": "Primary 4", "subject": "English", "subject_id": 2, "assessment_type": "B.O.T.", "maximum": 100},
    {"id": 3, "date": "01-05-2026", "class_name": "Primary 3", "subject": "French", "subject_id": 4, "assessment_type": "Mid", "maximum": 5},
]

ASSESSMENT_RESULTS = {
    1: {1: {"mark": 92, "aggregate": "1"}},
    2: {},
    3: {2: {"mark": "", "grade": "B", "remark": "Good grasp of vocabulary, needs more speaking practice."}},
}

REPORT_COMMENTS = [
    {"id": 1, "student_id": 1, "class_name": "Primary 5", "comment_type": "Class teacher", "comment": "Strong performance and consistent effort.", "teacher": "Raymond Gakwaya"},
    {"id": 2, "student_id": 2, "class_name": "Primary 3", "comment_type": "Head teacher", "comment": "Keep working steadily next term.", "teacher": "Taaka Beatrice"},
]

ATTENDANCE_TYPES = ["Class", "Event", "Subject"]
ATTENDANCE_STATUSES = ["Present", "Absent", "Late", "Sick"]

ATTENDANCE_RECORDS = [
    {"id": 1, "date": "07-07-2026", "attendance_type": "Class", "session": "Day", "entity": "Primary 5", "class_name": "Primary 5"},
    {"id": 2, "date": "07-07-2026", "attendance_type": "Subject", "session": "Period 1", "entity": "Mathematics", "class_name": "Primary 5"},
    {"id": 3, "date": "07-07-2026", "attendance_type": "Event", "session": "Day", "entity": "Parents meeting", "class_name": ""},
]

ATTENDANCE_MARKS = {
    1: {1: {"status": "Present", "time": "08:00"}},
    2: {},
    3: {},
}

REPORT_TYPES = [
    "Attendance report",
    "Beginning of term",
    "Mid-term",
    "End of term",
    "Assessment report",
]

REPORT_BATCHES = [
    {"id": 1, "class_name": "Primary 5", "report_type": "End of term", "created_at": "07-07-2026 12:30", "status": "Generated", "generated_student_ids": [1]},
    {"id": 2, "class_name": "Primary 3", "report_type": "Mid-term", "created_at": "07-07-2026 12:35", "status": "Generated", "generated_student_ids": [2]},
]

PUBLISHED_REPORTS = []


def staff_status(member):
    if member["account_created"] and member["has_logged_in"]:
        return "Active"
    return "Account not activated yet"


def student_status(student):
    return "Active" if student.get("enrolled_class") else "Inactive"


def next_id(records):
    return (max((r["id"] for r in records), default=0)) + 1


def parse_created_on(value):
    """Parse the 'DD-MM-YYYY' created_on string into a datetime for sorting.

    Falls back to datetime.min for missing/malformed values so bad data
    doesn't crash the sort — it just sinks to the bottom of "newest first".
    """
    try:
        return datetime.strptime(value, "%d-%m-%Y")
    except (TypeError, ValueError):
        return datetime.min


def parse_date(value):
    try:
        return datetime.strptime(value, "%d-%m-%Y").date()
    except (TypeError, ValueError):
        return None


def format_event_date_range(event):
    start = parse_date(event.get("start_date"))
    end = parse_date(event.get("end_date"))
    if not start:
        return event.get("start_date", "")
    if not end or start == end:
        return start.strftime("%b %-d")
    if start.month == end.month:
        return f"{start.strftime('%b %-d')} - {end.strftime('%-d')}"
    return f"{start.strftime('%b %-d')} - {end.strftime('%b %-d')}"


def event_activity(event, today=None):
    today = today or date.today()
    start = parse_date(event.get("start_date"))
    end = parse_date(event.get("end_date")) or start
    if not start:
        return "Pending"
    if start <= today <= end:
        return "Active"
    if today > end:
        return "Passed"
    return "Pending"


def event_records(today=None):
    return [
        {
            **event,
            "date_range": f"{event['start_date']} to {event['end_date']}",
            "activity": event_activity(event, today=today),
            "date_label": format_event_date_range(event),
            "calendar_start": parse_date(event["start_date"]).isoformat() if parse_date(event["start_date"]) else "",
            "calendar_end": parse_date(event["end_date"]).isoformat() if parse_date(event["end_date"]) else "",
        }
        for event in EVENT_RECORDS
    ]


def calendar_event_payload():
    return [
        {
            "title": event["name"],
            "start": record["calendar_start"],
            "end": record["calendar_end"],
            "activity": record["activity"],
        }
        for event, record in zip(EVENT_RECORDS, event_records())
    ]


def get_class_filter_options():
    """Classes offered in the student filter dropdown.

    Pulls from CLASSES (the whole school's class list) rather than just the
    classes currently in use, so a class shows up in the filter even before
    anyone is enrolled in it. "Not enrolled" is appended so students without
    a class can still be filtered on. Swap CLASSES for a real Academics
    lookup later and this keeps working unchanged.
    """
    return CLASSES + ["Not enrolled"]


def get_class_students(class_name):
    return [s for s in STUDENTS if s.get("enrolled_class") == class_name]


def class_level(class_name):
    normalized = class_name.lower().replace(".", "").replace("primary", "p").strip()
    for number in range(1, 8):
        if normalized.startswith(f"p {number}") or normalized.startswith(f"p{number}"):
            if number <= 3:
                return "Lower primary"
            if number <= 5:
                return "Upper primary"
            return "Candidate class"
    return "Primary"


def find_subject_for_assessment(assessment):
    """Look up the SUBJECTS entry an assessment belongs to.

    Prefers subject_id (set on every assessment created going forward); falls
    back to matching on name + class for any older records that predate the
    subject_id link.
    """
    subject_id = assessment.get("subject_id")
    if subject_id is not None:
        subject = next((s for s in SUBJECTS if s["id"] == subject_id), None)
        if subject:
            return subject
    return next(
        (s for s in SUBJECTS if s["name"] == assessment.get("subject") and s["class_name"] == assessment.get("class_name")),
        None,
    )


def is_other_subject_assessment(assessment):
    """An assessment is letter-graded ("Other subject" style) when its subject
    is marked non-compulsory in Academics > Subjects. Compulsory subjects are
    marks-graded ("Major subject" style). If the subject can't be found
    (e.g. it was since deleted) we default to marks mode."""
    subject = find_subject_for_assessment(assessment)
    if subject is None:
        return False
    return not subject.get("is_compulsory", True)


def aggregate_from_mark(mark):
    try:
        score = int(mark)
    except (TypeError, ValueError):
        return ""
    if score >= 90:
        return "1"
    if score >= 80:
        return "2"
    if score >= 70:
        return "3"
    if score >= 60:
        return "4"
    if score >= 55:
        return "5"
    if score >= 50:
        return "6"
    if score >= 45:
        return "7"
    if score >= 40:
        return "8"
    return "9"


def get_student_names(student_ids):
    names = []
    for student_id in student_ids:
        student = next((s for s in STUDENTS if s["id"] == student_id), None)
        if student:
            names.append(student["name"])
    return names


def teacher_names():
    return [m["name"] for m in STAFF if m.get("role") == "teacher"]


def students_payload(students):
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "registration_number": s["registration_number"],
            "class_name": s.get("enrolled_class") or "Not enrolled",
        }
        for s in students
    ]


def academic_class_records():
    records = []
    for class_record in ACADEMIC_CLASSES:
        class_students = get_class_students(class_record["name"])
        class_subjects = [s for s in SUBJECTS if s["class_name"] == class_record["name"]]
        records.append(
            {
                **class_record,
                "enrolled_students": len(class_students),
                "subjects": len(class_subjects),
                "students": students_payload(class_students),
                "subject_names": [s["name"] for s in class_subjects],
            }
        )
    return records


def subject_records():
    records = []
    for subject in SUBJECTS:
        class_students = get_class_students(subject["class_name"])
        records.append(
            {
                **subject,
                "students_count": len(class_students),
                "students": students_payload(class_students),
                "is_compulsory_label": "Yes" if subject["is_compulsory"] else "No",
                "subject_type_label": "Major subject" if subject["is_compulsory"] else "Other subject",
            }
        )
    return records


def enrollment_records():
    records = []
    for enrollment in ENROLLMENTS:
        students = get_student_names(enrollment["student_ids"])
        records.append(
            {
                **enrollment,
                "students_count": len(students),
                "students": students,
            }
        )
    return records


def promotion_records():
    records = []
    for class_record in ACADEMIC_CLASSES:
        class_students = get_class_students(class_record["name"])
        decision_counts = {"Promoted": 0, "Second sitting": 0, "Repeating": 0, "Discontinued": 0}
        for student in class_students:
            decision = PROMOTION_DECISIONS.get(student["id"])
            if decision in decision_counts:
                decision_counts[decision] += 1
        records.append(
            {
                "id": class_record["id"],
                "class_name": class_record["name"],
                "all_students": len(class_students),
                "students": students_payload(class_students),
                "promoted": decision_counts["Promoted"],
                "second_sitting": decision_counts["Second sitting"],
                "repeating": decision_counts["Repeating"],
                "discontinued": decision_counts["Discontinued"],
            }
        )
    return records


def academic_redirect(tab):
    return url_for("academics", tab=tab)


def json_or_redirect(tab, message):
    flash(message, "success")
    redirect_url = academic_redirect(tab)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "redirect": redirect_url})
    return redirect(redirect_url)


def grades_redirect(tab):
    return url_for("grades", tab=tab)


def grades_json_or_redirect(tab, message):
    flash(message, "success")
    redirect_url = grades_redirect(tab)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "redirect": redirect_url})
    return redirect(redirect_url)


def assessment_records():
    records = []
    for assessment in GRADING_ASSESSMENTS:
        class_students = get_class_students(assessment["class_name"])
        result_map = ASSESSMENT_RESULTS.get(assessment["id"], {})
        result_mode = "letter" if is_other_subject_assessment(assessment) else "marks"
        students = []
        for student in class_students:
            result = result_map.get(student["id"], {})
            students.append(
                {
                    "id": student["id"],
                    "name": student["name"],
                    "registration_number": student["registration_number"],
                    "mark": result.get("mark", ""),
                    "grade": result.get("grade", ""),
                    "aggregate": result.get("aggregate", aggregate_from_mark(result.get("mark", ""))),
                    "remark": result.get("remark", ""),
                }
            )
        records.append(
            {
                **assessment,
                "level": class_level(assessment["class_name"]),
                "result_mode": result_mode,
                "recorded_count": len(result_map),
                "total_students": len(class_students),
                "recorded_label": f"{len(result_map)}/{len(class_students)}",
                "students": students,
            }
        )
    return records


def comment_records():
    records = []
    for comment in REPORT_COMMENTS:
        student = next((s for s in STUDENTS if s["id"] == comment["student_id"]), None)
        records.append(
            {
                **comment,
                "student_name": student["name"] if student else "Unknown student",
                "level": class_level(comment["class_name"]),
            }
        )
    return records


def attendance_students(record):
    if record.get("class_name"):
        return get_class_students(record["class_name"])
    return [s for s in STUDENTS if s.get("enrolled_class")]


def attendance_records():
    records = []
    for record in ATTENDANCE_RECORDS:
        students = attendance_students(record)
        marks = ATTENDANCE_MARKS.get(record["id"], {})
        records.append(
            {
                **record,
                "recorded_count": len(marks),
                "total_students": len(students),
                "attendance_label": f"{len(marks)}/{len(students)}",
                "students": [
                    {
                        "id": student["id"],
                        "name": student["name"],
                        "registration_number": student["registration_number"],
                        "status": marks.get(student["id"], {}).get("status", ""),
                        "time": marks.get(student["id"], {}).get("time", ""),
                    }
                    for student in students
                ],
            }
        )
    return records


def todays_attendance_percentage(today=None):
    today_str = (today or date.today()).strftime("%d-%m-%Y")
    total_marked = 0
    total_present = 0
    for record in ATTENDANCE_RECORDS:
        if record.get("date") != today_str:
            continue
        marks = ATTENDANCE_MARKS.get(record["id"], {})
        for mark in marks.values():
            total_marked += 1
            if mark.get("status") == "Present":
                total_present += 1
    if total_marked == 0:
        return 0
    return round((total_present / total_marked) * 100)


def attendance_redirect():
    return url_for("attendance")


def attendance_json_or_redirect(message):
    flash(message, "success")
    redirect_url = attendance_redirect()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "redirect": redirect_url})
    return redirect(redirect_url)


def reports_redirect(tab="cards"):
    return url_for("reports", tab=tab)


def reports_json_or_redirect(tab, message):
    flash(message, "success")
    redirect_url = reports_redirect(tab)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "redirect": redirect_url})
    return redirect(redirect_url)


def report_classes_for_scope(scope):
    if scope == "All classes":
        return [c["name"] for c in ACADEMIC_CLASSES]
    if scope == "Lower primary":
        return [c["name"] for c in ACADEMIC_CLASSES if class_level(c["name"]) == "Lower primary"]
    if scope == "Upper primary":
        return [c["name"] for c in ACADEMIC_CLASSES if class_level(c["name"]) == "Upper primary"]
    return [scope] if any(c["name"] == scope for c in ACADEMIC_CLASSES) else []


def report_comment_map(student_id):
    comments = {"Class teacher": "", "Head teacher": ""}
    for comment in REPORT_COMMENTS:
        if comment["student_id"] == student_id and comment["comment_type"] in comments:
            comments[comment["comment_type"]] = comment["comment"]
    return comments


def report_assessment_rows(student):
    rows = []
    for assessment in GRADING_ASSESSMENTS:
        if assessment["class_name"] != student.get("enrolled_class"):
            continue
        result = ASSESSMENT_RESULTS.get(assessment["id"], {}).get(student["id"], {})
        rows.append(
            {
                "subject": assessment["subject"],
                "type": assessment["assessment_type"],
                "maximum": assessment["maximum"],
                "mark": result.get("mark", ""),
                "aggregate": result.get("aggregate", ""),
                "grade": result.get("grade", ""),
                "remark": result.get("remark", ""),
                "mode": "letter" if is_other_subject_assessment(assessment) else "marks",
            }
        )
    return rows


def student_enrollment_date(student_id, fallback=""):
    for enrollment in ENROLLMENTS:
        if student_id in enrollment.get("student_ids", []):
            return enrollment["date"]
    return fallback


def main_subjects_for_class(class_name):
    """Marks-graded subjects (B.O.T./Mid/E.O.T.) for a class — the 'compulsory' ones.
    Non-compulsory subjects (ICT, French, Music, etc.) are graded via letter grade
    in the 'Other subjects' section instead. Toggle a subject's compulsory flag in
    Academics > Subjects to move it between the two."""
    return [s["name"] for s in SUBJECTS if s["class_name"] == class_name and s.get("is_compulsory")]


def report_students_payload(report):
    students = [s for s in STUDENTS if s["id"] in report.get("generated_student_ids", [])]
    result = []
    for student in students:
        class_name = student.get("enrolled_class") or report["class_name"]
        class_record = next((c for c in ACADEMIC_CLASSES if c["name"] == class_name), None)
        result.append(
            {
                "id": student["id"],
                "name": student["name"],
                "registration_number": student["registration_number"],
                "date_of_birth": student.get("date_of_birth", ""),
                "lin": student.get("lin", ""),
                "class_name": class_name,
                "class_teacher": class_record["teacher"] if class_record else "",
                "enrollment_date": student_enrollment_date(student["id"], student.get("created_on", "")),
                "level": class_level(class_name),
                "main_subjects": main_subjects_for_class(class_name),
                "comments": report_comment_map(student["id"]),
                "assessments": report_assessment_rows(student),
            }
        )
    return result


def report_records(records):
    output = []
    for report in records:
        students = report_students_payload(report)
        output.append(
            {
                **report,
                "generated_count": len(students),
                "students": students,
            }
        )
    return output


def completed_assessment_subjects(class_name):
    complete = []
    for record in assessment_records():
        if record["class_name"] == class_name and record["total_students"] and record["recorded_count"] == record["total_students"]:
            complete.append(record["subject"])
    return complete


def events_redirect():
    return url_for("events")


def events_json_or_redirect(message):
    flash(message, "success")
    redirect_url = events_redirect()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "redirect": redirect_url})
    return redirect(redirect_url)


def get_current_term(today=None):
    """Return the term whose date range contains today's date, or None."""
    today = today or date.today()
    for term in TERMS:
        if term["start"] <= today <= term["end"]:
            return term
    return None


def base_context(active_endpoint):
    return {
        "school_name": SCHOOL_NAME,
        "nav_items": NAV_ITEMS,
        "active_endpoint": active_endpoint,
        "current_term": get_current_term(),
        "calendar_events": calendar_event_payload(),
        "user": {"name": "Jackson T.", "initials": "JT", "role": "admin"},
    }


@app.route("/")
def home():
    stats = [
        {"label": "Students", "value": str(len(STUDENTS))},
        {"label": "Teachers", "value": str(len(STAFF))},
        {"label": "Attendance today", "value": f"{todays_attendance_percentage()}%"},
        {"label": "Classes today", "value": str(len(ACADEMIC_CLASSES))},
    ]
    context = base_context("home")
    context.update(
        {
            "stats": stats,
            "quick_actions": QUICK_ACTIONS,
            "events": [
                {"icon": "ti-calendar", "title": event["name"], "date_label": event["date_label"]}
                for event in event_records()
            ],
        }
    )
    return render_template("home.html", **context)


# --- Profiles: staff + students ---

@app.route("/profiles")
def profiles():
    tab = request.args.get("tab", "staff")
    search_query = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "")
    sort = request.args.get("sort", "created_desc")
    if sort not in ("created_desc", "created_asc"):
        sort = "created_desc"
    context = base_context("profiles")

    if tab == "students":
        class_filter = request.args.get("class", "")
        records = [
            {**s, "status": student_status(s), "class_name": s["enrolled_class"] or "Not enrolled"}
            for s in STUDENTS
        ]

        # Classes offered in the filter dropdown come from the school's whole
        # class list (see get_class_filter_options), not just who's currently
        # registered — this is the pre-wired hook point for Academics > Classes.
        available_classes = get_class_filter_options()

        if class_filter:
            records = [r for r in records if r["class_name"] == class_filter]
        if status_filter:
            records = [r for r in records if r["status"] == status_filter]
        if search_query:
            records = [r for r in records if search_query.lower() in r["name"].lower()]

        records.sort(key=lambda r: parse_created_on(r["created_on"]), reverse=(sort == "created_desc"))

        context.update(
            {
                "active_tab": "students",
                "records": records,
                "singular_label": "Student",
                "plural_label": "Students",
                "available_classes": available_classes,
                "class_filter": class_filter,
                "status_options": ["Active", "Inactive"],
                "status_filter": status_filter,
                "search_query": search_query,
                "sort": sort,
            }
        )
    else:
        tab = "staff"
        records = [{**m, "status": staff_status(m)} for m in STAFF]

        if status_filter:
            records = [r for r in records if r["status"] == status_filter]
        if search_query:
            records = [r for r in records if search_query.lower() in r["name"].lower()]

        records.sort(key=lambda r: parse_created_on(r["created_on"]), reverse=(sort == "created_desc"))

        context.update(
            {
                "active_tab": "staff",
                "records": records,
                "singular_label": "Staff",
                "plural_label": "Staff",
                "status_options": ["Active", "Account not activated yet"],
                "status_filter": status_filter,
                "search_query": search_query,
                "sort": sort,
            }
        )

    return render_template("profiles.html", **context)


@app.route("/profiles/staff/new", methods=["GET", "POST"])
def new_staff():
    context = base_context("profiles")
    errors = {}
    form = {"name": "", "email": "", "phone": "", "role": "teacher"}
    wants_json = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        form["name"] = request.form.get("name", "").strip()
        form["email"] = request.form.get("email", "").strip()
        form["phone"] = request.form.get("phone", "").strip()
        form["role"] = request.form.get("role", "teacher")

        if not form["name"]:
            errors["name"] = "Full name is required."
        if not form["email"]:
            errors["email"] = "Email is required so we can send account activation instructions."

        if errors:
            if wants_json:
                return jsonify({"success": False, "errors": errors}), 400
        else:
            STAFF.append(
                {
                    "id": next_id(STAFF),
                    "name": form["name"],
                    "email": form["email"],
                    "phone": form["phone"],
                    "role": form["role"],
                    "account_created": True,
                    "has_logged_in": False,  # stays "Account not activated yet" until first login
                    "created_on": date.today().strftime("%d-%m-%Y"),
                }
            )
            flash(f"{form['name']} was added to staff. Their account is pending activation.", "success")
            redirect_url = url_for("profiles", tab="staff")
            if wants_json:
                return jsonify({"success": True, "redirect": redirect_url})
            return redirect(redirect_url)

    context.update({"form": form, "errors": errors})
    return render_template("new_staff.html", **context)


@app.route("/profiles/students/new", methods=["GET", "POST"])
def new_student():
    context = base_context("profiles")
    errors = {}
    form = {"registration_number": "", "name": "", "lin": "", "date_of_birth": ""}
    wants_json = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        form["registration_number"] = request.form.get("registration_number", "").strip()
        form["name"] = request.form.get("name", "").strip()
        form["lin"] = request.form.get("lin", "").strip()
        form["date_of_birth"] = request.form.get("date_of_birth", "").strip()

        if not form["registration_number"]:
            errors["registration_number"] = "Registration number is required."
        elif any(s["registration_number"] == form["registration_number"] for s in STUDENTS):
            errors["registration_number"] = "That registration number is already in use."

        if not form["name"]:
            errors["name"] = "Full name is required."
        if not form["date_of_birth"]:
            errors["date_of_birth"] = "Date of birth is required."
        # LIN is intentionally optional here — it can be added or corrected later from the student's profile.

        if errors:
            if wants_json:
                return jsonify({"success": False, "errors": errors}), 400
        else:
            STUDENTS.append(
                {
                    "id": next_id(STUDENTS),
                    "registration_number": form["registration_number"],
                    "name": form["name"],
                    "lin": form["lin"],
                    "date_of_birth": form["date_of_birth"],
                    "enrolled_class": "",  # not enrolled yet -> status will show as Inactive until Academics > Enrollment sets this
                    "created_on": date.today().strftime("%d-%m-%Y"),
                }
            )
            flash(f"{form['name']} was registered. Enroll them in a class under Academics to mark them active.", "success")
            redirect_url = url_for("profiles", tab="students")
            if wants_json:
                return jsonify({"success": True, "redirect": redirect_url})
            return redirect(redirect_url)

    context.update({"form": form, "errors": errors})
    return render_template("new_student.html", **context)


# --- Profiles: edit + delete (powers the Actions column popups) ---

@app.route("/profiles/staff/<int:staff_id>/edit", methods=["POST"])
def edit_staff(staff_id):
    member = next((m for m in STAFF if m["id"] == staff_id), None)
    if member is None:
        abort(404)

    wants_json = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()

    if not name or not email:
        message = "Full name and email are required to update a staff record."
        if wants_json:
            errors = {}
            if not name:
                errors["name"] = "Full name is required."
            if not email:
                errors["email"] = "Email is required."
            return jsonify({"success": False, "errors": errors}), 400
        flash(message, "error")
        return redirect(url_for("profiles", tab="staff"))

    member["name"] = name
    member["email"] = email
    member["phone"] = request.form.get("phone", "").strip()
    member["role"] = request.form.get("role", member.get("role", "teacher"))

    flash(f"{member['name']}'s details were updated.", "success")
    redirect_url = url_for("profiles", tab="staff")
    if wants_json:
        return jsonify({"success": True, "redirect": redirect_url})
    return redirect(redirect_url)


@app.route("/profiles/staff/<int:staff_id>/delete", methods=["POST"])
def delete_staff(staff_id):
    member = next((m for m in STAFF if m["id"] == staff_id), None)
    if member:
        STAFF.remove(member)
        flash(f"{member['name']} was removed from staff.", "success")
    return redirect(url_for("profiles", tab="staff"))


@app.route("/profiles/students/<int:student_id>/edit", methods=["POST"])
def edit_student(student_id):
    student = next((s for s in STUDENTS if s["id"] == student_id), None)
    if student is None:
        abort(404)

    wants_json = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    registration_number = request.form.get("registration_number", "").strip()
    name = request.form.get("name", "").strip()
    date_of_birth = request.form.get("date_of_birth", "").strip()

    if not registration_number or not name or not date_of_birth:
        message = "Registration number, full name, and date of birth are required."
        if wants_json:
            errors = {}
            if not registration_number:
                errors["registration_number"] = "Registration number is required."
            if not name:
                errors["name"] = "Full name is required."
            if not date_of_birth:
                errors["date_of_birth"] = "Date of birth is required."
            return jsonify({"success": False, "errors": errors}), 400
        flash(message, "error")
        return redirect(url_for("profiles", tab="students"))

    duplicate = any(
        s["registration_number"] == registration_number and s["id"] != student_id for s in STUDENTS
    )
    if duplicate:
        message = "That registration number is already in use by another student."
        if wants_json:
            return jsonify({"success": False, "errors": {"registration_number": message}}), 400
        flash(message, "error")
        return redirect(url_for("profiles", tab="students"))

    student["registration_number"] = registration_number
    student["name"] = name
    student["date_of_birth"] = date_of_birth
    student["lin"] = request.form.get("lin", "").strip()
    # enrolled_class is intentionally untouched here — enrollment is managed under Academics.

    flash(f"{student['name']}'s details were updated.", "success")
    redirect_url = url_for("profiles", tab="students")
    if wants_json:
        return jsonify({"success": True, "redirect": redirect_url})
    return redirect(redirect_url)


@app.route("/profiles/students/<int:student_id>/delete", methods=["POST"])
def delete_student(student_id):
    student = next((s for s in STUDENTS if s["id"] == student_id), None)
    if student:
        STUDENTS.remove(student)
        flash(f"{student['name']} was removed.", "success")
    return redirect(url_for("profiles", tab="students"))


# --- Academics: classes, subjects, enrollment, promotion ---

@app.route("/academics")
def academics():
    tab = request.args.get("tab", "classes")
    if tab not in ("classes", "subjects", "enrollment", "promotion"):
        tab = "classes"

    search_query = request.args.get("q", "").strip()
    context = base_context("academics")
    context.update(
        {
            "active_tab": tab,
            "search_query": search_query,
            "classes": ACADEMIC_CLASSES,
            "students": STUDENTS,
            "teachers": teacher_names(),
            "promotion_actions": ["Promoted", "Second sitting", "Repeating", "Discontinued"],
        }
    )

    if tab == "subjects":
        records = subject_records()
        if search_query:
            query = search_query.lower()
            records = [
                r for r in records
                if query in r["name"].lower() or query in r["class_name"].lower() or query in r["teacher"].lower()
            ]
        context.update({"records": records, "singular_label": "Subject", "plural_label": "Subjects"})
    elif tab == "enrollment":
        records = enrollment_records()
        if search_query:
            query = search_query.lower()
            records = [
                r for r in records
                if query in r["date"].lower() or query in r["description"].lower() or query in r["class_name"].lower()
            ]
        context.update({"records": records, "singular_label": "Enrollment", "plural_label": "Enrollment"})
    elif tab == "promotion":
        records = promotion_records()
        if search_query:
            query = search_query.lower()
            records = [r for r in records if query in r["class_name"].lower()]
        context.update({"records": records, "singular_label": "Promotion", "plural_label": "Promotions"})
    else:
        records = academic_class_records()
        if search_query:
            query = search_query.lower()
            records = [r for r in records if query in r["name"].lower() or query in r["teacher"].lower()]
        context.update({"records": records, "singular_label": "Class", "plural_label": "Classes"})

    return render_template("academics.html", **context)


@app.route("/academics/classes/new", methods=["POST"])
def new_academic_class():
    name = request.form.get("name", "").strip()
    teacher = request.form.get("teacher", "").strip()
    if not name:
        return jsonify({"success": False, "errors": {"name": "Class name is required."}}), 400
    if any(c["name"].lower() == name.lower() for c in ACADEMIC_CLASSES):
        return jsonify({"success": False, "errors": {"name": "That class already exists."}}), 400

    ACADEMIC_CLASSES.append({"id": next_id(ACADEMIC_CLASSES), "name": name, "teacher": teacher})
    if name not in CLASSES:
        CLASSES.append(name)
    return json_or_redirect("classes", f"{name} was added.")


@app.route("/academics/classes/<int:class_id>/edit", methods=["POST"])
def edit_academic_class(class_id):
    class_record = next((c for c in ACADEMIC_CLASSES if c["id"] == class_id), None)
    if class_record is None:
        abort(404)

    name = request.form.get("name", "").strip()
    teacher = request.form.get("teacher", "").strip()
    if not name:
        return jsonify({"success": False, "errors": {"name": "Class name is required."}}), 400
    if any(c["name"].lower() == name.lower() and c["id"] != class_id for c in ACADEMIC_CLASSES):
        return jsonify({"success": False, "errors": {"name": "That class already exists."}}), 400

    old_name = class_record["name"]
    class_record["name"] = name
    class_record["teacher"] = teacher
    for student in STUDENTS:
        if student.get("enrolled_class") == old_name:
            student["enrolled_class"] = name
    for subject in SUBJECTS:
        if subject.get("class_name") == old_name:
            subject["class_name"] = name
    for enrollment in ENROLLMENTS:
        if enrollment.get("class_name") == old_name:
            enrollment["class_name"] = name
            enrollment["description"] = f"{name} enrollment"
    if old_name in CLASSES:
        CLASSES[CLASSES.index(old_name)] = name
    elif name not in CLASSES:
        CLASSES.append(name)
    return json_or_redirect("classes", f"{name} was updated.")


@app.route("/academics/classes/<int:class_id>/delete", methods=["POST"])
def delete_academic_class(class_id):
    class_record = next((c for c in ACADEMIC_CLASSES if c["id"] == class_id), None)
    if class_record:
        ACADEMIC_CLASSES.remove(class_record)
        flash(f"{class_record['name']} was removed.", "success")
    return redirect(academic_redirect("classes"))


@app.route("/academics/classes/<int:class_id>/download")
def download_class_students(class_id):
    class_record = next((c for c in ACADEMIC_CLASSES if c["id"] == class_id), None)
    if class_record is None:
        abort(404)

    lines = ["Registration number,Name,Class"]
    for student in get_class_students(class_record["name"]):
        lines.append(f"{student['registration_number']},{student['name']},{class_record['name']}")
    csv_body = "\n".join(lines) + "\n"
    filename = f"{class_record['name'].lower().replace(' ', '-')}-students.csv"
    return Response(
        csv_body,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/academics/subjects/new", methods=["POST"])
def new_subject():
    name = request.form.get("name", "").strip()
    class_name = request.form.get("class_name", "").strip()
    maximum_mark = request.form.get("maximum_mark", "").strip()
    teacher = request.form.get("teacher", "").strip()
    is_compulsory = request.form.get("is_compulsory") == "on"
    errors = {}
    if not name:
        errors["name"] = "Subject name is required."
    if not class_name:
        errors["class_name"] = "Class is required."
    if not maximum_mark.isdigit():
        errors["maximum_mark"] = "Maximum mark must be a number."
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    SUBJECTS.append(
        {
            "id": next_id(SUBJECTS),
            "name": name,
            "class_name": class_name,
            "maximum_mark": int(maximum_mark),
            "is_compulsory": is_compulsory,
            "teacher": teacher,
        }
    )
    return json_or_redirect("subjects", f"{name} was added.")


@app.route("/academics/subjects/<int:subject_id>/edit", methods=["POST"])
def edit_subject(subject_id):
    subject = next((s for s in SUBJECTS if s["id"] == subject_id), None)
    if subject is None:
        abort(404)

    name = request.form.get("name", "").strip()
    class_name = request.form.get("class_name", "").strip()
    maximum_mark = request.form.get("maximum_mark", "").strip()
    teacher = request.form.get("teacher", "").strip()
    errors = {}
    if not name:
        errors["name"] = "Subject name is required."
    if not class_name:
        errors["class_name"] = "Class is required."
    if not maximum_mark.isdigit():
        errors["maximum_mark"] = "Maximum mark must be a number."
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    subject["name"] = name
    subject["class_name"] = class_name
    subject["maximum_mark"] = int(maximum_mark)
    subject["is_compulsory"] = request.form.get("is_compulsory") == "on"
    subject["teacher"] = teacher
    return json_or_redirect("subjects", f"{name} was updated.")


@app.route("/academics/subjects/<int:subject_id>/delete", methods=["POST"])
def delete_subject(subject_id):
    subject = next((s for s in SUBJECTS if s["id"] == subject_id), None)
    if subject:
        SUBJECTS.remove(subject)
        flash(f"{subject['name']} was removed.", "success")
    return redirect(academic_redirect("subjects"))


@app.route("/academics/enrollment/new", methods=["POST"])
def new_enrollment():
    class_name = request.form.get("class_name", "").strip()
    student_ids = [int(v) for v in request.form.getlist("student_ids") if v.isdigit()]
    if not class_name:
        return jsonify({"success": False, "errors": {"class_name": "Class is required."}}), 400
    if not student_ids:
        return jsonify({"success": False, "errors": {"student_ids": "Choose at least one student."}}), 400

    for student in STUDENTS:
        if student["id"] in student_ids:
            student["enrolled_class"] = class_name
    ENROLLMENTS.append(
        {
            "id": next_id(ENROLLMENTS),
            "date": date.today().strftime("%d-%m-%Y"),
            "class_name": class_name,
            "description": f"{class_name} enrollment",
            "student_ids": student_ids,
            "status": "Enrolled",
        }
    )
    return json_or_redirect("enrollment", f"{len(student_ids)} student(s) enrolled in {class_name}.")


@app.route("/academics/enrollment/<int:enrollment_id>/edit", methods=["POST"])
def edit_enrollment(enrollment_id):
    enrollment = next((e for e in ENROLLMENTS if e["id"] == enrollment_id), None)
    if enrollment is None:
        abort(404)

    class_name = request.form.get("class_name", "").strip()
    student_ids = [int(v) for v in request.form.getlist("student_ids") if v.isdigit()]
    status = request.form.get("status", "Enrolled")
    if not class_name:
        return jsonify({"success": False, "errors": {"class_name": "Class is required."}}), 400
    if not student_ids:
        return jsonify({"success": False, "errors": {"student_ids": "Choose at least one student."}}), 400

    enrollment["class_name"] = class_name
    enrollment["description"] = f"{class_name} enrollment"
    enrollment["student_ids"] = student_ids
    enrollment["status"] = status
    for student in STUDENTS:
        if student["id"] in student_ids:
            student["enrolled_class"] = class_name if status == "Enrolled" else ""
    return json_or_redirect("enrollment", f"{enrollment['description']} was updated.")


@app.route("/academics/enrollment/<int:enrollment_id>/unenroll", methods=["POST"])
def unenroll_students(enrollment_id):
    enrollment = next((e for e in ENROLLMENTS if e["id"] == enrollment_id), None)
    if enrollment:
        enrollment["status"] = "Unenrolled"
        for student in STUDENTS:
            if student["id"] in enrollment["student_ids"]:
                student["enrolled_class"] = ""
        flash(f"{enrollment['description']} was marked unenrolled.", "success")
    return redirect(academic_redirect("enrollment"))


@app.route("/academics/promotion/<int:class_id>/decisions", methods=["POST"])
def update_promotion_decisions(class_id):
    class_record = next((c for c in ACADEMIC_CLASSES if c["id"] == class_id), None)
    if class_record is None:
        abort(404)

    bulk_action = request.form.get("bulk_action", "")
    allowed = {"Promoted", "Second sitting", "Repeating", "Discontinued"}
    for student in get_class_students(class_record["name"]):
        decision = bulk_action or request.form.get(f"student_{student['id']}", "")
        if decision in allowed:
            PROMOTION_DECISIONS[student["id"]] = decision
    return json_or_redirect("promotion", f"{class_record['name']} promotion decisions were updated.")


# --- Placeholder routes for the rest of the main menu ---


@app.route("/grades")
def grades():
    tab = request.args.get("tab", "assessments")
    if tab not in ("assessments", "comments"):
        tab = "assessments"

    search_query = request.args.get("q", "").strip()
    sort = request.args.get("sort", "assessment_type")
    context = base_context("grades")
    context.update(
        {
            "active_tab": tab,
            "search_query": search_query,
            "sort": sort,
            "classes": ACADEMIC_CLASSES,
            "students": STUDENTS,
            "subjects": SUBJECTS,
            "teachers": teacher_names(),
            "assessment_types": ASSESSMENT_TYPES,
            "sort_options": [
                {"value": "assessment_type", "label": "Assessment type"},
                {"value": "student", "label": "Student"},
                {"value": "subject", "label": "Subject"},
            ],
        }
    )

    if tab == "comments":
        records = comment_records()
        if search_query:
            query = search_query.lower()
            records = [
                r for r in records
                if query in r["student_name"].lower()
                or query in r["class_name"].lower()
                or query in r["comment_type"].lower()
                or query in r["teacher"].lower()
            ]
        context.update({"records": records, "singular_label": "Comment", "plural_label": "Comments"})
    else:
        records = assessment_records()
        if search_query:
            query = search_query.lower()
            records = [
                r for r in records
                if query in r["subject"].lower()
                or query in r["assessment_type"].lower()
                or query in r["class_name"].lower()
                or any(query in s["name"].lower() for s in r["students"])
            ]
        if sort == "subject":
            records.sort(key=lambda r: (r["subject"].lower(), r["assessment_type"].lower()))
        elif sort == "student":
            records.sort(key=lambda r: (r["recorded_count"], r["subject"].lower()), reverse=True)
        else:
            sort = "assessment_type"
            records.sort(key=lambda r: (r["assessment_type"].lower(), r["subject"].lower()))
            context["sort"] = sort
        context.update({"records": records, "singular_label": "Assessment", "plural_label": "Assessments"})

    return render_template("grades.html", **context)


@app.route("/grades/assessments/new", methods=["POST"])
def new_assessment():
    assessment_date = request.form.get("date", "").strip()
    subject_id = request.form.get("subject_id", "").strip()
    assessment_type = request.form.get("assessment_type", "").strip()
    maximum = request.form.get("maximum", "").strip()
    subject = next((s for s in SUBJECTS if str(s["id"]) == subject_id), None)
    errors = {}
    if not assessment_date:
        errors["date"] = "Date is required."
    if not subject:
        errors["subject_id"] = "Subject is required."
    if not assessment_type:
        errors["assessment_type"] = "Assessment type is required."
    if not maximum.isdigit():
        errors["maximum"] = "Maximum mark must be a number."
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    assessment_id = next_id(GRADING_ASSESSMENTS)
    GRADING_ASSESSMENTS.append(
        {
            "id": assessment_id,
            "date": assessment_date,
            "class_name": subject["class_name"],
            "subject": subject["name"],
            "subject_id": subject["id"],
            "assessment_type": assessment_type,
            "maximum": int(maximum),
        }
    )
    ASSESSMENT_RESULTS[assessment_id] = {}
    return grades_json_or_redirect("assessments", f"{subject['name']} assessment was added.")


@app.route("/grades/assessments/<int:assessment_id>/edit", methods=["POST"])
def edit_assessment(assessment_id):
    assessment = next((a for a in GRADING_ASSESSMENTS if a["id"] == assessment_id), None)
    if assessment is None:
        abort(404)

    assessment_date = request.form.get("date", "").strip()
    subject_id = request.form.get("subject_id", "").strip()
    assessment_type = request.form.get("assessment_type", "").strip()
    maximum = request.form.get("maximum", "").strip()
    subject = next((s for s in SUBJECTS if str(s["id"]) == subject_id), None)
    errors = {}
    if not assessment_date:
        errors["date"] = "Date is required."
    if not subject:
        errors["subject_id"] = "Subject is required."
    if not assessment_type:
        errors["assessment_type"] = "Assessment type is required."
    if not maximum.isdigit():
        errors["maximum"] = "Maximum mark must be a number."
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    assessment["date"] = assessment_date
    assessment["class_name"] = subject["class_name"]
    assessment["subject"] = subject["name"]
    assessment["subject_id"] = subject["id"]
    assessment["assessment_type"] = assessment_type
    assessment["maximum"] = int(maximum)
    return grades_json_or_redirect("assessments", f"{subject['name']} assessment was updated.")


@app.route("/grades/assessments/<int:assessment_id>/results", methods=["POST"])
def update_assessment_results(assessment_id):
    assessment = next((a for a in GRADING_ASSESSMENTS if a["id"] == assessment_id), None)
    if assessment is None:
        abort(404)

    result_map = {}
    for student in get_class_students(assessment["class_name"]):
        if is_other_subject_assessment(assessment):
            grade = request.form.get(f"grade_{student['id']}", "").strip().upper()
            remark = request.form.get(f"remark_{student['id']}", "").strip()
            if grade or remark:
                result_map[student["id"]] = {"mark": "", "grade": grade, "remark": remark}
        else:
            mark = request.form.get(f"mark_{student['id']}", "").strip()
            aggregate = request.form.get(f"aggregate_{student['id']}", "").strip() or aggregate_from_mark(mark)
            if mark or aggregate:
                result_map[student["id"]] = {"mark": mark, "aggregate": aggregate}
    ASSESSMENT_RESULTS[assessment_id] = result_map
    return grades_json_or_redirect("assessments", f"{assessment['subject']} results were updated.")


@app.route("/grades/assessments/<int:assessment_id>/delete", methods=["POST"])
def delete_assessment(assessment_id):
    assessment = next((a for a in GRADING_ASSESSMENTS if a["id"] == assessment_id), None)
    if assessment:
        GRADING_ASSESSMENTS.remove(assessment)
        ASSESSMENT_RESULTS.pop(assessment_id, None)
        flash(f"{assessment['subject']} assessment was removed.", "success")
    return redirect(grades_redirect("assessments"))


@app.route("/grades/comments/new", methods=["POST"])
def new_grade_comment():
    student_id = request.form.get("student_id", "").strip()
    comment_type = request.form.get("comment_type", "").strip()
    comment = request.form.get("comment", "").strip()
    teacher = request.form.get("teacher", "").strip()
    student = next((s for s in STUDENTS if str(s["id"]) == student_id), None)
    errors = {}
    if not student:
        errors["student_id"] = "Student is required."
    if not comment_type:
        errors["comment_type"] = "Comment type is required."
    if not comment:
        errors["comment"] = "Comment is required."
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    REPORT_COMMENTS.append(
        {
            "id": next_id(REPORT_COMMENTS),
            "student_id": student["id"],
            "class_name": student.get("enrolled_class") or "Not enrolled",
            "comment_type": comment_type,
            "comment": comment,
            "teacher": teacher,
        }
    )
    return grades_json_or_redirect("comments", f"{student['name']}'s comment was added.")


@app.route("/grades/comments/<int:comment_id>/edit", methods=["POST"])
def edit_grade_comment(comment_id):
    report_comment = next((c for c in REPORT_COMMENTS if c["id"] == comment_id), None)
    if report_comment is None:
        abort(404)

    student_id = request.form.get("student_id", "").strip()
    comment_type = request.form.get("comment_type", "").strip()
    comment = request.form.get("comment", "").strip()
    teacher = request.form.get("teacher", "").strip()
    student = next((s for s in STUDENTS if str(s["id"]) == student_id), None)
    errors = {}
    if not student:
        errors["student_id"] = "Student is required."
    if not comment_type:
        errors["comment_type"] = "Comment type is required."
    if not comment:
        errors["comment"] = "Comment is required."
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    report_comment["student_id"] = student["id"]
    report_comment["class_name"] = student.get("enrolled_class") or "Not enrolled"
    report_comment["comment_type"] = comment_type
    report_comment["comment"] = comment
    report_comment["teacher"] = teacher
    return grades_json_or_redirect("comments", f"{student['name']}'s comment was updated.")


@app.route("/grades/comments/<int:comment_id>/delete", methods=["POST"])
def delete_grade_comment(comment_id):
    report_comment = next((c for c in REPORT_COMMENTS if c["id"] == comment_id), None)
    if report_comment:
        REPORT_COMMENTS.remove(report_comment)
        flash("Comment was removed.", "success")
    return redirect(grades_redirect("comments"))


@app.route("/reports")
def reports():
    tab = request.args.get("tab", "cards")
    if tab not in ("cards", "published"):
        tab = "cards"
    search_query = request.args.get("q", "").strip()
    sort = request.args.get("sort", "created_desc")

    source_records = PUBLISHED_REPORTS if tab == "published" else REPORT_BATCHES
    records = report_records(source_records)
    if search_query:
        query = search_query.lower()
        records = [
            r for r in records
            if query in r["class_name"].lower()
            or query in r["report_type"].lower()
            or query in r.get("status", "").lower()
        ]

    if sort == "class":
        records.sort(key=lambda r: (r["class_name"].lower(), r["created_at"]))
    elif sort == "type":
        records.sort(key=lambda r: (r["report_type"].lower(), r["created_at"]))
    else:
        sort = "created_desc"
        records.sort(key=lambda r: r["created_at"], reverse=True)

    context = base_context("reports")
    context.update(
        {
            "active_tab": tab,
            "records": records,
            "search_query": search_query,
            "sort": sort,
            "classes": ACADEMIC_CLASSES,
            "report_types": REPORT_TYPES,
            "class_scopes": ["All classes", "Lower primary", "Upper primary"] + [c["name"] for c in ACADEMIC_CLASSES],
            "school_info": SCHOOL_INFO,
            "sort_options": [
                {"value": "created_desc", "label": "Date created"},
                {"value": "class", "label": "Class"},
                {"value": "type", "label": "Type"},
            ],
        }
    )
    return render_template("reports.html", **context)


@app.route("/reports/generate", methods=["POST"])
def generate_report():
    report_type = request.form.get("report_type", "").strip()
    class_scope = request.form.get("class_scope", "").strip()
    errors = {}
    if report_type not in REPORT_TYPES:
        errors["report_type"] = "Report type is required."
    selected_classes = report_classes_for_scope(class_scope)
    if not selected_classes:
        errors["class_scope"] = "Choose a class group."
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    created_at = datetime.now().strftime("%d-%m-%Y %H:%M")
    generated = 0
    for class_name in selected_classes:
        class_students = get_class_students(class_name)
        if report_type == "Assessment report" and not completed_assessment_subjects(class_name):
            status = "Pending"
            student_ids = []
        else:
            status = "Generated" if class_students else "Pending"
            student_ids = [s["id"] for s in class_students]
        REPORT_BATCHES.append(
            {
                "id": next_id(REPORT_BATCHES),
                "class_name": class_name,
                "report_type": report_type,
                "created_at": created_at,
                "status": status,
                "generated_student_ids": student_ids,
            }
        )
        generated += 1
    return reports_json_or_redirect("cards", f"{generated} report batch(es) were created.")


@app.route("/reports/<int:report_id>/publish", methods=["POST"])
def publish_report(report_id):
    report = next((r for r in REPORT_BATCHES if r["id"] == report_id), None)
    if report is None:
        abort(404)

    publish_here = request.form.get("publish_here") == "on"
    publish_sms = request.form.get("publish_sms") == "on"
    publish_email = request.form.get("publish_email") == "on"
    email = request.form.get("email", "").strip()
    if publish_email and not email:
        return jsonify({"success": False, "errors": {"email": "Email is required when email publishing is on."}}), 400
    if not (publish_here or publish_sms or publish_email):
        return jsonify({"success": False, "errors": {"publish_here": "Choose at least one publish option."}}), 400

    published = {
        **report,
        "id": next_id(PUBLISHED_REPORTS),
        "published_at": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "publish_here": publish_here,
        "publish_sms": publish_sms,
        "publish_email": publish_email,
        "email": email,
    }
    PUBLISHED_REPORTS.append(published)
    report["status"] = "Generated"
    return reports_json_or_redirect("published", f"{report['class_name']} report was published.")


@app.route("/reports/<int:report_id>/delete", methods=["POST"])
def delete_report(report_id):
    tab = request.form.get("tab", "cards")
    target = PUBLISHED_REPORTS if tab == "published" else REPORT_BATCHES
    report = next((r for r in target if r["id"] == report_id), None)
    if report:
        target.remove(report)
        flash(f"{report['class_name']} report was removed.", "success")
    return redirect(reports_redirect(tab))


@app.route("/events")
def events():
    search_query = request.args.get("q", "").strip()
    records = event_records()
    if search_query:
        query = search_query.lower()
        records = [
            r for r in records
            if query in r["name"].lower()
            or query in r["audience"].lower()
            or query in r["teacher"].lower()
            or query in r["activity"].lower()
        ]
    records.sort(key=lambda r: parse_date(r["start_date"]) or date.max)

    context = base_context("attendance")
    context.update(
        {
            "records": records,
            "search_query": search_query,
            "classes": ACADEMIC_CLASSES,
            "teachers": teacher_names() + ["Taaka Beatrice"],
        }
    )
    return render_template("events.html", **context)


@app.route("/events/new", methods=["POST"])
def new_event():
    name = request.form.get("name", "").strip()
    start_date = request.form.get("start_date", "").strip()
    end_date = request.form.get("end_date", "").strip()
    audience_mode = request.form.get("audience_mode", "Whole school")
    audience_classes = request.form.getlist("audience_classes")
    teacher = request.form.get("teacher", "").strip()
    errors = {}

    if not name:
        errors["name"] = "Name is required."
    if not parse_date(start_date):
        errors["start_date"] = "Start date must be DD-MM-YYYY."
    if not parse_date(end_date):
        errors["end_date"] = "End date must be DD-MM-YYYY."
    if parse_date(start_date) and parse_date(end_date) and parse_date(end_date) < parse_date(start_date):
        errors["end_date"] = "End date cannot be before start date."

    audience = "Whole school"
    if audience_mode == "Classes":
        audience = ", ".join(audience_classes)
        if not audience:
            errors["audience_classes"] = "Choose at least one class."

    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    EVENT_RECORDS.append(
        {
            "id": next_id(EVENT_RECORDS),
            "name": name,
            "start_date": start_date,
            "end_date": end_date,
            "audience": audience,
            "teacher": teacher,
        }
    )
    return events_json_or_redirect(f"{name} was added.")


@app.route("/events/<int:event_id>/edit", methods=["POST"])
def edit_event(event_id):
    event = next((e for e in EVENT_RECORDS if e["id"] == event_id), None)
    if event is None:
        abort(404)

    name = request.form.get("name", "").strip()
    start_date = request.form.get("start_date", "").strip()
    end_date = request.form.get("end_date", "").strip()
    audience_mode = request.form.get("audience_mode", "Whole school")
    audience_classes = request.form.getlist("audience_classes")
    teacher = request.form.get("teacher", "").strip()
    errors = {}

    if not name:
        errors["name"] = "Name is required."
    if not parse_date(start_date):
        errors["start_date"] = "Start date must be DD-MM-YYYY."
    if not parse_date(end_date):
        errors["end_date"] = "End date must be DD-MM-YYYY."
    if parse_date(start_date) and parse_date(end_date) and parse_date(end_date) < parse_date(start_date):
        errors["end_date"] = "End date cannot be before start date."

    audience = "Whole school"
    if audience_mode == "Classes":
        audience = ", ".join(audience_classes)
        if not audience:
            errors["audience_classes"] = "Choose at least one class."

    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    event["name"] = name
    event["start_date"] = start_date
    event["end_date"] = end_date
    event["audience"] = audience
    event["teacher"] = teacher
    return events_json_or_redirect(f"{name} was updated.")


@app.route("/events/<int:event_id>/delete", methods=["POST"])
def delete_event(event_id):
    event = next((e for e in EVENT_RECORDS if e["id"] == event_id), None)
    if event:
        EVENT_RECORDS.remove(event)
        flash(f"{event['name']} was removed.", "success")
    return redirect(events_redirect())


@app.route("/attendance")
def attendance():
    search_query = request.args.get("q", "").strip()
    sort = request.args.get("sort", "date_desc")
    records = attendance_records()

    if search_query:
        query = search_query.lower()
        records = [
            r for r in records
            if query in r["date"].lower()
            or query in r["attendance_type"].lower()
            or query in r["session"].lower()
            or query in r["entity"].lower()
        ]

    if sort == "type":
        records.sort(key=lambda r: (r["attendance_type"].lower(), r["entity"].lower()))
    elif sort == "entity":
        records.sort(key=lambda r: (r["entity"].lower(), r["date"]))
    else:
        sort = "date_desc"
        records.sort(key=lambda r: parse_created_on(r["date"]), reverse=True)

    context = base_context("attendance")
    context.update(
        {
            "records": records,
            "search_query": search_query,
            "sort": sort,
            "classes": ACADEMIC_CLASSES,
            "subjects": SUBJECTS,
            "attendance_types": ATTENDANCE_TYPES,
            "attendance_statuses": ATTENDANCE_STATUSES,
            "sort_options": [
                {"value": "date_desc", "label": "Date"},
                {"value": "type", "label": "Type"},
                {"value": "entity", "label": "Entity"},
            ],
        }
    )
    return render_template("attendance.html", **context)


@app.route("/attendance/new", methods=["POST"])
def new_attendance():
    attendance_date = request.form.get("date", "").strip()
    attendance_type = request.form.get("attendance_type", "").strip()
    session = request.form.get("session", "").strip()
    class_name = request.form.get("class_name", "").strip()
    subject_id = request.form.get("subject_id", "").strip()
    event_name = request.form.get("event_name", "").strip()
    errors = {}

    if not attendance_date:
        errors["date"] = "Date is required."
    if attendance_type not in ATTENDANCE_TYPES:
        errors["attendance_type"] = "Type is required."
    if not session:
        errors["session"] = "Session is required."

    entity = ""
    if attendance_type == "Class":
        entity = class_name
        if not class_name:
            errors["class_name"] = "Class is required."
    elif attendance_type == "Subject":
        subject = next((s for s in SUBJECTS if str(s["id"]) == subject_id), None)
        if subject:
            entity = subject["name"]
            class_name = subject["class_name"]
        else:
            errors["subject_id"] = "Subject is required."
    elif attendance_type == "Event":
        entity = event_name
        if not event_name:
            errors["event_name"] = "Event is required."

    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    record_id = next_id(ATTENDANCE_RECORDS)
    ATTENDANCE_RECORDS.append(
        {
            "id": record_id,
            "date": attendance_date,
            "attendance_type": attendance_type,
            "session": session,
            "entity": entity,
            "class_name": class_name,
        }
    )
    ATTENDANCE_MARKS[record_id] = {}
    return attendance_json_or_redirect(f"{entity} attendance was created.")


@app.route("/attendance/<int:attendance_id>/marks", methods=["POST"])
def update_attendance_marks(attendance_id):
    record = next((r for r in ATTENDANCE_RECORDS if r["id"] == attendance_id), None)
    if record is None:
        abort(404)

    marks = {}
    for student in attendance_students(record):
        status = request.form.get(f"status_{student['id']}", "").strip()
        time_value = request.form.get(f"time_{student['id']}", "").strip()
        if status:
            marks[student["id"]] = {"status": status, "time": time_value}
    ATTENDANCE_MARKS[attendance_id] = marks
    return attendance_json_or_redirect(f"{record['entity']} attendance was saved.")


@app.route("/attendance/<int:attendance_id>/delete", methods=["POST"])
def delete_attendance(attendance_id):
    record = next((r for r in ATTENDANCE_RECORDS if r["id"] == attendance_id), None)
    if record:
        ATTENDANCE_RECORDS.remove(record)
        ATTENDANCE_MARKS.pop(attendance_id, None)
        flash(f"{record['entity']} attendance was removed.", "success")
    return redirect(attendance_redirect())


if __name__ == "__main__":
    app.run(debug=True)