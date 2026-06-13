import html
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from database import (
    add_user,
    get_user_completed_tests_count,
    get_user_mistakes_count,
    get_subject_analytics,
    get_user_exam_history
)
from keyboards import get_main_menu
from config import ADMIN_IDS

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Handles the /start command. Registers the user and displays the welcome message.
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    add_user(user_id, username, full_name)
    
    is_admin = user_id in ADMIN_IDS
    welcome_text = (
        f"Assalomu alaykum, {html.escape(full_name)}! 👋\n\n"
        "DTM uslubida tayyorlanish uchun mo'ljallangan Telegram botga xush kelibsiz!\n"
        "Bu bot orqali siz fandan variantlar yechishingiz, xatolaringizni tahlil qilishingiz "
        "va xato ishlangan savollarni qayta ishlashingiz mumkin.\n\n"
        "Boshlash uchun quyidagi menyu tugmalaridan foydalaning."
    )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu(is_admin=is_admin),
        parse_mode="HTML"
    )

@router.message(Command("my_results"))
@router.message(F.text == "📊 Mening natijalarim")
async def show_my_results(message: Message):
    """
    Displays the user's test solving statistics.
    """
    user_id = message.from_user.id
    
    completed_tests = get_user_completed_tests_count(user_id)
    mistakes_count = get_user_mistakes_count(user_id)
    
    text = (
        "📊 <b>Mening Natijalarim & Statistika</b>\n\n"
        f"🏆 Jami topshirilgan imtihonlar: <code>{completed_tests}</code> ta\n"
        f"📓 Xatolar daftari: <code>{mistakes_count}</code> ta savol\n\n"
        "Quyidagi tugmalardan birini tanlang:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Imtihonlar tarixi", callback_data="hist_list")],
        [InlineKeyboardButton(text="📈 Batafsil statistika (Grafik)", callback_data="hist_stats")]
    ])
    
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "hist_list")
async def show_history_list_callback(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    
    history = get_user_exam_history(user_id)
    
    if not history:
        await callback.message.edit_text(
            "❌ Siz hali birorta ham imtihon topshirmagansiz.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Orqaga", callback_data="back_results_menu")]
            ])
        )
        return
        
    text = "📋 <b>Oxirgi topshirilgan imtihonlar tarixi (Top 10):</b>\n\n"
    builder = InlineKeyboardBuilder()
    
    for idx, exam in enumerate(history[:10]):
        date_part = exam['started_at'].split(" ")[0] if exam['started_at'] else "Noma'lum"
        e_type = "Standart" if exam['exam_type'] != 'daily_mock' else f"Mock ({exam['mock_date']})"
        pct = int((exam['correct'] / exam['total']) * 100) if exam['total'] > 0 else 0
        
        text += f"{idx+1}. 📅 <b>{html.escape(date_part)}</b> | {e_type}\n"
        text += f"   🎯 Natija: <code>{exam['correct']}/{exam['total']}</code> ta to'g'ri ({pct}%)\n\n"
        
        builder.button(text=f"🔍 Tahlil #{exam['id']}", callback_data=f"an_hist:{exam['id']}")
        
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="↩️ Orqaga", callback_data="back_results_menu"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data == "back_results_menu")
async def back_results_menu_callback(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    completed_tests = get_user_completed_tests_count(user_id)
    mistakes_count = get_user_mistakes_count(user_id)
    
    text = (
        "📊 <b>Mening Natijalarim & Statistika</b>\n\n"
        f"🏆 Jami topshirilgan imtihonlar: <code>{completed_tests}</code> ta\n"
        f"📓 Xatolar daftari: <code>{mistakes_count}</code> ta savol\n\n"
        "Quyidagi tugmalardan birini tanlang:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Imtihonlar tarixi", callback_data="hist_list")],
        [InlineKeyboardButton(text="📈 Batafsil statistika (Grafik)", callback_data="hist_stats")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "hist_stats")
async def show_history_stats_callback(callback: CallbackQuery):
    await callback.answer("Hisob-kitob qilinmoqda...")
    user_id = callback.from_user.id
    from services import generate_analytics_report
    from aiogram.types import FSInputFile
    
    try:
        report = generate_analytics_report(user_id)
        
        await callback.message.delete()
        
        if report['has_chart']:
            photo = FSInputFile(report['chart_path'])
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="go_home")]
            ])
            await callback.message.answer_photo(
                photo=photo,
                caption=report['report_text'],
                parse_mode="HTML",
                reply_markup=kb
            )
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Orqaga", callback_data="back_results_menu")]
            ])
            await callback.message.answer(report['report_text'], parse_mode="HTML", reply_markup=kb)
            
    except Exception as e:
        await callback.message.answer(f"❌ Hisobot yaratishda xatolik yuz berdi: {str(e)}")

@router.callback_query(F.data.startswith("an_hist:"))
async def analyze_history_callback(callback: CallbackQuery, state: FSMContext):
    session_id = int(callback.data.split(":")[1])
    await callback.answer()
    
    from handlers.test import TestStates
    await state.set_state(TestStates.analyzing_test)
    await state.update_data(analysis_test_id=session_id)
    
    from handlers.test import process_analysis_callback
    callback.data = "an:1"
    await process_analysis_callback(callback, state)

