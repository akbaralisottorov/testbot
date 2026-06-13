import random
from database.connection import get_db_connection
from database import (
    create_test,
    add_test_question,
    save_answer,
    get_db_connection
)
from config import TEST_QUESTION_DISTRIBUTION

def generate_variant(user_id: int, selected_subjects: list, exam_type: str = 'standard', mock_date: str = None) -> dict:
    """
    Generates a 50-question test session with 16+17+17 distribution.
    For standard exams, prioritizes questions the user hasn't answered yet to avoid repetition.
    For daily mock exams, uses the mock_date as a seed to ensure identical question choice for all users.
    Returns a dict with session_id and questions list.
    """
    if len(selected_subjects) < 3:
        raise ValueError("Kamida 3 ta fan tanlanishi kerak.")
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Determine question selection strategy
        if exam_type == 'daily_mock':
            # Seeded random generator
            local_random = random.Random(mock_date)
            answered_ids = set()
        else:
            # Standard prioritization of unseen questions
            cursor.execute(
                """
                SELECT DISTINCT ea.question_id 
                FROM exam_answers ea
                JOIN exam_sessions es ON ea.session_id = es.id
                WHERE es.user_id = ? AND ea.user_answer IS NOT NULL;
                """,
                (user_id,)
            )
            answered_ids = {row[0] for row in cursor.fetchall()}
            local_random = random  # Use global random
        
        chosen_questions = []
        
        # We have 3 subjects and a distribution (16, 17, 17)
        for i, subject in enumerate(selected_subjects[:3]):
            limit = TEST_QUESTION_DISTRIBUTION[i]
            
            # Fetch all questions for this subject by joining with subjects table
            cursor.execute(
                """
                SELECT q.id 
                FROM questions q
                JOIN subjects s ON q.subject_id = s.id
                WHERE s.name = ?
                ORDER BY q.id ASC;
                """,
                (subject,)
            )
            all_subject_question_ids = [row[0] for row in cursor.fetchall()]
            
            if not all_subject_question_ids:
                raise ValueError(f"'{subject}' fanidan bazada savollar topilmadi.")
                
            if exam_type == 'daily_mock':
                # To ensure everyone gets the exact same questions, we shuffle the whole list based on date seed
                local_random.shuffle(all_subject_question_ids)
                selected_ids = all_subject_question_ids[:limit]
            else:
                # Partition into unseen and seen
                unseen = [qid for qid in all_subject_question_ids if qid not in answered_ids]
                seen = [qid for qid in all_subject_question_ids if qid in answered_ids]
                
                # Shuffle both
                random.shuffle(unseen)
                random.shuffle(seen)
                
                # Combine prioritizing unseen
                combined = unseen + seen
                selected_ids = combined[:limit]
            
            for qid in selected_ids:
                chosen_questions.append(qid)
                
        # Ensure we have questions selected
        if not chosen_questions:
            raise ValueError("Tanlangan fanlardan savollar yuklashda xatolik yuz berdi.")
            
        # Create a new test session in DB
        test_id = create_test(user_id, exam_type, mock_date)
        
        # Insert questions into the session
        # Keep them sorted/grouped by subject for a better user experience
        for idx, qid in enumerate(chosen_questions):
            add_test_question(test_id, qid, idx + 1)
            
        from database import get_test_questions
        return {
            "session_id": test_id,
            "questions": get_test_questions(test_id)
        }
        
    finally:
        conn.close()

def submit_test_answer(test_id: int, user_id: int, question_id: int, user_answer: str) -> dict:
    """
    Submits an answer for a specific question in a test.
    Updates the test session database. The database trigger (trg_after_answer_submission)
    automatically manages statistics and the mistakes pool.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Get correct answer for validation (column is correct_answer now)
        cursor.execute(
            "SELECT correct_answer, explanation FROM questions WHERE id = ?;",
            (question_id,)
        )
        row = cursor.fetchone()
        if not row:
            return {"success": False, "message": "Savol topilmadi."}
            
        correct_answer = row['correct_answer']
        explanation = row['explanation']
        
        is_correct = 1 if user_answer.upper() == correct_answer.upper() else 0
        
        # Save answer - this will trigger the database updates for stats and wrong answers
        save_answer(test_id, question_id, user_answer.upper(), is_correct)
            
        return {
            "success": True,
            "is_correct": bool(is_correct),
            "correct_option": correct_answer,
            "explanation": explanation
        }
    finally:
        conn.close()
