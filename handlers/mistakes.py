import html
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from database import get_user_mistakes, remove_mistake, clear_user_mistakes, get_user_mistakes_count
from keyboards import get_mistake_review_keyboard, get_main_menu, get_notebook_menu_keyboard
from config import ADMIN_IDS

router = Router()

class MistakeStates(StatesGroup):
    practicing = State()

async def send_mistake_question(message: Message, state: FSMContext, index: int):
    """Utility to display a question from the user's mistakes list."""
    state_data = await state.get_data()
    mistakes = state_data.get("mistakes_list", [])
    
    if index >= len(mistakes):
        await state.clear()
        is_admin = message.from_user.id in ADMIN_IDS
        text = "🎉 <b>Barcha xato savollarni ko'rib chiqdingiz!</b>\n\nTo'g'ri javob bergan savollaringiz xatolar ro'yxatidan muvaffaqiyatli o'chirildi."
        if isinstance(message, CallbackQuery):
            await callback_or_msg_ref(message, text, is_admin)
        else:
            await message.answer(text, reply_markup=get_main_menu(is_admin=is_admin), parse_mode="HTML")
        return
        
    q = mistakes[index]
    has_next = (index + 1) < len(mistakes)
    
    text = (
        f"🔄 <b>Xatolar ustida ishlash</b> | Savol {index + 1} / {len(mistakes)}\n"
        f"📖 <b>Fan:</b> {html.escape(q['subject'])}\n\n"
        f"{html.escape(q['question'])}\n\n"
        f"A) {html.escape(str(q['option_a']))}\n"
        f"B) {html.escape(str(q['option_b']))}\n"
        f"C) {html.escape(str(q['option_c']))}\n"
        f"D) {html.escape(str(q['option_d']))}"
    )
    
    keyboard = get_mistake_review_keyboard(
        question_id=q['question_id'],
        has_next=has_next,
        answered=False
    )
    
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

async def callback_or_msg_ref(callback: CallbackQuery, text: str, is_admin: bool):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(text, reply_markup=get_main_menu(is_admin=is_admin), parse_mode="HTML")

@router.message(Command("retry_wrong_answers"))
@router.message(F.text == "📓 Xatolar daftari")
async def show_notebook_menu(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    
    count = get_user_mistakes_count(user_id)
    text = (
        "📓 <b>Xatolar Daftari (Notebook)</b>\n\n"
        "Siz imtihon topshirish davomida xato yechgan savollaringiz ushbu daftarga yig'ilib boradi. "
        f"Hozirda daftaringizda <b>{count}</b> ta xato savol bor.\n\n"
        "Quyidagi amallardan birini tanlang:"
    )
    await message.answer(text, reply_markup=get_notebook_menu_keyboard(has_mistakes=count > 0), parse_mode="HTML")

@router.callback_query(F.data == "m_clear_notebook")
async def clear_notebook_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    clear_user_mistakes(user_id)
    await callback.answer("Xatolar daftari muvaffaqiyatli tozalandi!", show_alert=True)
    
    is_admin = user_id in ADMIN_IDS
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "Xatolar daftari tozalandi. Asosiy menyu:",
        reply_markup=get_main_menu(is_admin=is_admin)
    )

@router.callback_query(F.data == "m_start_practice")
async def start_practice_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    mistakes = get_user_mistakes(user_id)
    if not mistakes:
        await callback.answer("Xato savollar topilmadi.", show_alert=True)
        return
        
    await callback.answer()
    await state.set_state(MistakeStates.practicing)
    await state.update_data(mistakes_list=mistakes, current_index=0)
    await send_mistake_question(callback, state, 0)

# --- Process Mistake Answer Callback ---
@router.callback_query(MistakeStates.practicing, F.data.startswith("m_ans:"))
async def process_mistake_answer(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    question_id = int(parts[1])
    option = parts[2]
    
    state_data = await state.get_data()
    mistakes = state_data.get("mistakes_list", [])
    index = state_data.get("current_index", 0)
    user_id = callback.from_user.id
    
    if index >= len(mistakes) or mistakes[index]['question_id'] != question_id:
        await callback.answer("Savol ma'lumotlari mos kelmadi.", show_alert=True)
        return
        
    q = mistakes[index]
    correct = q['correct_option']
    is_correct = option.upper() == correct.upper()
    
    explanation_text = html.escape(q['explanation']) if q['explanation'] else "Ushbu savol uchun izoh mavjud emas."
    
    if is_correct:
        remove_mistake(user_id, question_id)
        status_text = "✅ <b>To'g'ri!</b> 🎉\nSavol xatolar ro'yxatidan o'chirildi."
        await callback.answer("To'g'ri javob!", show_alert=False)
    else:
        status_text = f"❌ <b>Noto'g'ri!</b>\nTo'g'ri javob: <b>{html.escape(correct)}</b> (Siz: {html.escape(option)})"
        await callback.answer("Noto'g'ri javob.", show_alert=False)
        
    text = (
        f"🔄 <b>Xatolar ustida ishlash</b> | Savol {index + 1} / {len(mistakes)}\n"
        f"📖 <b>Fan:</b> {html.escape(q['subject'])}\n\n"
        f"{html.escape(q['question'])}\n\n"
        f"A) {html.escape(str(q['option_a']))}\n"
        f"B) {html.escape(str(q['option_b']))}\n"
        f"C) {html.escape(str(q['option_c']))}\n"
        f"D) {html.escape(str(q['option_d']))}\n\n"
        f"Natija: {status_text}\n\n"
        f"💡 <b>Izoh:</b>\n{explanation_text}"
    )
    
    has_next = (index + 1) < len(mistakes)
    keyboard = get_mistake_review_keyboard(
        question_id=question_id,
        has_next=has_next,
        answered=True,
        is_correct=is_correct
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

# --- Next Mistake Question Callback ---
@router.callback_query(MistakeStates.practicing, F.data == "m_nxt")
async def process_next_mistake(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    index = state_data.get("current_index", 0)
    next_index = index + 1
    
    await state.update_data(current_index=next_index)
    await callback.answer()
    await send_mistake_question(callback, state, next_index)

# --- Exit Practice Callback ---
@router.callback_query(F.data == "m_ext")
async def exit_mistakes_practice(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Xatolar ustida ishlash yakunlandi.")
    
    is_admin = callback.from_user.id in ADMIN_IDS
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "Asosiy menyuga qaytdingiz:",
        reply_markup=get_main_menu(is_admin=is_admin)
    )

