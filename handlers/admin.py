import os
import logging
import html
import pandas as pd
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command

from database import (
    get_all_users_count,
    get_total_completed_tests_count,
    get_all_questions_count,
    get_subjects,
    get_subject_questions_count,
    delete_question,
    get_question,
    edit_question,
    get_all_users,
    get_all_exam_results
)
from services import parse_and_import_excel
from keyboards import get_admin_keyboard, get_main_menu
from config import ADMIN_IDS, DATA_DIR

logger = logging.getLogger("admin")
router = Router()

class AdminStates(StatesGroup):
    selecting_mode = State()
    waiting_for_file = State()
    waiting_for_broadcast = State()
    
    # Add Question states
    add_q_subject = State()
    add_q_question = State()
    add_q_a = State()
    add_q_b = State()
    add_q_c = State()
    add_q_d = State()
    add_q_correct = State()
    add_q_explanation = State()
    
    # Delete Question states
    del_q_id = State()
    
    # Edit Question states
    edit_q_id = State()
    edit_q_subject = State()
    edit_q_question = State()
    edit_q_a = State()
    edit_q_b = State()
    edit_q_c = State()
    edit_q_d = State()
    edit_q_correct = State()
    edit_q_explanation = State()

def generate_template_file(file_path: str):
    """Generates a sample Excel template for the admin."""
    data = {
        'subject': ['Matematika', 'Ona tili', 'Tarix'],
        'question': [
            '2 + 2 * 2 ifodaning qiymatini toping.',
            'Ot so\'z turkumi qanday so\'roqlarga javob bo\'ladi?',
            'Amir Temur qaysi yilda va qayerda tug\'ilgan?'
        ],
        'option_a': ['6', 'Kim? nima? qayer?', '1336-yil, Shahrisabz (Xo\'ja Ilg\'or)'],
        'option_b': ['8', 'Qanday? qanaqa?', '1346-yil, Samarqand'],
        'option_c': ['4', 'Qancha? necha?', '1405-yil, O\'tror'],
        'option_d': ['10', 'Nima qiladi? nima qildi?', '1336-yil, Buxoro'],
        'correct_answer': ['A', 'A', 'A'],
        'explanation': [
            'Birinchi ko\'paytirish bajariladi: 2 * 2 = 4. Keyin qo\'shish: 2 + 4 = 6.',
            'Ot narsa-buyum nomini bildiradi va Kim? nima? qayer? so\'roqlariga javob bo\'ladi.',
            'Amir Temur 1336-yil 9-aprelda hozirgi Shahrisabz yaqinidagi Xo\'ja Ilg\'or qishlog\'ida tug\'ilgan.'
        ]
    }
    df = pd.DataFrame(data)
    df.to_excel(file_path, index=False)

# --- Helper to return to Admin Panel ---
async def return_to_admin(message: Message, state: FSMContext, text="Muvaffaqiyatli bajarildi!"):
    await state.clear()
    await message.answer(
        f"✅ {text}\n\n⚙️ <b>Admin Panel Menu:</b>",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

# --- Admin Panel Entry ---
@router.message(F.text == "⚙️ Admin panel")
async def show_admin_panel(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
        
    await state.clear()
    await message.answer(
        "⚙️ <b>Admin Panel</b>\n\nLoyihani boshqarish va testlar yuklash menyusiga xush kelibsiz. "
        "Quyidagi amallardan birini tanlang:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

# --- Statistics Handler ---
@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in ADMIN_IDS:
        await callback.answer("Siz admin emassiz.", show_alert=True)
        return
        
    await callback.answer()
    
    users_cnt = get_all_users_count()
    tests_cnt = get_total_completed_tests_count()
    qs_cnt = get_all_questions_count()
    subjects = get_subjects()
    
    subj_breakdown = ""
    for s in subjects:
        s_cnt = get_subject_questions_count(s)
        subj_breakdown += f"• <b>{html.escape(s)}:</b> <code>{s_cnt}</code> ta savol\n"
        
    if not subj_breakdown:
        subj_breakdown = "<i>Hozircha savollar mavjud emas.</i>\n"
        
    stats_text = (
        "📊 <b>Bot Statistikasi:</b>\n\n"
        f"👤 Ro'yxatdan o'tgan foydalanuvchilar: <code>{users_cnt}</code> ta\n"
        f"🏆 Jami yechilgan variantlar: <code>{tests_cnt}</code> ta\n"
        f"❓ Jami bazadagi savollar: <code>{qs_cnt}</code> ta\n\n"
        f"📚 <b>Fanlar bo'yicha savollar:</b>\n{subj_breakdown}\n"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Admin panelga qaytish", callback_data="back_admin")]
    ])
    
    await callback.message.edit_text(stats_text, reply_markup=kb, parse_mode="HTML")

# --- Template Downloader ---
@router.callback_query(F.data == "admin_template")
async def admin_template_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in ADMIN_IDS:
        await callback.answer("Siz admin emassiz.", show_alert=True)
        return
        
    await callback.answer("Fayl tayyorlanmoqda...")
    template_path = os.path.join(DATA_DIR, "shablon.xlsx")
    generate_template_file(template_path)
    
    doc = FSInputFile(template_path, filename="shablon_testlar.xlsx")
    await callback.message.answer_document(
        doc,
        caption=(
            "📤 <b>Excel Shablon Fayli</b>\n\n"
            "Savollarni botga yuklash uchun ushbu shablon faylidan foydalaning. "
            "Ustunlar tartibi va nomlarini o'zgartirmang!"
        ),
        parse_mode="HTML"
    )

# --- Upload Excel Module ---
@router.callback_query(F.data == "admin_upload")
async def admin_upload_mode_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in ADMIN_IDS:
        await callback.answer("Siz admin emassiz.", show_alert=True)
        return
        
    await callback.answer()
    await state.set_state(AdminStates.selecting_mode)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Mavjudlariga qo'shish (Append)", callback_data="import_mode:append")],
        [InlineKeyboardButton(text="🗑 Mavjudlarni o'chirib yangi yuklash (Clear)", callback_data="import_mode:clear")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="back_admin")]
    ])
    
    await callback.message.edit_text(
        "📥 **Test yuklash rejimi:**\n\n"
        "Baza tozalansinmi yoki yangi testlar eskilariga qo'shilsinmi?",
        reply_markup=kb
    )

