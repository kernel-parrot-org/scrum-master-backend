import logging
from datetime import datetime

from notion_client import AsyncClient
from pydantic import SecretStr

logger = logging.getLogger(__name__)


class NotionService:
    def __init__(self, token: SecretStr, page_id: str):
        self.client = AsyncClient(auth=token.get_secret_value())
        self.parent_page_id = page_id

    async def create_meeting_page(self, meeting_data: dict) -> str:
        summary = meeting_data.get('summary', {})
        title = summary.get('title', 'Meeting')
        meeting_type = meeting_data.get('meeting_type', 'meeting')
        participants = meeting_data.get('participants', {})
        topics = summary.get('topics', [])
        decisions = summary.get('decisions', [])
        key_points = summary.get('key_points', [])
        tasks = meeting_data.get('tasks', [])

        children = list()

        children.append({
            'object': 'block',
            'type': 'heading_2',
            'heading_2': {'rich_text': [{'text': {'content': '📋 Обзор встречи'}}]}
        })
        children.append({
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'rich_text': [{
                    'text': {
                        'content': f"Тип встречи: {meeting_type.title()} — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    }
                }]
            }
        })

        if participants:
            active = ', '.join([p['name'] for p in participants.get('active_speakers', [])]) or '—'
            mentioned = ', '.join(participants.get('mentioned', [])) or '—'
            children.append({
                'object': 'block',
                'type': 'heading_2',
                'heading_2': {'rich_text': [{'text': {'content': '👥 Участники встречи'}}]}
            })
            children.append({
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [
                        {'text': {'content': f'Активные спикеры: {active}\n'}},
                        {'text': {'content': f'Упомянуты: {mentioned}'}}
                    ]
                }
            })

        if topics:
            children.append({
                'object': 'block',
                'type': 'heading_2',
                'heading_2': {'rich_text': [{'text': {'content': '🧩 Темы обсуждения'}}]}
            })
            for t in topics:
                speakers = ', '.join(t.get('speakers', [])) or 'Не указано'
                children.append({
                    'object': 'block',
                    'type': 'toggle',
                    'toggle': {
                        'rich_text': [{'text': {'content': f"{t['title']} (👥 {speakers})"}}],
                        'children': [{
                            'object': 'block',
                            'type': 'paragraph',
                            'paragraph': {'rich_text': [{'text': {'content': t['description']}}]}
                        }]
                    }
                })

        if decisions:
            children.append({
                'object': 'block',
                'type': 'heading_2',
                'heading_2': {'rich_text': [{'text': {'content': '✅ Принятые решения'}}]}
            })
            for d in decisions:
                who = ', '.join(d.get('who_decided', [])) or '—'
                context = d.get('context', 'Без контекста')
                children.append({
                    'object': 'block',
                    'type': 'bulleted_list_item',
                    'bulleted_list_item': {
                        'rich_text': [
                            {'text': {'content': f"{d['description']}"}},
                            {'text': {'content': f'\n💬 {context}\n👤 Решил: {who}'}}
                        ]
                    }
                })

        if key_points:
            children.append({
                'object': 'block',
                'type': 'heading_2',
                'heading_2': {'rich_text': [{'text': {'content': '💡 Ключевые моменты'}}]}
            })
            for kp in key_points:
                children.append({
                    'object': 'block',
                    'type': 'bulleted_list_item',
                    'bulleted_list_item': {
                        'rich_text': [{'text': {'content': kp}}]
                    }
                })

        if tasks:
            children.append({
                'object': 'block',
                'type': 'heading_2',
                'heading_2': {'rich_text': [{'text': {'content': '📌 To-Do список'}}]}
            })
            for t in tasks:
                assignee = t.get('assignee') or 'Не назначено'
                deadline = t.get('deadline') or 'Без срока'
                priority = t.get('priority', 'medium').capitalize()
                mentioned_by = t.get('mentioned_by')
                reason = t.get('priority_reason')
                context = t.get('context')

                # Каждый таск — toggle для компактности
                toggle_text = f"{t['title']} (👤 {assignee} | 🕒 {deadline} | ⚡ {priority})"
                children.append({
                    'object': 'block',
                    'type': 'toggle',
                    'toggle': {
                        'rich_text': [{'text': {'content': toggle_text}}],
                        'children': [
                            {
                                'object': 'block',
                                'type': 'paragraph',
                                'paragraph': {
                                    'rich_text': [{'text': {'content': t['description']}}]
                                }
                            },
                            *([
                                {
                                    'object': 'block',
                                    'type': 'paragraph',
                                    'paragraph': {
                                        'rich_text': [
                                            {'text': {'content': f'💬 Упомянул: {mentioned_by}'}}
                                        ]
                                    }
                                }
                            ] if mentioned_by else []),
                            *([
                                {
                                    'object': 'block',
                                    'type': 'paragraph',
                                    'paragraph': {
                                        'rich_text': [
                                            {'text': {'content': f'📎 Причина приоритета: {reason}'}}
                                        ]
                                    }
                                }
                            ] if reason else []),
                            *([
                                {
                                    'object': 'block',
                                    'type': 'paragraph',
                                    'paragraph': {
                                        'rich_text': [
                                            {'text': {'content': f'🗒 Контекст: {context}'}}
                                        ]
                                    }
                                }
                            ] if context else [])
                        ]
                    }
                })

        try:
            page = await self.client.pages.create(
                parent={'page_id': self.parent_page_id},
                properties={
                    'title': [
                        {'text': {
                            'content': f"{title} ({meeting_type}) — {datetime.now().strftime('%Y-%m-%d')}"
                        }}
                    ]
                },
                children=children
            )

            logger.info(f"[NOTION] Meeting page created: {page['id']}")
            return page['id']

        except Exception as e:
            logger.error(f'[NOTION] Failed to create meeting page: {e}')
            raise

    async def close(self):
        await self.client.aclose()
