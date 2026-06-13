import datetime
import html
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from database import (
    get_subjects,
    get_active_test,
    get_test_question_by_order,
    get_test_questions,
    get_test_results,
    finish_test,
    delete_test,
    get_subject_questions_count,
    has_taken_daily_mock
)
from services import generate_variant, submit_test_answer
from keyboards import (
    get_subject_selection_keyboard,
    get_test_keyboard,
    get_test_finished_keyboard,
    get_analysis_keyboard,
    get_main_menu
)
from config import ADMIN_IDS

router = Router()

class TestStates(StatesGroup):
    selecting_subjects = State()
    taking_test = State()
    analyzing_test = State()

def generate_progress_bar(current: int, total: int) -> str:
    """Generates a text progress bar."""
    bar_length = 10
    filled = int((current / total) * bar_length)
    empty = bar_length - filled
    percentage = int((current / total) * 100)
    return f"[{'■' * filled}{'□' * empty}] {percentage}%"

async def send_question_message(message: Message, test_id: int, order: int, user_id: int):
    """Utility to format and send a test question with active timer."""
    q_data = get_test_question_by_order(test_id, order)
    if not q_data:
        if isinstance(message, CallbackQuery):
            await message.message.answer("Savolni yuklashda xatolik yuz berdi.")
        else:
            await message.answer("Savolni yuklashda xatolik yuz berdi.")
        return
        
    progress = generate_progress_bar(order, 50)
    
    # Calculate qolgan vaqt
    active_test = get_active_test(user_id)
    timer_str = ""
    if active_test:
        started = datetime.datetime.strptime(active_test['started_at'], "%Y-%m-%d %H:%M:%S")
        elapsed = datetime.datetime.utcnow() - started
        remaining_sec = max(0, 90 * 60 - int(elapsed.total_seconds()))
        mins, secs = divmod(remaining_sec, 60)
        timer_str = f"⏱ <b>Qolgan vaqt:</b> {mins:02d}:{secs:02d}\n\n"
        
    # Shuffle options deterministically
    from services.question_helper import prepare_question
    q_dict = {
        "question": q_data['question'],
        "A": q_data['option_a'],
        "B": q_data['option_b'],
        "C": q_data['option_c'],
        "D": q_data['option_d'],
        "correct": q_data['correct_option']
    }
    shuffled_q = prepare_question(q_dict, test_id, order)
        
    text = (
        f"📖 <b>Fan:</b> {html.escape(q_data['subject'])}\n"
        f"❓ <b>Savol:</b> {order} / 50\n\n"
        f"{timer_str}"
        f"{html.escape(shuffled_q['question'])}\n\n"
        f"A) {html.escape(str(shuffled_q['A']))}\n"
        f"B) {html.escape(str(shuffled_q['B']))}\n"
        f"C) {html.escape(str(shuffled_q['C']))}\n"
        f"D) {html.escape(str(shuffled_q['D']))}\n\n"
        f"📊 <b>Jarayon:</b> {html.escape(progress)}"
    )
    
    keyboard = get_test_keyboard(
        current_order=order,
        total_questions=50,
        selected_answer=q_data['user_answer']
    )
    
    # Check if we are editing an existing message or sending a new one
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

