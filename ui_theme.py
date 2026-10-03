import streamlit as st


def apply_lockin_theme():
    st.markdown(
        """
        <style>
        /* =====================================================
           LOCKIN DESIGN SYSTEM
           UI ONLY — NO APPLICATION LOGIC
           ===================================================== */

        :root {
            --lockin-navy: #18243A;
            --lockin-blue: #3B5CCC;
            --lockin-blue-dark: #3049A8;
            --lockin-bg: #F5F7FB;
            --lockin-card: #FFFFFF;
            --lockin-text: #18243A;
            --lockin-muted: #687386;
            --lockin-border: #E3E8F0;
            --lockin-success: #2F8F6B;
        }

        /* Page background */
        .stApp {
            background: var(--lockin-bg);
            color: var(--lockin-text);
        }

        /* Hide Streamlit default chrome */
        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }

        header {
            background: transparent !important;
        }

        /* Main content width */
        .block-container {
            max-width: 980px;
            padding-top: 3rem;
            padding-bottom: 4rem;
        }

        /* General typography */
        html, body, [class*="css"] {
            font-family:
                Inter,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;
        }

        h1, h2, h3 {
            color: var(--lockin-navy) !important;
            letter-spacing: -0.02em;
        }

        p {
            color: var(--lockin-muted);
        }

        /* LockIn hero */
        .lockin-brand {
            text-align: center;
            margin-bottom: 0.35rem;
        }

        .lockin-brand-name {
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.18em;
            color: var(--lockin-blue);
            text-transform: uppercase;
        }

        .lockin-hero-title {
            text-align: center;
            font-size: 2.55rem;
            line-height: 1.1;
            font-weight: 750;
            color: var(--lockin-navy);
            margin: 0.35rem 0 0.65rem 0;
        }

        .lockin-hero-subtitle {
            max-width: 620px;
            margin: 0 auto 2rem auto;
            text-align: center;
            font-size: 1rem;
            line-height: 1.6;
            color: var(--lockin-muted);
        }

        /* Start card */
        .lockin-card {
            background: var(--lockin-card);
            border: 1px solid var(--lockin-border);
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 10px 30px rgba(24, 36, 58, 0.06);
            margin-bottom: 1.5rem;
        }

        .lockin-card-title {
            font-size: 1.2rem;
            font-weight: 700;
            color: var(--lockin-navy);
            margin-bottom: 0.25rem;
        }

        .lockin-card-subtitle {
            font-size: 0.92rem;
            color: var(--lockin-muted);
            margin-bottom: 1.2rem;
        }

        /* Inputs */
        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div {
            background: #FFFFFF !important;
            border: 1px solid var(--lockin-border) !important;
            border-radius: 11px !important;
            min-height: 46px;
        }

        div[data-baseweb="input"] > div:focus-within,
        div[data-baseweb="select"] > div:focus-within {
            border-color: var(--lockin-blue) !important;
            box-shadow: 0 0 0 2px rgba(59, 92, 204, 0.10) !important;
        }

        label {
            color: var(--lockin-navy) !important;
            font-weight: 600 !important;
        }

        /* Buttons */
        .stButton > button {
            width: 100%;
            min-height: 48px;
            border-radius: 11px;
            border: 0;
            background: var(--lockin-blue);
            color: white;
            font-weight: 700;
            font-size: 0.96rem;
            transition: 0.18s ease;
        }

        .stButton > button:hover {
            background: var(--lockin-blue-dark);
            border: 0;
            color: white;
            transform: translateY(-1px);
            box-shadow: 0 7px 18px rgba(59, 92, 204, 0.20);
        }

        /* Small informational strip */
        .lockin-trust-strip {
            display: flex;
            justify-content: center;
            gap: 2rem;
            flex-wrap: wrap;
            margin-top: 1rem;
            color: var(--lockin-muted);
            font-size: 0.82rem;
        }

        .lockin-trust-item {
            white-space: nowrap;
        }

        /* Divider */
        hr {
            border: 0;
            border-top: 1px solid var(--lockin-border);
            margin: 1.6rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
