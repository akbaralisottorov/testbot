# DTM-style Telegram Exam Simulator Bot 🚀

Ushbu Telegram bot DTM (Davlat Test Markazi) uslubidagi variantlarni yechish, natijalarni tahlil qilish, xatolar ustida ishlash va foydalanuvchilar o'rtasida raqobatni shakllantirish uchun mo'ljallangan.

This Telegram bot is a DTM-style Exam Simulator allowing users to take 50-question mock exams (16+17+17 subject distribution), practice mistake corrections, check global & daily mock leaderboards, and view history charts.

---

## ✨ Imkoniyatlar (Features)

*   **📝 Standart Imtihon (Standard Exams)**: Tanlangan 3 ta fandan jami 50 ta savol (16 + 17 + 17 taqsimotda) tasodifiy tarzda shakllantiriladi. Savollar takrorlanmasligi uchun foydalanuvchi hali yechmagan savollar ustuvor ravishda tanlanadi.
*   **⏱ 90-Daqiqalik Taymer (90-Minute Timer)**: Variantni yechish jarayonida foydalanuvchiga qolgan vaqt ko'rsatiladi (`⏱ Qolgan vaqt: MM:SS`).
*   **🔄 Avtomatik Topshirish (Auto-Submit)**: Vaqt tugaganda imtihon avtomatik ravishda yakunlanadi, FSM holati tozalanadi va foydalanuvchiga natijalar xabari yuboriladi (ham faol harakatda, ham fondagi asinxron timer orqali).
*   **🏆 Kunlik Mock Imtihon (Daily Mock Exams)**: Har kuni barcha foydalanuvchilar uchun yagona bo'lgan va kunlik sana (seed) asosida generatsiya qilinadigan mock imtihon. Kuniga faqat 1 marta topshirish mumkin.
*   **🏅 Peshqadamlar Reytingi (Leaderboards)**:
    *   *Umumiy Reyting*: Standart testlardagi o'rtacha foizi bo'yicha top 10 talik.
    *   *Kunlik Mock Reytingi*: Bugungi mock imtihonida eng yuqori ball to'plagan va eng tez yechganlar (vaqt bo'yicha saralangan) top 10 talik.
*   **📓 Xatolar Daftari (Wrong Answers Notebook)**: Imtihonlarda xato qilingan savollar alohida notebookda jamlanadi. Ularni qayta ishlab to'g'ri javob berilganda notebookdan avtomatik o'chiriladi.
*   **📊 Natijalar Tarixi (Exam History)**: Oxirgi topshirilgan 10 ta imtihon ro'yxati, ballar, foiz va batafsil tahlil (`🔍 Tahlil #ID` tugmasi orqali har bir savol va izohini ko'rish).
*   **⚙️ Admin Panel**: Adminlar uchun foydalanuvchilar soni va fanlar statistikasi, Excel (.xlsx) shablonini yuklab olish, Excel orqali testlarni qo'shish/tozalab yuklash, xabar tarqatish (broadcast) hamda jami natijalarni Excelga eksport qilish.

---

## 📂 Loyiha Strukturasi (Project Structure)

```
project/
├── bot.py                        # Botni ishga tushirish va fondagi timer checker.
├── config.py                     # Sozlamalar va .env faylidan o'zgaruvchilarni yuklash.
├── requirements.txt              # Zaruriy python paketlar ro'yxati.
├── verify_test_logic.py          # 13 bosqichli programmatic unit testlar to'plami.
├── generate_large_sample.py      # Test uchun 1860 ta savol generatsiya qiluvchi skript.
├── database/
│   ├── __init__.py               # DB funksiyalarining paketi.
│   ├── connection.py             # SQLite ulanish menedjeri.
│   └── models.py                 # DB jadvallari, indekslari, triggerlar va CRUD funksiyalar.
├── services/
│   ├── __init__.py               # Servislar paketi.
│   ├── excel_parser.py           # Excel fayllarini tekshirish va import qilish.
│   ├── test_manager.py           # Variantlar generatsiyasi va javoblarni baholash.
│   └── analytics.py              # Foydalanuvchi statistikasi va matplotlib grafik yaratish.
├── keyboards/
│   ├── reply.py                  # Asosiy menyu (ReplyMarkup) tugmalari.
│   └── inline.py                 # Imtihon yechish, peshqadamlar va admin inline tugmalari.
├── handlers/
│   ├── start.py                  # Start, mening natijalarim va tarix handlerlari.
│   ├── test.py                   # Imtihon topshirish va tahlil handlerlari.
│   ├── mistakes.py               # Xatolar daftari handleri.
│   ├── leaderboard.py            # Peshqadamlar reytingi handleri.
│   └── admin.py                  # Admin panel handleri.
└── data/
    ├── database.db               # Avtomatik yaratiladigan SQLite baza fayli.
    └── tests.xlsx                # Namunaviy 1860 ta savoldan iborat Excel fayli.
```

---

## 🛠 O'rnatish va Ishga tushirish (Setup & Running)

### 1. Kutubxonalarni o'rnatish
Loyiha uchun virtual muhit yaratib, kerakli kutubxonalarni o'rnating:
```bash
python -m venv .venv
# Windowsda faollashtirish:
.venv\Scripts\activate
# Paketlarni o'rnatish:
pip install -r requirements.txt
```

### 2. Sozlamalar (.env)
Loyiha ildiz papkasida `.env` faylini yarating va quyidagicha to'ldiring:
```env
BOT_TOKEN=Sizning_Telegram_Bot_Tokeningiz
ADMIN_IDS=12345678,98765432
```
*   `BOT_TOKEN` - `@BotFather` orqali olingan token.
*   `ADMIN_IDS` - Admin hisoblangan foydalanuvchilarning Telegram ID raqamlari (vergul bilan ajratilgan holda).

### 3. Savollarni tayyorlash
Loyiha bazasini savollar bilan to'ldirish uchun namunaviy 1860 ta savolni generatsiya qiling yoki admin panel orqali o'zingizning Excel faylingizni yuklang:
```bash
python generate_large_sample.py
```
Bu buyruq `data/tests.xlsx` faylini yaratadi. Unda Matematika, Ona tili va Tarix fanlaridan 620 tadan savollar mavjud bo'ladi.

### 4. Testlarni ishga tushirish
Tizimning barcha zanjirlari muvaffaqiyatli ishlayotganini tekshirish uchun unit testlarni yuriting:
```bash
python verify_test_logic.py
```

### 5. Botni ishga tushirish
Botni long polling rejimida yoqish uchun quyidagi buyruqni bering:
```bash
python bot.py
```

---

## 📊 Excel Shablon Ustunlari (Excel Column Schema)

Savollarni Excel orqali yuklamoqchi bo'lsangiz, ustun nomlari quyidagicha bo'lishi shart:
1.  `subject` - Fan nomi (masalan, Matematika).
2.  `question` - Savol matni.
3.  `option_a` - A varianti matni.
4.  `option_b` - B varianti matni.
5.  `option_c` - C varianti matni.
6.  `option_d` - D varianti matni.
7.  `correct_answer` - To'g'ri javob harfi (faqat `A`, `B`, `C` yoki `D`).
8.  `explanation` *(ixtiyoriy)* - Savol uchun izoh/yechilish yo'li.
