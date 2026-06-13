import os
import logging
import html
import matplotlib
matplotlib.use('Agg')  # Set non-interactive backend for server-side generation
import matplotlib.pyplot as plt
from database import get_user_overall_stats, get_subject_analytics, get_user_exam_history
from config import DATA_DIR

logger = logging.getLogger("analytics")

def generate_analytics_report(user_id: int) -> dict:
    """
    Computes advanced statistics (correct/wrong counts, weak/strong subjects)
    and generates a visual line chart of the user's learning progress.
    """
    stats = get_user_overall_stats(user_id)
    subject_stats = get_subject_analytics(user_id)
    history = get_user_exam_history(user_id)
    
    # If no exams completed, return textual message
    if stats['exams_completed'] == 0:
        return {
            "has_chart": False,
            "report_text": (
                "📊 <b>Batafsil Analitika Hisoboti</b>\n\n"
                "Siz hali biron-bir test variantini yakunlamagansiz.\n"
                "Tahlil va progress grafigini ko'rish uchun oldin kamida bitta test topshiring."
            )
        }
        
    total_answered = stats['total_answered']
    total_correct = stats['total_correct']
    total_wrong = stats['total_wrong']
    overall_percentage = int((total_correct / total_answered) * 100) if total_answered > 0 else 0
    
    # Subject breakdown calculations
    subjects_text = ""
    weak_subject = None
    weak_pct = 101
    strong_subject = None
    strong_pct = -1
    
    for row in subject_stats:
        subj = row['subject']
        answered = row['total_answered']
        correct = row['total_correct']
        wrong = answered - correct
        pct = int((correct / answered) * 100) if answered > 0 else 0
        
        subjects_text += (
            f"🔹 <b>{html.escape(subj)}:</b>\n"
            f"   - Jami yechilgan: <code>{answered}</code> ta\n"
            f"   - To'g'ri: <code>{correct}</code> | Noto'g'ri: <code>{wrong}</code>\n"
            f"   - Samaradorlik: <code>{pct}%</code>\n\n"
        )
        
        # Only determine weak/strong subjects among attempted ones
        if answered > 0:
            if pct < weak_pct:
                weak_pct = pct
                weak_subject = subj
            if pct > strong_pct:
                strong_pct = pct
                strong_subject = subj
                 
    weak_display = f"⚠️ <b>E'tibor berish kerak bo'lgan fan:</b> {html.escape(weak_subject)} ({weak_pct}%)" if weak_subject else "⚠️ <b>E'tibor berish kerak bo'lgan fan:</b> Aniqlanmadi"
    strong_display = f"🌟 <b>Eng yaxshi o'zlashtirilgan fan:</b> {html.escape(strong_subject)} ({strong_pct}%)" if strong_subject else "🌟 <b>Eng yaxshi o'zlashtirilgan fan:</b> Aniqlanmadi"
    
    report_text = (
        "📊 <b>Advanced Analytics Report</b>\n\n"
        f"🏆 Yakunlangan variantlar: <code>{stats['exams_completed']}</code> ta\n"
        f"🎯 Jami yechilgan savollar: <code>{total_answered}</code> ta\n"
        f"✅ To'g'ri javoblar: <code>{total_correct}</code> ta\n"
        f"❌ Noto'g'ri javoblar: <code>{total_wrong}</code> ta\n"
        f"🎯 Umumiy samaradorlik ko'rsatkichi: <code>{overall_percentage}%</code>\n\n"
        "📚 <b>Fanlar kesimidagi tahlil:</b>\n"
        f"{subjects_text}"
        f"{strong_display}\n"
        f"{weak_display}\n\n"
        "📈 <i>Quyida oxirgi 10 ta yechilgan variant bo'yicha progress grafigingiz ilova qilindi:</i> "
    )
    
    # Generate progress chart image
    chart_path = os.path.join(DATA_DIR, f"progress_{user_id}.png")
    has_chart = False
    
    if len(history) > 0:
        try:
            # Limit history to the last 10 attempts
            last_attempts = history[-10:]
            attempts_indices = list(range(1, len(last_attempts) + 1))
            percentages = [int((h['correct'] / h['total']) * 100) if h['total'] > 0 else 0 for h in last_attempts]
            
            plt.figure(figsize=(8, 4.5))
            plt.plot(attempts_indices, percentages, marker='o', color='#3F51B5', linewidth=2.5, markersize=8, label='Samaradorlik %')
            
            plt.title("O'zlashtirish progress grafigi (Oxirgi 10 ta variant)", fontsize=12, fontweight='bold', pad=15)
            plt.xlabel("Taqdim etilgan variant tartibi", fontsize=10)
            plt.ylabel("To'g'ri javoblar ulushi (%)", fontsize=10)
            plt.ylim(0, 105)
            plt.xticks(attempts_indices)
            plt.grid(True, linestyle='--', alpha=0.5)
            
            # Add annotations for each data point
            for x, y in zip(attempts_indices, percentages):
                plt.annotate(f"{y}%", (x, y), textcoords="offset points", xytext=(0,8), ha='center', fontsize=9, fontweight='bold', color='#1A237E')
                 
            plt.tight_layout()
            plt.savefig(chart_path, dpi=150)
            plt.close()
            has_chart = True
        except Exception as e:
            logger.exception("Matplotlib plotting encountered an exception")
            has_chart = False
             
    return {
        "has_chart": has_chart,
        "chart_path": chart_path if has_chart else None,
        "report_text": report_text
    }

