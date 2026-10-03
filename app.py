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
from ui_theme import apply_lockin_theme


st.set_page_config(
    page_title="LockIn",
    page_icon="L",
    layout="centered",
)

apply_lockin_theme()


llm_service = LLMService()
voice_service = VoiceService()
quiz_engine = QuizEngine()
adaptive_engine = AdaptiveEngine()
report_service = ReportService()


def generate_stage_quiz(stage):
    try:
        with st.spinner(
            f"LockIn {stage.title()} level ke 2 questions bana raha hai... 🤖"
        ):
            quiz = quiz_engine.generate_quiz(
                topic=st.session_state["topic"],
                grade=st.session_state["student_class"],
                subject=st.session_state["subject"],
                difficulty=stage,
            )

        st.session_state["current_quiz"] = quiz
        st.session_state["quiz_stage"] = stage
        st.session_state["quiz_version"] = str(uuid.uuid4())
        st.session_state["last_stage_result"] = None
        st.session_state["stage_remediation"] = []

    except Exception as e:
        # If the first Easy quiz cannot be generated, allow
        # the student to try starting the quiz again.
        if (
            stage == "easy"
            and not st.session_state.get("quiz_attempts")
        ):
            st.session_state["quiz_started"] = False

        st.session_state["current_quiz"] = None

        st.error(
            f"Quiz generate nahi ho saka: {e}"
        )


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

            generate_stage_quiz("easy")

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

                remediation_messages = [
                    item.remediation_analogy
                    for item in evaluation.evaluations
                    if item.remediation_analogy
                ]

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

                if stage_result["next_stage"] == "remediation":
                    latest_stage_attempts = attempts[-2:]

                    learning_gap = (
                        adaptive_engine.identify_learning_gap(
                            attempts=latest_stage_attempts,
                            current_stage=stage,
                            gap_id=str(uuid.uuid4()),
                            session_id=st.session_state["session_id"],
                        )
                    )

                    if learning_gap:
                        create_learning_gap(learning_gap)

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
                    "stage_remediation"
                ] = remediation_messages

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

            remediation_messages = st.session_state.get(
                "stage_remediation",
                [],
            )

            if remediation_messages:
                st.subheader("💡 Let's Review")

                for message in remediation_messages:
                    st.info(message)

            st.write(
                f"Hum **{stage.title()}** level "
                "ko dobara try karenge."
            )

            if st.button(
                f"🔁 Retry {stage.title()}",
                use_container_width=True,
            ):

                generate_stage_quiz(
                    stage
                )

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

                generate_stage_quiz(
                    next_stage
                )

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
                st.session_state["quiz_attempts"],
            )

            save_learning_report(
                st.session_state["session_id"],
                report,
            )

            st.subheader("📊 Your Learning Report")

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Final Score",
                    f"{report['final_score']}/6",
                )

            with col2:
                st.metric(
                    "Mastery",
                    report["mastery_level"].title(),
                )

            st.write(
                f"**Class:** {report['student_class']}"
            )

            st.write(
                f"**Subject:** {report['subject']}"
            )

            st.write(
                f"**Topic:** {report['topic']}"
            )

            st.write(
                f"**Easy:** {report['easy_score']}/2"
            )

            st.write(
                f"**Medium:** {report['medium_score']}/2"
            )

            st.write(
                f"**Hard:** {report['hard_score']}/2"
            )

            if report["weak_concepts"]:
                st.subheader("📚 Concepts to Review")

                for concept in report["weak_concepts"]:
                    st.write(f"• {concept}")

            else:
                st.success(
                    "✅ Koi major weak concept identify nahi hua."
                )

    # =====================================================
    # NEW SESSION
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
            "stage_remediation",
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

