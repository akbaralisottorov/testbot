from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Generates the main menu reply keyboard.
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📝 Standart Imtihon"),
        KeyboardButton(text="🏆 Kunlik Mock")
    )
    builder.row(
        KeyboardButton(text="📓 Xatolar daftari"),
        KeyboardButton(text="📊 Mening natijalarim")
    )
    builder.row(
        KeyboardButton(text="🏅 Peshqadamlar")
    )
    if is_admin:
        builder.row(KeyboardButton(text="⚙️ Admin panel"))
        
    return builder.as_markup(resize_keyboard=True, placeholder="Menyudan birini tanlang:")
