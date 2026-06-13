from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_subject_selection_keyboard(subjects: list, step: int, selected: list) -> InlineKeyboardMarkup:
    """
    Generates the keyboard for selecting subjects one by one.
    subjects: List of available subjects.
    step: 1, 2, or 3 (current subject selection step).
    selected: List of already selected subjects.
    """
    builder = InlineKeyboardBuilder()
    
    for idx, subject in enumerate(subjects):
        if subject in selected:
            continue
        # Use idx to keep callback data short
        builder.button(text=subject, callback_data=f"select_subj:{step}:{idx}")
        
    builder.adjust(2)
    return builder.as_markup()

def get_test_keyboard(current_order: int, total_questions: int, selected_answer: str = None) -> InlineKeyboardMarkup:
    """
    Generates the keyboard for test taking.
    Includes A, B, C, D choices, navigation (Previous/Next), and Finish.
    Selected option is highlighted with emojis.
    """
    builder = InlineKeyboardBuilder()
    
    # Row 1: Options A, B, C, D
    options = ['A', 'B', 'C', 'D']
    for opt in options:
        text = f"🅰️" if opt == selected_answer else opt
        if opt == 'A' and selected_answer == 'A': text = "🅰️"
        elif opt == 'B' and selected_answer == 'B': text = "🅱️"
        elif opt == 'C' and selected_answer == 'C': text = "🆃" # or 🅲
        elif opt == 'D' and selected_answer == 'D': text = "🅳"
        
        # fallback to plain emoji styling if symbols are hard to read
        if opt == selected_answer:
            text = f"✅ {opt}"
            
        builder.button(text=text, callback_data=f"ans:{current_order}:{opt}")
        
    # Row 2: Navigation
    nav_buttons = []
    if current_order > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"nav:{current_order - 1}"))
    if current_order < total_questions:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Keyingi", callback_data=f"nav:{current_order + 1}"))
    else:
        # If last question, Next can be replaced with finish or we can just let them click finish
        pass
        
    builder.row(*nav_buttons)
    
    # Row 3: Finish Test
    builder.row(InlineKeyboardButton(text="❌ Testni tugatish", callback_data="finish_test"))
    
    return builder.as_markup()

def get_test_finished_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard displayed after test ends.
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Xatolar tahlili", callback_data="an:1"))
    builder.row(
        InlineKeyboardButton(text="🔄 Yangi test", callback_data="start_new_test"),
        InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="go_home")
    )
    return builder.as_markup()

def get_analysis_keyboard(current_order: int, total_questions: int) -> InlineKeyboardMarkup:
    """
    Keyboard for navigating mistakes analysis.
    """
    builder = InlineKeyboardBuilder()
    
    nav_buttons = []
    if current_order > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"an:{current_order - 1}"))
    if current_order < total_questions:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Keyingi", callback_data=f"an:{current_order + 1}"))
        
    builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text="↩️ Natijalarga qaytish", callback_data="back_results"))
    
    return builder.as_markup()

def get_mistake_review_keyboard(question_id: int, has_next: bool, answered: bool = False, is_correct: bool = False) -> InlineKeyboardMarkup:
    """
    Keyboard for mistake review practice mode.
    """
    builder = InlineKeyboardBuilder()
    
    # If not answered yet, show choices
    if not answered:
        for opt in ['A', 'B', 'C', 'D']:
            builder.button(text=opt, callback_data=f"m_ans:{question_id}:{opt}")
        builder.adjust(4)
    
    # Show navigation/next button
    nav_buttons = []
    if answered or not has_next:
        if has_next:
            nav_buttons.append(InlineKeyboardButton(text="➡️ Keyingi savol", callback_data="m_nxt"))
    
    nav_buttons.append(InlineKeyboardButton(text="🏠 Chiqish", callback_data="m_ext"))
    builder.row(*nav_buttons)
    
    return builder.as_markup()

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard for Admin Panel options.
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"))
    builder.row(InlineKeyboardButton(text="📥 Testlarni yuklash (Excel)", callback_data="admin_upload"))
    builder.row(InlineKeyboardButton(text="📤 Shablon fayl yuklab olish", callback_data="admin_template"))
    builder.row(
        InlineKeyboardButton(text="➕ Savol qo'shish", callback_data="admin_add_q"),
        InlineKeyboardButton(text="🗑 Savolni o'chirish", callback_data="admin_del_q")
    )
    builder.row(InlineKeyboardButton(text="📝 Savolni tahrirlash", callback_data="admin_edit_q"))
    builder.row(
        InlineKeyboardButton(text="📢 Xabar tarqatish", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="📤 Natijalarni eksport (Excel)", callback_data="admin_export")
    )
    return builder.as_markup()

def get_leaderboard_keyboard() -> InlineKeyboardMarkup:
    """
    Generates inline keyboard for choosing leaderboards.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏆 Kunlik Mock", callback_data="lb_mock"),
        InlineKeyboardButton(text="👑 Umumiy Reyting", callback_data="lb_overall")
    )
    return builder.as_markup()

def get_notebook_menu_keyboard(has_mistakes: bool) -> InlineKeyboardMarkup:
    """
    Generates inline keyboard for Wrong Answers Notebook menu.
    """
    builder = InlineKeyboardBuilder()
    if has_mistakes:
        builder.row(InlineKeyboardButton(text="📓 Mashq qilish", callback_data="m_start_practice"))
        builder.row(InlineKeyboardButton(text="🗑 Daftarni tozalash", callback_data="m_clear_notebook"))
    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="go_home"))
    return builder.as_markup()
