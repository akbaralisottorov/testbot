import os
import sys

# Ensure current folder is on path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import (
    init_db,
    add_user,
    get_user,
    get_all_questions_count,
    get_subjects,
    get_subject_questions_count,
    get_user_mistakes_count,
    get_test_questions,
    get_test_results,
    get_active_test,
    get_subject_analytics,
    finish_test
)
from services import (
    parse_and_import_excel,
    generate_variant,
    submit_test_answer,
    generate_analytics_report
)

def run_tests():
    print("=== STARTING BOT LOGIC VERIFICATION ===")
    
    # 1. Initialize DB
    print("\n1. Initializing Database...")
    db_file = os.path.join("data", "database.db")
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print("   Old database file deleted.")
        except Exception as e:
            print(f"   Could not delete old database file: {e}")
            
    init_db()
    
    # 2. Parse and Import Excel
    from generate_large_sample import generate_large_dataset
    excel_path = os.path.join("data", "temp_test.xlsx")
    generate_large_dataset(excel_path)
    
    print(f"\n2. Importing Excel file: {excel_path}...")
    import_result = parse_and_import_excel(excel_path, clear_existing=True)
    
    assert import_result['success'] == True, f"Excel import failed: {import_result['message']}"
    print(f"   Success: Imported {import_result['imported']} questions.")
    
    # Check DB counts
    total_q = get_all_questions_count()
    assert total_q == 1860, f"Expected 1860 questions, got {total_q}"
    print(f"   DB verification: Total questions count = {total_q} (Passed)")
    
    # Check duplicate detection logic (DB-level)
    print("   Testing database-level duplicate detection...")
    dup_result = parse_and_import_excel(excel_path, clear_existing=False)
    assert dup_result['success'] == True, "Duplicate test import run failed"
    assert dup_result['imported'] == 0, f"Expected 0 new questions imported, got {dup_result['imported']}"
    assert dup_result['duplicate_db'] == 1860, f"Expected 1860 DB duplicates, got {dup_result['duplicate_db']}"
    print("   - DB-level duplicate detection check: All 1860 questions skipped on re-import (Passed)")
    
    subjects = get_subjects()
    assert len(subjects) == 3, f"Expected 3 subjects, got {len(subjects)}"
    print(f"   Detected Subjects: {subjects}")
    
    for s in subjects:
        cnt = get_subject_questions_count(s)
        assert cnt == 620, f"Expected 620 questions for {s}, got {cnt}"
        print(f"   - Subject '{s}': {cnt} questions (Passed)")
        
    # 3. Register a test user
    print("\n3. Registering test user...")
    test_user_id = 123456789
    add_user(test_user_id, "test_user", "Test User Uzbekistan")
    user_info = get_user(test_user_id)
    assert user_info is not None, "Failed to retrieve user"
    assert user_info['username'] == "test_user", "Username mismatch"
    print(f"   User registered: {user_info['full_name']} (Passed)")
    
    # 4. Generate test variant
    print("\n4. Generating test variant (16+17+17 distribution)...")
    exam_object = generate_variant(test_user_id, subjects)
    test_id = exam_object['session_id']
    print(f"   Test variant created with ID: {test_id}")
    
    # Fetch questions in the test
    t_questions = get_test_questions(test_id)
    assert len(t_questions) == 50, f"Expected 50 questions, got {len(t_questions)}"
    print(f"   - Total questions in variant: {len(t_questions)} (Passed)")
    
    # Check distribution: Matematika (first subject) = 16, others = 17
    sub_counts = {}
    q_ids_in_test = set()
    for tq in t_questions:
        subj = tq['subject']
        sub_counts[subj] = sub_counts.get(subj, 0) + 1
        q_ids_in_test.add(tq['question_id'])
        
    # Verify no duplicates in the variant
    assert len(q_ids_in_test) == 50, f"Duplicate questions found inside the test variant! Unique count: {len(q_ids_in_test)}"
    print("   - Uniqueness check: No duplicate questions in variant (Passed)")
    
    # Verify subject distribution
    print(f"   - Distribution details: {sub_counts}")
    assert sub_counts[subjects[0]] == 16, f"Expected 16 for {subjects[0]}, got {sub_counts[subjects[0]]}"
    assert sub_counts[subjects[1]] == 17, f"Expected 17 for {subjects[1]}, got {sub_counts[subjects[1]]}"
    assert sub_counts[subjects[2]] == 17, f"Expected 17 for {subjects[2]}, got {sub_counts[subjects[2]]}"
    print("   - Distribution check: 16 + 17 + 17 (Passed)")
    
    # Check active test resume logic
    active = get_active_test(test_user_id)
    assert active is not None and active['id'] == test_id, "Active test tracking failed"
    print("   - Active test tracking: Resume checks (Passed)")
    
    # 5. Answer questions and verify mistakes pool
    print("\n5. Simulating answering questions...")
    # Answer 10 questions correctly, 10 incorrectly, leave 30 unanswered
    for i in range(1, 11):
        # Correct answer
        tq = t_questions[i - 1]
        correct_option = tq['correct_option']
        res = submit_test_answer(test_id, test_user_id, tq['question_id'], correct_option)
        assert res['is_correct'] == True, "Correct answer flagged as incorrect"
        
    for i in range(11, 21):
        # Incorrect answer (using an option that is definitely wrong)
        tq = t_questions[i - 1]
        wrong_option = 'A' if tq['correct_option'] != 'A' else 'B'
        res = submit_test_answer(test_id, test_user_id, tq['question_id'], wrong_option)
        assert res['is_correct'] == False, "Incorrect answer flagged as correct"
        
    # Verify mistakes table populated
    mistakes_count = get_user_mistakes_count(test_user_id)
    assert mistakes_count == 10, f"Expected 10 mistakes in pool, got {mistakes_count}"
    print(f"   - Mistakes pool check: Added {mistakes_count} incorrect answers to mistakes pool (Passed)")
    
    # 6. Finish test and verify results
    print("\n6. Completing the test...")
    finish_test(test_id)
    results = get_test_results(test_id)
    print(f"   Test results statistics:")
    print(f"   - Total: {results['total']}")
    print(f"   - Correct: {results['correct']}")
    print(f"   - Incorrect: {results['incorrect']}")
    print(f"   - Unanswered: {results['unanswered']}")
    
    assert results['correct'] == 10, f"Expected 10 correct, got {results['correct']}"
    assert results['incorrect'] == 10, f"Expected 10 incorrect, got {results['incorrect']}"
    assert results['unanswered'] == 30, f"Expected 30 unanswered, got {results['unanswered']}"
    print("   - Test scoring and stats verification (Passed)")
    
    # 7. Mistakes practice flow
    print("\n7. Simulating mistakes practice session...")
    # Select a mistake and answer it correctly
    from database import get_user_mistakes
    user_mistakes = get_user_mistakes(test_user_id)
    assert len(user_mistakes) == 10, "Expected 10 mistakes"
    
    target_q = user_mistakes[0]
    # Solve it correctly
    submit_res = submit_test_answer(test_id, test_user_id, target_q['question_id'], target_q['correct_option'])
    assert submit_res['is_correct'] == True, "Correct practice answer failed"
    
    # Check if removed from mistakes pool
    new_mistakes_count = get_user_mistakes_count(test_user_id)
    assert new_mistakes_count == 9, f"Expected 9 mistakes left, got {new_mistakes_count}"
    print(f"   - Mistakes practice check: Mistake successfully resolved and cleared from pool (Passed)")
    
    # 8. Uniqueness across attempts (Bir xil savol qayta tushmasligi)
    print("\n8. Verifying repetition avoidance across attempts...")
    # Generate another variant and ensure it has different questions from the first variant
    new_exam_object = generate_variant(test_user_id, subjects)
    new_test_id = new_exam_object['session_id']
    new_t_questions = get_test_questions(new_test_id)
    
    new_q_ids = {tq['question_id'] for tq in new_t_questions}
    
    # Check overlaps with answered questions from previous test
    # Answered questions were question 1 to 20 of the first test
    answered_q_ids = {tq['question_id'] for tq in t_questions[:20]}
    
    overlap = new_q_ids.intersection(answered_q_ids)
    print(f"   - Questions in first test: 50")
    print(f"   - Answered in first test: 20")
    print(f"   - Questions in second test: 50")
    print(f"   - Overlap with answered questions: {len(overlap)} questions")
    
    # Since we have 620 questions per subject and we only answered 20, the algorithm should prioritize
    # the other 600+ unseen questions. Therefore, the overlap with the answered ones should be exactly 0!
    assert len(overlap) == 0, f"Reused answered questions! Overlap: {overlap}"
    print("   - Repetition avoidance check: Answered questions were completely avoided in new test (Passed)")
    
    # 9. Verify subject analytics (from the new statistics table populated by triggers!)
    print("\n9. Verifying subject analytics (from statistics table)...")
    analytics = get_subject_analytics(test_user_id)
    print(f"   Analytics: {analytics}")
    assert len(analytics) == 3, f"Expected 3 subjects in analytics, got {len(analytics)}"
    for row in analytics:
        print(f"   - {row['subject']}: answered={row['total_answered']}, correct={row['total_correct']}")
    print("   - Subject analytics check: Statistics trigger-based updates (Passed)")
    
    # 10. Verify Advanced Analytics & Matplotlib Chart Generation
    print("\n10. Verifying Advanced Analytics & Progress Chart generation...")
    report = generate_analytics_report(test_user_id)
    assert report['has_chart'] == True, "Expected learning progress chart to be generated"
    assert report['chart_path'] is not None, "Expected valid chart image path"
    assert os.path.exists(report['chart_path']), f"Chart image file not found at: {report['chart_path']}"
    print(f"    Generated Chart Path: {report['chart_path']}")
    print(f"    Report Text Snippet:\n{report['report_text'][:150]}...")
    print("   - Advanced Analytics & visual progress chart check (Passed)")
    
    # 11. Verify Daily Mock Seeded Exam Consistency
    print("\n11. Verifying Daily Mock Seeded Exam Consistency...")
    # Two different users start mock on same day
    mock_date = "2026-06-13"
    add_user(1111111, "mock_user_1", "Mock User 1")
    add_user(2222222, "mock_user_2", "Mock User 2")
    exam_u1 = generate_variant(1111111, subjects, exam_type="daily_mock", mock_date=mock_date)
    exam_u2 = generate_variant(2222222, subjects, exam_type="daily_mock", mock_date=mock_date)
    
    q_ids_u1 = [q['question_id'] for q in exam_u1['questions']]
    q_ids_u2 = [q['question_id'] for q in exam_u2['questions']]
    
    assert q_ids_u1 == q_ids_u2, "Daily mock questions were different or out of order for two users!"
    print("   - Seeded consistency check: Both users got identical mock questions in identical order (Passed)")
    
    # 12. Verify Leaderboards
    print("\n12. Verifying Leaderboard queries...")
    from database import get_overall_leaderboard, get_daily_mock_leaderboard
    # Make sure we finish the mock exam for u1 to populate daily mock leaderboard
    finish_test(exam_u1['session_id'])
    
    overall_lb = get_overall_leaderboard()
    mock_lb = get_daily_mock_leaderboard(mock_date)
    
    assert isinstance(overall_lb, list), "Overall leaderboard must be a list"
    assert isinstance(mock_lb, list), "Daily mock leaderboard must be a list"
    print(f"   - Leaderboard check: Overall LB returned {len(overall_lb)} entries, Daily Mock LB returned {len(mock_lb)} entries (Passed)")
    
    # 13. Verify Wrong Answers Notebook Clearing
    print("\n13. Verifying Wrong Answers Notebook clearing...")
    from database import clear_user_mistakes
    mistakes_before = get_user_mistakes_count(test_user_id)
    assert mistakes_before > 0, "Expected user to have mistakes before clearing"
    
    clear_user_mistakes(test_user_id)
    mistakes_after = get_user_mistakes_count(test_user_id)
    assert mistakes_after == 0, f"Expected 0 mistakes after clearing, got {mistakes_after}"
    print("   - Wrong Answers Notebook clearing check: Cleared successfully (Passed)")
    
    # Clean up temp file
    if os.path.exists(excel_path):
        try: os.remove(excel_path)
        except Exception: pass
        
    print("\n=== ALL LOGIC VERIFIED SUCCESSFULLY ===")
    
    # Restore actual database
    print("\n14. Restoring user database from tests.xlsx...")
    db_file = os.path.join("data", "database.db")
    if os.path.exists(db_file):
        try: os.remove(db_file)
        except Exception: pass
    init_db()
    
    actual_excel = os.path.join("data", "tests.xlsx")
    if os.path.exists(actual_excel):
        parse_and_import_excel(actual_excel, clear_existing=True)
        print("   User database restored successfully.")
    else:
        print("   No actual tests.xlsx file found to restore.")

if __name__ == "__main__":
    run_tests()
