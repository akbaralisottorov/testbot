import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database import get_overall_leaderboard, get_daily_mock_leaderboard
from keyboards import get_leaderboard_keyboard

router = Router()

def format_duration(seconds):
    if seconds is None:
        return "N/A"
    mins, secs = divmod(int(seconds), 60)
    return f"{mins}m {secs}s"

@router.message(Command("leaderboard") | (F.text == "🏅 Peshqadamlar"))
async def show_leaderboard_menu(message: Message):
    """
    Displays the leaderboard selection menu.
    """
    text = (
        "🏅 **Peshqadamlar Reytingi**\n\n"
        "Qaysi reytingni ko'rmoqchisiz? Quyidagi tugmalardan birini tanlang:\n\n"
        "🏆 **Kunlik Mock** - Bugungi mock imtihonida eng yuqori ball to'plagan va eng tez yechganlar.\n"
        "👑 **Umumiy Reyting** - Barcha topshirgan standart testlar bo'yicha o'rtacha foizi eng yuqorilar."
    )
    await message.answer(text, reply_markup=get_leaderboard_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "lb_overall")
async def show_overall_leaderboard_callback(callback: CallbackQuery):
    await callback.answer()
    
    leaders = get_overall_leaderboard()
    
    text = "👑 **Umumiy Peshqadamlar Reytingi (Top 10):**\n\n"
    if not leaders:
        text += "_Hozircha peshqadamlar mavjud emas. Birinchi bo'lib test topshiring!_"
    else:
        medals = ["🥇", "🥈", "🥉", "4.", "5.", "6.", "7.", "8.", "9.", "10."]
        for idx, l in enumerate(leaders):
            medal = medals[idx] if idx < len(medals) else f"{idx+1}."
            name = l['full_name'] or f"Foydalanuvchi {l['user_id']}"
            username_str = f" (@{l['username']})" if l['username'] else ""
            text += f"{medal} **{name}**{username_str}\n"
            text += f"   🎯 O'rtacha: `{l['avg_percent']}%` | Jami: `{l['total_exams']}` ta variant\n\n"
            
    await callback.message.edit_text(text, reply_markup=get_leaderboard_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "lb_mock")
async def show_mock_leaderboard_callback(callback: CallbackQuery):
    await callback.answer()
    
    today_str = datetime.date.today().isoformat()
    leaders = get_daily_mock_leaderboard(today_str)
    
    text = f"🏆 **Kunlik Mock Imtihon Reytingi ({today_str}) (Top 10):**\n\n"
    if not leaders:
        text += "_Bugungi mock imtihonida hali hech kim qatnashmadi. Birinchi bo'ling!_"
    else:
        medals = ["🥇", "🥈", "🥉", "4.", "5.", "6.", "7.", "8.", "9.", "10."]
        for idx, l in enumerate(leaders):
            medal = medals[idx] if idx < len(medals) else f"{idx+1}."
            name = l['full_name'] or f"Foydalanuvchi {l['user_id']}"
            username_str = f" (@{l['username']})" if l['username'] else ""
            duration_str = format_duration(l['duration_sec'])
            text += f"{medal} **{name}**{username_str}\n"
            text += f"   🎯 Natija: `{l['correct_count']} / {l['total_count']}` | ⏱ Vaqt: `{duration_str}`\n\n"
            
    await callback.message.edit_text(text, reply_markup=get_leaderboard_keyboard(), parse_mode="Markdown")