# --- Helper to check timer expiration ---
async def is_test_expired(callback: CallbackQuery, state: FSMContext) -> bool:
    user_id = callback.from_user.id
    active_test = get_active_test(user_id)
    if active_test:
        started = datetime.datetime.strptime(active_test['started_at'], "%Y-%m-%d %H:%M:%S")
        elapsed = datetime.datetime.utcnow() - started
        if elapsed.total_seconds() >= 90 * 60:
            finish_test(active_test['id'])
            await state.clear()
            await callback.answer("Vaqt tugadi! Imtihon avtomatik ravishda yakunlandi.", show_alert=True)
            
            results = get_test_results(active_test['id'])
            percentage = int((results['correct'] / results['total']) * 100) if results['total'] > 0 else 0
            
            subjects_breakdown = ""
            for s_res in results['breakdown']:
                s_pct = int((s_res['correct'] / s_res['total']) * 100) if s_res['total'] > 0 else 0
                subjects_breakdown += f"• <b>{html.escape(s_res['subject'])}:</b> {s_res['correct']}/{s_res['total']} ta ({s_pct}%)\n"
                
            summary_text = (
                "⏱ <b>Vaqtingiz tugadi!</b>\n\n"
                "Imtihon avtomatik ravishda yakunlandi va topshirildi.\n\n"
                "📈 <b>Natijalar:</b>\n"
                f"• Jami savollar: <code>{results['total']}</code> ta\n"
                f"• To'g'ri javoblar: <code>{results['correct']}</code> ta\n"
                f"• Noto'g'ri javoblar: <code>{results['incorrect']}</code> ta\n"
                f"• Belgilanmagan: <code>{results['unanswered']}</code> ta\n\n"
                f"📚 <b>Fanlar kesimida:</b>\n{subjects_breakdown}\n"
                f"🎯 <b>Umumiy natija:</b> <code>{percentage}%</code>"
            )
            await state.update_data(analysis_test_id=active_test['id'])
            await callback.message.edit_text(
                summary_text,
                reply_markup=get_test_finished_keyboard(),
                parse_mode="HTML"
            )
            return True
    return False

# --- Start Test Command ---
@router.message(Command("start_exam"))
@router.message(F.text == "📝 Standart Imtihon")
async def start_test_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Check if user has an active, unfinished test in the database
    active_test = get_active_test(user_id)
    if active_test:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Davom ettirish", callback_data=f"resume_test:{active_test['id']}")],
            [InlineKeyboardButton(text="❌ O'chirib, yangi boshlash", callback_data=f"delete_and_start:{active_test['id']}")]
        ])
        await message.answer(
            "⚠️ Sizda yakunlanmagan test sessiyasi mavjud. Uni davom ettirasizmi yoki o'chirib yuborib yangisini boshlaysizmi?",
            reply_markup=kb
        )
        return
        
    await start_new_test_flow(message, state)

async def start_new_test_flow(message: Message, state: FSMContext):
    subjects = get_subjects()
    
    if len(subjects) < 3:
        await message.answer(
            "❌ Bazada yetarli fanlar mavjud emas. Test boshlash uchun kamida 3 ta fan bo'lishi kerak.\n"
            "Iltimos, adminlar tomonidan testlar yuklanishini kuting."
        )
        return
        
    # Check if each subject has at least some questions
    valid_subjects = []
    for s in subjects:
        cnt = get_subject_questions_count(s)
        if cnt >= 10: # Minimum requirement to participate
            valid_subjects.append(s)
            
    if len(valid_subjects) < 3:
        await message.answer(
            f"❌ Bazada 3 ta fandan yetarli savollar yo'q. Faqat quyidagilarda 10 tadan ko'p savol bor: {', '.join(valid_subjects)}.\n"
            "Admin panel orqali qo'shimcha testlar yuklang."
        )
        return
        
    # If exactly 3 subjects, auto-select them and confirm
    if len(valid_subjects) == 3:
        await state.update_data(selected_subjects=valid_subjects)
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Boshlash", callback_data="start_test_now")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="go_home")]
        ])
        subjects_str = "\n".join([f"{idx+1}. {s}" for idx, s in enumerate(valid_subjects)])
        await message.answer(
            f"Sizda quyidagi 3 ta fan bo'yicha variant yaratiladi:\n\n{subjects_str}\n\n"
            "Savollar taqsimoti: 16 + 17 + 17 (Jami 50 ta).\n"
            "Boshlashga tayyormisiz?",
            reply_markup=kb
        )
        return
        
    # If more than 3, enter subject selection state
    await state.set_state(TestStates.selecting_subjects)
    await state.update_data(subjects_pool=valid_subjects, selected_subjects=[])
    
    kb = get_subject_selection_keyboard(valid_subjects, step=1, selected=[])
    await message.answer(
        "📚 <b>1-fanni tanlang</b> (Ushbu fandan 16 ta savol tushadi):",
        reply_markup=kb,
        parse_mode="HTML"
    )

