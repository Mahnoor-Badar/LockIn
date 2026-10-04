import uuid
from datetime import datetime

import streamlit as st
from streamlit_mic_recorder import mic_recorder

from models.session import LearningSession
from models.quiz_attempt import QuizAttempt

from services.firebase_service import (
    create_learning_session,
    create_quiz_attempt,
    create_learning_gap,
    save_learning_report,
    update_session,
)

from services.llm_service import LLMService
from services.voice_service import VoiceService
from services.quiz_engine import QuizEngine
from services.adaptive_engine import AdaptiveEngine
from services.report_service import ReportService


st.set_page_config(
    page_title="LockIn",
    page_icon="🔒",
    layout="centered",
)

# Temporary local quiz mode for testing while Gemini quota is exhausted.


llm_service = LLMService()
voice_service = VoiceService()
quiz_engine = QuizEngine()
adaptive_engine = AdaptiveEngine()
report_service = ReportService()


def generate_stage_quiz(stage):
    try:
        # Local test mode avoids Gemini quota usage.
        if st.session_state.get("quiz_test_mode", False):
            from schemas.quiz_schema import QuizSchema, Question

            stage_questions = {
                "easy": [
                    Question(
                        id=1,
                        difficulty="easy",
                        question="1/2 mein numerator kya hai?",
                        options=["1", "2", "3", "4"],
                        correct_answer="1",
                        concept_tag="numerator",
                    ),
                    Question(
                        id=2,
                        difficulty="easy",
                        question="1/2 + 1/2 kitna hota hai?",
                        options=["1", "2", "1/4", "3/2"],
                        correct_answer="1",
                        concept_tag="fraction addition",
                    ),
                ],
                "medium": [
                    Question(
                        id=1,
                        difficulty="medium",
                        question="2/4 kis fraction ke barabar hai?",
                        options=["1/2", "1/4", "2/3", "3/4"],
                        correct_answer="1/2",
                        concept_tag="equivalent fractions",
                    ),
                    Question(
                        id=2,
                        difficulty="medium",
                        question="3/4 aur 1/4 ko add karein.",
                        options=["1", "2", "3/8", "4/8"],
                        correct_answer="1",
                        concept_tag="fraction addition",
                    ),
                ],
                "hard": [
                    Question(
                        id=1,
                        difficulty="hard",
                        question="2/3 aur 3/4 mein kaunsa bara hai?",
                        options=["2/3", "3/4", "Dono equal", "1/2"],
                        correct_answer="3/4",
                        concept_tag="fraction comparison",
                    ),
                    Question(
                        id=2,
                        difficulty="hard",
                        question="1 1/2 ko improper fraction mein convert karein.",
                        options=["2/2", "3/2", "4/2", "5/2"],
                        correct_answer="3/2",
                        concept_tag="mixed fractions",
                    ),
                ],
            }

            quiz = QuizSchema(
                subject=st.session_state["subject"],
                topic=st.session_state["topic"],
                grade=st.session_state["student_class"],
                questions=stage_questions[stage],
            )

        else:
            with st.spinner(
                f"LockIn {stage.title()} level ke 2 questions bana raha hai... 🤖"
            ):
                quiz = quiz_engine.generate_quiz(
                    subject=st.session_state["subject"],
                    topic=st.session_state["topic"],
                    grade=st.session_state["student_class"],
                    difficulty=stage,
                )

        if len(quiz.questions) != 2:
            raise ValueError(
                f"Expected exactly 2 questions, got {len(quiz.questions)}."
            )

        st.session_state["current_quiz"] = quiz
        st.session_state["quiz_stage"] = stage
        st.session_state["quiz_version"] = str(uuid.uuid4())
        st.session_state["last_stage_result"] = None

        return True

    except Exception as e:
        st.error(f"Quiz generate nahi ho saka: {e}")
        st.exception(e)
        return False


# =========================================================
# SAFETY CARD
# =========================================================

if "session_id" in st.session_state:

    if not st.session_state.get(
        "safety_acknowledged",
        False,
    ):
        st.title("🔒 LockIn")
        st.subheader("Before we start")

        st.info(
            """
            🤖 LockIn ek AI hai, kabhi kabhi ghalti kar sakta hai.
            Zaroori cheezein apni book se check kar lo.

            🔒 Apni personal info mat batao
            (address, phone number, password).

            📚 LockIn sirf educational topics sikhata hai.
            Agar aap kisi non-educational topic ke baare mein
            poochain, LockIn aapko wapas parhai par le aayega.
            """
        )

        if st.button(
            "Okay, samajh gaya",
            use_container_width=True,
        ):
            st.session_state["safety_acknowledged"] = True
            st.rerun()

        st.stop()


