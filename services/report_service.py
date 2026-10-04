from typing import Dict


class ReportService:

    def build_report(self, session, attempts) -> Dict:
        weak_concepts = []

        for attempt in attempts:
            if not attempt.is_correct:
                weak_concepts.append(attempt.concept)

        weak_concepts = list(
            dict.fromkeys(weak_concepts)
        )

        return {
            "student_class": session.student_class,
            "board": session.board,
            "subject": session.subject,
            "topic": session.topic,
            "easy_score": session.easy_score,
            "medium_score": session.medium_score,
            "hard_score": session.hard_score,
            "final_score": session.final_score,
            "total_questions": 6,
            "mastery_level": session.mastery_level,
            "weak_concepts": weak_concepts,
        }