# --- Resume & Delete Actions ---
@router.callback_query(F.data.startswith("resume_test:"))
async def resume_test_callback(callback: CallbackQuery, state: FSMContext):
    test_id = int(callback.data.split(":")[1])
    await callback.answer("Test davom ettirilmoqda...")
    
    # Find the first unanswered question
    questions = get_test_questions(test_id)
    first_unanswered_order = 1
    for q in questions:
        if q['user_answer'] is None:
            first_unanswered_order = q['question_order']
            break
            
    await state.set_state(TestStates.taking_test)
    await state.update_data(test_id=test_id, current_order=first_unanswered_order)
    await send_question_message(callback, test_id, first_unanswered_order, callback.from_user.id)

@router.callback_query(F.data.startswith("delete_and_start:"))
async def delete_and_start_callback(callback: CallbackQuery, state: FSMContext):
    test_id = int(callback.data.split(":")[1])
    delete_test(test_id)
    await callback.answer("Eski test o'chirildi.")
    await start_new_test_flow(callback.message, state)

# --- Subject Selection Callback ---
@router.callback_query(TestStates.selecting_subjects, F.data.startswith("select_subj:"))
async def select_subject_callback(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    step = int(parts[1])
    subj_idx = int(parts[2])
    
    data = await state.get_data()
    subjects_pool = data['subjects_pool']
    selected_subjects = data['selected_subjects']
    
    selected_subject = subjects_pool[subj_idx]
    selected_subjects.append(selected_subject)
    await state.update_data(selected_subjects=selected_subjects)
    
    await callback.answer(f"{selected_subject} tanlandi.")
    
    if step < 3:
        next_step = step + 1
        limit = 17 # Step 2 and 3 get 17 questions
        kb = get_subject_selection_keyboard(subjects_pool, step=next_step, selected=selected_subjects)
        await callback.message.edit_text(
            f"📚 <b>{next_step}-fanni tanlang</b> (Ushbu fandan {limit} ta savol tushadi):",
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        # Confirmed
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Testni boshlash", callback_data="start_test_now")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="go_home")]
        ])
        subjects_str = "\n".join([f"{idx+1}. {html.escape(s)} ({'16' if idx==0 else '17'} ta savol)" for idx, s in enumerate(selected_subjects)])
        await callback.message.edit_text(
            f"Siz tanlagan fanlar:\n\n{subjects_str}\n\n"
            "Testni boshlashga tayyormisiz?",
            reply_markup=kb,
            parse_mode="HTML"
        )

# --- Start Test Now Callback ---
@router.callback_query(F.data == "start_test_now")
async def start_test_now_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    selected_subjects = data.get('selected_subjects')
    
    if not selected_subjects:
        await callback.answer("Xatolik: Fanlar tanlanmagan.", show_alert=True)
        return
        
    await callback.answer("Variant tayyorlanmoqda...")
    
    try:
        exam_data = generate_variant(user_id, selected_subjects)
        test_id = exam_data['session_id']
        await state.set_state(TestStates.taking_test)
        await state.update_data(test_id=test_id, current_order=1)
        await send_question_message(callback, test_id, 1, user_id)
    except Exception as e:
        await callback.message.answer(f"❌ Xatolik yuz berdi: {str(e)}")