st.markdown(
    """
    <style>

    /* ---------- Page ---------- */

    .lockin-topbar {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 58px;
        margin-bottom: 3rem;
        padding: 0 1.25rem;
        border-radius: 15px;
        background: #1F2937;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.12);
    }

    .lockin-logo {
        font-size: 1.05rem;
        font-weight: 850;
        letter-spacing: 0.18em;
        color: #FFFFFF;
        text-align: center;
    }

    .lockin-topbar-label {
        position: absolute;
        right: 1.1rem;
        font-size: 0.76rem;
        color: #D8DEE9;
        font-weight: 650;
    }

    /* ---------- Hero ---------- */

    .lockin-hero {
        max-width: 720px;
        margin: 0 auto 2rem auto;
        text-align: center;
    }

    .lockin-eyebrow {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        background: #EEF2FF;
        color: #4F46E5;
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        margin-bottom: 1rem;
    }

    .lockin-title {
        font-size: 2.2rem;
        line-height: 1.08;
        font-weight: 800;
        letter-spacing: -0.045em;
        color: #111827;
        margin-bottom: 0.9rem;
    }

    .lockin-subtitle {
        font-size: 1.5rem;
        line-height: 1.55;
        color: #222222;
        max-width: 610px;
        margin: 0 auto;
    }

    /* ---------- Setup card ---------- */

    .lockin-setup {
        max-width: 720px;
        margin: 0 auto;
        background: #FFFFFF;
        border: 1px solid #E7EAF0;
        border-radius: 24px;
        padding: 2rem;
        box-shadow:
            0 14px 40px rgba(17, 24, 39, 0.06),
            0 2px 8px rgba(17, 24, 39, 0.03);
    }

    .lockin-step {
        padding-bottom: 1.45rem;
        margin-bottom: 1.45rem;
        border-bottom: 1px solid #EEF0F4;
    }

    .lockin-step:last-child {
        border-bottom: none;
        margin-bottom: 0;
        padding-bottom: 0;
    }

    .lockin-step-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border-radius: 9px;
        background: #EEF2FF;
        color: #4F46E5;
        font-size: 0.76rem;
        font-weight: 800;
        margin-right: 0.55rem;
        vertical-align: middle;
    }

    .lockin-step-title {
        display: inline;
        vertical-align: middle;
        color: #1F2937;
        font-size: 0.95rem;
        font-weight: 750;
    }

    .lockin-step-help {
        margin: 0.55rem 0 1rem 2.15rem;
        color: #7A8495;
        font-size: 1.23rem;
        line-height: 1.5;
    }

    /* ---------- Topic helper ---------- */

    .lockin-topic-help {
        margin-top: 0.35rem;
        padding: 0.75rem 0.9rem;
        background: #F8FAFC;
        border: 1px solid #EDF0F5;
        border-radius: 12px;
        color: #6B7280;
        font-size: 0.78rem;
    }

    /* ---------- Bottom promise ---------- */

    .lockin-promise {
        display: flex;
        justify-content: center;
        gap: 1.4rem;
        flex-wrap: wrap;
        margin: 1.3rem auto 0 auto;
        color: #7A8495;
        font-size: 0.76rem;
        font-weight: 600;
    }

    /* ---------- Streamlit controls ---------- */

    /* ---------- Shared field surface ---------- */

    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div,
    div[data-baseweb="select"] > div {
        min-height: 48px !important;
        border-radius: 12px !important;
        border: 1px solid #D6E1F5 !important;
        background: #EEF4FF !important;
        box-shadow: none !important;
    }

    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"] textarea {
        background: #EEF4FF !important;
        color: #1F2937 !important;
    }

    div[data-baseweb="select"] input {
        background: #EEF4FF !important;
    }

    div[data-baseweb="input"] > div:focus-within,
    div[data-baseweb="textarea"] > div:focus-within,
    div[data-baseweb="select"] > div:focus-within {
        border-color: #9CB5E8 !important;
        box-shadow: 0 0 0 3px rgba(93, 125, 190, 0.10) !important;
    }

    .lockin-learning-note {
        margin-top: 0.8rem;
        padding: 0.85rem 1rem;
        border-radius: 12px;
        border: 1px solid #D6E1F5;
        background: #EEF4FF;
        color: #4B5B73;
        font-size: 1.23rem;
        line-height: 1.5;
        font-weight: 600;
    }


    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div {
        min-height: 48px !important;
        border-radius: 12px !important;
        border: 1px solid #DCE1E9 !important;
        background: #FFFFFF !important;
        box-shadow: none !important;
    }

    div[data-baseweb="input"] > div:focus-within,
    div[data-baseweb="select"] > div:focus-within {
        border-color: #6366F1 !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.09) !important;
    }

    label {
        color: #344054 !important;
        font-size: 0.84rem !important;
        font-weight: 650 !important;
    }

    .stButton > button {
        min-height: 50px !important;
        border-radius: 13px !important;
        border: 1px solid #111827 !important;
        background: #111827 !important;
        color: #111827 !important;
        font-size: 0.93rem !important;
        font-weight: 750 !important;
        text-shadow: none !important;
        box-shadow: 0 8px 18px rgba(17, 24, 39, 0.16) !important;
        transition: all 0.18s ease !important;
    }

    .stButton > button p,
    .stButton > button span {
        color: #111827 !important;
    }

    .stButton > button:hover {
        background: #1F2937 !important;
        border-color: #1F2937 !important;
        color: #FFFFFF !important;
        transform: translateY(-1px);
        box-shadow: 0 11px 22px rgba(17, 24, 39, 0.22) !important;
    }

    .stButton > button:active {
        background: #0F172A !important;
        color: #FFFFFF !important;
    }


    /* =====================================================
       FINAL LOCKIN COLOR OVERRIDES
       ===================================================== */

    .lockin-topbar {
        background: #7EE2E6 !important;
        border: 1px solid #000000 !important;
    }

    .lockin-logo {
        color: #D9D9D9 !important;
        font-weight: 850 !important;
    }

    .lockin-topbar-label {
        color: #BFC3C8 !important;
    }

    .lockin-title,
    .lockin-hero-title,
    h1, h2, h3,
    .lockin-step-title {
        color: #000000 !important;
    }

    .lockin-subtitle,
    .lockin-step-help,
    .lockin-card-subtitle {
        color: #333333 !important;
    }

    /* Ice-blue fields */
    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div,
    div[data-baseweb="select"] > div {
        background: #EAF4FF !important;
        border: 1px solid #C7DCF3 !important;
    }

    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"] textarea,
    div[data-baseweb="select"] input {
        background: #EAF4FF !important;
        color: #000000 !important;
    }

    div[data-baseweb="input"] input::placeholder,
    div[data-baseweb="textarea"] textarea::placeholder {
        color: #68788A !important;
        opacity: 1 !important;
    }

    div[data-baseweb="input"] > div:focus-within,
    div[data-baseweb="textarea"] > div:focus-within,
    div[data-baseweb="select"] > div:focus-within {
        background: #EAF4FF !important;
        border-color: #8FB6DF !important;
        box-shadow: 0 0 0 3px rgba(143, 182, 223, 0.18) !important;
    }

    /* Same ice-blue surface for learning-flow box */
    .lockin-learning-note {
        background: #EAF4FF !important;
        border: 1px solid #C7DCF3 !important;
        color: #000000 !important;
    }

    /* Primary buttons */
    .stButton > button {
        background: #7EE2E6 !important;
        border-color: #7EE2E6 !important;
        color: #FFFFFF !important;
    }

    .stButton > button p,
    .stButton > button span {
        color: #111827 !important;
    }

    .stButton > button:hover {
        background: #69D6DA !important;
        border-color: #69D6DA !important;
        color: #111827 !important;
    }


    /* =====================================================
       FINAL START-SCREEN COLOR / HEADER STYLE
       ===================================================== */

    .lockin-wordmark {
        width: 100%;
        text-align: center;
        margin: 0 0 2.5rem 0;
        color: #D6D9DE !important;
        font-size: 1.45rem;
        line-height: 1;
        font-weight: 900;
        letter-spacing: 0.18em;
    }

    /* Keep field labels readable */
    label {
        color: #111827 !important;
        font-weight: 650 !important;
    }

    /* Ice-blue text fields and select fields */
    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div,
    div[data-baseweb="select"] > div {
        background: #EAF4FF !important;
        border: 1px solid #C9DDF2 !important;
        border-radius: 12px !important;
        box-shadow: none !important;
    }

    /* Entered text */
    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"] textarea {
        background: #EAF4FF !important;
        color: #B9C0C8 !important;
        -webkit-text-fill-color: #B9C0C8 !important;
    }

    /* Placeholder text */
    div[data-baseweb="input"] input::placeholder,
    div[data-baseweb="textarea"] textarea::placeholder {
        color: #AEB7C2 !important;
        opacity: 1 !important;
    }

    /* Selectbox selected value */
    div[data-baseweb="select"] * {
        color: #B9C0C8 !important;
    }

    div[data-baseweb="select"] input {
        background: #EAF4FF !important;
        color: #B9C0C8 !important;
        -webkit-text-fill-color: #B9C0C8 !important;
    }

    /* Focus state */
    div[data-baseweb="input"] > div:focus-within,
    div[data-baseweb="textarea"] > div:focus-within,
    div[data-baseweb="select"] > div:focus-within {
        background: #EAF4FF !important;
        border-color: #9DBEDC !important;
        box-shadow: 0 0 0 3px rgba(157, 190, 220, 0.18) !important;
    }

    /* Learning-flow box uses the same ice-blue */
    .lockin-learning-note {
        background: #EAF4FF !important;
        border: 1px solid #C9DDF2 !important;
        color: #B9C0C8 !important;
    }

    .lockin-learning-note strong {
        color: #9EA8B3 !important;
    }


    /* =====================================================
       FINAL LOCKIN START SCREEN COLORS
       ===================================================== */

    /* White page */
    .stApp {
        background: #FFFFFF !important;
    }

    .block-container {
        background: #FFFFFF !important;
    }

    /* LOCKIN wordmark */
    .lockin-wordmark {
        width: 100%;
        text-align: center;
        margin: 0 0 2.7rem 0;
        color: #4A4F57 !important;
        font-size: 2.05rem;
        line-height: 1;
        font-weight: 900;
        letter-spacing: 0.20em;
    }

    /* Main heading */
    .lockin-title,
    .lockin-hero-title {
        color: #000000 !important;
    }

    /* Supporting text */
    .lockin-subtitle {
        color: #222222 !important;
    }

    /* Section headings */
    .lockin-step-title,
    h2,
    h3 {
        color: #000000 !important;
    }

    /* Field labels */
    label {
        color: #000000 !important;
        font-weight: 650 !important;
    }

    /* =====================================================
       USER INPUT FIELDS — ICE BLUE
       ===================================================== */

    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div,
    div[data-baseweb="select"] > div {
        background: #97C1E6 !important;
        border: 1px solid #7FAED3 !important;
        border-radius: 12px !important;
        box-shadow: none !important;
    }

    /* Text entered by the user */
    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"] textarea {
        background: #97C1E6 !important;
        color: #20242A !important;
        -webkit-text-fill-color: #20242A !important;
    }

    /* Placeholder */
    div[data-baseweb="input"] input::placeholder,
    div[data-baseweb="textarea"] textarea::placeholder {
        color: #66727D !important;
        opacity: 1 !important;
    }

    /* Selectbox selected value */
    div[data-baseweb="select"] * {
        color: #20242A !important;
    }

    div[data-baseweb="select"] input {
        background: #97C1E6 !important;
        color: #20242A !important;
        -webkit-text-fill-color: #20242A !important;
    }

    /* Focus */
    div[data-baseweb="input"] > div:focus-within,
    div[data-baseweb="textarea"] > div:focus-within,
    div[data-baseweb="select"] > div:focus-within {
        background: #97C1E6 !important;
        border-color: #79BFE3 !important;
        box-shadow: 0 0 0 3px rgba(121, 191, 227, 0.18) !important;
    }

    /* Learning-flow box */
    .lockin-learning-note {
        background: #97C1E6 !important;
        border: 1px solid #7FAED3 !important;
        color: #20242A !important;
    }

    .lockin-learning-note strong {
        color: #000000 !important;
    }


    /* 15px supporting text */
    .lockin-subtitle {
        font-size: 15px !important;
        line-height: 1.6 !important;
    }

    .lockin-step-help {
        font-size: 15px !important;
        line-height: 1.6 !important;
    }


    /* Exact 15px supporting text */
    .lockin-description-15 {
        color: #222222 !important;
        font-size: 15px !important;
        line-height: 1.6 !important;
        margin: 0.45rem 0 1.5rem 0;
    }

    .lockin-step-description-15 {
        color: #333333 !important;
        font-size: 15px !important;
        line-height: 1.6 !important;
        margin: 0.35rem 0 1rem 0;
    }

    /* Input fields */
    div[data-testid="stTextInput"] div[data-baseweb="input"] > div,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background-color: #97C1E6 !important;
        border: 1px solid #7FAED3 !important;
        border-radius: 12px !important;
    }

    div[data-testid="stTextInput"] input {
        background-color: #97C1E6 !important;
        color: #20242A !important;
        -webkit-text-fill-color: #20242A !important;
        font-size: 15px !important;
    }

    div[data-testid="stTextInput"] input::placeholder {
        color: #687784 !important;
        opacity: 1 !important;
    }

    div[data-testid="stSelectbox"] [role="combobox"] {
        background-color: #97C1E6 !important;
        color: #20242A !important;
    }

    div[data-testid="stSelectbox"] span {
        color: #20242A !important;
    }

    div[data-testid="stTextInput"] label,
    div[data-testid="stSelectbox"] label {
        color: #000000 !important;
        font-size: 15px !important;
        font-weight: 650 !important;
    }



    /* =====================================================
       GLOBAL LOCKIN UI COLORS
       Applies to Tutor, Quiz, Remediation and Report screens
       ===================================================== */

    /* ---------- ALL STREAMLIT BUTTONS ---------- */

    .stButton > button {
        background: #7EE2E6 !important;
        border: 1px solid #69D6DA !important;
        color: #111827 !important;
        font-weight: 750 !important;
        box-shadow: none !important;
    }

    .stButton > button p,
    .stButton > button span {
        color: #111827 !important;
    }

    .stButton > button:hover {
        background: #69D6DA !important;
        border-color: #69D6DA !important;
        color: #111827 !important;
        box-shadow: 0 5px 14px rgba(105, 214, 218, 0.22) !important;
    }

    .stButton > button:active {
        background: #58C7CC !important;
        border-color: #58C7CC !important;
    }

    /* ---------- ALL TEXT INPUTS ---------- */

    div[data-testid="stTextInput"] div[data-baseweb="input"] > div,
    div[data-testid="stTextArea"] div[data-baseweb="textarea"] > div {
        background: #97C1E6 !important;
        border: 1px solid #7FAED3 !important;
        border-radius: 12px !important;
    }

    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea {
        background: #97C1E6 !important;
        color: #20242A !important;
        -webkit-text-fill-color: #20242A !important;
    }

    div[data-testid="stTextInput"] input::placeholder,
    div[data-testid="stTextArea"] textarea::placeholder {
        color: #5F6F7D !important;
        opacity: 1 !important;
    }

    /* ---------- ALL SELECTBOXES ---------- */

    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background: #97C1E6 !important;
        border: 1px solid #7FAED3 !important;
        border-radius: 12px !important;
    }

    div[data-testid="stSelectbox"] [role="combobox"],
    div[data-testid="stSelectbox"] input {
        background: #97C1E6 !important;
        color: #20242A !important;
        -webkit-text-fill-color: #20242A !important;
    }

    div[data-testid="stSelectbox"] span {
        color: #20242A !important;
    }

    /* ---------- FOCUS ---------- */

    div[data-testid="stTextInput"] div[data-baseweb="input"] > div:focus-within,
    div[data-testid="stTextArea"] div[data-baseweb="textarea"] > div:focus-within,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within {
        background: #97C1E6 !important;
        border-color: #679FCB !important;
        box-shadow: 0 0 0 3px rgba(103, 159, 203, 0.16) !important;
    }



    /* =====================================================
       FINAL LOCKIN UI OVERRIDES
       UI ONLY — NO WORKFLOW CHANGES
       ===================================================== */

    /* -----------------------------------------------------
       ALL INPUT FIELDS
       Normal + Hover + Focus = SAME #97C1E6
       ----------------------------------------------------- */

    /* Text inputs */
    div[data-testid="stTextInput"] div[data-baseweb="input"] > div,
    div[data-testid="stTextInput"] div[data-baseweb="input"] > div:hover,
    div[data-testid="stTextInput"] div[data-baseweb="input"] > div:focus-within {
        background-color: #97C1E6 !important;
        border-color: #7FAED3 !important;
        box-shadow: none !important;
    }

    div[data-testid="stTextInput"] input,
    div[data-testid="stTextInput"] input:hover,
    div[data-testid="stTextInput"] input:focus {
        background-color: #97C1E6 !important;
        color: #20242A !important;
        -webkit-text-fill-color: #20242A !important;
        caret-color: #20242A !important;
    }

    /* Selectbox */
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within {
        background-color: #97C1E6 !important;
        border-color: #7FAED3 !important;
        box-shadow: none !important;
    }

    div[data-testid="stSelectbox"] [role="combobox"],
    div[data-testid="stSelectbox"] [role="combobox"]:hover,
    div[data-testid="stSelectbox"] [role="combobox"]:focus {
        background-color: #97C1E6 !important;
        color: #20242A !important;
    }

    div[data-testid="stSelectbox"] input,
    div[data-testid="stSelectbox"] input:focus {
        background-color: #97C1E6 !important;
        color: #20242A !important;
        -webkit-text-fill-color: #20242A !important;
    }

    div[data-testid="stSelectbox"] span {
        color: #20242A !important;
    }

    /* Text area, for Tutor screen if used */
    div[data-testid="stTextArea"] div[data-baseweb="textarea"] > div,
    div[data-testid="stTextArea"] div[data-baseweb="textarea"] > div:hover,
    div[data-testid="stTextArea"] div[data-baseweb="textarea"] > div:focus-within {
        background-color: #97C1E6 !important;
        border-color: #7FAED3 !important;
        box-shadow: none !important;
    }

    div[data-testid="stTextArea"] textarea,
    div[data-testid="stTextArea"] textarea:hover,
    div[data-testid="stTextArea"] textarea:focus {
        background-color: #97C1E6 !important;
        color: #20242A !important;
        -webkit-text-fill-color: #20242A !important;
        caret-color: #20242A !important;
    }

    /* -----------------------------------------------------
       ALL BUTTONS
       Safety screen + Tutor + Quiz + Report
       ----------------------------------------------------- */

    .stButton > button,
    .stButton > button:hover,
    .stButton > button:focus,
    .stButton > button:active {
        background-color: #7EE2E6 !important;
        border: 1px solid #69D6DA !important;
        color: #111827 !important;
        box-shadow: none !important;
    }

    .stButton > button p,
    .stButton > button span,
    .stButton > button div {
        color: #111827 !important;
    }

    .stButton > button:hover {
        box-shadow: 0 5px 14px rgba(105, 214, 218, 0.22) !important;
    }

    /* -----------------------------------------------------
       FORM SUBMIT BUTTONS
       Covers quiz Submit Stage as well.
       ----------------------------------------------------- */

    div[data-testid="stFormSubmitButton"] > button,
    div[data-testid="stFormSubmitButton"] > button:hover,
    div[data-testid="stFormSubmitButton"] > button:focus,
    div[data-testid="stFormSubmitButton"] > button:active {
        background-color: #7EE2E6 !important;
        border: 1px solid #69D6DA !important;
        color: #111827 !important;
        box-shadow: none !important;
    }

    div[data-testid="stFormSubmitButton"] > button p,
    div[data-testid="stFormSubmitButton"] > button span {
        color: #111827 !important;
    }



    /* =====================================================
       FORCE INPUT BACKGROUND IN EVERY STATE
       ===================================================== */

    /* TextInput outer layers */
    div[data-testid="stTextInput"] div[data-baseweb="base-input"],
    div[data-testid="stTextInput"] div[data-baseweb="input"],
    div[data-testid="stTextInput"] div[data-baseweb="input"] > div {
        background-color: #97C1E6 !important;
        background: #97C1E6 !important;
    }

    /* Actual HTML input */
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextInput"] input:hover,
    div[data-testid="stTextInput"] input:focus,
    div[data-testid="stTextInput"] input:active {
        background-color: #97C1E6 !important;
        background: #97C1E6 !important;
        color: #20242A !important;
        -webkit-text-fill-color: #20242A !important;
        caret-color: #20242A !important;
        box-shadow: none !important;
        outline: none !important;
    }

    /* Chrome autofill can force a different color */
    div[data-testid="stTextInput"] input:-webkit-autofill,
    div[data-testid="stTextInput"] input:-webkit-autofill:hover,
    div[data-testid="stTextInput"] input:-webkit-autofill:focus,
    div[data-testid="stTextInput"] input:-webkit-autofill:active {
        -webkit-box-shadow: 0 0 0 1000px #97C1E6 inset !important;
        box-shadow: 0 0 0 1000px #97C1E6 inset !important;
        -webkit-text-fill-color: #20242A !important;
        background-color: #97C1E6 !important;
    }

    /* Selectbox */
    div[data-testid="stSelectbox"] div[data-baseweb="select"],
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    div[data-testid="stSelectbox"] div[data-baseweb="base-input"] {
        background-color: #97C1E6 !important;
        background: #97C1E6 !important;
    }

    div[data-testid="stSelectbox"] input,
    div[data-testid="stSelectbox"] input:focus {
        background-color: #97C1E6 !important;
        background: #97C1E6 !important;
        color: #20242A !important;
        -webkit-text-fill-color: #20242A !important;
        box-shadow: none !important;
    }

    div[data-testid="stSelectbox"] [role="combobox"] {
        background-color: #97C1E6 !important;
        background: #97C1E6 !important;
        color: #20242A !important;
    }



    /* Safety / primary action buttons */
    .stButton > button {
        background-color: #7EE2E6 !important;
        background: #7EE2E6 !important;
        border-color: #69D6DA !important;
        color: #111827 !important;
    }

    .stButton > button p,
    .stButton > button span,
    .stButton > button div {
        color: #111827 !important;
    }

    .stButton > button:hover,
    .stButton > button:focus,
    .stButton > button:active {
        background-color: #69D6DA !important;
        background: #69D6DA !important;
        border-color: #58C7CC !important;
        color: #111827 !important;
    }



    /* =====================================================
       EXACT STREAMLIT BUTTON TARGET
       ===================================================== */

    div[data-testid="stButton"] > button {
        background-color: #7EE2E6 !important;
        background: #7EE2E6 !important;
        border: 1px solid #69D6DA !important;
        color: #111827 !important;
    }

    div[data-testid="stButton"] > button > div {
        color: #111827 !important;
    }

    div[data-testid="stButton"] > button p {
        color: #111827 !important;
    }

    div[data-testid="stButton"] > button:hover {
        background-color: #69D6DA !important;
        background: #69D6DA !important;
        border-color: #58C7CC !important;
        color: #111827 !important;
    }



    /* =====================================================
       BEFORE WE START — OKAY BUTTON
       ===================================================== */

    div[data-testid="stButton"] button[data-testid="baseButton-secondary"],
    div[data-testid="stButton"] button[data-testid="baseButton-primary"] {
        background-color: #7EE2E6 !important;
        background: #7EE2E6 !important;
        border-color: #69D6DA !important;
        color: #111827 !important;
    }

    div[data-testid="stButton"] button[data-testid="baseButton-secondary"] p,
    div[data-testid="stButton"] button[data-testid="baseButton-secondary"] span,
    div[data-testid="stButton"] button[data-testid="baseButton-primary"] p,
    div[data-testid="stButton"] button[data-testid="baseButton-primary"] span {
        color: #111827 !important;
    }

    div[data-testid="stButton"] button[data-testid="baseButton-secondary"]:hover,
    div[data-testid="stButton"] button[data-testid="baseButton-primary"]:hover {
        background-color: #69D6DA !important;
        background: #69D6DA !important;
        border-color: #58C7CC !important;
        color: #111827 !important;
    }

</style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="lockin-wordmark">LOCKIN</div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='lockin-hero-title'>Let's set up your learning session.</div>",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="lockin-description-15">'
    "Give LockIn a little context so it can teach, practise, "
    "and assess the topic at the right level for you."
    "</div>",
    unsafe_allow_html=True,
)

st.markdown(
    "### 01 · Your level"
)

st.markdown(
    '<div class="lockin-step-description-15">'
    "Select your current class so the explanations and questions "
    "match your level."
    "</div>",
    unsafe_allow_html=True,
)

student_class = st.selectbox(
    "Class",
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

st.markdown("### 02 · Your learning context")

st.markdown(
    '<div class="lockin-step-description-15">'
    "This helps LockIn use the right curriculum context for your lesson."
    "</div>",
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)

with col1:
    board = st.text_input(
        "Education Board",
        placeholder="e.g. Federal Board",
    )

with col2:
    subject = st.text_input(
        "Subject",
        placeholder="e.g. Mathematics",
    )

st.markdown("### 03 · What do you want to learn?")

st.markdown(
    '<div class="lockin-step-description-15">'
    "Enter one focused topic. You can start simple; "
    "LockIn will adapt the practice later."
    "</div>",
    unsafe_allow_html=True,
)

topic = st.text_input(
    "Topic",
    placeholder="e.g. Fractions",
)

st.markdown(
    """
    <div class="lockin-learning-note">
        Your session will follow:
        <strong>Learn → Practise → Assess</strong>.
    </div>
    """,
    unsafe_allow_html=True,
)

if st.button(
    "Start Learning  →",
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

st.caption(
    "Personalized  •  Adaptive  •  Progress-based"
)
