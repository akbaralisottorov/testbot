import os
import random
import pandas as pd
from config import DATA_DIR

def generate_large_dataset(file_path=None):
    # Set seed for reproducible generation but randomly distributed answers
    random.seed(42)
    
    subjects = [
        ("Matematika", "savol", "To'g'ri Matematika javobi", "Xato Matematika A", "Xato Matematika B", "Xato Matematika C"),
        ("Ona tili", "ona tili test savoli", "To'g'ri Ona tili javobi", "Xato Ona tili A", "Xato Ona tili B", "Xato Ona tili C"),
        ("Tarix", "tarixiy voqea haqida savol", "To'g'ri Tarix javobi", "Xato Tarix A", "Xato Tarix B", "Xato Tarix C")
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
    for subj_name, q_prefix, correct_val, wrong_1, wrong_2, wrong_3 in subjects:
        for num in range(1, 621):
            data['subject'].append(subj_name)
            data['question'].append(f"{subj_name} fani bo'yicha {num}-savol: Ushbu savol test tizimini sinash uchun yaratilgan.")
            
            # Put the correct option and wrong options in a list
            options = [correct_val, wrong_1, wrong_2, wrong_3]
            
            # Shuffle choices randomly
            shuffled_indices = [0, 1, 2, 3]
            random.shuffle(shuffled_indices)
            
            shuffled_options = [options[idx] for idx in shuffled_indices]
            
            # Find the new index of the correct answer (which is index 0 in the original options list)
            correct_idx = shuffled_indices.index(0)
            correct_harf = ['A', 'B', 'C', 'D'][correct_idx]
            
            data['option_a'].append(f"{shuffled_options[0]} ({num})")
            data['option_b'].append(f"{shuffled_options[1]} ({num})")
            data['option_c'].append(f"{shuffled_options[2]} ({num})")
            data['option_d'].append(f"{shuffled_options[3]} ({num})")
            
            data['correct_answer'].append(correct_harf)
            data['explanation'].append(f"Izoh {num}: To'g'ri variant - {correct_harf}.")
            
    df = pd.DataFrame(data)
    
    os.makedirs(DATA_DIR, exist_ok=True)
    if file_path is None:
        file_path = os.path.join(DATA_DIR, "tests.xlsx")
    
    print(f"Generating {len(df)} questions...")
    df.to_excel(file_path, index=False)
    print(f"Successfully saved sample test data to: {file_path}")
 
if __name__ == "__main__":
    generate_large_dataset()
