import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "mock_interview_agent.db")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table with COLLATE NOCASE for case-insensitivity
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT COLLATE NOCASE,
        email TEXT UNIQUE COLLATE NOCASE,
        mobile TEXT UNIQUE COLLATE NOCASE,
        secret_key TEXT COLLATE NOCASE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create interviews table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interviews (
        interview_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        topic TEXT,
        difficulty TEXT,
        date TEXT,
        overall_score REAL,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    """)
    
    # Create interview QA logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interview_qa (
        qa_id INTEGER PRIMARY KEY AUTOINCREMENT,
        interview_id INTEGER,
        question TEXT,
        user_answer_transcript TEXT,
        reviewer_score REAL,
        reviewer_reasoning TEXT,
        reviewer_improvements TEXT,
        is_follow_up INTEGER DEFAULT 0,
        time_taken INTEGER DEFAULT 0,
        fluency_score INTEGER DEFAULT 0,
        professionalism_score INTEGER DEFAULT 0,
        industry_standards_score INTEGER DEFAULT 0,
        FOREIGN KEY (interview_id) REFERENCES interviews (interview_id)
    )
    """)
    
    # Check and perform migration for existing databases to add missing columns
    for col, col_type in [("time_taken", "INTEGER DEFAULT 0"), 
                          ("fluency_score", "INTEGER DEFAULT 0"), 
                          ("professionalism_score", "INTEGER DEFAULT 0"), 
                          ("industry_standards_score", "INTEGER DEFAULT 0"),
                          ("reviewer_improvements", "TEXT DEFAULT ''")]:
        try:
            cursor.execute(f"SELECT {col} FROM interview_qa LIMIT 1")
        except sqlite3.OperationalError:
            try:
                cursor.execute(f"ALTER TABLE interview_qa ADD COLUMN {col} {col_type}")
            except Exception as e:
                print(f"Migration warning for {col}:", e)

    # Create mock tests table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mock_tests (
        test_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        topic_or_source TEXT,
        question_count INTEGER,
        score REAL,
        date TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    """)
    
    # Create generated questions log table for repetition prevention
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS generated_questions (
        q_id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT UNIQUE COLLATE NOCASE,
        q_type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create user weak topics table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_weak_topics (
        wt_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        topic_text TEXT COLLATE NOCASE,
        incorrect_count INTEGER DEFAULT 1,
        last_incorrect_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, topic_text),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)
    
    # Create mock test QA logging table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mock_test_qa (
        qa_id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_id INTEGER,
        question TEXT,
        topic TEXT COLLATE NOCASE,
        is_correct INTEGER,
        user_choice TEXT,
        correct_choice TEXT,
        FOREIGN KEY (test_id) REFERENCES mock_tests (test_id)
    )
    """)

    # Check and perform migration for existing databases to add missing columns in mock_tests
    try:
        cursor.execute("SELECT difficulty FROM mock_tests LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor.execute("ALTER TABLE mock_tests ADD COLUMN difficulty TEXT DEFAULT 'Medium'")
        except Exception as e:
            print("Migration warning for mock_tests difficulty:", e)
            
    # Check and perform migration for existing databases to add missing columns in interview_qa
    try:
        cursor.execute("SELECT topic FROM interview_qa LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor.execute("ALTER TABLE interview_qa ADD COLUMN topic TEXT DEFAULT 'General ML'")
        except Exception as e:
            print("Migration warning for interview_qa topic:", e)

    # Check and perform migration for users table to add saved_topics column
    try:
        cursor.execute("SELECT saved_topics FROM users LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN saved_topics TEXT DEFAULT '[]'")
        except Exception as e:
            print("Migration warning for users saved_topics:", e)
            
    conn.commit()
    conn.close()

def log_generated_question(question_text, q_type):
    """Logs a generated question to prevent future repetition."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO generated_questions (question_text, q_type) VALUES (?, ?)",
            (question_text.strip(), q_type)
        )
        conn.commit()
    except Exception as e:
        print("Error logging generated question:", e)
    finally:
        conn.close()

def get_recently_generated_questions(limit=200):
    """Retrieves recently generated questions for the exclusion list."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT question_text FROM generated_questions ORDER BY q_id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        return [row['question_text'] for row in rows]
    except Exception as e:
        print("Error getting recently generated questions:", e)
        return []
    finally:
        conn.close()

def register_user(name, email, mobile, secret_key):
    """Registers a new user. Returns user_id if successful, or raises ValueError on duplicate email/mobile."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, mobile, secret_key) VALUES (?, ?, ?, ?)",
            (name.strip(), email.strip(), mobile.strip(), secret_key.strip())
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError as e:
        if "email" in str(e).lower():
            raise ValueError("An account with this email already exists.")
        elif "mobile" in str(e).lower():
            raise ValueError("An account with this mobile number already exists.")
        else:
            raise ValueError("Database integrity error: " + str(e))
    finally:
        conn.close()

def login_user(email, secret_key):
    """Logins user. Returns user dictionary if successful, None otherwise."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Since email and secret_key are COLLATE NOCASE, SQLite automatically does case-insensitive comparison
    cursor.execute(
        "SELECT * FROM users WHERE email = ? AND secret_key = ?",
        (email.strip(), secret_key.strip())
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def reset_secret_key(email, mobile, new_secret_key):
    """Resets user's secret key if email and mobile match. Returns True on success, False otherwise."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Verify email and mobile match
    cursor.execute(
        "SELECT user_id FROM users WHERE email = ? AND mobile = ?",
        (email.strip(), mobile.strip())
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
        
    user_id = row['user_id']
    cursor.execute(
        "UPDATE users SET secret_key = ? WHERE user_id = ?",
        (new_secret_key.strip(), user_id)
    )
    conn.commit()
    conn.close()
    return True

def create_interview(user_id, topic, difficulty):
    """Creates a new interview record and returns its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO interviews (user_id, topic, difficulty, date, overall_score) VALUES (?, ?, ?, ?, ?)",
        (user_id, topic, difficulty, date_str, 0.0)
    )
    conn.commit()
    interview_id = cursor.lastrowid
    conn.close()
    return interview_id

def log_interview_qa(interview_id, question, user_answer_transcript, reviewer_score, reviewer_reasoning, reviewer_improvements="", is_follow_up=0, time_taken=0, fluency_score=0, professionalism_score=0, industry_standards_score=0, topic="General ML"):
    """Logs a single question and answer in an interview session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO interview_qa 
           (interview_id, question, user_answer_transcript, reviewer_score, reviewer_reasoning, reviewer_improvements, is_follow_up, time_taken, fluency_score, professionalism_score, industry_standards_score, topic) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (interview_id, question, user_answer_transcript, reviewer_score, reviewer_reasoning, reviewer_improvements, is_follow_up, time_taken, fluency_score, professionalism_score, industry_standards_score, topic)
    )
    conn.commit()
    conn.close()

def finalize_interview_score(interview_id):
    """Calculates and updates the overall average score for an interview."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT AVG(reviewer_score) as avg_score FROM interview_qa WHERE interview_id = ? AND reviewer_score IS NOT NULL",
        (interview_id,)
    )
    row = cursor.fetchone()
    avg_score = row['avg_score'] if row['avg_score'] is not None else 0.0
    
    cursor.execute(
        "UPDATE interviews SET overall_score = ? WHERE interview_id = ?",
        (round(avg_score, 2), interview_id)
    )
    conn.commit()
    conn.close()
    return avg_score

def log_mock_test(user_id, topic_or_source, question_count, score, difficulty="Medium"):
    """Logs a completed mock test attempt."""
    conn = get_db_connection()
    cursor = conn.cursor()
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO mock_tests (user_id, topic_or_source, question_count, score, date, difficulty) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, topic_or_source, question_count, score, date_str, difficulty)
    )
    conn.commit()
    conn.close()
    return cursor.lastrowid