# =========================================================
# ACTIVE SESSION
# =========================================================

if "session_id" in st.session_state:

    st.title("🎓 LockIn Tutor")
    st.caption("Your adaptive AI learning tutor.")

    col1, col2 = st.columns(2)

    with col1:
        st.write(
            f"**Class:** {st.session_state['student_class']}"
        )
        st.write(
            f"**Board:** {st.session_state['board']}"
        )

    with col2:
        st.write(
            f"**Subject:** {st.session_state['subject']}"
        )
        st.write(
            f"**Topic:** {st.session_state['topic']}"
        )

    st.divider()

    # =====================================================
    # TUTOR
    # =====================================================

    st.subheader("📚 Learning Topic")

    st.write(
        f"Today we are learning "
        f"**{st.session_state['topic']}** "
        f"in **{st.session_state['subject']}**."
    )

    st.info(
        "Ask LockIn a question about your selected topic. "
        "You can type or use your microphone."
    )

    student_question = st.text_input(
        "Ask LockIn something:",
        placeholder="Apne topic ke baare mein sawal poochein...",
    )

    if st.button(
        "Ask LockIn",
        use_container_width=True,
    ):
        if not student_question.strip():
            st.warning(
                "Please enter a question first."
            )
        else:
            question = student_question.strip()

            st.session_state["last_question"] = question

            with st.spinner(
                "LockIn soch raha hai... 🤖"
            ):
                tutor_response = (
                    llm_service.explain_topic(
                        topic=st.session_state["topic"],
                        grade=st.session_state["student_class"],
                        board=st.session_state["board"],
                        subject=st.session_state["subject"],
                        student_question=question,
                    )
                )

            st.session_state[
                "tutor_response"
            ] = tutor_response

            st.rerun()

    # =====================================================
    # VOICE
    # =====================================================

    st.write(
        "🎙️ **Ya bol kar apna sawal poochein:**"
    )

    recorded_audio = mic_recorder(
        start_prompt="🎙️ Record",
        stop_prompt="⏹️ Stop",
        key="lockin_recorder",
    )

    if recorded_audio:

        with st.spinner(
            "Aap ki awaaz samjhi ja rahi hai... 🎧"
        ):
            voice_question = (
                voice_service.transcribe_audio(
                    recorded_audio["bytes"]
                )
            )

        if voice_question:
            st.success(
                f"Aap ne kaha: {voice_question}"
            )

    # =====================================================
    # TUTOR RESPONSE + TTS
    # =====================================================

    if "tutor_response" in st.session_state:

        st.divider()
        st.subheader("🤖 LockIn")

        st.write(
            st.session_state["tutor_response"]
        )

        audio_fp = voice_service.text_to_speech(
            st.session_state["tutor_response"]
        )

        if audio_fp:
            st.audio(
                audio_fp,
                format="audio/mp3",
            )

    # =====================================================
    # ADAPTIVE QUIZ
    # =====================================================

    st.divider()
    st.header("🧠 Adaptive Quiz")

    quiz_started = st.session_state.get(
        "quiz_started",
        False,
    )

    current_quiz = st.session_state.get(
        "current_quiz"
    )

    current_stage = st.session_state.get(
        "quiz_stage"
    )

    last_stage_result = st.session_state.get(
        "last_stage_result"
    )

    # -----------------------------------------------------
    # START QUIZ
    # -----------------------------------------------------

    if not quiz_started and not last_stage_result:

        st.write(
            "Tutor ke baad apni understanding test karein."
        )

        st.write(
            "Har level mein exactly 2 questions honge:"
        )

        st.write(
            "🟢 Easy → 🟡 Medium → 🔴 Hard"
        )

        if st.button(
            "🚀 Start Adaptive Quiz",
            use_container_width=True,
        ):

            session = st.session_state[
                "learning_session"
            ]

            session.current_stage = "easy"

            update_session(session)

            st.session_state[
                "quiz_started"
            ] = True

            st.session_state[
                "quiz_stage"
            ] = "easy"

            st.session_state[
                "quiz_attempts"
            ] = []

            st.session_state[
                "current_quiz"
            ] = None

            if generate_stage_quiz("easy"):
                st.rerun()

    # -----------------------------------------------------
    # CURRENT QUIZ
    # -----------------------------------------------------

    if current_quiz:

        stage = st.session_state[
            "quiz_stage"
        ]

        st.subheader(
            f"{stage.title()} Level — 2 Questions"
        )

        st.write(
            "Dono questions attempt karein "
            "phir Submit Stage press karein."
        )

        quiz_version = st.session_state[
            "quiz_version"
        ]

        with st.form(
            key=f"quiz_form_{quiz_version}"
        ):

            answers = {}

            for question in current_quiz.questions:

                st.markdown(
                    f"**Q{question.id}. "
                    f"{question.question}**"
                )

                answers[question.id] = st.radio(
                    "Select your answer:",
                    question.options,
                    index=None,
                    key=(
                        f"quiz_{quiz_version}_"
                        f"{question.id}"
                    ),
                )

                st.write("")

            submitted = st.form_submit_button(
                "✅ Submit Stage",
                use_container_width=True,
            )

        if submitted:

            unanswered = [
                question.id
                for question in current_quiz.questions
                if not answers.get(question.id)
            ]

            if unanswered:

                st.warning(
                    "Please answer all 2 questions "
                    "before submitting."
                )

            else:

                evaluation = (
                    quiz_engine.evaluate_quiz(
                        current_quiz,
                        answers,
                    )
                )

                attempts = st.session_state[
                    "quiz_attempts"
                ]

                for question, evaluation_item in zip(
                    current_quiz.questions,
                    evaluation.evaluations,
                ):

                    attempt = QuizAttempt(
                        attempt_id=str(uuid.uuid4()),
                        session_id=(
                            st.session_state[
                                "session_id"
                            ]
                        ),
                        question=question.question,
                        difficulty=question.difficulty,
                        concept=question.concept_tag,
                        selected_answer=(
                            evaluation_item.user_answer
                        ),
                        correct_answer=(
                            evaluation_item.correct_answer
                        ),
                        is_correct=(
                            evaluation_item.is_correct
                        ),
                        timestamp=datetime.now(),
                    )

                    attempts.append(attempt)

                    create_quiz_attempt(
                        attempt
                    )

                stage_result = (
                    adaptive_engine.process_stage(
                        attempts,
                        stage,
                    )
                )

                if stage_result[
                    "next_stage"
                ] == "remediation":

                    latest_stage_attempts = attempts[-2:]

                    learning_gap = (
                        adaptive_engine.identify_learning_gap(
                            attempts=latest_stage_attempts,
                            current_stage=stage,
                            gap_id=str(uuid.uuid4()),
                            session_id=(
                                st.session_state[
                                    "session_id"
                                ]
                            ),
                        )
                    )

                    if learning_gap:
                        create_learning_gap(
                            learning_gap
                        )

                session = (
                    st.session_state[
                        "learning_session"
                    ]
                )

                adaptive_engine.update_session(
                    session,
                    stage_result,
                )

                if (
                    stage_result["next_stage"]
                    == "remediation"
                ):
                    session.current_stage = stage

                if (
                    stage_result["next_stage"]
                    == "complete"
                ):
                    session.completed_at = (
                        datetime.now()
                    )

                update_session(session)

                st.session_state[
                    "last_stage_result"
                ] = stage_result

                st.session_state[
                    "current_quiz"
                ] = None

                st.rerun()

    # -----------------------------------------------------
    # STAGE RESULT
    # -----------------------------------------------------

    if (
        last_stage_result
        and not current_quiz
    ):

        stage = last_stage_result[
            "stage"
        ]

        score = last_stage_result[
            "score"
        ]

        next_stage = last_stage_result[
            "next_stage"
        ]

        st.subheader(
            f"{stage.title()} Stage Result"
        )

        st.metric(
            "Score",
            f"{score}/2",
        )

        if next_stage == "remediation":

            st.warning(
                "Abhi is level par thori aur "
                "practice chahiye."
            )

            st.write(
                f"Hum **{stage.title()}** level "
                "ko dobara try karenge."
            )

            if st.button(
                f"🔁 Retry {stage.title()}",
                use_container_width=True,
            ):

                if generate_stage_quiz(stage):
                    st.rerun()

        elif next_stage in {
            "medium",
            "hard",
        }:

            st.success(
                f"Great! Aap ne "
                f"{stage.title()} level master "
                "kar liya. 🎉"
            )

            st.write(
                f"Next stage: "
                f"**{next_stage.title()}**"
            )

            if st.button(
                f"➡️ Continue to "
                f"{next_stage.title()}",
                use_container_width=True,
            ):

                if generate_stage_quiz(next_stage):
                    st.rerun()

        elif next_stage == "complete":

            session = (
                st.session_state[
                    "learning_session"
                ]
            )

            st.success(
                "🎉 Congratulations! Aap ne "
                "Easy, Medium aur Hard teeno "
                "stages complete kar liye."
            )

            report = report_service.build_report(
                session,
                st.session_state[
                    "quiz_attempts"
                ],
            )

            save_learning_report(
                st.session_state[
                    "session_id"
                ],
                report,
            )

            st.subheader(
                "📊 Your Learning Report"
            )

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Final Score",
                    f"{report['final_score']}/6",
                )

            with col2:
                st.metric(
                    "Mastery",
                    report[
                        "mastery_level"
                    ].title(),
                )

            st.write(
                f"**Class:** "
                f"{report['student_class']}"
            )

            st.write(
                f"**Subject:** "
                f"{report['subject']}"
            )

            st.write(
                f"**Topic:** "
                f"{report['topic']}"
            )

            st.write(
                f"**Easy:** "
                f"{report['easy_score']}/2"
            )

            st.write(
                f"**Medium:** "
                f"{report['medium_score']}/2"
            )

            st.write(
                f"**Hard:** "
                f"{report['hard_score']}/2"
            )

            if report["weak_concepts"]:

                st.subheader(
                    "📚 Concepts to Review"
                )

                for concept in (
                    report["weak_concepts"]
                ):
                    st.write(
                        f"• {concept}"
                    )

            else:

                st.success(
                    "✅ Koi major weak concept "
                    "identify nahi hua."
                )

    # =====================================================
    # START NEW SESSION
    # =====================================================

    st.divider()

    if st.button(
        "🔄 Start New Session",
        use_container_width=True,
    ):

        for key in [
            "session_id",
            "student_class",
            "board",
            "subject",
            "topic",
            "safety_acknowledged",
            "last_question",
            "tutor_response",
            "learning_session",
            "quiz_started",
            "quiz_attempts",
            "quiz_stage",
            "quiz_version",
            "current_quiz",
            "last_stage_result",
        ]:

            st.session_state.pop(
                key,
                None,
            )

        st.rerun()

    st.stop()


