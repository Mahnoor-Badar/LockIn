# LockIn Repository // this line must be removed afer writing this document.
🔒 LockIn
Adaptive AI-Powered Urdu–English Learning Assistant
 *"Teach in the language and at the level the learner understands."*
LockIn is an adaptive AI-powered learning web app that helps students learn a topic through clear explanations, voice features, and a real-time adaptive quiz. Instead of assuming a student understood, LockIn checks whether they actually did.

📑 Table of Contents
Problem Statement
Target Users
How It Works
Flow Diagram
Features
Adaptive Quiz Logic
Tech Stack
Architecture
Data Model
UI / Design
Getting Started
Security
MVP Scope
Business Model
Future Roadmap
Team

❗ Problem Statement
Language barrier: students often understand concepts better through mixed Urdu–English.
Assumed understanding: AI may assume a student understood a topic without actually checking.
No adaptive help: students need a different explanation when a basic question exposes a knowledge gap.
Cluttered tools: learners need a clean and professional learning interface.
🎯 Target Users
Students who need simpler explanations, Urdu–English communication, relatable analogies, and a quick assessment of their actual understanding.

🔄 How It Works
The learning experience follows a simple loop:
Explain → Confirm Understanding → Quiz → Evaluate → Re-teach or Complete
The student selects/opens a topic.
Gemini AI explains the topic using text + TTS audio.
The student clicks or says "OK, I got it" (button or STT voice input).
The Quiz Engine generates 6 MCQs: 2 Easy → 2 Medium → 2 Hard.
Questions are evaluated step-by-step.
If an Easy question is failed → the quiz stops → the topic is re-explained with a new nature/animal analogy → the student retries the quiz.
If all 6 questions are cleared → "You got it! Best of Luck 🎉"

🗺️ Flow Diagram
flowchart TD
    Student opens LockIn
                 |
                 v
          Select a topic
                 |
                 v
   Gemini explains the topic (Text + Voice)
                 |
                 v
   Student says "OK, I got it"? (Button or Voice)
         |                  |
        No                 Yes
         |                  |
         +--> back to       v
              explanation  Quiz: 6 MCQs
                           (2 Easy, 2 Medium, 2 Hard)
                                |
                                v
                          Easy questions
                                |
                                v
                      Easy question failed?
                       |                 |
                      Yes                No
                       |                 |
                       v                 v
                  Stop quiz        Medium questions
                       |                 |
                       v                 v
          Re-teach with a NEW      Hard questions
          nature / animal                |
          analogy                        v
                       |          You got it! Best of Luck
                       v
                  Retry quiz
                  (back to Quiz)


✨ Features
ID	Area	Description
FR-01	Topic Selection	Learner selects the topic they want to learn.
FR-02	AI Explanation	Gemini explains in an understandable Urdu–English style.
FR-03	Text + TTS	Explanation is available as readable text and spoken audio.
FR-04	Understanding Confirmation	"OK, I got it" button or STT voice input.
FR-05	Quiz Generation	6 MCQs: 2 Easy, 2 Medium, 2 Hard.
FR-06	Step-by-Step Evaluation	Questions are evaluated progressively.
FR-07	Easy-Level Gate	Failing an Easy question stops the quiz and triggers re-teaching.
FR-08	Adaptive Re-teaching	New nature/animal or relatable analogy.
FR-09	Quiz Retry	Learner can retry the quiz after re-teaching.
FR-10	Completion Feedback	Success message after clearing all 6 questions.
FR-11	Progress / Data	Learner/session/quiz info stored in Firebase where required.
FR-12	Guardrails	AI responses stay educational, safe, and age-appropriate.

🧠 Adaptive Quiz Logic

Start quiz → Easy Q1/Q2 → Medium Q1/Q2 → Hard Q1/Q2

Easy question failed?  → stop progression immediately
                       → generate a different explanation (new nature/animal analogy)
                       → restart/retry the quiz

All 6 cleared?         → "You got it! Best of Luck 🎉"

🛠️ Tech Stack
Layer	Technology
Frontend	Streamlit
Backend	Firebase
Database	Firebase
LLM	Google Gemini
Voice	Gemini-based voice capabilities / STT + TTS
Platform	Web
Version Control	GitHub
🏗️ Architecture

Student → Streamlit Web UI → Gemini → Explanation / Voice
        → Understanding Confirmation → Quiz Engine → Evaluation
        → Firebase (where required) → Progress / Re-teach

🗄️ Data Model
Learner/session information
Selected topic
Generated quiz questions and difficulty levels
Student answers and quiz outcome
Concepts requiring reinforcement
Progress information
🎨 UI / Design
Clean and professional interface
Primary palette: white, light purple, and black
Clear topic selection and learning controls
Prominent audio/voice controls
Simple quiz layout with clear answer options
Immediate and understandable feedback

🔐 Security
API keys and credentials must never be committed to GitHub.
Use environment variables or secure configuration for secrets.
Handle Gemini/API failures gracefully.
Protect learner/session data stored in Firebase.
The core text-learning path stays usable if voice fails.

✅ MVP Scope
 Working Streamlit web interface
 Gemini-powered topic explanation
 Text + TTS learning experience
 STT/button-based understanding confirmation
 Six-question quiz (2 Easy, 2 Medium, 2 Hard)
 Easy-level failure gate with adaptive re-teaching
 New nature/animal analogy after an Easy-level failure
 Quiz retry after re-teaching
 Success message after clearing all 6 questions
 Firebase integration where required
 Clean GitHub repository and web deployment


💰 Business Model
The proposed model is freemium + monthly subscription for students (B2C). Pricing below is a draft and will be confirmed after the team reviews development and operating costs.
Cost factors: Gemini/API usage · Firebase database/storage · hosting/deployment · voice processing · maintenance and scaling.
Proposed Subscription Tiers
Tier	Price	Total Cost	Net Profit	Margin
Free (Freemium Acquisition)	Free	–	–	–
Standard Student Pass	599 PKR / month	~479 PKR / month	~120 PKR / student / month	~20%
Pro / Unlimited Pass (recommended for heavy users)	899 PKR / month	~479 PKR / month	~420 PKR / student / month	~47%
Free Tier limit: 1 topic per day (short 2-minute voice explanation + 3 MCQs).
Goal: convert free users to paid subscribers without eating into the API budget.
Monthly Revenue Projections (B2C)
Assuming an average subscription price of 750 PKR / month per active subscriber:
Active Paid Subscribers	Total Monthly Revenue	Operational Cost (~479 PKR/user)	Net Monthly Profit
100 Students	75,000 PKR	47,900 PKR	27,100 PKR / month
500 Students	375,000 PKR	239,500 PKR	135,500 PKR / month
1,000 Students	750,000 PKR	479,000 PKR	271,000 PKR / month

🔮 Future Roadmap
Personalized study plans
Teacher/parent dashboards
Long-term learning analytics
More subjects and regional languages
Gamification and learning streaks
Mobile-first experience

👥 Team
Javaria Murtaza- Frontend and Backend
Umaima Rashid- PRD, Slides and Documentation support
Muhammad Junaid Murtaza- Pricing, Business model and Tester
Mahnoor(Lead) -AI/ LLM Integration, Setup, App Deployment and Presentation video