def get_user_progress(user_id):
    """
    Fetches average daily interview scores and test scores for plotting.
    Returns:
        dict: {
            'interviews': list of (date_str, avg_score),
            'tests': list of (date_str, avg_score)
        }
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get daily average interview scores (group by date portion of datetime)
    cursor.execute(
        """
        SELECT substr(date, 1, 10) as day, AVG(overall_score) as avg_score 
        FROM interviews 
        WHERE user_id = ? 
        GROUP BY day 
        ORDER BY day ASC
        """,
        (user_id,)
    )
    interview_rows = cursor.fetchall()
    
    # Get daily average mock test scores
    cursor.execute(
        """
        SELECT substr(date, 1, 10) as day, AVG(score) as avg_score 
        FROM mock_tests 
        WHERE user_id = ? 
        GROUP BY day 
        ORDER BY day ASC
        """,
        (user_id,)
    )
    test_rows = cursor.fetchall()
    
    conn.close()
    
    return {
        'interviews': [(r['day'], r['avg_score']) for r in interview_rows],
        'tests': [(r['day'], r['avg_score']) for r in test_rows]
    }

def get_interview_qas(interview_id):
    """Fetches all questions and answers logged for a specific interview."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM interview_qa WHERE interview_id = ? ORDER BY qa_id ASC",
        (interview_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def log_weak_topic(user_id, topic_text):
    """Logs or increments user weakness count for a sub-topic."""
    if not topic_text or not topic_text.strip():
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO user_weak_topics (user_id, topic_text, incorrect_count)
               VALUES (?, ?, 1)
               ON CONFLICT(user_id, topic_text) DO UPDATE SET
               incorrect_count = incorrect_count + 1,
               last_incorrect_at = CURRENT_TIMESTAMP""",
            (user_id, topic_text.strip())
        )
        conn.commit()
    except Exception as e:
        print("Error logging weak topic:", e)
    finally:
        conn.close()

def get_user_weak_topics(user_id, limit=5):
    """Retrieves top weak sub-topics for user, sorted by incorrect_count."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT topic_text FROM user_weak_topics WHERE user_id = ? ORDER BY incorrect_count DESC, last_incorrect_at DESC LIMIT ?",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        return [row['topic_text'] for row in rows]
    except Exception as e:
        print("Error getting weak topics:", e)
        return []
    finally:
        conn.close()

def log_mock_test_qa(test_id, question, topic, is_correct, user_choice, correct_choice):
    """Logs individual MCQ question response for weakness and topic progress reporting."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO mock_test_qa (test_id, question, topic, is_correct, user_choice, correct_choice)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (test_id, question, topic.strip() if topic else 'General ML', int(is_correct), user_choice, correct_choice)
        )
        conn.commit()
    except Exception as e:
        print("Error logging mock test QA:", e)
    finally:
        conn.close()

def get_topic_progress_report(user_id):
    """
    Calculates the dynamic performance percentage of each sub-topic.
    Aggregates interview scores (score/10) and mock test answers (is_correct).
    Returns list of dicts: [{'topic': '...', 'percentage': 85}]
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    report = {}
    try:
        # 1. Fetch from interview_qa
        cursor.execute(
            """SELECT q.topic, q.reviewer_score
               FROM interview_qa q
               JOIN interviews i ON q.interview_id = i.interview_id
               WHERE i.user_id = ? AND q.reviewer_score IS NOT NULL""",
            (user_id,)
        )
        rows = cursor.fetchall()
        for r in rows:
            t = r['topic'].strip() if r['topic'] else 'General ML'
            t_normalized = t.title()
            score = float(r['reviewer_score']) / 10.0  # normalize to 0-1
            if t_normalized not in report:
                report[t_normalized] = []
            report[t_normalized].append(score)

        # 2. Fetch from mock_test_qa
        cursor.execute(
            """SELECT mq.topic, mq.is_correct
               FROM mock_test_qa mq
               JOIN mock_tests mt ON mq.test_id = mt.test_id
               WHERE mt.user_id = ?""",
            (user_id,)
        )
        rows = cursor.fetchall()
        for r in rows:
            t = r['topic'].strip() if r['topic'] else 'General ML'
            t_normalized = t.title()
            score = float(r['is_correct'])  # 0 or 1
            if t_normalized not in report:
                report[t_normalized] = []
            report[t_normalized].append(score)
            
    except Exception as e:
        print("Error generating topic progress report:", e)
    finally:
        conn.close()

    result = []
    for topic, scores in report.items():
        if scores:
            avg_pct = int(round((sum(scores) / len(scores)) * 100))
            result.append({'topic': topic, 'percentage': avg_pct})
            
    result.sort(key=lambda x: x['percentage'], reverse=True)
    return result

def get_resume_efficiency(user_id):
    """
    Computes overall average score percentage for resume rounds.
    Defined as interviews where topic starts with "Resume:".
    Returns integer percentage, or 0 if no resume rounds completed.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """SELECT AVG(overall_score) as avg_score
               FROM interviews
               WHERE user_id = ? AND topic LIKE 'Resume:%' AND overall_score > 0""",
            (user_id,)
        )
        row = cursor.fetchone()
        if row and row['avg_score'] is not None:
            return int(round(row['avg_score'] * 10))  # E.g. 8.5/10 -> 85%
    except Exception as e:
        print("Error getting resume efficiency:", e)
    finally:
        conn.close()
    return 0

def get_detailed_interview_history(user_id):
    """Fetches list of completed interviews and resume rounds with durations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """SELECT i.interview_id, i.topic, i.difficulty, i.date, i.overall_score,
                      COUNT(q.qa_id) as total_questions,
                      AVG(q.time_taken) as avg_time_taken
               FROM interviews i
               LEFT JOIN interview_qa q ON i.interview_id = q.interview_id
               WHERE i.user_id = ?
               GROUP BY i.interview_id
               ORDER BY i.date DESC""",
            (user_id,)
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print("Error getting detailed interview history:", e)
        return []
    finally:
        conn.close()

def get_detailed_test_history(user_id):
    """Fetches detailed mock test attempt history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM mock_tests WHERE user_id = ? ORDER BY date DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print("Error getting detailed test history:", e)
        return []
    finally:
        conn.close()

def save_user_topics(user_id, topics_list):
    """Saves user's preferred topics as a JSON list in the database."""
    import json
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET saved_topics = ? WHERE user_id = ?",
            (json.dumps(topics_list), user_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print("Error saving user topics:", e)
        return False
    finally:
        conn.close()

def get_user_topics(user_id):
    """Retrieves user's preferred topics as a list of strings."""
    import json
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT saved_topics FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row['saved_topics']:
            return json.loads(row['saved_topics'])
    except Exception as e:
        print("Error getting user topics:", e)
    finally:
        conn.close()
    return []

def get_mock_test_qas(test_id):
    """Fetches all questions and answers logged for a specific mock test."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM mock_test_qa WHERE test_id = ? ORDER BY qa_id ASC",
            (test_id,)
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print("Error getting mock test QAs:", e)
        return []
    finally:
        conn.close()
