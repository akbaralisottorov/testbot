from aiogram import Router
from handlers.start import router as start_router
from handlers.test import router as test_router
from handlers.mistakes import router as mistakes_router
from handlers.admin import router as admin_router
from handlers.leaderboard import router as leaderboard_router

# Root router for the bot handlers
router = Router()
router.include_routers(
    admin_router,
    leaderboard_router,
    test_router,
    mistakes_router,
    start_router
)
