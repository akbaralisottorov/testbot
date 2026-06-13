import os
import logging
import pandas as pd
from database import get_db_connection, add_question, clear_questions

# Setup Logger
logger = logging.getLogger("excel_parser")

def parse_and_import_excel(file_path: str, clear_existing: bool = False) -> dict:
    """
    Parses an Excel file containing questions and loads them into the SQLite database.
    
    Requirements covered:
    - strict header validation
    - data validation (correct answers A-D, missing fields)
    - duplicate detection (in-file and in-database)
    - logging & error handling
    """
    logger.info(f"Starting Excel import from: {file_path} (clear_existing={clear_existing})")
    
    if not os.path.exists(file_path):
        err_msg = f"Excel import failed: file not found at {file_path}"
        logger.error(err_msg)
        return {"success": False, "message": err_msg}
    
    try:
        # Read Excel file using pandas (openpyxl engine)
        df = pd.read_excel(file_path, engine="openpyxl")
    except Exception as e:
        err_msg = f"Failed to read Excel file: {str(e)}"
        logger.exception(err_msg)
        return {"success": False, "message": err_msg}
        
    # Check required headers (Strict validation)
    required_cols = ['subject', 'question', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
    excel_cols = [str(c).strip().lower() for c in df.columns]
    
    # Map headers to find exact columns
    found_cols = {}
    missing_cols = []
    
    for req in required_cols:
        if req in excel_cols:
            idx = excel_cols.index(req)
            found_cols[req] = df.columns[idx]
        else:
            missing_cols.append(req)
            
    # Include explanation as optional column if exists
    explanation_col = None
    if 'explanation' in excel_cols:
        idx = excel_cols.index('explanation')
        explanation_col = df.columns[idx]
        
    if missing_cols:
        err_msg = f"Header validation failed. Missing required columns: {missing_cols}"
        logger.error(err_msg)
        return {"success": False, "message": err_msg}
        
    # Clean database if requested
    if clear_existing:
        logger.info("Clearing existing questions from the database as requested.")
        clear_questions()
        
    imported_count = 0
    skipped_count = 0
    duplicate_sheet_count = 0
    duplicate_db_count = 0
    errors = []
    
    # Set to keep track of duplicates within the same sheet during this run
    seen_in_sheet = set()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Iterate rows
        for index, row in df.iterrows():
            row_num = index + 2  # Excel rows are 1-indexed and header is row 1
            try:
                subject = str(row[found_cols['subject']]).strip()
                question_text = str(row[found_cols['question']]).strip()
                opt_a = str(row[found_cols['option_a']]).strip()
                opt_b = str(row[found_cols['option_b']]).strip()
                opt_c = str(row[found_cols['option_c']]).strip()
                opt_d = str(row[found_cols['option_d']]).strip()
                correct = str(row[found_cols['correct_answer']]).strip().upper()
                
                explanation = None
                if explanation_col and pd.notna(row[explanation_col]):
                    explanation = str(row[explanation_col]).strip()
                
                # 1. Validation for empty values
                if not subject or not question_text or not opt_a or not opt_b or not opt_c or not opt_d or not correct:
                    logger.warning(f"Row {row_num}: Skipped due to missing required fields.")
                    skipped_count += 1
                    errors.append(f"Qator {row_num}: To'ldirilmagan maydonlar mavjud.")
                    continue
                    
                # 2. Validation for correct answer format
                if correct not in ['A', 'B', 'C', 'D']:
                    logger.warning(f"Row {row_num}: Invalid correct answer '{correct}' (must be A, B, C, or D).")
                    skipped_count += 1
                    errors.append(f"Qator {row_num}: To'g'ri javob formatda emas ('{correct}').")
                    continue
                
                # 3. Duplicate Detection: Check within Excel sheet
                question_key = (subject.lower(), question_text.lower())
                if question_key in seen_in_sheet:
                    logger.warning(f"Row {row_num}: Duplicate question found in Excel sheet: '{question_text[:30]}...'")
                    duplicate_sheet_count += 1
                    skipped_count += 1
                    errors.append(f"Qator {row_num}: Ushbu savol faylda takrorlangan.")
                    continue
                seen_in_sheet.add(question_key)
                
                # 4. Duplicate Detection: Check against database
                cursor.execute(
                    """
                    SELECT 1 FROM questions q
                    JOIN subjects s ON q.subject_id = s.id
                    WHERE LOWER(s.name) = LOWER(?) AND LOWER(q.question_text) = LOWER(?);
                    """,
                    (subject, question_text)
                )
                if cursor.fetchone():
                    logger.info(f"Row {row_num}: Duplicate question found in Database: '{question_text[:30]}...'")
                    duplicate_db_count += 1
                    skipped_count += 1
                    errors.append(f"Qator {row_num}: Ushbu savol bazada mavjud.")
                    continue
                
                # Add to DB
                add_question(
                    subject_name=subject,
                    question=question_text,
                    option_a=opt_a,
                    option_b=opt_b,
                    option_c=opt_c,
                    option_d=opt_d,
                    correct_answer=correct,
                    explanation=explanation
                )
                imported_count += 1
                
            except Exception as ex:
                logger.exception(f"Row {row_num}: Unexpected error processing row.")
                skipped_count += 1
                errors.append(f"Qator {row_num}: Kutilmagan xatolik: {str(ex)}")
                
    finally:
        conn.close()
        
    logger.info(
        f"Excel import complete. Imported: {imported_count}, Skipped: {skipped_count} "
        f"(Duplicate in sheet: {duplicate_sheet_count}, Duplicate in DB: {duplicate_db_count})"
    )
    
    return {
        "success": True,
        "imported": imported_count,
        "skipped": skipped_count,
        "duplicate_sheet": duplicate_sheet_count,
        "duplicate_db": duplicate_db_count,
        "errors": errors[:10]  # Return first 10 errors for user feedback
    }
