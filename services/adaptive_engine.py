from models.learning_gap import LearningGap


class AdaptiveEngine:
    MASTERY_SCORE = 2

    def calculate_score(self, attempts):
        return sum(
            1 for attempt in attempts
            if attempt.is_correct
        )

    def calculate_stage_score(self, attempts, difficulty):
        stage_attempts = [
            attempt
            for attempt in attempts
            if attempt.difficulty == difficulty
        ]

        # Each stage contains exactly 2 questions.
        # On retry, use only the latest 2 attempts.
        latest_stage_attempts = stage_attempts[-2:]

        return self.calculate_score(
            latest_stage_attempts
        )

    def evaluate_stage(self, correct_answers, current_stage):
        if correct_answers >= self.MASTERY_SCORE:
            if current_stage == "easy":
                return "medium"

            if current_stage == "medium":
                return "hard"

            if current_stage == "hard":
                return "complete"

        return "remediation"

    def process_stage(self, attempts, current_stage):
        score = self.calculate_stage_score(
            attempts,
            current_stage,
        )

        next_stage = self.evaluate_stage(
            score,
            current_stage,
        )

        return {
            "stage": current_stage,
            "score": score,
            "next_stage": next_stage,
            "mastered": score >= self.MASTERY_SCORE,
        }

    def update_session(self, session, stage_result):
        stage = stage_result["stage"]
        score = stage_result["score"]
        next_stage = stage_result["next_stage"]

        if stage == "easy":
            session.easy_score = score

        elif stage == "medium":
            session.medium_score = score

        elif stage == "hard":
            session.hard_score = score

        session.current_stage = next_stage

        if next_stage == "complete":
            session.final_score = (
                session.easy_score
                + session.medium_score
                + session.hard_score
            )

            session.mastery_level = "mastered"

        return session

    def create_learning_gap(
        self,
        gap_id,
        session_id,
        concept,
        misconception,
        difficulty,
    ):
        return LearningGap(
            gap_id=gap_id,
            session_id=session_id,
            concept=concept,
            misconception=misconception,
            difficulty=difficulty,
            attempt_count=1,
            resolved=False,
        )

    def identify_learning_gap(
        self,
        attempts,
        current_stage,
        gap_id,
        session_id,
    ):
        failed_attempts = [
            attempt
            for attempt in attempts
            if (
                attempt.difficulty == current_stage
                and not attempt.is_correct
            )
        ]

        if not failed_attempts:
            return None

        failed_attempt = failed_attempts[0]

        return self.create_learning_gap(
            gap_id=gap_id,
            session_id=session_id,
            concept=failed_attempt.concept,
            misconception=(
                f"Student answered "
                f"'{failed_attempt.selected_answer}' "
                f"instead of "
                f"'{failed_attempt.correct_answer}'."
            ),
            difficulty=failed_attempt.difficulty,
        )