# --- Answer Option Clicked ---
@router.callback_query(TestStates.taking_test, F.data.startswith("ans:"))
async def process_answer_callback(callback: CallbackQuery, state: FSMContext):
    if await is_test_expired(callback, state):
        return
        
    parts = callback.data.split(":")
    order = int(parts[1])
    option = parts[2]
    
    data = await state.get_data()
    test_id = data['test_id']
    user_id = callback.from_user.id
    
    # Fetch question ID for this order
    q_data = get_test_question_by_order(test_id, order)
    if not q_data:
        await callback.answer("Savol topilmadi.", show_alert=True)
        return
        
    # Submit answer
    submit_test_answer(test_id, user_id, q_data['question_id'], option)
    await callback.answer(f"{option} javob yozib olindi.")
    
    # Auto-advance to next question if not last
    if order < 50:
        next_order = order + 1
        await state.update_data(current_order=next_order)
        await send_question_message(callback, test_id, next_order, user_id)
    else:
        # Refresh the current message to show the selected answer highlighted
        await send_question_message(callback, test_id, order, user_id)

# --- Navigation Callback ---
@router.callback_query(TestStates.taking_test, F.data.startswith("nav:"))
async def process_nav_callback(callback: CallbackQuery, state: FSMContext):
    if await is_test_expired(callback, state):
        return
        
    order = int(callback.data.split(":")[1])
    data = await state.get_data()
    test_id = data['test_id']
    user_id = callback.from_user.id
    
    await state.update_data(current_order=order)
    await callback.answer()
    await send_question_message(callback, test_id, order, user_id)

# --- Finish Test Callback ---
@router.callback_query(F.data == "finish_test")
async def finish_test_callback(callback: CallbackQuery, state: FSMContext):
    if await is_test_expired(callback, state):
        return
        
    data = await state.get_data()
    test_id = data.get('test_id')
    
    if not test_id:
        # Attempt to get active test from DB directly
        active = get_active_test(callback.from_user.id)
        if active:
            test_id = active['id']
        else:
            await callback.answer("Sizda faol test mavjud emas.", show_alert=True)
            return
            
    # Complete test in database
    finish_test(test_id)
    await callback.answer("Test yakunlandi.")
    
    # Generate stats
    results = get_test_results(test_id)
    
    # Calculate duration
    fmt = "%Y-%m-%d %H:%M:%S"
    started = datetime.datetime.strptime(results['started_at'], fmt)
    finished = datetime.datetime.strptime(results['finished_at'], fmt)
    duration = finished - started
    
    # Format duration beautifully
    minutes, seconds = divmod(duration.total_seconds(), 60)
    duration_str = f"{int(minutes)} daqiqa {int(seconds)} soniya"
    
    percentage = int((results['correct'] / results['total']) * 100) if results['total'] > 0 else 0
    
    # Build text
    subjects_breakdown = ""
    for s_res in results['breakdown']:
        s_pct = int((s_res['correct'] / s_res['total']) * 100) if s_res['total'] > 0 else 0
        subjects_breakdown += f"• <b>{html.escape(s_res['subject'])}:</b> {s_res['correct']}/{s_res['total']} ta ({s_pct}%)\n"
        
    summary_text = (
        "🏁 <b>Test yakunlandi!</b>\n\n"
        f"⏱ <b>Sarflangan vaqt:</b> {html.escape(duration_str)}\n\n"
        "📈 <b>Natijalar:</b>\n"
        f"• Jami savollar: <code>{results['total']}</code> ta\n"
        f"• To'g'ri javoblar: <code>{results['correct']}</code> ta\n"
        f"• Noto'g'ri javoblar: <code>{results['incorrect']}</code> ta\n"
        f"• Belgilanmagan: <code>{results['unanswered']}</code> ta\n\n"
        f"📚 <b>Fanlar kesimida:</b>\n{subjects_breakdown}\n"
        f"🎯 <b>Umumiy natija:</b> <code>{percentage}%</code>"
    )
    
    await state.clear()
    # Save the test ID in state for analysis module
    await state.update_data(analysis_test_id=test_id)
    
    await callback.message.edit_text(
        summary_text,
        reply_markup=get_test_finished_keyboard(),
        parse_mode="HTML"
    )

