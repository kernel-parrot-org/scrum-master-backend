import io
import logging
from datetime import datetime

from core.config import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from services.telegram_service import TelegramService

logger = logging.getLogger(__name__)


def _generate_pdf(meeting_data: dict) -> bytes:
    buffer = io.BytesIO()

    pdfmetrics.registerFont(
        TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    )

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=25,
        rightMargin=25,
        topMargin=40,
        bottomMargin=30,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Russian', fontName='DejaVu', fontSize=10, leading=13))
    styles.add(ParagraphStyle(name='Heading', fontName='DejaVu', fontSize=14, leading=18, spaceAfter=8, textColor=colors.darkblue))
    styles.add(ParagraphStyle(name='SubHeading', fontName='DejaVu', fontSize=12, leading=16, textColor=colors.darkslateblue))
    styles.add(ParagraphStyle(name='TableCell', fontName='DejaVu', fontSize=9, leading=11))

    elements = []

    summary = meeting_data.get('summary', {})
    tasks = meeting_data.get('tasks', [])
    participants = meeting_data.get('participants', {})
    meeting_type = meeting_data.get('meeting_type', 'Не определен')

    elements.append(Paragraph(f"Протокол встречи: <b>{summary.get('title', 'Без названия')}</b>", styles['Heading']))
    elements.append(Paragraph(f'Тип встречи: {meeting_type}', styles['Russian']))
    elements.append(Paragraph(f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}", styles['Russian']))
    elements.append(Spacer(1, 10))

    if participants:
        elements.append(Paragraph('<b>Участники</b>', styles['SubHeading']))
        actives = ', '.join([p['name'] for p in participants.get('active_speakers', [])]) or '—'
        mentioned = ', '.join(participants.get('mentioned', [])) or '—'
        elements.append(Paragraph(f'Активные спикеры: {actives}', styles['Russian']))
        elements.append(Paragraph(f'Упомянуты: {mentioned}', styles['Russian']))
        elements.append(Spacer(1, 8))

    elements.append(Paragraph('<b>Темы обсуждения</b>', styles['SubHeading']))
    for t in summary.get('topics', []):
        elements.append(Paragraph(f"• <b>{t['title']}</b>: {t['description']}", styles['Russian']))
    elements.append(Spacer(1, 8))

    if summary.get('decisions'):
        elements.append(Paragraph('<b>Принятые решения</b>', styles['SubHeading']))
        for d in summary['decisions']:
            elements.append(Paragraph(f"• {d['description']}", styles['Russian']))
            if d.get('context'):
                elements.append(Paragraph(f"<font color='grey'><i>{d['context']}</i></font>", styles['Russian']))
        elements.append(Spacer(1, 8))

    if summary.get('key_points'):
        elements.append(Paragraph('<b>Ключевые моменты</b>', styles['SubHeading']))
        for kp in summary['key_points']:
            elements.append(Paragraph(f'• {kp}', styles['Russian']))
        elements.append(Spacer(1, 8))

    if tasks:
        elements.append(Paragraph('<b>To-Do список</b>', styles['SubHeading']))
        table_data = [
            [
                Paragraph('<b>№</b>', styles['TableCell']),
                Paragraph('<b>Задача и описание</b>', styles['TableCell']),
                Paragraph('<b>Исполнитель</b>', styles['TableCell']),
                Paragraph('<b>Срок</b>', styles['TableCell']),
                Paragraph('<b>Приоритет</b>', styles['TableCell']),
            ]
        ]

        for i, t in enumerate(tasks, 1):
            description = (
                f"<b>{t.get('title','')}</b><br/>"
                f"<font color='grey'>{t.get('description','')}</font>"
            )
            extra = []
            if t.get('mentioned_by'):
                extra.append(f"<i>Упомянул: {t['mentioned_by']}</i>")
            if t.get('priority_reason'):
                extra.append(f"<i>Причина: {t['priority_reason']}</i>")
            if extra:
                description += '<br/>' + '<br/>'.join(extra)

            table_data.append([
                Paragraph(str(i), styles['TableCell']),
                Paragraph(description, styles['TableCell']),
                Paragraph(t.get('assignee') or '—', styles['TableCell']),
                Paragraph(t.get('deadline') or '—', styles['TableCell']),
                Paragraph(t.get('priority','').capitalize(), styles['TableCell']),
            ])

        table = Table(table_data, colWidths=[15*mm, 90*mm, 30*mm, 25*mm, 25*mm], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(table)

    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data



def _parse_meeting_data(meeting_data: dict) -> dict:
    try:
        summary = meeting_data.get('summary', {})

        title = summary.get('title', 'Без названия')
        summary_text = f"📋 <b>{title}</b> {datetime.now().strftime('%Y-%m-%d')}\n\n"

        if summary.get('topics'):
            summary_text += '🧩 <b>Темы обсуждения:</b>\n'
            for i, topic in enumerate(summary['topics'], 1):
                speakers = ', '.join(topic.get('speakers', [])) or '—'
                summary_text += (
                    f"{i}. <b>{topic['title']}</b>\n"
                    f"   ┗ {topic['description']}\n"
                    f"   👥 Спикеры: {speakers}\n"
                )
            summary_text += '\n'

        if summary.get('key_points'):
            summary_text += '💡 <b>Ключевые моменты:</b>\n'
            for i, kp in enumerate(summary['key_points'], 1):
                summary_text += f'{i}. {kp}\n'
            summary_text += '\n'

        return {
            'status': 'success',
            'summary_text': summary_text.strip(),
        }

    except Exception as e:
        return {'status': 'error', 'message': str(e)}


async def send_meeting_report(meeting_data: dict) -> dict:
    try:
        logger.info('[TOOL] Sending meeting report...')
        parsed_meeting_data = _parse_meeting_data(meeting_data)
        telegram_service = TelegramService(
            settings.telegram.bot_token,
            settings.telegram.chat_id,
        )
        pdf_data = _generate_pdf(meeting_data)
        await telegram_service.send_pdf(pdf_data, filename='meeting_report.pdf')

        logger.info(
            '[TOOL] telegram service configured successfully, sending report...'
        )
        await telegram_service.send_message(

                "📋 <b>Summary встречи готов!</b>\n\n"
                "──────────────────────────────\n\n"
                f"{parsed_meeting_data['summary_text']}\n\n"

        )

        return {
            'status': 'success',
            'message': 'Report generated and sent successfully',
        }

    except Exception as e:
        logger.info(f'[TOOL] Telegram sending error: {e}')
        return {
            'status': 'error',
            'error_message': f'{e!s}',
            'stage': 'send_meeting_report',
        }


async def send_failure_report(message: str) -> dict:
    try:
        logger.info(f'[TOOL] Telegram sending error: {message}')
        telegram_service = TelegramService(
            settings.telegram.bot_token,
            settings.telegram.chat_id,
        )

        await telegram_service.send_message(
            f'Произошла ошибка, которая приостановила работу агента: {message}'
        )

        return {'status': 'success', 'message': 'Failure report sent successfully'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
