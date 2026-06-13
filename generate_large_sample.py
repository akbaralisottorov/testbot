import os
import pandas as pd
from config import DATA_DIR

def generate_large_dataset():
    subjects = [
        ("Matematika", "savol", "A", "B", "C", "D", "B", "Matematik tushuntirish"),
        ("Ona tili", "ona tili test savoli", "To'g'ri variant", "Noto'g'ri 1", "Noto'g'ri 2", "Noto'g'ri 3", "A", "Ona tili grammatikasi izohi"),
        ("Tarix", "tarixiy voqea haqida savol", "To'g'ri javob", "Xato 1", "Xato 2", "Xato 3", "A", "Tarixiy manba va dalil izohi")
    ]
    
    data = {
        'subject': [],
        'question': [],
        'option_a': [],
        'option_b': [],
        'option_c': [],
        'option_d': [],
        'correct_answer': [],
        'explanation': []
    }
    
    # Generate 620 questions for each of the 3 subjects
    for subj_name, q_prefix, opt_a, opt_b, opt_c, opt_d, correct, exp_prefix in subjects:
        for num in range(1, 621):
            data['subject'].append(subj_name)
            data['question'].append(f"{subj_name} fani bo'yicha {num}-savol: Ushbu savol test tizimini sinash uchun yaratilgan.")
            data['option_a'].append(f"{opt_a} ({num})")
            data['option_b'].append(f"{opt_b} ({num})")
            data['option_c'].append(f"{opt_c} ({num})")
            data['option_d'].append(f"{opt_d} ({num})")
            data['correct_answer'].append(correct)
            data['explanation'].append(f"{exp_prefix} {num}: To'g'ri variant - {correct}.")
            
    df = pd.DataFrame(data)
    
    os.makedirs(DATA_DIR, exist_ok=True)
    file_path = os.path.join(DATA_DIR, "tests.xlsx")
    
    print(f"Generating {len(df)} questions...")
    df.to_excel(file_path, index=False)
    print(f"Successfully saved sample test data to: {file_path}")

if __name__ == "__main__":
    generate_large_dataset()
