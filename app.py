import streamlit as st
import time
import os
from datetime import datetime
import plotly.graph_objects as go

# Import our backend files
import database as db
import pdf_utils as pdf
import agents

# Set page configuration
st.set_page_config(
    page_title="GET MOCKED!!! (A.T)",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
db.init_db()


# ==========================================
# CUSTOM CSS FOR PREMIUM LOOK (GLASSMORPHISM, FONTS, CARDS)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    /* Main container background gradient */
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #161a24 100%);
        color: #e2e8f0;
    }
    
    /* Premium Cards styling */
    .premium-card, div[data-testid="stVerticalBlockBorder"] {
        background: rgba(30, 41, 59, 0.45) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        margin-bottom: 20px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
        transition: transform 0.2s ease, border-color 0.2s ease !important;
    }
    .premium-card:hover, div[data-testid="stVerticalBlockBorder"]:hover {
        border-color: rgba(99, 102, 241, 0.4) !important;
        transform: translateY(-2px) !important;
    }
    
    /* Status indicators */
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 8px;
    }
    .status-active {
        background-color: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .status-inactive {
        background-color: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    /* Gradient headers */
    .gradient-text {
        background: linear-gradient(90deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    
    /* Input adjustments */
    div[data-baseweb="input"] {
        background-color: rgba(15, 23, 42, 0.6) !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Custom Alert Info */
    .info-box {
        background: rgba(59, 130, 246, 0.1);
        border-left: 4px solid #3b82f6;
        padding: 16px;
        border-radius: 8px;
        margin: 15px 0;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"
if "saved_topics" not in st.session_state:
    st.session_state.saved_topics = []

if st.session_state.authenticated and st.session_state.user_info and not st.session_state.saved_topics:
    st.session_state.saved_topics = db.get_user_topics(st.session_state.user_info['user_id'])

# Interview State
if "interview_active" not in st.session_state:
    st.session_state.interview_active = False
if "questions" not in st.session_state:
    st.session_state.questions = []
if "current_q_index" not in st.session_state:
    st.session_state.current_q_index = 0
if "interview_id" not in st.session_state:
    st.session_state.interview_id = None
if "answers_logged" not in st.session_state:
    st.session_state.answers_logged = {}
if "q_start_time" not in st.session_state:
    st.session_state.q_start_time = None
if "follow_up_questions" not in st.session_state:
    st.session_state.follow_up_questions = []
if "follow_up_answers" not in st.session_state:
    st.session_state.follow_up_answers = {}
if "last_feedback" not in st.session_state:
    st.session_state.last_feedback = None

# Mock Test State
if "test_active" not in st.session_state:
    st.session_state.test_active = False
if "test_finished" not in st.session_state:
    st.session_state.test_finished = False
if "test_questions" not in st.session_state:
    st.session_state.test_questions = []
if "test_answers" not in st.session_state:
    st.session_state.test_answers = {}
if "test_score" not in st.session_state:
    st.session_state.test_score = None
if "test_explanations" not in st.session_state:
    st.session_state.test_explanations = {}
if "test_details" not in st.session_state:
    st.session_state.test_details = []
if "test_correct_cnt" not in st.session_state:
    st.session_state.test_correct_cnt = 0

# ==========================================
# AUTHENTICATION FLOW
# ==========================================
def render_auth():
    st.markdown("""
    <h1 style='text-align: center; margin-top: 40px; font-family: "Outfit", sans-serif; font-size: 3.8rem; font-weight: 900; letter-spacing: -2px; text-transform: uppercase; background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-shadow: 0 0 30px rgba(99, 102, 241, 0.3); margin-bottom: 5px;'>GET MOCKED!!! <span style='font-size: 70%; position: relative; top: -5px; font-weight: 800; background: linear-gradient(135deg, #a855f7 0%, #ec4899 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-left: 8px; letter-spacing: 0px;'>(A.T)</span></h1>
    <p style='text-align: center; color: #94a3b8; font-size: 1.1rem; margin-bottom: 40px; font-weight: 500;'>Elevate your Machine Learning interview readiness with our multi-agent AI system.</p>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        with st.container(border=True):
            if st.session_state.auth_mode == "login":
                st.subheader("Login to Your Console")
                email = st.text_input("Email Address", key="login_email")
                secret_key = st.text_input("Secret Key", type="password", key="login_key")
                
                if st.button("Log In", use_container_width=True, type="primary"):
                    user = db.login_user(email, secret_key)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user_info = user
                        st.session_state.saved_topics = db.get_user_topics(user['user_id'])
                        st.success(f"Welcome back, {user['name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid email or secret key. Please try again.")
                
                st.markdown("<hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
                col_l, col_r = st.columns(2)
                with col_l:
                    if st.button("Need an Account?", use_container_width=True):
                        st.session_state.auth_mode = "signup"
                        st.rerun()
                with col_r:
                    if st.button("Forgot Secret Key?", use_container_width=True):
                        st.session_state.auth_mode = "forgot"
                        st.rerun()
                        
            elif st.session_state.auth_mode == "signup":
                st.subheader("Create a New Account")
                name = st.text_input("Full Name", key="signup_name")
                email = st.text_input("Email Address", key="signup_email")
                mobile = st.text_input("Mobile Number", key="signup_mobile")
                secret_key = st.text_input("Secret Key (case-insensitive key used for recovery/login)", type="password", key="signup_key")
                
                if st.button("Sign Up", use_container_width=True, type="primary"):
                    if not name or not email or not mobile or not secret_key:
                        st.warning("Please fill in all details.")
                    else:
                        try:
                            user_id = db.register_user(name, email, mobile, secret_key)
                            st.success("Registration successful! You can now log in.")
                            st.session_state.auth_mode = "login"
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))
                            
                st.markdown("<hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
                if st.button("Already have an account? Log In", use_container_width=True):
                    st.session_state.auth_mode = "login"
                    st.rerun()
                    
            elif st.session_state.auth_mode == "forgot":
                st.subheader("Reset Secret Key")
                email = st.text_input("Registered Email Address", key="reset_email")
                mobile = st.text_input("Registered Mobile Number", key="reset_mobile")
                new_key = st.text_input("New Secret Key", type="password", key="reset_key")
                
                if st.button("Reset Secret Key", use_container_width=True, type="primary"):
                    if not email or not mobile or not new_key:
                        st.warning("Please fill in all details.")
                    else:
                        success = db.reset_secret_key(email, mobile, new_key)
                        if success:
                            st.success("Secret key reset successfully! Please log in.")
                            st.session_state.auth_mode = "login"
                            st.rerun()
                        else:
                            st.error("No account matches that email and mobile number combination.")
                            
                st.markdown("<hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
                if st.button("Back to Login", use_container_width=True):
                    st.session_state.auth_mode = "login"
                    st.rerun()

# ==========================================
# CORE SIDEBAR SETTINGS
# ==========================================
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style='padding: 10px 0 20px 0;'>
            <h2 style='font-family: "Outfit", sans-serif; font-size: 2.2rem; font-weight: 900; letter-spacing: -1.5px; text-transform: uppercase; background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; padding: 0;'>GET MOCKED!!! <span style='font-size: 65%; position: relative; top: -3px; font-weight: 800; background: linear-gradient(135deg, #a855f7 0%, #ec4899 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-left: 5px; letter-spacing: 0px;'>(A.T)</span></h2>
            <span style='font-size: 0.85rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 2px; font-weight: 600;'>Agent Console</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Glassmorphic user card
        st.markdown(f"""
        <div style='background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 15px; margin-bottom: 20px; box-shadow: inset 0 1px 1px rgba(255,255,255,0.05);'>
            <div style='font-size: 0.8rem; color: #8a99ad; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;'>Logged in as</div>
            <div style='font-size: 1.35rem; font-weight: 700; color: #ffffff; line-height: 1.2; font-family: "Outfit", sans-serif;'>{st.session_state.user_info['name']}</div>
            <hr style='margin: 10px 0; border-color: rgba(255,255,255,0.05);'>
            <div style='display: flex; align-items: center; margin-bottom: 8px; font-size: 0.9rem; color: #cbd5e1;'>
                <span style='margin-right: 8px; font-size: 1.1rem;'>📧</span>
                <span style='word-break: break-all;'>{st.session_state.user_info['email']}</span>
            </div>
            <div style='display: flex; align-items: center; font-size: 0.9rem; color: #cbd5e1;'>
                <span style='margin-right: 8px; font-size: 1.1rem;'>📞</span>
                <span>{st.session_state.user_info['mobile']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
        
        if st.button("Log Out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_info = None
            st.rerun()

# ==========================================
# PAGE 1: USER DASHBOARD
# ==========================================
def render_dashboard():
    st.markdown("## 📊 Performance Dashboard")
    st.write("Track your progress across Mock Interviews, Resume Rounds, and MCQ Tests.")
    
    user_id = st.session_state.user_info['user_id']
    
    # Get Resume Efficiency metric
    resume_efficiency = db.get_resume_efficiency(user_id)
    
    # Retrieve detailed histories
    interview_history = db.get_detailed_interview_history(user_id)
    test_history = db.get_detailed_test_history(user_id)
    
    # 1. Summary Metric Cards
    m1, m2 = st.columns(2)
    with m1:
        with st.container(border=True):
            st.metric(label="📄 Resume Efficiency Score", value=f"{resume_efficiency}%")
            st.markdown("<div style='text-align: center;'><span style='font-size:0.8rem; color:#94a3b8;'>Based on average Resume Round interview scores</span></div>", unsafe_allow_html=True)
    with m2:
        with st.container(border=True):
            # Average mock test score
            if test_history:
                avg_test_score = int(round(sum([float(t['score']) for t in test_history]) / len(test_history) * 100))
            else:
                avg_test_score = 0
            st.metric(label="📝 Avg Mock Test Accuracy", value=f"{avg_test_score}%")
            st.markdown("<div style='text-align: center;'><span style='font-size:0.8rem; color:#94a3b8;'>Based on all completed multiple-choice tests</span></div>", unsafe_allow_html=True)
        
    col_tables, col_report = st.columns([2, 1])
    
    with col_tables:
        with st.container(border=True):
            st.subheader("🎤 Interview & Resume Round Logs")
            if not interview_history:
                st.info("No mock interviews completed yet.")
            else:
                import pandas as pd
                # Format history rows
                rows = []
                for item in interview_history:
                    t_taken_display = ""
                    if item['avg_time_taken'] is not None:
                        t_val = int(item['avg_time_taken'])
                        t_m = t_val // 60
                        t_s = t_val % 60
                        t_taken_display = f"{t_m}m {t_s}s" if t_m > 0 else f"{t_s}s"
                    
                    rows.append({
                        "Date & Time": item['date'],
                        "Topic / Round": item['topic'],
                        "Difficulty": item['difficulty'],
                        "Questions": item['total_questions'],
                        "Avg Duration": t_taken_display,
                        "Overall Score": f"{item['overall_score']}/10"
                    })
                df_int = pd.DataFrame(rows)
                st.dataframe(df_int, use_container_width=True, hide_index=True)
        
        with st.container(border=True):
            st.subheader("📝 MCQ Mock Test Logs")
            if not test_history:
                st.info("No mock tests logged yet.")
            else:
                import pandas as pd
                rows = []
                for item in test_history:
                    rows.append({
                        "Date & Time": item['date'],
                        "Topic / Source": item['topic_or_source'],
                        "Difficulty": item.get('difficulty', 'Medium'),
                        "Total Questions": item['question_count'],
                        "Accuracy Score": f"{int(round(float(item['score']) * 100))}%"
                    })
                df_tests = pd.DataFrame(rows)
                st.dataframe(df_tests, use_container_width=True, hide_index=True)

    with col_report:
        with st.container(border=True):
            st.subheader("📈 Dynamic Topic Progress Report")
            topic_report = db.get_topic_progress_report(user_id)
            if not topic_report:
                st.info("Complete mock tests or interviews to generate topic performance reports.")
            else:
                for item in topic_report:
                    st.markdown(f"<div style='margin-bottom:12px;'><b>{item['topic']}</b>", unsafe_allow_html=True)
                    pct = item['percentage']
                    # Determine progress bar color/style based on score
                    if pct >= 80:
                        bar_color = "linear-gradient(90deg, #10b981, #34d399)" # green
                    elif pct >= 60:
                        bar_color = "linear-gradient(90deg, #6366f1, #a855f7)" # indigo/purple
                    else:
                        bar_color = "linear-gradient(90deg, #ef4444, #f87171)" # red
                        
                    st.markdown(f"""
                    <div style="background-color: rgba(255,255,255,0.05); border-radius: 9999px; height: 16px; width: 100%; position: relative; border: 1px solid rgba(255,255,255,0.08); overflow: hidden;">
                        <div style="background: {bar_color}; width: {pct}%; height: 100%; border-radius: 9999px; transition: width 0.3s ease;"></div>
                    </div>
                    <div style="text-align: right; font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">{pct}% Accuracy</div>
                    """, unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# PAGE 2: MOCK INTERVIEW ROOM
# ==========================================
def render_interview_room():
    st.markdown("## 🎤 AI Mock Interview Room")
    
    if "ingested_pdf_text" not in st.session_state:
        st.session_state.ingested_pdf_text = ""
    if "ingested_pdf_name" not in st.session_state:
        st.session_state.ingested_pdf_name = ""
        
    if not st.session_state.interview_active:
        notification_msg = st.session_state.get("topics_saved_notification")
        if notification_msg:
            st.success(notification_msg)
            st.session_state.topics_saved_notification = None
            
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            with st.container(border=True):
                st.subheader("1. General Setup")
                
                predefined_topics = ["Supervised Learning", "Unsupervised Learning", "Deep Learning / Neural Networks", 
                                     "Natural Language Processing (NLP)", "Computer Vision (CV)", "Reinforcement Learning",
                                     "MLOps & System Design", "Feature Engineering & Data Prep", "Optimization & Loss Functions",
                                     "Other / Custom Topic..."]
                
                # Determine options and default values from saved_topics
                int_options = list(predefined_topics)
                saved_topics = st.session_state.get("saved_topics", [])
                
                if saved_topics:
                    default_int_topics = []
                    has_custom = False
                    for t in saved_topics:
                        if t not in predefined_topics:
                            if t not in int_options:
                                int_options.insert(-1, t)
                            default_int_topics.append(t)
                            has_custom = True
                        else:
                            default_int_topics.append(t)
                    if has_custom and "Other / Custom Topic..." not in default_int_topics:
                        default_int_topics.append("Other / Custom Topic...")
                else:
                    default_int_topics = ["Supervised Learning", "Deep Learning / Neural Networks"]
                
                topics = st.multiselect(
                    "Select Machine Learning Topics",
                    options=int_options,
                    default=default_int_topics,
                    key="int_topics_select"
                )
                
                if "Other / Custom Topic..." in topics:
                    custom_defaults = [t for t in saved_topics if t not in predefined_topics]
                    default_custom_text = ", ".join(custom_defaults)
                    custom_topic = st.text_input("Fill your custom topic(s) (comma-separated):", value=default_custom_text, key="int_custom_topic")
                else:
                    custom_topic = ""
                    
                st.markdown("<b style='font-size:0.9rem;'>Or, Ingest PDF Syllabus/Textbook:</b>", unsafe_allow_html=True)
                pdf_file = st.file_uploader("Upload a PDF document to generate questions from its text", type="pdf", key="int_pdf_uploader")
                
                if st.session_state.get("ingested_pdf_name"):
                    st.info(f"📁 Ingested Document: {st.session_state.ingested_pdf_name}")
                    
                # Unified Save & Ingest button at the end
                if st.button("💾 Save Selected Topics & Ingest Document", key="int_save_topics_btn", use_container_width=True):
                    selected_topics = [t for t in topics if t != "Other / Custom Topic..."]
                    if "Other / Custom Topic..." in topics and custom_topic.strip():
                        selected_topics.extend([t.strip() for t in custom_topic.split(",") if t.strip()])
                    
                    if db.save_user_topics(st.session_state.user_info['user_id'], selected_topics):
                        st.session_state.saved_topics = selected_topics
                        if pdf_file:
                            with st.spinner("Ingesting document for RAG..."):
                                pdf_text = pdf.extract_text_from_pdf(pdf_file.read())
                                st.session_state.ingested_pdf_text = pdf_text
                                st.session_state.ingested_pdf_name = pdf_file.name
                            st.session_state.topics_saved_notification = "Selected topics saved and document successfully ingested into the RAG system!"
                        else:
                            st.session_state.ingested_pdf_text = ""
                            st.session_state.ingested_pdf_name = ""
                            st.session_state.topics_saved_notification = "Selected topics have been saved successfully!"
                        st.rerun()
                    else:
                        st.error("Failed to save topics.")
                
        with col2:
            with st.container(border=True):
                st.subheader("2. Question Settings")
                
                total_q = st.slider("Total Number of Questions", min_value=1, max_value=10, value=3)
                
                st.write("Difficulty Counts (Must add up to total questions):")
                c1, c2, c3 = st.columns(3)
                with c1:
                    easy_cnt = st.number_input("Easy", min_value=0, max_value=total_q, value=total_q // 3)
                with c2:
                    medium_cnt = st.number_input("Medium", min_value=0, max_value=total_q, value=(total_q - (total_q // 3)) // 2)
                with c3:
                    hard_cnt = st.number_input("Hard", min_value=0, max_value=total_q, value=total_q - easy_cnt - medium_cnt)
                    
                if easy_cnt + medium_cnt + hard_cnt != total_q:
                    st.error(f"Difficulty counts sum to {easy_cnt + medium_cnt + hard_cnt}, but must equal total questions ({total_q}).")
                    start_disabled = True
                else:
                    start_disabled = False
                    
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Start Interview Session", type="primary", use_container_width=True, disabled=start_disabled):
                    with st.spinner("Extracting content and generating custom questions..."):
                        pdf_text = st.session_state.get("ingested_pdf_text", "")
                        if not pdf_text and pdf_file:
                            pdf_text = pdf.extract_text_from_pdf(pdf_file.read())
                        
                        # Merge dropdown and custom topics
                        selected_topics = [t for t in topics if t != "Other / Custom Topic..."]
                        if "Other / Custom Topic..." in topics and custom_topic.strip():
                            selected_topics.extend([t.strip() for t in custom_topic.split(",") if t.strip()])
                        topic_str = ", ".join(selected_topics) if selected_topics else ("PDF Ingestion" if pdf_file else "General ML")
                        
                        # Generate Questions
                        qs = agents.generate_interview_questions(
                            st.session_state.user_info['user_id'],
                            topic_str, 
                            pdf_text, 
                            total_q, 
                            easy_cnt, 
                            medium_cnt, 
                            hard_cnt
                        )
                        
                        if qs:
                            for q in qs:
                                q["is_follow_up"] = False
                                
                            st.session_state.questions = qs
                            st.session_state.current_q_index = 0
                            st.session_state.interview_active = True
                            st.session_state.interview_finished = False
                            st.session_state.answers_logged = {}
                            st.session_state.q_start_time = time.time()
                            st.session_state.interview_id = db.create_interview(
                                st.session_state.user_info['user_id'],
                                topic_str,
                                f"E:{easy_cnt}/M:{medium_cnt}/H:{hard_cnt}"
                            )
                            st.session_state.follow_up_questions = []
                            st.session_state.follow_up_answers = {}
                            st.session_state.last_feedback = None
                            st.session_state.timer_running = False
                            st.session_state.timer_accumulated_seconds = 0.0
                            st.session_state.timer_start_timestamp = None
                            st.session_state.last_time_taken = 0
                            if "synthesis_report" in st.session_state:
                                del st.session_state.synthesis_report
                            st.rerun()
                        else:
                            st.error("Failed to generate questions. Verify your LLM keys.")
            
    elif st.session_state.get('interview_finished', False):
        st.markdown("### 📋 Professional ML Scientist Analysis")
        st.write("Below is a rigorous evaluation of your responses compiled by a Principal AI Scientist.")
        
        # Load all logged QA entries for this interview
        int_id = st.session_state.interview_id
        qas = db.get_interview_qas(int_id)
        
        if not qas:
            st.warning("No questions were completed in this session.")
        else:
            # Generate Synthesis report under spinner if not in session state
            if "synthesis_report" not in st.session_state:
                with st.spinner("Principal AI Scientist compiling comprehensive synthesis report..."):
                    report = agents.generate_synthesis_report(qas)
                    st.session_state.synthesis_report = report
            
            # Display Synthesis Report
            st.markdown("<div class='premium-card' style='border-left: 6px solid #a855f7;'>", unsafe_allow_html=True)
            st.subheader("🤖 AI Scientist Synthesis Evaluation")
            st.markdown(st.session_state.synthesis_report)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Display Question-wise breakdowns
            st.markdown("<h3 style='margin-top: 25px;'>📝 Question-by-Question Grading Breakdown</h3>", unsafe_allow_html=True)
            for qa_idx, qa in enumerate(qas):
                q_type = "Follow-up Question" if qa['is_follow_up'] else "Core Question"
                score_val = qa['reviewer_score']
                time_val = qa['time_taken']
                
                t_m = time_val // 60
                t_s = time_val % 60
                time_taken_str = f"{t_m}m {t_s}s" if t_m > 0 else f"{t_s}s"
                
                with st.expander(f"Question {qa_idx + 1}: {qa['question'][:75]}... - Score: {score_val}/10 ({q_type})"):
                    st.markdown(f"**Question:** {qa['question']}")
                    st.markdown(f"**Your Answer:** *{qa['user_answer_transcript']}*")
                    st.markdown("---")
                    
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    with sc1:
                        st.metric("Fluency Score", f"{qa.get('fluency_score', 0)}/10")
                    with sc2:
                        st.metric("Professionalism", f"{qa.get('professionalism_score', 0)}/10")
                    with sc3:
                        st.metric("Industry Standards", f"{qa.get('industry_standards_score', 0)}/10")
                    with sc4:
                        st.metric("Overall Score (Avg)", f"{score_val}/10")
                        
                    st.write(f"⏱️ **Time Taken:** {time_taken_str}")
                    st.markdown(f"**Scientist reasoning:**\n{qa['reviewer_reasoning']}")
                    if qa.get('reviewer_improvements'):
                        st.markdown(f"**Key Suggestions for Improvement:**\n{qa['reviewer_improvements']}")
            
        if st.button("Complete Round", type="primary", use_container_width=True):
            st.session_state.interview_active = False
            st.session_state.interview_finished = False
            if "synthesis_report" in st.session_state:
                del st.session_state.synthesis_report
            st.rerun()
            
    else:
        # ACTIVE INTERVIEW ROOM
        qs = st.session_state.questions
        current_idx = st.session_state.current_q_index
        q_count = len(qs)
        current_q = qs[current_idx]
        
        # Check automatic 8-minute timeout (480 seconds)
        elapsed_sec = time.time() - st.session_state.q_start_time
        if elapsed_sec >= 480: # 8 minutes
            st.warning("⏱️ Time limit exceeded (8 minutes). Automatically moving to the next question.")
            # Log zero score for timeout
            db.log_interview_qa(
                interview_id=st.session_state.interview_id,
                question=current_q['question'],
                user_answer_transcript="[No response: Timeout]",
                reviewer_score=0,
                reviewer_reasoning="The candidate exceeded the 8-minute timer to answer this question.",
                reviewer_improvements="",
                is_follow_up=1 if current_q.get('is_follow_up') else 0,
                time_taken=480,
                fluency_score=0,
                professionalism_score=0,
                industry_standards_score=0
            )
            # Reset timer
            st.session_state.timer_running = False
            st.session_state.timer_accumulated_seconds = 0.0
            st.session_state.timer_start_timestamp = None
            
            # Move to next
            if current_idx + 1 < q_count:
                st.session_state.current_q_index += 1
                st.session_state.q_start_time = time.time()
                st.session_state.follow_up_questions = []
                st.session_state.follow_up_answers = {}
                st.session_state.last_feedback = None
                st.rerun()
            else:
                db.finalize_interview_score(st.session_state.interview_id)
                st.session_state.interview_finished = True
                st.rerun()
                
        # Display Question Card
        q_type_str = "Follow-up Question" if current_q.get("is_follow_up", False) else "Core Question"
        st.markdown(f"#### Question {current_idx + 1} of {q_count} ({q_type_str})")
        
        st.markdown(f"""
        <div class='premium-card' style='border-left: 6px solid #6366f1;'>
            <span class="status-badge status-active">{current_q['topic']}</span>
            <span class="status-badge" style="background-color: rgba(168, 85, 247, 0.2); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.3);">{current_q['difficulty']}</span>
            <h3 style='margin-top: 10px;'>{current_q['question']}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if not st.session_state.last_feedback:
            # SINGLE UNIFIED INTERVIEW TIMER ROW
            with st.container(border=True):
                st.markdown("⏱️ **Interview Timer (2-Minute Visual Countdown)**")
                
                if "timer_running" not in st.session_state:
                    st.session_state.timer_running = False
                if "timer_accumulated_seconds" not in st.session_state:
                    st.session_state.timer_accumulated_seconds = 0.0
                    
                if st.session_state.timer_running:
                    current_elapsed = st.session_state.timer_accumulated_seconds + (time.time() - st.session_state.timer_start_timestamp)
                else:
                    current_elapsed = st.session_state.timer_accumulated_seconds
                    
                time_left = max(0, int(120 - current_elapsed))
                m = time_left // 60
                s = time_left % 60
                timer_str = f"{m:02d}:{s:02d}"
                
                col_timer_display, col_timer_controls = st.columns([1, 2])
                
                with col_timer_display:
                    if st.session_state.timer_running and time_left > 0:
                        st.components.v1.html(f"""
                        <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 32px; font-weight: bold; color: #ec4899; text-align: center; background: rgba(0,0,0,0.1); padding: 12px; border-radius: 8px;">
                            <span id="countdown">{timer_str}</span>
                        </div>
                        <script>
                            var seconds = {time_left};
                            var timer = setInterval(function() {{
                                seconds--;
                                if (seconds < 0) {{
                                    clearInterval(timer);
                                    document.getElementById('countdown').innerHTML = "00:00 - TIME UP!";
                                    document.getElementById('countdown').style.color = '#ef4444';
                                }} else {{
                                    var m = Math.floor(seconds / 60);
                                    var s = seconds % 60;
                                    document.getElementById('countdown').innerHTML = (m < 10 ? '0' : '') + m + ":" + (s < 10 ? '0' : '') + s;
                                }}
                            }}, 1000);
                        </script>
                        """, height=80)
                    else:
                        paused_txt = " (PAUSED)" if current_elapsed > 0 else ""
                        st.markdown(f"""
                        <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 32px; font-weight: bold; color: #94a3b8; text-align: center; background: rgba(30, 41, 59, 0.05); padding: 12px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.05);">
                            {timer_str}{paused_txt}
                        </div>
                        """, unsafe_allow_html=True)
                        
                with col_timer_controls:
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.session_state.timer_running:
                            if st.button("Pause Timer", use_container_width=True):
                                delta = time.time() - st.session_state.timer_start_timestamp
                                st.session_state.timer_accumulated_seconds += delta
                                st.session_state.timer_running = False
                                st.session_state.timer_start_timestamp = None
                                st.rerun()
                        else:
                            btn_label = "Start Timer" if current_elapsed == 0 else "Resume Timer"
                            if st.button(btn_label, type="primary" if current_elapsed == 0 else "secondary", use_container_width=True):
                                st.session_state.timer_running = True
                                st.session_state.timer_start_timestamp = time.time()
                                st.rerun()
                    with cc2:
                        if current_elapsed > 0:
                            if st.button("Reset Timer", use_container_width=True):
                                st.session_state.timer_running = False
                                st.session_state.timer_accumulated_seconds = 0.0
                                st.session_state.timer_start_timestamp = Non            # ANSWER SUBMISSION SECTION
            st.markdown("### Answer Submission")
            audio_file = st.audio_input("Record your answer verbally:", key=f"audio_ans_{current_idx}")
            text_answer = st.text_area("Or type/edit your answer transcript below:", key=f"text_ans_{current_idx}")
            
            c_sub, c_skip = st.columns([1, 1])
            
            with c_sub:
                if st.button("Submit Answer", type="primary", use_container_width=True):
                    transcript = text_answer.strip()
                    if audio_file and not transcript:
                        with st.spinner("Transcribing audio answer via Voice-to-Text Agent..."):
                            audio_bytes = audio_file.read()
                            transcript = agents.transcribe_audio(audio_bytes)
                    
                    if not transcript:
                        st.warning("Please type an answer or record your audio before submitting.")
                    else:
                        # Calculate time taken
                        if st.session_state.get('timer_accumulated_seconds', 0.0) > 0 or st.session_state.get('timer_running', False):
                            t_taken = st.session_state.get('timer_accumulated_seconds', 0.0)
                            if st.session_state.get('timer_running', False) and st.session_state.get('timer_start_timestamp'):
                                t_taken += (time.time() - st.session_state.timer_start_timestamp)
                        else:
                            t_taken = time.time() - st.session_state.q_start_time
                        t_taken = min(480, max(1, int(t_taken)))
                        st.session_state.last_time_taken = t_taken
                        
                        # Stop and Reset Timer immediately on submit
                        st.session_state.timer_running = False
                        st.session_state.timer_accumulated_seconds = 0.0
                        st.session_state.timer_start_timestamp = None
                        st.session_state.hint_text = None
                        
                        with st.spinner("Reviewer & Critique Agents evaluating your answer..."):
                            evaluation = agents.evaluate_answer_with_critique(
                                current_q['question'], 
                                transcript, 
                                current_q['difficulty']
                            )
                            
                            # Generate AI recommended answer
                            recommended_ans = agents.generate_ai_recommended_answer(
                                current_q['question'], mode="interview"
                            )
                            evaluation['recommended_answer'] = recommended_ans
                            db_improvements = evaluation.get('improvements', '') + f"\n\n**💡 AI Recommended Answer:**\n{recommended_ans}"
                            
                            # Log to SQLite DB
                            db.log_interview_qa(
                                interview_id=st.session_state.interview_id,
                                question=current_q['question'],
                                user_answer_transcript=transcript,
                                reviewer_score=evaluation.get('score', 0),
                                reviewer_reasoning=evaluation.get('reasoning', ''),
                                reviewer_improvements=db_improvements,
                                is_follow_up=1 if current_q.get('is_follow_up') else 0,
                                time_taken=t_taken,
                                fluency_score=evaluation.get('fluency_score', 0),
                                professionalism_score=evaluation.get('professionalism_score', 0),
                                industry_standards_score=evaluation.get('industry_standards_score', 0),
                                topic=current_q.get('topic', 'General ML')
                            )
                            # Log weak topic if score is low (< 7.0)
                            if evaluation.get('score', 0) < 7.0:
                                db.log_weak_topic(st.session_state.user_info['user_id'], current_q.get('topic', 'General ML'))
                            
                            st.session_state.last_feedback = evaluation
                            st.session_state.answers_logged[current_idx] = transcript
                            st.rerun()
     
            with c_skip:
                if st.button("Skip Question (Log 0)", use_container_width=True):
                    # Calculate time taken
                    if st.session_state.get('timer_accumulated_seconds', 0.0) > 0 or st.session_state.get('timer_running', False):
                        t_taken = st.session_state.get('timer_accumulated_seconds', 0.0)
                        if st.session_state.get('timer_running', False) and st.session_state.get('timer_start_timestamp'):
                            t_taken += (time.time() - st.session_state.timer_start_timestamp)
                    else:
                        t_taken = time.time() - st.session_state.q_start_time
                    t_taken = min(480, max(1, int(t_taken)))
                    
                    db.log_interview_qa(
                        interview_id=st.session_state.interview_id,
                        question=current_q['question'],
                        user_answer_transcript="[Skipped]",
                        reviewer_score=0,
                        reviewer_reasoning="Candidate skipped this question.",
                        reviewer_improvements="",
                        is_follow_up=1 if current_q.get('is_follow_up') else 0,
                        time_taken=t_taken,
                        fluency_score=0,
                        professionalism_score=0,
                        industry_standards_score=0
                    )
                    
                    # Stop and Reset Timer immediately on skip
                    st.session_state.timer_running = False
                    st.session_state.timer_accumulated_seconds = 0.0
                    st.session_state.timer_start_timestamp = None
                    st.session_state.hint_text = None
                    
                    if current_idx + 1 < q_count:
                        st.session_state.current_q_index += 1
                        st.session_state.q_start_time = time.time()
                        st.session_state.follow_up_questions = []
                        st.session_state.follow_up_answers = {}
                        st.session_state.last_feedback = None
                        st.rerun()
                    else:
                        db.finalize_interview_score(st.session_state.interview_id)
                        st.session_state.interview_finished = True
                        st.rerun()
 
        # FEEDBACK & PROCEED PANEL
        if st.session_state.last_feedback:
            st.markdown("---")
            st.markdown("<h3 class='gradient-text'>📝 Evaluation Results</h3>", unsafe_allow_html=True)
            
            f_score = st.session_state.last_feedback.get('score', 0)
            f_reason = st.session_state.last_feedback.get('reasoning', '')
            f_imp = st.session_state.last_feedback.get('improvements', '')
            
            fluency = st.session_state.last_feedback.get('fluency_score', 0)
            professionalism = st.session_state.last_feedback.get('professionalism_score', 0)
            standards = st.session_state.last_feedback.get('industry_standards_score', 0)
            
            t_taken_display = st.session_state.get('last_time_taken', 0)
            t_m = t_taken_display // 60
            t_s = t_taken_display % 60
            time_taken_str = f"{t_m}m {t_s}s" if t_m > 0 else f"{t_s}s"
            
            c_sc, c_rs = st.columns([1.2, 3])
            with c_sc:
                st.markdown(f"""
                <div class='premium-card' style='text-align: center; border: 2px solid #6366f1;'>
                    <h4>Overall Score</h4>
                    <h1 style='font-size: 3.5rem; color: #6366f1; margin: 10px 0;'>{f_score}/10</h1>
                    <hr style='border-color: rgba(255,255,255,0.05); margin: 10px 0;'>
                    <div style='text-align: left; font-size: 0.85rem;'>
                        <b>Fluency:</b> {fluency}/10<br>
                        <b>Professionalism:</b> {professionalism}/10<br>
                        <b>Industry Standards:</b> {standards}/10
                    </div>
                    <hr style='border-color: rgba(255,255,255,0.05); margin: 10px 0;'>
                    <h5>⏱️ Time Taken</h5>
                    <h3 style='color: #ec4899; margin: 0;'>{time_taken_str}</h3>
                </div>
                """, unsafe_allow_html=True)
            with c_rs:
                with st.container(border=True):
                    st.markdown("**Evaluation Reasoning:**")
                    st.write(f_reason)
                    st.markdown("**Suggested Improvements:**")
                    st.write(f_imp)
                    
                    rec_ans = st.session_state.last_feedback.get('recommended_answer', '')
                    if rec_ans:
                        st.markdown("---")
                        st.markdown("**💡 AI Recommended Answer:**")
                        st.write(rec_ans)
                
            # Proceed Button
            btn_text = "Proceed to Next Question" if current_idx + 1 < q_count else "Complete Interview & View Analysis"
            if current_q.get("is_follow_up", False) == False and current_idx + 1 == q_count:
                btn_text = "Proceed to Follow-up Questions"
                
            if st.button(btn_text, type="primary", use_container_width=True):
                # If this was a core question, generate and insert follow-ups
                if not current_q.get("is_follow_up", False):
                    with st.spinner("ML Scientist formulating follow-up questions..."):
                        ans_transcript = st.session_state.answers_logged.get(current_idx, "")
                        fups = agents.generate_follow_ups(
                            current_q['question'], 
                            ans_transcript, 
                            current_q['difficulty']
                        )
                        # Construct fup objects
                        fup_objects = []
                        for i, f_q in enumerate(fups):
                            fup_objects.append({
                                "id": current_q['id'] * 100 + i,
                                "question": f_q,
                                "difficulty": current_q['difficulty'],
                                "topic": f"Follow-up: {current_q['topic']}",
                                "is_follow_up": True
                            })
                        # Insert right after current question
                        for f_obj in reversed(fup_objects):
                            st.session_state.questions.insert(current_idx + 1, f_obj)
                            
                # Reset visual timer state
                st.session_state.timer_running = False
                st.session_state.timer_accumulated_seconds = 0.0
                st.session_state.timer_start_timestamp = None
                
                # Re-calculate counts
                q_count = len(st.session_state.questions)
                
                # Advance or finish
                if current_idx + 1 < q_count:
                    st.session_state.current_q_index += 1
                    st.session_state.q_start_time = time.time()
                    st.session_state.last_feedback = None
                    st.rerun()
                else:
                    db.finalize_interview_score(st.session_state.interview_id)
                    st.session_state.interview_finished = True
                    st.rerun()

# ==========================================
# PAGE 3: MOCK TEST CENTER
# ==========================================
# ==========================================
# PAGE 3: MOCK TEST CENTER
# ==========================================
def render_mock_test_center():
    st.markdown("## 📝 ML Mock Test Center")
    
    # Initialize settings variables in session state if not exist
    if "prev_test_topics" not in st.session_state:
        st.session_state.prev_test_topics = []
    if "prev_test_pdf_text" not in st.session_state:
        st.session_state.prev_test_pdf_text = ""
    if "prev_test_q_count" not in st.session_state:
        st.session_state.prev_test_q_count = 20
    if "prev_test_difficulty" not in st.session_state:
        st.session_state.prev_test_difficulty = "Medium"
    if "prev_test_duration" not in st.session_state:
        st.session_state.prev_test_duration = 30
    if "test_ingested_pdf_text" not in st.session_state:
        st.session_state.test_ingested_pdf_text = ""
    if "test_ingested_pdf_name" not in st.session_state:
        st.session_state.test_ingested_pdf_name = ""
        
    if not st.session_state.test_active and not st.session_state.get("test_finished", False):
        notification_msg = st.session_state.get("topics_saved_notification")
        if notification_msg:
            st.success(notification_msg)
            st.session_state.topics_saved_notification = None
            
        # Setup View
        st.write("Construct custom multiple choice tests from specific topics or uploaded files.")
        
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            with st.container(border=True):
                st.subheader("1. Test Source Config")
                
                # Determine default topics and options
                predefined_topics = ["Supervised Learning", "Unsupervised Learning", "Deep Learning / Neural Networks", 
                                     "Natural Language Processing (NLP)", "Computer Vision (CV)", "Reinforcement Learning",
                                     "MLOps & System Design", "Feature Engineering & Data Prep", "Optimization & Loss Functions",
                                     "Other / Custom Topic..."]
                test_options = list(predefined_topics)
                saved_topics = st.session_state.get("saved_topics", [])
                
                if saved_topics:
                    default_topics = []
                    has_custom = False
                    for t in saved_topics:
                        if t not in predefined_topics:
                            if t not in test_options:
                                test_options.insert(-1, t)
                            default_topics.append(t)
                            has_custom = True
                        else:
                            default_topics.append(t)
                    if has_custom and "Other / Custom Topic..." not in default_topics:
                        default_topics.append("Other / Custom Topic...")
                else:
                    default_topics = ["Supervised Learning", "Unsupervised Learning"]
                
                topics = st.multiselect(
                    "Select Test Topics",
                    options=test_options,
                    default=default_topics,
                    key="test_topics_select"
                )
                
                if "Other / Custom Topic..." in topics:
                    custom_defaults = [t for t in saved_topics if t not in predefined_topics]
                    default_text = ", ".join(custom_defaults)
                    custom_topic = st.text_input("Fill your custom topic(s) (comma-separated):", value=default_text, key="test_custom_topics_input")
                else:
                    custom_topic = ""
                    
                st.markdown("<b style='font-size:0.9rem;'>Or, Ingest Source PDF:</b>", unsafe_allow_html=True)
                pdf_file = st.file_uploader("Upload a PDF document to generate test questions", type="pdf", key="test_pdf_uploader")
                
                if st.session_state.get("test_ingested_pdf_name"):
                    st.info(f"📁 Ingested Document: {st.session_state.test_ingested_pdf_name}")
                    
                # Unified Save & Ingest button at the end
                if st.button("💾 Save Selected Topics & Ingest Document", key="test_save_topics_btn", use_container_width=True):
                    selected_topics = [t for t in topics if t != "Other / Custom Topic..."]
                    if "Other / Custom Topic..." in topics and custom_topic.strip():
                        selected_topics.extend([t.strip() for t in custom_topic.split(",") if t.strip()])
                    
                    if db.save_user_topics(st.session_state.user_info['user_id'], selected_topics):
                        st.session_state.saved_topics = selected_topics
                        if pdf_file:
                            with st.spinner("Ingesting document for RAG..."):
                                pdf_text = pdf.extract_text_from_pdf(pdf_file.read())
                                st.session_state.test_ingested_pdf_text = pdf_text
                                st.session_state.test_ingested_pdf_name = pdf_file.name
                            st.session_state.topics_saved_notification = "Selected topics saved and document successfully ingested into the RAG system!"
                        else:
                            st.session_state.test_ingested_pdf_text = ""
                            st.session_state.test_ingested_pdf_name = ""
                            st.session_state.topics_saved_notification = "Selected topics have been saved successfully!"
                        st.rerun()
                    else:
                        st.error("Failed to save topics.")
                
        with col2:
            with st.container(border=True):
                st.subheader("2. Settings & Difficulty")
                
                diff_options = ["Easy", "Medium", "Hard"]
                default_diff = st.session_state.prev_test_difficulty if st.session_state.prev_test_difficulty in diff_options else "Medium"
                diff_index = diff_options.index(default_diff)
                difficulty = st.selectbox("Select Difficulty Level", diff_options, index=diff_index, key="test_diff_select")
                
                default_q_count = st.session_state.prev_test_q_count if st.session_state.prev_test_q_count else 20
                q_count = st.slider("Select Question Count", min_value=15, max_value=60, value=int(default_q_count))
                
                default_duration = st.session_state.get("prev_test_duration", 30)
                duration = st.slider("Select Test Duration (Minutes)", min_value=15, max_value=120, value=int(default_duration), step=5)
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Generate Test Profile", type="primary", use_container_width=True):
                    with st.spinner("Mock Test Agent generating questions..."):
                        pdf_text = st.session_state.get("test_ingested_pdf_text", "")
                        if not pdf_text and pdf_file:
                            pdf_text = pdf.extract_text_from_pdf(pdf_file.read())
                            
                        # Merge dropdown and custom topics
                        selected_topics = [t for t in topics if t != "Other / Custom Topic..."]
                        if "Other / Custom Topic..." in topics and custom_topic.strip():
                            selected_topics.extend([t.strip() for t in custom_topic.split(",") if t.strip()])
                        topic_str = ", ".join(selected_topics) if selected_topics else ("PDF Ingestion" if pdf_file else "General ML")
                        
                        # Save setup settings to session state
                        st.session_state.prev_test_topics = selected_topics
                        st.session_state.prev_test_pdf_text = pdf_text
                        st.session_state.prev_test_q_count = q_count
                        st.session_state.prev_test_difficulty = difficulty
                        st.session_state.prev_test_duration = duration
                        
                        test_qs = agents.generate_mock_test(
                            st.session_state.user_info['user_id'],
                            topic_str, 
                            pdf_text, 
                            q_count,
                            difficulty
                        )
                        
                        if test_qs:
                            st.session_state.test_questions = test_qs
                            st.session_state.test_answers = {}
                            st.session_state.test_score = None
                            st.session_state.test_active = True
                            st.session_state.test_start_timestamp = time.time()
                            st.session_state.test_duration_seconds = duration * 60
                            st.session_state.test_explanations = {q['id']: q.get('explanation', '') for q in test_qs}
                            if "test_weakness_analysis" in st.session_state:
                                del st.session_state.test_weakness_analysis
                            st.rerun()
                        else:
                            st.error("Failed to generate test. Check API credentials.")
            
    elif st.session_state.get("test_finished", False):
        # RESULTS VIEW
        test_qs = st.session_state.test_questions
        
        # Render evaluation details
        st.markdown("---")
        st.markdown(f"""
        <div class='premium-card' style='text-align: center; border: 2px solid #ec4899;'>
            <h2>Mock Test Score</h2>
            <h1 style='font-size: 5rem; color: #ec4899; margin: 15px 0;'>{int(st.session_state.test_score * 100)}%</h1>
            <h4>Correct Answers: {st.session_state.test_correct_cnt} / {len(test_qs)}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div class='premium-card' style='border-left: 6px solid #ef4444;'>", unsafe_allow_html=True)
        st.subheader("📊 Weakness Analysis & Study Plan")
        st.markdown(st.session_state.test_weakness_analysis)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Display Review List
        st.subheader("📝 Answer Review & Explanations")
        for idx, item in enumerate(st.session_state.test_details):
            bg_color = "rgba(16, 185, 129, 0.15)" if item['is_correct'] else "rgba(239, 68, 68, 0.15)"
            border_color = "#10b981" if item['is_correct'] else "#ef4444"
            status_txt = "Correct" if item['is_correct'] else "Incorrect"
            
            st.markdown(f"""
            <div style='background: {bg_color}; border-left: 5px solid {border_color}; padding: 15px; border-radius: 8px; margin-bottom: 12px;'>
                <b>Question {idx+1}: {item['question']}</b> | Sub-topic: <span style='color:#a855f7; font-weight:600;'>{item['topic']}</span><br>
                Your Answer: {item['user_choice'] or 'None'} | Correct Answer: {item['correct_choice']}<br>
                <span style='font-weight: bold; color: {border_color};'>{status_txt}</span><br>
                <i>Explanation: {item['explanation']}</i>
            </div>
            """, unsafe_allow_html=True)
            
        col_new1, col_new2 = st.columns(2)
        with col_new1:
            if st.button("Start Similar Test (Adaptive)", type="primary", use_container_width=True, key="test_adaptive_btn"):
                with st.spinner("Generating next adaptive test based on weaknesses..."):
                    topic_str = ", ".join(st.session_state.prev_test_topics) if st.session_state.prev_test_topics else "General ML"
                    incorrect_topics = list(set([item['topic'] for item in st.session_state.test_details if not item['is_correct']]))
                    
                    test_qs = agents.generate_mock_test(
                        st.session_state.user_info['user_id'],
                        topic_str,
                        st.session_state.prev_test_pdf_text,
                        st.session_state.prev_test_q_count,
                        st.session_state.prev_test_difficulty,
                        adaptive_weak_topics=incorrect_topics
                    )
                    if test_qs:
                        st.session_state.test_questions = test_qs
                        st.session_state.test_answers = {}
                        st.session_state.test_score = None
                        st.session_state.test_correct_cnt = 0
                        st.session_state.test_details = []
                        st.session_state.test_active = True
                        st.session_state.test_finished = False
                        st.session_state.test_start_timestamp = time.time()
                        duration = st.session_state.get("prev_test_duration", 30)
                        st.session_state.test_duration_seconds = duration * 60
                        st.session_state.test_explanations = {q['id']: q.get('explanation', '') for q in test_qs}
                        if "test_weakness_analysis" in st.session_state:
                            del st.session_state.test_weakness_analysis
                        st.rerun()
                    else:
                        st.error("Failed to generate test.")
        with col_new2:
            if st.button("Complete Round", type="primary", use_container_width=True, key="test_complete_round_btn"):
                st.session_state.test_active = False
                st.session_state.test_finished = False
                st.session_state.test_questions = []
                st.session_state.test_answers = {}
                st.session_state.test_score = None
                st.session_state.test_correct_cnt = 0
                st.session_state.test_details = []
                if "test_weakness_analysis" in st.session_state:
                    del st.session_state.test_weakness_analysis
                st.rerun()
    else:
        # ACTIVE TEST
        test_qs = st.session_state.test_questions
        st.markdown(f"### Mock Exam ({len(test_qs)} Questions) — Level: **{st.session_state.prev_test_difficulty}**")
        
        # Calculate time remaining
        elapsed = time.time() - st.session_state.get("test_start_timestamp", time.time())
        duration_sec = st.session_state.get("test_duration_seconds", 30 * 60)
        remaining = duration_sec - elapsed
        
        def submit_test():
            correct_cnt = 0
            details = []
            
            # Log Mock Test to DB and get test ID
            topic_summary = ", ".join(st.session_state.prev_test_topics[:3]) if st.session_state.prev_test_topics else "General ML"
            test_id = db.log_mock_test(
                st.session_state.user_info['user_id'],
                topic_summary,
                len(test_qs),
                0.0, # Will finalize later
                difficulty=st.session_state.prev_test_difficulty
            )
            
            for q in test_qs:
                user_ans = st.session_state.test_answers.get(q['id'])
                user_choice = user_ans[0] if user_ans else None
                correct_choice = q['correct_option']
                
                is_correct = (user_choice == correct_choice)
                if is_correct:
                    correct_cnt += 1
                    
                details.append({
                    "question": q['question'],
                    "topic": q.get('topic', 'General ML'),
                    "user_choice": user_choice,
                    "correct_choice": correct_choice,
                    "is_correct": is_correct,
                    "explanation": q['explanation']
                })
                
                # Log individual question QA log
                db.log_mock_test_qa(
                    test_id=test_id,
                    question=q['question'],
                    topic=q.get('topic', 'General ML'),
                    is_correct=is_correct,
                    user_choice=user_choice,
                    correct_choice=correct_choice
                )
                
                # Log weak topic if incorrect
                if not is_correct:
                    db.log_weak_topic(st.session_state.user_info['user_id'], q.get('topic', 'General ML'))
                
            final_pct = round(correct_cnt / len(test_qs), 2)
            st.session_state.test_score = final_pct
            st.session_state.test_correct_cnt = correct_cnt
            st.session_state.test_details = details
            
            # Update the test score in DB
            conn = db.get_db_connection()
            conn.execute("UPDATE mock_tests SET score = ? WHERE test_id = ?", (final_pct, test_id))
            conn.commit()
            conn.close()
            
            # Generate weakness analyzer analysis
            wrong_qs = [d for d in details if not d['is_correct']]
            with st.spinner("Weakness Analyzer Agent compiling study recommendations..."):
                st.session_state.test_weakness_analysis = agents.generate_test_weakness_analysis(wrong_qs)
            
            st.session_state.test_finished = True
            st.rerun()

        if remaining <= 0:
            st.warning("⏱️ Time is up! Automatically submitting and grading your mock test...")
            submit_test()
        else:
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            st.markdown(f"""
            <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; border-radius: 12px; padding: 12px; text-align: center; margin-bottom: 20px;">
                <span style="font-size: 1.4rem; font-weight: bold; color: #ef4444;">⏱️ Mock Exam Timer: {mins:02d}:{secs:02d}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Render each question
            for i, q in enumerate(test_qs):
                st.markdown(f"""
                <div class='premium-card'>
                    <span class="status-badge status-active">{q.get('topic', 'General ML')}</span>
                    <br><br>
                    <b>Question {i + 1}: {q['question']}</b>
                </div>
                """, unsafe_allow_html=True)
                
                ans_key = f"t_ans_{q['id']}"
                st.session_state.test_answers[q['id']] = st.radio(
                    "Select Option:",
                    q['options'],
                    index=None,
                    key=ans_key
                )
                st.markdown("<br>", unsafe_allow_html=True)
                
            if st.button("Submit Test & Grade Answers", type="primary", use_container_width=True, key="test_submit_grading_btn"):
                submit_test()

# ==========================================
# PAGE 4: RESUME ROUND
# ==========================================
def render_resume_round():
    st.markdown("## 📄 Resume Round Technical Interview")
    
    # Initialize Resume Round session states if not present
    if "resume_active" not in st.session_state:
        st.session_state.resume_active = False
    if "resume_questions" not in st.session_state:
        st.session_state.resume_questions = []
    if "resume_current_q_index" not in st.session_state:
        st.session_state.resume_current_q_index = 0
    if "resume_answers_logged" not in st.session_state:
        st.session_state.resume_answers_logged = {}
    if "resume_round_start_time" not in st.session_state:
        st.session_state.resume_round_start_time = None
    if "resume_time_limit" not in st.session_state:
        st.session_state.resume_time_limit = 25
    if "resume_difficulty" not in st.session_state:
        st.session_state.resume_difficulty = "Medium"
    if "resume_interview_id" not in st.session_state:
        st.session_state.resume_interview_id = None
    if "resume_last_feedback" not in st.session_state:
        st.session_state.resume_last_feedback = None
    if "resume_timer_running" not in st.session_state:
        st.session_state.resume_timer_running = False
    if "resume_timer_accumulated_seconds" not in st.session_state:
        st.session_state.resume_timer_accumulated_seconds = 0.0
    if "resume_timer_start_timestamp" not in st.session_state:
        st.session_state.resume_timer_start_timestamp = None
    if "resume_last_time_taken" not in st.session_state:
        st.session_state.resume_last_time_taken = 0
    if "resume_synthesis_report" not in st.session_state:
        st.session_state.resume_synthesis_report = None
    if "resume_finished" not in st.session_state:
        st.session_state.resume_finished = False

    if not st.session_state.resume_active:
        # Setup View
        st.write("Upload your resume and configure the time limits to begin the Resume Round.")
        
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            with st.container(border=True):
                st.subheader("1. Ingest Resume")
                resume_file = st.file_uploader("Upload your Resume (PDF format)", type="pdf", key="resume_uploader")
            
        with col2:
            with st.container(border=True):
                st.subheader("2. Round Configuration")
                
                res_difficulty = st.selectbox("Interview Difficulty Level", ["Easy", "Medium", "Hard"], index=1, key="res_diff")
                time_limit = st.slider("Total Round Duration Limit (minutes)", min_value=15, max_value=45, value=25)
                question_count = st.slider("Number of Questions to Ask", min_value=3, max_value=8, value=5)
                
                st.markdown("<br>", unsafe_allow_html=True)
                start_disabled = (resume_file is None)
                
                if st.button("Start Resume Round Interview", type="primary", use_container_width=True, disabled=start_disabled):
                    with st.spinner("Principal AI Scientist performing OCR/parsing on resume..."):
                        resume_bytes = resume_file.read()
                        resume_text = pdf.extract_text_from_pdf(resume_bytes)
                        
                        if not resume_text or len(resume_text.strip()) < 50:
                            st.error("Failed to extract legible text from your resume. Ensure it is a valid text PDF.")
                        else:
                            with st.spinner("Generating professional custom project questions..."):
                                qs = agents.generate_resume_questions(resume_text, question_count, res_difficulty, st.session_state.user_info['name'])
                                if qs:
                                    st.session_state.resume_questions = qs
                                    st.session_state.resume_text = resume_text  # Save resume text to session state
                                    st.session_state.resume_current_q_index = 0
                                    st.session_state.resume_active = True
                                    st.session_state.resume_finished = False
                                    st.session_state.resume_answers_logged = {}
                                    st.session_state.resume_round_start_time = time.time()
                                    st.session_state.resume_time_limit = time_limit
                                    st.session_state.resume_difficulty = res_difficulty
                                    
                                    # Create entry in interviews DB using topic "Resume: [filename]"
                                    resume_title = f"Resume: {resume_file.name[:35]}"
                                    st.session_state.resume_interview_id = db.create_interview(
                                        st.session_state.user_info['user_id'],
                                        resume_title,
                                        res_difficulty
                                    )
                                    
                                    st.session_state.resume_timer_running = False
                                    st.session_state.resume_timer_accumulated_seconds = 0.0
                                    st.session_state.resume_timer_start_timestamp = None
                                    st.session_state.resume_last_feedback = None
                                    if "resume_synthesis_report" in st.session_state:
                                        del st.session_state.resume_synthesis_report
                                    st.rerun()
                                else:
                                    st.error("Failed to generate interview questions. Verify API keys.")
            
    elif st.session_state.get('resume_finished', False):
        # RESUME ROUND RESULTS SCREEN
        st.markdown("### 📋 Professional Resume Round Analysis")
        st.write("Below is a rigorous evaluation of your resume defense compiled by a strict Data Scientist.")
        
        int_id = st.session_state.resume_interview_id
        qas = db.get_interview_qas(int_id)
        
        if not qas:
            st.warning("No questions were completed in this session.")
        else:
            if "resume_synthesis_report" not in st.session_state or st.session_state.resume_synthesis_report is None:
                with st.spinner("Data Scientist compiling comprehensive synthesis report..."):
                    report = agents.generate_resume_synthesis_report(qas, st.session_state.user_info['name'])
                    st.session_state.resume_synthesis_report = report
            
            # Display Synthesis Report
            st.markdown("<div class='premium-card' style='border-left: 6px solid #10b981;'>", unsafe_allow_html=True)
            st.subheader("🤖 AI Data Scientist Synthesis Evaluation")
            st.markdown(st.session_state.resume_synthesis_report)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Display Question-wise breakdowns
            st.markdown("<h3 style='margin-top: 25px;'>📝 Question-by-Question Grading Breakdown</h3>", unsafe_allow_html=True)
            for qa_idx, qa in enumerate(qas):
                score_val = qa['reviewer_score']
                time_val = qa['time_taken']
                t_m = time_val // 60
                t_s = time_val % 60
                time_taken_str = f"{t_m}m {t_s}s" if t_m > 0 else f"{t_s}s"
                
                with st.expander(f"Question {qa_idx + 1}: {qa['question'][:75]}... - Score: {score_val}/10"):
                    st.markdown(f"**Question:** {qa['question']}")
                    st.markdown(f"**Your Answer:** *{qa['user_answer_transcript']}*")
                    st.markdown("---")
                    
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    with sc1:
                        st.metric("Fluency Score", f"{qa.get('fluency_score', 0)}/10")
                    with sc2:
                        st.metric("Professionalism", f"{qa.get('professionalism_score', 0)}/10")
                    with sc3:
                        st.metric("Technical Depth", f"{qa.get('industry_standards_score', 0)}/10")
                    with sc4:
                        st.metric("Overall Score (Avg)", f"{score_val}/10")
                        
                    st.write(f"⏱️ **Time Taken:** {time_taken_str}")
                    st.markdown(f"**Data Scientist reasoning:**\n{qa['reviewer_reasoning']}")
                    if qa.get('reviewer_improvements'):
                        st.markdown(f"**Key Suggestions for Improvement:**\n{qa['reviewer_improvements']}")
                        
        if st.button("Complete Round", type="primary", use_container_width=True):
            st.session_state.resume_active = False
            st.session_state.resume_finished = False
            st.session_state.resume_questions = []
            st.session_state.resume_answers_logged = {}
            st.session_state.resume_interview_id = None
            st.session_state.resume_last_feedback = None
            if "resume_synthesis_report" in st.session_state:
                del st.session_state.resume_synthesis_report
            st.rerun()
            
    else:
        # ACTIVE RESUME ROUND ROOM
        qs = st.session_state.resume_questions
        current_idx = st.session_state.resume_current_q_index
        q_count = len(qs)
        current_q = qs[current_idx]
        
        # 1. Check cumulative time limit (15 to 45 mins)
        elapsed_sec = time.time() - st.session_state.resume_round_start_time
        time_limit_sec = st.session_state.resume_time_limit * 60
        
        # Display cumulative round timer
        round_time_left = max(0, int(time_limit_sec - elapsed_sec))
        rt_m = round_time_left // 60
        rt_s = round_time_left % 60
        
        # If cumulative time is up
        if elapsed_sec >= time_limit_sec:
            st.warning("⏱️ Cumulative round time limit exceeded! Automatically closing the interview round.")
            db.finalize_interview_score(st.session_state.resume_interview_id)
            st.session_state.resume_finished = True
            st.rerun()
            
        st.markdown(f"<div style='text-align: right; font-weight: 600; color: #ef4444; font-size: 1.1rem; margin-bottom: 10px;'>⏱️ Cumulative Round Time Remaining: {rt_m:02d}:{rt_s:02d}</div>", unsafe_allow_html=True)
        
        # Display question
        st.markdown(f"#### Resume Round Question {current_idx + 1} of {q_count}")
        st.markdown(f"""
        <div class='premium-card' style='border-left: 6px solid #10b981;'>
            <span class="status-badge status-active">{current_q.get('topic', 'Resume Review')}</span>
            <span class="status-badge" style="background-color: rgba(168, 85, 247, 0.2); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.3);">{st.session_state.resume_difficulty}</span>
            <h3 style='margin-top: 10px;'>{current_q['question']}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Visual countdown timer (3 minutes max = 180 seconds)
        if not st.session_state.resume_last_feedback:
            with st.container(border=True):
                st.markdown("⏱️ **Interview Timer (3-Minute Visual Countdown)**")
                
                if st.session_state.resume_timer_running:
                    current_elapsed = st.session_state.resume_timer_accumulated_seconds + (time.time() - st.session_state.resume_timer_start_timestamp)
                else:
                    current_elapsed = st.session_state.resume_timer_accumulated_seconds
                    
                time_left = max(0, int(180 - current_elapsed))
                m = time_left // 60
                s = time_left % 60
                timer_str = f"{m:02d}:{s:02d}"
                
                col_timer_display, col_timer_controls = st.columns([1, 2])
                
                with col_timer_display:
                    if st.session_state.resume_timer_running and time_left > 0:
                        st.components.v1.html(f"""
                        <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 32px; font-weight: bold; color: #ec4899; text-align: center; background: rgba(0,0,0,0.1); padding: 12px; border-radius: 8px;">
                            <span id="countdown">{timer_str}</span>
                        </div>
                        <script>
                            var seconds = {time_left};
                            var timer = setInterval(function() {{
                                seconds--;
                                if (seconds < 0) {{
                                    clearInterval(timer);
                                    document.getElementById('countdown').innerHTML = "00:00 - TIME UP!";
                                    document.getElementById('countdown').style.color = '#ef4444';
                                }} else {{
                                    var m = Math.floor(seconds / 60);
                                    var s = seconds % 60;
                                    document.getElementById('countdown').innerHTML = (m < 10 ? '0' : '') + m + ":" + (s < 10 ? '0' : '') + s;
                                }}
                            }}, 1000);
                        </script>
                        """, height=80)
                    else:
                        paused_txt = " (PAUSED)" if current_elapsed > 0 else ""
                        st.markdown(f"""
                        <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 32px; font-weight: bold; color: #94a3b8; text-align: center; background: rgba(30, 41, 59, 0.05); padding: 12px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.05);">
                            {timer_str}{paused_txt}
                        </div>
                        """, unsafe_allow_html=True)
                        
                with col_timer_controls:
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.session_state.resume_timer_running:
                            if st.button("Pause Timer", use_container_width=True, key="res_pause_btn"):
                                delta = time.time() - st.session_state.resume_timer_start_timestamp
                                st.session_state.resume_timer_accumulated_seconds += delta
                                st.session_state.resume_timer_running = False
                                st.session_state.resume_timer_start_timestamp = None
                                st.rerun()
                        else:
                            btn_label = "Start Timer" if current_elapsed == 0 else "Resume Timer"
                            if st.button(btn_label, type="primary" if current_elapsed == 0 else "secondary", use_container_width=True, key="res_start_btn"):
                                st.session_state.resume_timer_running = True
                                st.session_state.resume_timer_start_timestamp = time.time()
                                st.rerun()
                    with cc2:
                        if current_elapsed > 0:
                            if st.button("Reset Timer", use_container_width=True, key="res_reset_btn"):
                                st.session_state.resume_timer_running = False
                                st.session_state.resume_timer_accumulated_seconds = 0.0
                                st.session_state.resume_timer_start_timestamp = None
                                st.rerun()
            
            # Answer inputs
            st.markdown("### Answer Submission")
            audio_file = st.audio_input("Record your answer verbally:", key=f"res_audio_ans_{current_idx}")
            text_answer = st.text_area("Or type/edit your answer transcript below:", key=f"res_text_ans_{current_idx}")
            
            # AI Recommended Answer will be shown in the Evaluation Results analysis section after submission.
                
            c_sub, c_skip = st.columns([1, 1])
            with c_sub:
                if st.button("Submit Answer", type="primary", use_container_width=True, key="res_submit_btn"):
                    transcript = text_answer.strip()
                    if audio_file and not transcript:
                        with st.spinner("Transcribing audio answer via Voice-to-Text Agent..."):
                            audio_bytes = audio_file.read()
                            transcript = agents.transcribe_audio(audio_bytes)
                            
                    if not transcript:
                        st.warning("Please type an answer or record your audio before submitting.")
                    else:
                        if st.session_state.get('resume_timer_accumulated_seconds', 0.0) > 0 or st.session_state.get('resume_timer_running', False):
                            t_taken = st.session_state.get('resume_timer_accumulated_seconds', 0.0)
                            if st.session_state.get('resume_timer_running', False) and st.session_state.get('resume_timer_start_timestamp'):
                                t_taken += (time.time() - st.session_state.resume_timer_start_timestamp)
                        else:
                            t_taken = time.time() - st.session_state.resume_round_start_time
                        t_taken = min(180, max(1, int(t_taken)))
                        st.session_state.resume_last_time_taken = t_taken
                        
                        # Stop and reset timer immediately
                        st.session_state.resume_timer_running = False
                        st.session_state.resume_timer_accumulated_seconds = 0.0
                        st.session_state.resume_timer_start_timestamp = None
                        st.session_state.resume_hint_text = None
                        
                        with st.spinner("Data Scientist & Critique Agents evaluating your answer..."):
                            evaluation = agents.evaluate_resume_answer_with_critique(
                                current_q['question'],
                                transcript,
                                st.session_state.resume_difficulty,
                                st.session_state.user_info['name']
                            )
                            
                            # Generate AI recommended answer (Resume-Tailored)
                            recommended_ans = agents.generate_ai_recommended_answer(
                                current_q['question'],
                                context_text=st.session_state.get("resume_text", ""),
                                mode="resume"
                            )
                            evaluation['recommended_answer'] = recommended_ans
                            db_improvements = evaluation.get('improvements', '') + f"\n\n**💡 AI Recommended Answer:**\n{recommended_ans}"
                            
                            # Log to DB
                            db.log_interview_qa(
                                interview_id=st.session_state.resume_interview_id,
                                question=current_q['question'],
                                user_answer_transcript=transcript,
                                reviewer_score=evaluation.get('score', 0),
                                reviewer_reasoning=evaluation.get('reasoning', ''),
                                reviewer_improvements=db_improvements,
                                is_follow_up=0,
                                time_taken=t_taken,
                                fluency_score=evaluation.get('fluency_score', 0),
                                professionalism_score=evaluation.get('professionalism_score', 0),
                                industry_standards_score=evaluation.get('industry_standards_score', 0),
                                topic=current_q.get('topic', 'Resume Details')
                            )
                            
                            # Log weakness if low score
                            if evaluation.get('score', 0) < 7.0:
                                db.log_weak_topic(st.session_state.user_info['user_id'], current_q.get('topic', 'Resume Details'))
                            
                            st.session_state.resume_last_feedback = evaluation
                            st.session_state.resume_answers_logged[current_idx] = transcript
                            st.rerun()
            with c_skip:
                if st.button("Skip Question (Log 0)", use_container_width=True, key="res_skip_btn"):
                    if st.session_state.get('resume_timer_accumulated_seconds', 0.0) > 0 or st.session_state.get('resume_timer_running', False):
                        t_taken = st.session_state.get('resume_timer_accumulated_seconds', 0.0)
                        if st.session_state.get('resume_timer_running', False) and st.session_state.get('resume_timer_start_timestamp'):
                            t_taken += (time.time() - st.session_state.resume_timer_start_timestamp)
                    else:
                        t_taken = 0
                    t_taken = min(180, max(1, int(t_taken)))
                    
                    db.log_interview_qa(
                        interview_id=st.session_state.resume_interview_id,
                        question=current_q['question'],
                        user_answer_transcript="[Skipped]",
                        reviewer_score=0,
                        reviewer_reasoning="Candidate skipped this question.",
                        reviewer_improvements="",
                        is_follow_up=0,
                        time_taken=t_taken,
                        fluency_score=0,
                        professionalism_score=0,
                        industry_standards_score=0,
                        topic=current_q.get('topic', 'Resume Details')
                    )
                    
                    # Reset timer
                    st.session_state.resume_timer_running = False
                    st.session_state.resume_timer_accumulated_seconds = 0.0
                    st.session_state.resume_timer_start_timestamp = None
                    st.session_state.resume_hint_text = None
                    
                    if current_idx + 1 < q_count:
                        st.session_state.resume_current_q_index += 1
                        st.session_state.resume_last_feedback = None
                        st.rerun()
                    else:
                        db.finalize_interview_score(st.session_state.resume_interview_id)
                        st.session_state.resume_finished = True
                        st.rerun()
                        
        # Display feedback & proceed
        if st.session_state.resume_last_feedback:
            st.markdown("---")
            st.markdown("<h3 class='gradient-text'>📝 Evaluation Results</h3>", unsafe_allow_html=True)
            
            f_score = st.session_state.resume_last_feedback.get('score', 0)
            f_reason = st.session_state.resume_last_feedback.get('reasoning', '')
            f_imp = st.session_state.resume_last_feedback.get('improvements', '')
            
            fluency = st.session_state.resume_last_feedback.get('fluency_score', 0)
            professionalism = st.session_state.resume_last_feedback.get('professionalism_score', 0)
            depth = st.session_state.resume_last_feedback.get('industry_standards_score', 0)
            
            t_taken_display = st.session_state.get('resume_last_time_taken', 0)
            t_m = t_taken_display // 60
            t_s = t_taken_display % 60
            time_taken_str = f"{t_m}m {t_s}s" if t_m > 0 else f"{t_s}s"
            
            c_sc, c_rs = st.columns([1.2, 3])
            with c_sc:
                st.markdown(f"""
                <div class='premium-card' style='text-align: center; border: 2px solid #10b981;'>
                    <h4>Overall Score</h4>
                    <h1 style='font-size: 3.5rem; color: #10b981; margin: 10px 0;'>{f_score}/10</h1>
                    <hr style='border-color: rgba(255,255,255,0.05); margin: 10px 0;'>
                    <div style='text-align: left; font-size: 0.85rem;'>
                        <b>Fluency:</b> {fluency}/10<br>
                        <b>Professionalism:</b> {professionalism}/10<br>
                        <b>Technical Depth:</b> {depth}/10
                    </div>
                    <hr style='border-color: rgba(255,255,255,0.05); margin: 10px 0;'>
                    <h5>⏱️ Time Taken</h5>
                    <h3 style='color: #ec4899; margin: 0;'>{time_taken_str}</h3>
                </div>
                """, unsafe_allow_html=True)
            with c_rs:
                with st.container(border=True):
                    st.markdown("**Evaluation Reasoning:**")
                    st.write(f_reason)
                    st.markdown("**Suggested Improvements:**")
                    st.write(f_imp)
                    
                    rec_ans = st.session_state.resume_last_feedback.get('recommended_answer', '')
                    if rec_ans:
                        st.markdown("---")
                        st.markdown("**💡 AI Recommended Answer:**")
                        st.write(rec_ans)
                
            btn_text = "Proceed to Next Question" if current_idx + 1 < q_count else "Complete Resume Round & View Analysis"
            if st.button(btn_text, type="primary", use_container_width=True, key="res_proceed_btn"):
                # Reset visual timer state
                st.session_state.resume_timer_running = False
                st.session_state.resume_timer_accumulated_seconds = 0.0
                st.session_state.resume_timer_start_timestamp = None
                st.session_state.resume_hint_text = None
                
                if current_idx + 1 < q_count:
                    st.session_state.resume_current_q_index += 1
                    st.session_state.resume_last_feedback = None
                    st.rerun()
                else:
                    db.finalize_interview_score(st.session_state.resume_interview_id)
                    st.session_state.resume_finished = True
                    st.rerun()

# ==========================================
# PAGE 5: REVISIT PAST ROUNDS
# ==========================================
def render_revisit_rounds():
    st.markdown("## 🔍 Revisit Past Rounds")
    st.write("Browse and review your past mock test attempts, technical interviews, and resume rounds.")
    
    user_id = st.session_state.user_info['user_id']
    
    category = st.radio("Select Category to Revisit:", ["Mock Interviews", "Resume Rounds", "Mock Tests"], horizontal=True, key="revisit_category")
    
    if category == "Mock Interviews":
        # Get all interview history and filter out Resume rounds
        history = db.get_detailed_interview_history(user_id)
        interviews = [h for h in history if not h['topic'].startswith("Resume:")]
        
        if not interviews:
            st.info("No mock interviews recorded yet.")
        else:
            options = {f"{i['date']} - {i['topic']} ({i['difficulty']}) | Score: {i['overall_score']}/10": i for i in interviews}
            selected_label = st.selectbox("Select past interview round to review:", list(options.keys()))
            selected_item = options[selected_label]
            
            # Display detailed view
            int_id = selected_item['interview_id']
            qas = db.get_interview_qas(int_id)
            
            st.markdown(f"### Review: **{selected_item['topic']}**")
            st.write(f"📅 **Date:** {selected_item['date']} | 🏆 **Overall Score:** {selected_item['overall_score']}/10")
            
            for qa_idx, qa in enumerate(qas):
                q_type = "Follow-up Question" if qa['is_follow_up'] else "Core Question"
                score_val = qa['reviewer_score']
                time_val = qa['time_taken']
                t_m = time_val // 60
                t_s = time_val % 60
                time_taken_str = f"{t_m}m {t_s}s" if t_m > 0 else f"{t_s}s"
                
                with st.container(border=True):
                    st.markdown(f"**Question {qa_idx + 1} ({q_type}):** {qa['question']}")
                    st.markdown(f"**Your Answer:** *{qa['user_answer_transcript']}*")
                    
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    with sc1:
                        st.metric("Fluency Score", f"{qa.get('fluency_score', 0)}/10")
                    with sc2:
                        st.metric("Professionalism", f"{qa.get('professionalism_score', 0)}/10")
                    with sc3:
                        st.metric("Industry Standards", f"{qa.get('industry_standards_score', 0)}/10")
                    with sc4:
                        st.metric("Score", f"{score_val}/10")
                        
                    st.write(f"⏱️ **Time Taken:** {time_taken_str}")
                    st.markdown(f"**AI Reviewer Reasoning:**\n{qa['reviewer_reasoning']}")
                    if qa.get('reviewer_improvements'):
                        st.markdown(f"**Suggested Improvements:**\n{qa['reviewer_improvements']}")
                        
    elif category == "Resume Rounds":
        # Get all interview history and filter matching Resume rounds
        history = db.get_detailed_interview_history(user_id)
        resumes = [h for h in history if h['topic'].startswith("Resume:")]
        
        if not resumes:
            st.info("No resume rounds recorded yet.")
        else:
            options = {f"{r['date']} - {r['topic']} ({r['difficulty']}) | Score: {r['overall_score']}/10": r for r in resumes}
            selected_label = st.selectbox("Select past resume round to review:", list(options.keys()))
            selected_item = options[selected_label]
            
            # Display detailed view
            int_id = selected_item['interview_id']
            qas = db.get_interview_qas(int_id)
            
            st.markdown(f"### Review: **{selected_item['topic']}**")
            st.write(f"📅 **Date:** {selected_item['date']} | 🏆 **Overall Score:** {selected_item['overall_score']}/10")
            
            for qa_idx, qa in enumerate(qas):
                score_val = qa['reviewer_score']
                time_val = qa['time_taken']
                t_m = time_val // 60
                t_s = time_val % 60
                time_taken_str = f"{t_m}m {t_s}s" if t_m > 0 else f"{t_s}s"
                
                with st.container(border=True):
                    st.markdown(f"**Question {qa_idx + 1}:** {qa['question']}")
                    st.markdown(f"**Your Answer:** *{qa['user_answer_transcript']}*")
                    
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    with sc1:
                        st.metric("Fluency Score", f"{qa.get('fluency_score', 0)}/10")
                    with sc2:
                        st.metric("Professionalism", f"{qa.get('professionalism_score', 0)}/10")
                    with sc3:
                        st.metric("Technical Depth", f"{qa.get('industry_standards_score', 0)}/10")
                    with sc4:
                        st.metric("Score", f"{score_val}/10")
                        
                    st.write(f"⏱️ **Time Taken:** {time_taken_str}")
                    st.markdown(f"**AI Reviewer Reasoning:**\n{qa['reviewer_reasoning']}")
                    if qa.get('reviewer_improvements'):
                        st.markdown(f"**Suggested Improvements:**\n{qa['reviewer_improvements']}")
                        
    elif category == "Mock Tests":
        tests = db.get_detailed_test_history(user_id)
        if not tests:
            st.info("No mock tests recorded yet.")
        else:
            options = {f"{t['date']} - Topics: {t['topic_or_source']} ({t.get('difficulty', 'Medium')}) | Score: {int(t['score']*100)}%": t for t in tests}
            selected_label = st.selectbox("Select past mock test to review:", list(options.keys()))
            selected_item = options[selected_label]
            
            test_id = selected_item['test_id']
            qas = db.get_mock_test_qas(test_id)
            
            st.markdown(f"### Review: **Mock Test**")
            st.write(f"📅 **Date:** {selected_item['date']} | 🏆 **Score:** {int(selected_item['score']*100)}% | 🔢 **Questions:** {selected_item['question_count']}")
            
            for qa_idx, qa in enumerate(qas):
                bg_color = "rgba(16, 185, 129, 0.15)" if qa['is_correct'] else "rgba(239, 68, 68, 0.15)"
                border_color = "#10b981" if qa['is_correct'] else "#ef4444"
                status_txt = "Correct" if qa['is_correct'] else "Incorrect"
                
                st.markdown(f"""
                <div style='background: {bg_color}; border-left: 5px solid {border_color}; padding: 15px; border-radius: 8px; margin-bottom: 12px;'>
                    <b>Question {qa_idx+1}: {qa['question']}</b> | Topic: <span style='color:#a855f7; font-weight:600;'>{qa['topic']}</span><br>
                    Your Choice: {qa['user_choice'] or 'None'} | Correct Answer: {qa['correct_choice']}<br>
                    <span style='font-weight: bold; color: {border_color};'>{status_txt}</span>
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# MAIN APP ORCHESTRATION
# ==========================================
if not st.session_state.authenticated:
    render_auth()
else:
    render_sidebar()
    
    # Render Navigation tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Performance Dashboard", 
        "🎤 Interview Room", 
        "📄 Resume Round", 
        "📝 Mock Test Center",
        "🔍 Revisit Rounds"
    ])
    
    with tab1:
        render_dashboard()
        
    with tab2:
        render_interview_room()
        
    with tab3:
        render_resume_round()
        
    with tab4:
        render_mock_test_center()
        
    with tab5:
        render_revisit_rounds()
