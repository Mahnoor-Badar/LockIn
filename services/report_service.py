from typing import Dict


class ReportService:

    def build_report(self, session, attempts) -> Dict:
        # Keep only the latest 2 attempts for each difficulty stage.
        # This removes old failed attempts that were superseded by a retry.
        latest_by_stage = {}

        for difficulty in ("easy", "medium", "hard"):
            stage_attempts = [
                attempt
                for attempt in attempts
                if attempt.difficulty == difficulty
            ]

            latest_by_stage[difficulty] = stage_attempts[-2:]

        weak_concepts = []

        for stage_attempts in latest_by_stage.values():
            for attempt in stage_attempts:
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
