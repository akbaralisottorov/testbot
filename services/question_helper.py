import random

def prepare_question(question_dict: dict, session_id: int = None, question_order: int = None) -> dict:
    """
    Shuffles the options A, B, C, D of a question.
    If session_id and question_order are provided, shuffles deterministically
    to ensure the same question always has the same shuffled options in the same session.
    
    Input format:
    {
        "question": str,
        "A": str,
        "B": str,
        "C": str,
        "D": str,
        "correct": "A" | "B" | "C" | "D"
    }
    """
    if session_id is not None and question_order is not None:
        seed = f"session_{session_id}_q_{question_order}"
        local_random = random.Random(seed)
    else:
        local_random = random.Random()
        
    pairs = [
        ('A', question_dict['A']),
        ('B', question_dict['B']),
        ('C', question_dict['C']),
        ('D', question_dict['D'])
    ]
    local_random.shuffle(pairs)
    
    shuffled_options = {}
    new_correct = None
    for idx, (orig_key, val) in enumerate(pairs):
        new_key = ['A', 'B', 'C', 'D'][idx]
        shuffled_options[new_key] = val
        if orig_key == question_dict['correct']:
            new_correct = new_key
            
    return {
        "question": question_dict["question"],
        "A": shuffled_options['A'],
        "B": shuffled_options['B'],
        "C": shuffled_options['C'],
        "D": shuffled_options['D'],
        "correct": new_correct
    }

def check_answer(user_answer: str, correct_answer: str) -> bool:
    """
    Validates if the user's selected answer matches the correct option.
    """
    if not user_answer or not correct_answer:
        return False
    return user_answer.strip().upper() == correct_answer.strip().upper()