@router.callback_query(AdminStates.selecting_mode, F.data.startswith("import_mode:"))
async def process_import_mode(callback: CallbackQuery, state: FSMContext):
    mode = callback.data.split(":")[1]
    await state.update_data(import_mode=mode)
    await state.set_state(AdminStates.waiting_for_file)
    await callback.answer()
    
    mode_text = "Mavjudlariga qo'shish" if mode == 'append' else "Bazani tozalab qayta yuklash"
    await callback.message.edit_text(
        f"📥 <b>Fayl yuborish kutilmoqda...</b>\n\n"
        f"Tanlangan rejim: <b>{html.escape(mode_text)}</b>\n\n"
        "Iltimos, test savollari yozilgan Excel (.xlsx) faylini yuboring.\n"
        "Jarayonni bekor qilish uchun /cancel deb yozing.",
        parse_mode="HTML"
    )

@router.message(AdminStates.waiting_for_file, F.document)
async def process_excel_upload(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
        
    doc = message.document
    if not doc.file_name.endswith('.xlsx'):
        await message.answer("❌ Iltimos, faqat Excel (.xlsx) formatidagi fayl yuboring.")
        return
        
    status_msg = await message.answer("⏳ Fayl tahlil qilinmoqda...")
    temp_path = os.path.join(DATA_DIR, f"temp_import_{user_id}.xlsx")
    
    try:
        await bot.download(doc, destination=temp_path)
        data = await state.get_data()
        mode = data.get('import_mode', 'append')
        result = parse_and_import_excel(temp_path, clear_existing=(mode == 'clear'))
        
        if result['success']:
            res_text = (
                "✅ <b>Testlar muvaffaqiyatli import qilindi!</b>\n\n"
                f"📥 Baza yuklandi: <code>{result['imported']}</code> ta yangi savol.\n"
                f"⚠️ O'tkazib yuborildi: <code>{result['skipped']}</code> ta qator.\n"
                f"Takrorlangan (fayl): <code>{result['duplicate_sheet']}</code> | (baza): <code>{result['duplicate_db']}</code>"
            )
            if result['errors']:
                err_details = "\n".join(result['errors'])
                res_text += f"\n\n<b>Xatolik tafsilotlari:</b>\n<code>{html.escape(err_details)}</code>"
        else:
            res_text = f"❌ <b>Import qilishda xatolik yuz berdi:</b>\n{html.escape(result['message'])}"
            
        await status_msg.edit_text(res_text, parse_mode="HTML")
    except Exception as e:
        await status_msg.edit_text(f"❌ Faylni qayta ishlashda xatolik: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except Exception: pass
        await state.clear()

# --- Individual Add Question Wizard ---
@router.callback_query(F.data == "admin_add_q")
async def admin_add_q_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in ADMIN_IDS: return
    
    await callback.answer()
    await state.set_state(AdminStates.add_q_subject)
    await callback.message.answer("➕ **Yangi savol qo'shish**\n\n1. Fanning nomini kiriting:")

@router.message(AdminStates.add_q_subject, F.text)
async def process_add_q_subject(message: Message, state: FSMContext):
    await state.update_data(subject=message.text.strip())
    await state.set_state(AdminStates.add_q_question)
    await message.answer("2. Savol matnini yuboring:")

@router.message(AdminStates.add_q_question, F.text)
async def process_add_q_question(message: Message, state: FSMContext):
    await state.update_data(question=message.text.strip())
    await state.set_state(AdminStates.add_q_a)
    await message.answer("3. **A variant** matnini yuboring:")

@router.message(AdminStates.add_q_a, F.text)
async def process_add_q_a(message: Message, state: FSMContext):
    await state.update_data(option_a=message.text.strip())
    await state.set_state(AdminStates.add_q_b)
    await message.answer("4. **B variant** matnini yuboring:")

@router.message(AdminStates.add_q_b, F.text)
async def process_add_q_b(message: Message, state: FSMContext):
    await state.update_data(option_b=message.text.strip())
    await state.set_state(AdminStates.add_q_c)
    await message.answer("5. **C variant** matnini yuboring:")

@router.message(AdminStates.add_q_c, F.text)
async def process_add_q_c(message: Message, state: FSMContext):
    await state.update_data(option_c=message.text.strip())
    await state.set_state(AdminStates.add_q_d)
    await message.answer("6. **D variant** matnini yuboring:")

@router.message(AdminStates.add_q_d, F.text)
async def process_add_q_d(message: Message, state: FSMContext):
    await state.update_data(option_d=message.text.strip())
    await state.set_state(AdminStates.add_q_correct)
    await message.answer("7. To'g'ri javob variantini yuboring (A, B, C yoki D):")

@router.message(AdminStates.add_q_correct, F.text)
async def process_add_q_correct(message: Message, state: FSMContext):
    ans = message.text.strip().upper()
    if ans not in ['A', 'B', 'C', 'D']:
        await message.answer("⚠️ Faqat **A**, **B**, **C** yoki **D** variantlaridan birini yozing:")
        return
        
    await state.update_data(correct_answer=ans)
    await state.set_state(AdminStates.add_q_explanation)
    await message.answer("8. Izoh/Tushuntirishni yuboring (Agar tushuntirish kiritmasangiz, /skip deb yozing):")

@router.message(AdminStates.add_q_explanation, F.text)
async def process_add_q_explanation(message: Message, state: FSMContext):
    exp = message.text.strip()
    explanation = None if exp == "/skip" else exp
    
    data = await state.get_data()
    
    from database import add_question
    qid = add_question(
        subject_name=data['subject'],
        question=data['question'],
        option_a=data['option_a'],
        option_b=data['option_b'],
        option_c=data['option_c'],
        option_d=data['option_d'],
        correct_answer=data['correct_answer'],
        explanation=explanation
    )
    
    await return_to_admin(message, state, f"Savol muvaffaqiyatli qo'shildi! ID: `{qid}`")

# --- Individual Delete Question ---
@router.callback_query(F.data == "admin_del_q")
async def admin_del_q_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in ADMIN_IDS: return
    
    await callback.answer()
    await state.set_state(AdminStates.del_q_id)
    await callback.message.answer("🗑 **Savolni o'chirish**\n\nIltimos, o'chirmoqchi bo'lgan savolning ID raqamini kiriting:")

@router.message(AdminStates.del_q_id, F.text)
async def process_delete_q(message: Message, state: FSMContext):
    text = message.text.strip()
    try:
        qid = int(text)
    except ValueError:
        await message.answer("⚠️ Iltimos, faqat butun son ko'rinishidagi ID kiriting:")
        return
        
    success = delete_question(qid)
    if success:
        await return_to_admin(message, state, f"ID `{qid}` bo'lgan savol muvaffaqiyatli o'chirildi.")
    else:
        await return_to_admin(message, state, f"ID `{qid}` bo'lgan savol topilmadi.")

# --- Individual Edit Question Wizard ---
@router.callback_query(F.data == "admin_edit_q")
async def admin_edit_q_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in ADMIN_IDS: return
    
    await callback.answer()
    await state.set_state(AdminStates.edit_q_id)
    await callback.message.answer("📝 **Savolni tahrirlash**\n\nTahrir qilmoqchi bo'lgan savolning ID raqamini kiriting:")

@router.message(AdminStates.edit_q_id, F.text)
async def process_edit_q_id(message: Message, state: FSMContext):
    try:
        qid = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Iltimos, faqat butun son ko'rinishidagi ID kiriting:")
        return
        
    q = get_question(qid)
    if not q:
        await return_to_admin(message, state, f"ID `{qid}` bo'lgan savol topilmadi.")
        return
        
    await state.update_data(edit_qid=qid, current_q=q)
    await state.set_state(AdminStates.edit_q_subject)
    await message.answer(
        f"Savol topildi!\n"
        f"📖 Joriy fan: `{q['subject']}`\n\n"
        f"Yangi fanni yozing (o'zgarishsiz qoldirish uchun /skip deb yozing):"
    )

@router.message(AdminStates.edit_q_subject, F.text)
async def process_edit_subject(message: Message, state: FSMContext):
    val = message.text.strip()
    data = await state.get_data()
    
    subject = data['current_q']['subject'] if val == '/skip' else val
    await state.update_data(edit_subject=subject)
    await state.set_state(AdminStates.edit_q_question)
    await message.answer(
        f"❓ Joriy savol: `{data['current_q']['question_text']}`\n\n"
        f"Yangi savolni yozing (o'zgarishsiz qoldirish uchun /skip deb yozing):"
    )

@router.message(AdminStates.edit_q_question, F.text)
async def process_edit_question(message: Message, state: FSMContext):
    val = message.text.strip()
    data = await state.get_data()
    
    q_text = data['current_q']['question_text'] if val == '/skip' else val
    await state.update_data(edit_question=q_text)
    await state.set_state(AdminStates.edit_q_a)
    await message.answer(
        f"🅰️ Joriy A varianti: `{data['current_q']['option_a']}`\n\n"
        f"Yangi variantni yozing (o'zgarishsiz qoldirish uchun /skip deb yozing):"
    )

@router.message(AdminStates.edit_q_a, F.text)
async def process_edit_a(message: Message, state: FSMContext):
    val = message.text.strip()
    data = await state.get_data()
    
    opt_a = data['current_q']['option_a'] if val == '/skip' else val
    await state.update_data(edit_option_a=opt_a)
    await state.set_state(AdminStates.edit_q_b)
    await message.answer(
        f"🅱️ Joriy B varianti: `{data['current_q']['option_b']}`\n\n"
        f"Yangi variantni yozing (o'zgarishsiz qoldirish uchun /skip deb yozing):"
    )

@router.message(AdminStates.edit_q_b, F.text)
async def process_edit_b(message: Message, state: FSMContext):
    val = message.text.strip()
    data = await state.get_data()
    
    opt_b = data['current_q']['option_b'] if val == '/skip' else val
    await state.update_data(edit_option_b=opt_b)
    await state.set_state(AdminStates.edit_q_c)
    await message.answer(
        f"🅲 Joriy C varianti: `{data['current_q']['option_c']}`\n\n"
        f"Yangi variantni yozing (o'zgarishsiz qoldirish uchun /skip deb yozing):"
    )

@router.message(AdminStates.edit_q_c, F.text)
async def process_edit_c(message: Message, state: FSMContext):
    val = message.text.strip()
    data = await state.get_data()
    
    opt_c = data['current_q']['option_c'] if val == '/skip' else val
    await state.update_data(edit_option_c=opt_c)
    await state.set_state(AdminStates.edit_q_d)
    await message.answer(
        f"🅳 Joriy D varianti: `{data['current_q']['option_d']}`\n\n"
        f"Yangi variantni yozing (o'zgarishsiz qoldirish uchun /skip deb yozing):"
    )

@router.message(AdminStates.edit_q_d, F.text)
async def process_edit_d(message: Message, state: FSMContext):
    val = message.text.strip()
    data = await state.get_data()
    
    opt_d = data['current_q']['option_d'] if val == '/skip' else val
    await state.update_data(edit_option_d=opt_d)
    await state.set_state(AdminStates.edit_q_correct)
    await message.answer(
        f"🔑 Joriy to'g'ri javob: `{data['current_q']['correct_answer']}`\n\n"
        f"Yangi to'g'ri javobni kiriting (A, B, C, D yoki /skip):"
    )

@router.message(AdminStates.edit_q_correct, F.text)
async def process_edit_correct(message: Message, state: FSMContext):
    val = message.text.strip().upper()
    data = await state.get_data()
    
    if val != '/SKIP' and val not in ['A', 'B', 'C', 'D']:
        await message.answer("⚠️ Faqat **A**, **B**, **C**, **D** yoki **/skip** yuboring:")
        return
        
    correct = data['current_q']['correct_answer'] if val == '/SKIP' else val
    await state.update_data(edit_correct=correct)
    await state.set_state(AdminStates.edit_q_explanation)
    await message.answer(
        f"💡 Joriy izoh: `{data['current_q']['explanation'] or 'Mavjud emas'}`\n\n"
        f"Yangi izohni yozing (/skip - o'zgarishsiz qoldirish, /clear - izohni o'chirish):"
    )

@router.message(AdminStates.edit_q_explanation, F.text)
async def process_edit_explanation(message: Message, state: FSMContext):
    val = message.text.strip()
    data = await state.get_data()
    
    explanation = data['current_q']['explanation']
    if val == '/clear':
        explanation = None
    elif val != '/skip':
        explanation = val
        
    edit_question(
        qid=data['edit_qid'],
        subject_name=data['edit_subject'],
        question=data['edit_question'],
        option_a=data['edit_option_a'],
        option_b=data['edit_option_b'],
        option_c=data['edit_option_c'],
        option_d=data['edit_option_d'],
        correct_answer=data['edit_correct'],
        explanation=explanation
    )
    
    await return_to_admin(message, state, f"Savol muvaffaqiyatli tahrirlandi! ID: `{data['edit_qid']}`")

# --- Broadcast Message Handler ---
@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in ADMIN_IDS: return
    
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.answer(
        "📢 **Xabar tarqatish**\n\nBarcha bot foydalanuvchilariga yuboriladigan xabar matnini yuboring. "
        "Matnda Telegram HTML formatlashlaridan foydalanishingiz mumkin:"
    )

@router.message(AdminStates.waiting_for_broadcast, F.text)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    broadcast_text = message.text
    users = get_all_users()
    
    status_msg = await message.answer(f"⏳ Xabar `{len(users)}` ta foydalanuvchiga yuborilmoqda...")
    
    success_cnt = 0
    failed_cnt = 0
    
    for u in users:
        try:
            await bot.send_message(chat_id=u['user_id'], text=broadcast_text, parse_mode="HTML")
            success_cnt += 1
        except Exception:
            failed_cnt += 1
            
    await status_msg.delete()
    await return_to_admin(
        message, 
        state, 
        f"Xabar tarqatish yakunlandi:\n\n"
        f"✅ Muvaffaqiyatli: <code>{success_cnt}</code> ta\n"
        f"❌ Muammolar (bloklangan): <code>{failed_cnt}</code> ta"
    )

# --- Export Results Handler ---
@router.callback_query(F.data == "admin_export")
async def admin_export_callback(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    if user_id not in ADMIN_IDS: return
    
    await callback.answer("Natijalar tayyorlanmoqda...")
    results = get_all_exam_results()
    
    if not results:
        await callback.message.answer("❌ Tizimda hali yakunlangan test natijalari mavjud emas.")
        return
        
    export_path = os.path.join(DATA_DIR, "exam_results_export.xlsx")
    
    try:
        # Create DataFrame
        df = pd.DataFrame(results)
        df.rename(columns={
            'session_id': 'Imtihon ID',
            'full_name': 'F.I.O',
            'username': 'Telegram Username',
            'started_at': 'Boshlangan vaqt',
            'finished_at': 'Tugallangan vaqt',
            'correct': 'To\'g\'ri javoblar',
            'total': 'Jami savollar'
        }, inplace=True)
        
        # Calculate percentage column
        df['Samaradorlik (%)'] = ((df['To\'g\'ri javoblar'] / df['Jami savollar']) * 100).astype(int)
        
        # Write to Excel
        df.to_excel(export_path, index=False, engine="openpyxl")
        
        doc = FSInputFile(export_path, filename="imtihon_natijalari.xlsx")
        await callback.message.answer_document(
            doc,
            caption="📊 <b>Tizimdagi jami yakunlangan imtihon natijalari eksporti (Excel)</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.answer(f"❌ Eksport qilishda xato: {str(e)}")
    finally:
        if os.path.exists(export_path):
            try: os.remove(export_path)
            except Exception: pass

# --- Back to Admin Panel Menu Callback ---
@router.callback_query(F.data == "back_admin")
async def back_admin_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in ADMIN_IDS: return
    
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ <b>Admin Panel</b>\n\nLoyihani boshqarish va testlar yuklash menyusiga xush kelibsiz. "
        "Quyidagi amallardan birini tanlang:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

# --- Cancel handler for admin flows ---
@router.message(Command("cancel"))
async def cancel_any_admin_state(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Amal bekor qilindi.",
        reply_markup=get_main_menu(message.from_user.id in ADMIN_IDS)
    )
