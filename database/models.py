import sqlite3
from database.connection import get_db_connection

def row_to_dict(row):
    return {key: row[key] for key in row.keys()} if row else None

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 2. Subjects table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );
    """)
    
    # 3. Questions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        question_text TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_answer TEXT NOT NULL,
        explanation TEXT,
        FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
    );
    """)
    
    # 4. Exam Sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exam_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        finished_at TIMESTAMP,
        is_completed INTEGER DEFAULT 0,
        exam_type TEXT DEFAULT 'standard',
        mock_date TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    );
    """)
    
    # 5. Exam Answers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exam_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        user_answer TEXT,
        is_correct INTEGER,
        question_order INTEGER NOT NULL,
        FOREIGN KEY (session_id) REFERENCES exam_sessions (id) ON DELETE CASCADE,
        FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
    );
    """)
    
    # 6. Statistics table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS statistics (
        user_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        total_answered INTEGER DEFAULT 0,
        total_correct INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, subject_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
    );
    """)
    
    # 7. Wrong Answers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wrong_answers (
        user_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, question_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
    );
    """)
    
    # Create indexes for optimization
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON exam_sessions(user_id, is_completed);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_answers_session ON exam_answers(session_id, question_id, user_answer);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wrong_answers_user ON wrong_answers(user_id);")
    
    # Migrations for existing databases
    try:
        cursor.execute("ALTER TABLE exam_sessions ADD COLUMN exam_type TEXT DEFAULT 'standard';")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE exam_sessions ADD COLUMN mock_date TEXT;")
    except sqlite3.OperationalError:
        pass
    
    # Create Trigger for Auto Statistics and Auto Wrong Answers tracking
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_after_answer_submission
    AFTER UPDATE OF user_answer, is_correct ON exam_answers
    WHEN NEW.user_answer IS NOT NULL AND NEW.is_correct IS NOT NULL
    BEGIN
        -- 1. Update subject statistics for user
        INSERT INTO statistics (user_id, subject_id, total_answered, total_correct)
        VALUES (
            (SELECT user_id FROM exam_sessions WHERE id = NEW.session_id),
            (SELECT subject_id FROM questions WHERE id = NEW.question_id),
            1,
            NEW.is_correct
        )
        ON CONFLICT(user_id, subject_id) DO UPDATE SET
            total_answered = total_answered + 1,
            total_correct = total_correct + NEW.is_correct;

        -- 2. Add to wrong answers if incorrect
        INSERT OR IGNORE INTO wrong_answers (user_id, question_id)
        SELECT es.user_id, NEW.question_id
        FROM exam_sessions es
        WHERE es.id = NEW.session_id AND NEW.is_correct = 0;

        -- 3. Delete from wrong answers if correct
        DELETE FROM wrong_answers
        WHERE question_id = NEW.question_id
          AND user_id = (SELECT user_id FROM exam_sessions WHERE id = NEW.session_id)
          AND NEW.is_correct = 1;
    END;
    """)
    
    conn.commit()
    conn.close()

# --- User Functions ---
def add_user(user_id, username, full_name):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO users (user_id, username, full_name) VALUES (?, ?, ?);",
            (user_id, username, full_name)
        )
        conn.commit()
    finally:
        conn.close()

def get_user(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?;", (user_id,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()

def get_all_users_count():
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT COUNT(*) as count FROM users;").fetchone()
        return row['count']
    finally:
        conn.close()

# --- Subject Functions ---
def add_subject(name):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO subjects (name) VALUES (?);", (name,))
        conn.commit()
        # Fetch ID
        row = conn.execute("SELECT id FROM subjects WHERE name = ?;", (name,)).fetchone()
        return row['id'] if row else None
    finally:
        conn.close()

def get_subjects():
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT name FROM subjects ORDER BY name ASC;").fetchall()
        return [row['name'] for row in rows]
    finally:
        conn.close()

# --- Question Functions ---
def add_question(subject_name, question, option_a, option_b, option_c, option_d, correct_answer, explanation=None):
    # Resolve subject_id first
    subject_id = add_subject(subject_name)
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO questions (subject_id, question_text, option_a, option_b, option_c, option_d, correct_answer, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (subject_id, question, option_a, option_b, option_c, option_d, correct_answer.upper(), explanation)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_questions_by_subject(subject_name):
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT q.*, s.name as subject 
            FROM questions q
            JOIN subjects s ON q.subject_id = s.id
            WHERE s.name = ?;
            """,
            (subject_name,)
        ).fetchall()
        return [row_to_dict(row) for row in rows]
    finally:
        conn.close()