# =========================================================
# START SCREEN
# =========================================================

st.title("🔒 LockIn")

st.subheader(
    "Your adaptive AI learning tutor"
)

st.write(
    "Learn a topic with an AI tutor "
    "and then test your understanding "
    "through an adaptive quiz."
)

student_class = st.selectbox(
    "Select your class",
    [
        "Class 1",
        "Class 2",
        "Class 3",
        "Class 4",
        "Class 5",
        "Class 6",
        "Class 7",
        "Class 8",
        "Class 9",
        "Class 10",
    ],
)

board = st.text_input(
    "Education Board",
    placeholder="e.g. Federal Board",
)

subject = st.text_input(
    "Subject",
    placeholder=(
        "e.g. Mathematics, Science, English"
    ),
)

topic = st.text_input(
    "What do you want to learn?",
    placeholder="e.g. Fractions",
)

if st.button(
    "Start Learning",
    use_container_width=True,
):

    if not board.strip():

        st.warning(
            "Please enter your education board."
        )

    elif not subject.strip():

        st.warning(
            "Please enter a subject."
        )

    elif not topic.strip():

        st.warning(
            "Please enter a topic."
        )

    else:

        session_id = str(uuid.uuid4())

        session = LearningSession(
            session_id=session_id,
            user_id="demo-user",
            student_class=student_class,
            board=board.strip(),
            subject=subject.strip(),
            topic=topic.strip(),
            started_at=datetime.now(),
        )

        create_learning_session(
            session
        )

        st.session_state[
            "session_id"
        ] = session_id

        st.session_state[
            "student_class"
        ] = student_class

        st.session_state[
            "board"
        ] = board.strip()

        st.session_state[
            "subject"
        ] = subject.strip()

        st.session_state[
            "topic"
        ] = topic.strip()

        st.session_state[
            "learning_session"
        ] = session

        st.session_state[
            "safety_acknowledged"
        ] = False

        st.session_state[
            "quiz_started"
        ] = False

        st.session_state[
            "quiz_attempts"
        ] = []

        st.session_state[
            "current_quiz"
        ] = None

        st.session_state[
            "last_stage_result"
        ] = None

        st.rerun()