# --- Analysis Navigation Callback ---
@router.callback_query(F.data.startswith("an:"))
async def process_analysis_callback(callback: CallbackQuery, state: FSMContext):
    order = int(callback.data.split(":")[1])
    data = await state.get_data()
    test_id = data.get('analysis_test_id')
    
    if not test_id:
        await callback.answer("Tahlil qilish uchun test topilmadi.", show_alert=True)
        return
        
    await callback.answer()
    
    q_data = get_test_question_by_order(test_id, order)
    if not q_data:
        await callback.message.answer("Savol topilmadi.")
        return
        
    # Reconstruct the deterministic shuffle
    from services.question_helper import prepare_question, check_answer
    q_dict = {
        "question": q_data['question'],
        "A": q_data['option_a'],
        "B": q_data['option_b'],
        "C": q_data['option_c'],
        "D": q_data['option_d'],
        "correct": q_data['correct_option']
    }
    shuffled_q = prepare_question(q_dict, test_id, order)
    
    user_ans = q_data['user_answer']
    correct_ans = shuffled_q['correct']
    
    if user_ans is None:
        status_text = "❌ <b>Belgilanmagan</b>"
    elif check_answer(user_ans, correct_ans):
        status_text = "✅ <b>To'g'ri</b>"
    else:
        status_text = f"❌ <b>Noto'g'ri</b> (Siz: {html.escape(user_ans)})"
        
    explanation_text = html.escape(q_data['explanation']) if q_data['explanation'] else "Ushbu savol uchun izoh mavjud emas."
    
    text = (
        f"📊 <b>Xatolar tahlili</b> | Savol {order} / 50\n"
        f"📖 <b>Fan:</b> {html.escape(q_data['subject'])}\n\n"
        f"{html.escape(shuffled_q['question'])}\n\n"
        f"A) {html.escape(str(shuffled_q['A']))}\n"
        f"B) {html.escape(str(shuffled_q['B']))}\n"
        f"C) {html.escape(str(shuffled_q['C']))}\n"
        f"D) {html.escape(str(shuffled_q['D']))}\n\n"
        f"👤 Sizning javobingiz: {html.escape(user_ans or 'Belgilanmagan')}\n"
        f"🔑 To'g'ri javob: <b>{html.escape(correct_ans)}</b> ({status_text})\n\n"
        f"💡 <b>Izoh:</b>\n{explanation_text}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_analysis_keyboard(order, 50),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "back_results")
async def back_to_results_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    test_id = data.get('analysis_test_id')
    if not test_id:
        await callback.answer("Natija topilmadi.", show_alert=True)
        return
        
    await callback.answer()
    results = get_test_results(test_id)
    
    fmt = "%Y-%m-%d %H:%M:%S"
    started = datetime.datetime.strptime(results['started_at'], fmt)
    finished = datetime.datetime.strptime(results['finished_at'], fmt)
    duration = finished - started
    minutes, seconds = divmod(duration.total_seconds(), 60)
    duration_str = f"{int(minutes)} daqiqa {int(seconds)} soniya"
    percentage = int((results['correct'] / results['total']) * 100) if results['total'] > 0 else 0
    
    subjects_breakdown = ""
    for s_res in results['breakdown']:
        s_pct = int((s_res['correct'] / s_res['total']) * 100) if s_res['total'] > 0 else 0
        subjects_breakdown += f"• <b>{html.escape(s_res['subject'])}:</b> {s_res['correct']}/{s_res['total']} ta ({s_pct}%)\n"
        
    summary_text = (
        "🏁 <b>Test yakunlandi!</b>\n\n"
        f"⏱ <b>Sarflangan vaqt:</b> {html.escape(duration_str)}\n\n"
        "📈 <b>Natijalar:</b>\n"
        f"• Jami savollar: <code>{results['total']}</code> ta\n"
        f"• To'g'ri javoblar: <code>{results['correct']}</code> ta\n"
        f"• Noto'g'ri javoblar: <code>{results['incorrect']}</code> ta\n"
        f"• Belgilanmagan: <code>{results['unanswered']}</code> ta\n\n"
        f"📚 <b>Fanlar kesimida:</b>\n{subjects_breakdown}\n"
        f"🎯 <b>Umumiy natija:</b> <code>{percentage}%</code>"
    )
    
    await callback.message.edit_text(
        summary_text,
        reply_markup=get_test_finished_keyboard(),
        parse_mode="HTML"
    )

# --- Start New Test Callback ---
@router.callback_query(F.data == "start_new_test")
async def start_new_test_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await start_new_test_flow(callback.message, state)

# --- Kunlik Mock Exam Handler ---
@router.message(Command("mock"))
@router.message(F.text == "🏆 Kunlik Mock")
async def start_mock_exam_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    today_str = datetime.date.today().isoformat()
    
    # Check if already taken today
    if has_taken_daily_mock(user_id, today_str):
        from database import get_daily_mock_leaderboard
        leaders = get_daily_mock_leaderboard(today_str)
        leaders_str = ""
        if leaders:
            for idx, l in enumerate(leaders[:5]):
                medals = ["🥇", "🥈", "🥉", "4.", "5."]
                medal = medals[idx] if idx < len(medals) else f"{idx+1}."
                duration_formatted = f"{l['duration_sec'] // 60}m {l['duration_sec'] % 60}s"
                leaders_str += f"{medal} {html.escape(l['full_name'] or '')} - {l['correct_count']}/50 ({duration_formatted})\n"
        
        leaderboard_note = f"\n\n🏆 <b>Top 5 Natijalar:</b>\n{leaders_str}" if leaders_str else "\n\nBugungi mock natijalari hali e'lon qilinmadi."
        
        await message.answer(
            f"❌ Siz bugungi Kunlik Mock imtihonini topshirib bo'lgansiz. "
            "Kunlik Mock imtihonini kuniga faqat 1 marta topshirish mumkin."
            f"{leaderboard_note}",
            parse_mode="HTML"
        )
        return
        
    active = get_active_test(user_id)
    if active:
        if active['exam_type'] == 'daily_mock':
            await state.set_state(TestStates.taking_test)
            questions = get_test_questions(active['id'])
            first_unanswered_order = 1
            for q in questions:
                if q['user_answer'] is None:
                    first_unanswered_order = q['question_order']
                    break
            await state.update_data(test_id=active['id'], current_order=first_unanswered_order)
            await send_question_message(message, active['id'], first_unanswered_order, user_id)
            return
        else:
            await message.answer(
                "⚠️ Sizda faol Standart Imtihon mavjud. Iltimos, oldin uni yakunlang yoki "
                "bosh menyudan o'chirib yuboring."
            )
            return
            
    subjects = get_subjects()
    if len(subjects) < 3:
        await message.answer(
            "❌ Bazada yetarli fanlar mavjud emas. Mock imtihon yaratish uchun kamida 3 ta fan bo'lishi kerak."
        )
        return
        
    selected_subjects = sorted(subjects)[:3]
    status_msg = await message.answer("⏳ Kunlik mock imtihon variantingiz yuklanmoqda...")
    
    try:
        exam_data = generate_variant(user_id, selected_subjects, exam_type='daily_mock', mock_date=today_str)
        test_id = exam_data['session_id']
        
        await state.set_state(TestStates.taking_test)
        await state.update_data(test_id=test_id, current_order=1)
        
        await status_msg.delete()
        await send_question_message(message, test_id, 1, user_id)
    except Exception as e:
        await status_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)}")

# --- Go Home Callback ---
@router.callback_query(F.data == "go_home")
async def go_home_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    is_admin = callback.from_user.id in ADMIN_IDS
    await callback.message.delete()
    await callback.message.answer(
        "Asosiy menyuga qaytdingiz. Boshlash uchun tugmalardan foydalaning:",
        reply_markup=get_main_menu(is_admin=is_admin)
    )