def get_all_questions_count():
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT COUNT(*) as count FROM questions;").fetchone()
        return row['count']
    finally:
        conn.close()

def get_subject_questions_count(subject_name):
    conn = get_db_connection()
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) as count 
            FROM questions q
            JOIN subjects s ON q.subject_id = s.id
            WHERE s.name = ?;
            """,
            (subject_name,)
        ).fetchone()
        return row['count']
    finally:
        conn.close()

def clear_questions():
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM questions;")
        conn.execute("DELETE FROM subjects;")
        conn.commit()
    finally:
        conn.close()

# --- Exam Session Functions ---
def create_test(user_id, exam_type='standard', mock_date=None):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO exam_sessions (user_id, exam_type, mock_date) VALUES (?, ?, ?);",
            (user_id, exam_type, mock_date)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def finish_test(test_id):
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE exam_sessions SET finished_at = CURRENT_TIMESTAMP, is_completed = 1 WHERE id = ?;",
            (test_id,)
        )
        conn.commit()
    finally:
        conn.close()

def add_test_question(test_id, question_id, question_order):
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO exam_answers (session_id, question_id, question_order)
            VALUES (?, ?, ?);
            """,
            (test_id, question_id, question_order)
        )
        conn.commit()
    finally:
        conn.close()

def get_active_test(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM exam_sessions WHERE user_id = ? AND is_completed = 0 ORDER BY started_at DESC LIMIT 1;",
            (user_id,)
        ).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()

def delete_test(test_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM exam_sessions WHERE id = ?;", (test_id,))
        conn.commit()
    finally:
        conn.close()

def get_test_questions(test_id):
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT ea.*, s.name as subject, q.question_text as question, q.option_a, q.option_b, q.option_c, q.option_d, q.correct_answer as correct_option, q.explanation
            FROM exam_answers ea
            JOIN questions q ON ea.question_id = q.id
            JOIN subjects s ON q.subject_id = s.id
            WHERE ea.session_id = ?
            ORDER BY ea.question_order ASC;
            """,
            (test_id,)
        )
        return [row_to_dict(row) for row in rows]
    finally:
        conn.close()

def get_test_question_by_order(test_id, order):
    conn = get_db_connection()
    try:
        row = conn.execute(
            """
            SELECT ea.*, s.name as subject, q.question_text as question, q.option_a, q.option_b, q.option_c, q.option_d, q.correct_answer as correct_option, q.explanation
            FROM exam_answers ea
            JOIN questions q ON ea.question_id = q.id
            JOIN subjects s ON q.subject_id = s.id
            WHERE ea.session_id = ? AND ea.question_order = ?;
            """,
            (test_id, order)
        ).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()

def save_answer(test_id, question_id, user_answer, is_correct):
    conn = get_db_connection()
    try:
        conn.execute(
            """
            UPDATE exam_answers
            SET user_answer = ?, is_correct = ?
            WHERE session_id = ? AND question_id = ?;
            """,
            (user_answer, is_correct, test_id, question_id)
        )
        conn.commit()
    finally:
        conn.close()

def get_test_results(test_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Total questions
        cursor.execute("SELECT COUNT(*) FROM exam_answers WHERE session_id = ?;", (test_id,))
        total = cursor.fetchone()[0]
        
        # Correct questions
        cursor.execute("SELECT COUNT(*) FROM exam_answers WHERE session_id = ? AND is_correct = 1;", (test_id,))
        correct = cursor.fetchone()[0]
        
        # Incorrect questions
        cursor.execute("SELECT COUNT(*) FROM exam_answers WHERE session_id = ? AND is_correct = 0 AND user_answer IS NOT NULL;", (test_id,))
        incorrect = cursor.fetchone()[0]
        
        # Unanswered questions
        cursor.execute("SELECT COUNT(*) FROM exam_answers WHERE session_id = ? AND user_answer IS NULL;", (test_id,))
        unanswered = cursor.fetchone()[0]
        
        # Subject breakdown
        cursor.execute(
            """
            SELECT s.name as subject, COUNT(*) as total, SUM(ea.is_correct) as correct
            FROM exam_answers ea
            JOIN questions q ON ea.question_id = q.id
            JOIN subjects s ON q.subject_id = s.id
            WHERE ea.session_id = ?
            GROUP BY s.id;
            """,
            (test_id,)
        )
        breakdown = [row_to_dict(row) for row in cursor.fetchall()]
        
        # Fetch started/finished time
        cursor.execute("SELECT started_at, finished_at FROM exam_sessions WHERE id = ?;", (test_id,))
        times = cursor.fetchone()
        
        return {
            "total": total,
            "correct": correct,
            "incorrect": incorrect,
            "unanswered": unanswered,
            "breakdown": breakdown,
            "started_at": times[0] if times else None,
            "finished_at": times[1] if times else None
        }
    finally:
        conn.close()

def get_user_completed_tests_count(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT COUNT(*) as count FROM exam_sessions WHERE user_id = ? AND is_completed = 1;", (user_id,)).fetchone()
        return row['count']
    finally:
        conn.close()

def get_total_completed_tests_count():
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT COUNT(*) as count FROM exam_sessions WHERE is_completed = 1;").fetchone()
        return row['count']
    finally:
        conn.close()

# --- Mistakes/Wrong Answers Functions ---
def get_user_mistakes(user_id):
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT wa.question_id, s.name as subject, q.question_text as question, q.option_a, q.option_b, q.option_c, q.option_d, q.correct_answer as correct_option, q.explanation
            FROM wrong_answers wa
            JOIN questions q ON wa.question_id = q.id
            JOIN subjects s ON q.subject_id = s.id
            WHERE wa.user_id = ?
            ORDER BY wa.added_at DESC;
            """,
            (user_id,)
        )
        return [row_to_dict(row) for row in rows]
    finally:
        conn.close()

