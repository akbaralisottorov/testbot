import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from database import init_db
from handlers import router as handlers_router

async def background_timer_checker(bot: Bot, dp: Dispatcher):
    logger = logging.getLogger("timer_checker")
    logger.info("Background exam timer checker started.")
    while True:
        try:
            from database.connection import get_db_connection
            from database import finish_test, get_test_results
            
            conn = get_db_connection()
            cursor = conn.cursor()
            # Fetch all active exams
            cursor.execute("SELECT id, user_id, started_at FROM exam_sessions WHERE is_completed = 0;")
            rows = cursor.fetchall()
            active_sessions = []
            for r in rows:
                active_sessions.append({
                    'id': r['id'],
                    'user_id': r['user_id'],
                    'started_at': r['started_at']
                })
            conn.close()
            
            import datetime
            fmt = "%Y-%m-%d %H:%M:%S"
            now = datetime.datetime.utcnow()
            
            for session in active_sessions:
                s_id = session['id']
                u_id = session['user_id']
                started_str = session['started_at']
                
                started = datetime.datetime.strptime(started_str, fmt)
                elapsed = now - started
                if elapsed.total_seconds() >= 90 * 60:
                    logger.info(f"Auto-submitting expired exam session {s_id} for user {u_id}")
                    # Auto submit!
                    finish_test(s_id)
                    
                    # Clear FSM state
                    ctx = dp.fsm.resolve_context(bot, chat_id=u_id, user_id=u_id)
                    await ctx.clear()
                    
                    # Notify user
                    results = get_test_results(s_id)
                    percentage = int((results['correct'] / results['total']) * 100) if results['total'] > 0 else 0
                    
                    summary_text = (
                        "⏱ <b>Imtihon topshirish vaqtingiz (90 daqiqa) tugadi!</b>\n\n"
                        "Variantingiz avtomatik ravishda yakunlandi va topshirildi.\n\n"
                        f"📊 <b>Natija:</b> {results['correct']} / {results['total']} ({percentage}%)"
                    )
                    
                    try:
                        await bot.send_message(chat_id=u_id, text=summary_text, parse_mode="HTML")
                    except Exception as msg_e:
                        logger.warning(f"Could not send notification to user {u_id}: {msg_e}")
                        
        except Exception as e:
            logger.error(f"Error in background timer checker: {e}")
            
        await asyncio.sleep(15) # Check every 15 seconds

async def main():
    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger("bot")
    logger.info("Initializing database...")
    init_db()
    
    # Check token configuration
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN is not set in environment variables! Please configure it in .env")
        sys.exit(1)
        
    logger.info("Initializing bot instance...")
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    
    # Dispatcher with MemoryStorage
    dp = Dispatcher(storage=MemoryStorage())
    
    # Include combined handlers router
    dp.include_router(handlers_router)
    
    # Start background task for checking expired exams
    asyncio.create_task(background_timer_checker(bot, dp))
    
    logger.info("Starting bot in long polling mode...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot execution stopped.")
