import glob
from dataclasses import asdict

import firebase_admin
from firebase_admin import credentials, firestore


def initialize_firebase():
    if firebase_admin._apps:
        return firestore.client()

    firebase_files = glob.glob("*.json")

    if not firebase_files:
        raise FileNotFoundError(
            "Firebase service account JSON file was not found."
        )

    cred = credentials.Certificate(firebase_files[0])
    firebase_admin.initialize_app(cred)

    return firestore.client()


db = initialize_firebase()


def create_session(session_id, data):
    db.collection("sessions").document(session_id).set(data)


def create_learning_session(session):
    data = asdict(session)

    db.collection("sessions").document(
        session.session_id
    ).set(data)


def update_session(session):
    data = asdict(session)

    db.collection("sessions").document(
        session.session_id
    ).set(data, merge=True)


def get_session(session_id):
    document = (
        db.collection("sessions")
        .document(session_id)
        .get()
    )

    if document.exists:
        return document.to_dict()

    return None


def add_quiz_attempt(session_id, attempt_id, data):
    (
        db.collection("sessions")
        .document(session_id)
        .collection("quiz_attempts")
        .document(attempt_id)
        .set(data)
    )


def create_quiz_attempt(attempt):
    data = asdict(attempt)

    (
        db.collection("sessions")
        .document(attempt.session_id)
        .collection("quiz_attempts")
        .document(attempt.attempt_id)
        .set(data)
    )


def create_learning_gap(gap):
    data = asdict(gap)

    (
        db.collection("sessions")
        .document(gap.session_id)
        .collection("learning_gaps")
        .document(gap.gap_id)
        .set(data)
    )

def save_learning_report(session_id, report):
    (
        db.collection("sessions")
        .document(session_id)
        .set(
            {"learning_report": report},
            merge=True,
        )
    )