def get_user_mistakes_count(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT COUNT(*) as count FROM wrong_answers WHERE user_id = ?;", (user_id,)).fetchone()
        return row['count']
    finally:
        conn.close()

def remove_mistake(user_id, question_id):
    conn = get_db_connection()
    try:
        conn.execute(
            "DELETE FROM wrong_answers WHERE user_id = ? AND question_id = ?;",
            (user_id, question_id)
        )
        conn.commit()
    finally:
        conn.close()

# --- Subject Analytics Functions ---
def get_subject_analytics(user_id):
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT s.name as subject, 
                   COALESCE(st.total_answered, 0) as total_answered, 
                   COALESCE(st.total_correct, 0) as total_correct
            FROM subjects s
            LEFT JOIN statistics st ON s.id = st.subject_id AND st.user_id = ?
            ORDER BY s.name ASC;
            """,
            (user_id,)
        ).fetchall()
        return [row_to_dict(row) for row in rows]
    finally:
        conn.close()

# --- Exam History and Overall Stats Functions ---
def get_user_exam_history(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT es.id, es.started_at, es.finished_at, es.exam_type, es.mock_date,
                   (SELECT COUNT(*) FROM exam_answers WHERE session_id = es.id AND is_correct = 1) as correct,
                   (SELECT COUNT(*) FROM exam_answers WHERE session_id = es.id) as total
            FROM exam_sessions es
            WHERE es.user_id = ? AND es.is_completed = 1
            ORDER BY es.finished_at DESC;
            """,
            (user_id,)
        )
        return [row_to_dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_user_overall_stats(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM exam_sessions WHERE user_id = ? AND is_completed = 1;", (user_id,))
        exams_count = cursor.fetchone()[0]
        
        cursor.execute(
            """
            SELECT SUM(total_answered) as total, SUM(total_correct) as correct
            FROM statistics
            WHERE user_id = ?;
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        total_answered = row[0] if row[0] is not None else 0
        total_correct = row[1] if row[1] is not None else 0
        
        return {
            "exams_completed": exams_count,
            "total_answered": total_answered,
            "total_correct": total_correct,
            "total_wrong": total_answered - total_correct
        }
    finally:
        conn.close()

# --- Admin Operations ---
def delete_question(qid):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM questions WHERE id = ?;", (qid,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def get_question(qid):
    conn = get_db_connection()
    try:
        row = conn.execute(
            """
            SELECT q.*, s.name as subject 
            FROM questions q 
            JOIN subjects s ON q.subject_id = s.id 
            WHERE q.id = ?;
            """, 
            (qid,)
        ).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()

def edit_question(qid, subject_name, question, option_a, option_b, option_c, option_d, correct_answer, explanation=None):
    subject_id = add_subject(subject_name)
    conn = get_db_connection()
    try:
        conn.execute(
            """
            UPDATE questions 
            SET subject_id = ?, question_text = ?, option_a = ?, option_b = ?, option_c = ?, option_d = ?, correct_answer = ?, explanation = ?
            WHERE id = ?;
            """,
            (subject_id, question, option_a, option_b, option_c, option_d, correct_answer.upper(), explanation, qid)
        )
        conn.commit()
    finally:
        conn.close()

def get_all_users():
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM users;").fetchall()
        return [row_to_dict(row) for row in rows]
    finally:
        conn.close()

def get_all_exam_results():
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT es.id as session_id, u.full_name, u.username, es.started_at, es.finished_at,
                   (SELECT COUNT(*) FROM exam_answers WHERE session_id = es.id AND is_correct = 1) as correct,
                   (SELECT COUNT(*) FROM exam_answers WHERE session_id = es.id) as total
            FROM exam_sessions es
            JOIN users u ON es.user_id = u.user_id
            WHERE es.is_completed = 1
            ORDER BY es.finished_at DESC;
            """
        ).fetchall()
        return [row_to_dict(row) for row in rows]
    finally:
        conn.close()

def has_taken_daily_mock(user_id: int, date_str: str) -> bool:
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM exam_sessions WHERE user_id = ? AND exam_type = 'daily_mock' AND mock_date = ? LIMIT 1;",
            (user_id, date_str)
        ).fetchone()
        return row is not None
    finally:
        conn.close()

def get_overall_leaderboard():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.user_id, u.full_name, u.username,
                   COUNT(stats.id) as total_exams,
                   SUM(stats.correct_count) as total_correct,
                   SUM(stats.total_count) as total_questions,
                   ROUND(AVG(CAST(stats.correct_count AS REAL) / stats.total_count * 100), 1) as avg_percent
            FROM (
                SELECT es.id, es.user_id,
                       SUM(ea.is_correct) as correct_count,
                       COUNT(ea.id) as total_count
                FROM exam_sessions es
                JOIN exam_answers ea ON es.id = ea.session_id
                WHERE es.is_completed = 1
                GROUP BY es.id
            ) stats
            JOIN users u ON stats.user_id = u.user_id
            GROUP BY u.user_id
            ORDER BY avg_percent DESC, total_exams DESC, total_correct DESC
            LIMIT 10;
            """
        )
        return [row_to_dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_daily_mock_leaderboard(date_str: str):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.user_id, u.full_name, u.username,
                   SUM(ea.is_correct) as correct_count,
                   COUNT(ea.id) as total_count,
                   (strftime('%s', es.finished_at) - strftime('%s', es.started_at)) as duration_sec
            FROM exam_sessions es
            JOIN exam_answers ea ON es.id = ea.session_id
            JOIN users u ON es.user_id = u.user_id
            WHERE es.is_completed = 1 AND es.exam_type = 'daily_mock' AND es.mock_date = ?
            GROUP BY es.id
            ORDER BY correct_count DESC, duration_sec ASC
            LIMIT 10;
            """,
            (date_str,)
        )
        return [row_to_dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def clear_user_mistakes(user_id: int):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM wrong_answers WHERE user_id = ?;", (user_id,))
        conn.commit()
    finally:
        conn.close()

def export_questions_to_excel(file_path: str):
    import pandas as pd
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.name as subject, q.question_text as question, 
                   q.option_a, q.option_b, q.option_c, q.option_d, 
                   q.correct_answer, q.explanation
            FROM questions q
            JOIN subjects s ON q.subject_id = s.id
            ORDER BY q.id ASC;
            """
        )
        rows = cursor.fetchall()
        data = []
        for r in rows:
            data.append({
                'subject': r['subject'],
                'question': r['question'],
                'option_a': r['option_a'],
                'option_b': r['option_b'],
                'option_c': r['option_c'],
                'option_d': r['option_d'],
                'correct_answer': r['correct_answer'],
                'explanation': r['explanation']
            })
        df = pd.DataFrame(data)
        df.to_excel(file_path, index=False, engine="openpyxl")
    finally:
        conn.close()
