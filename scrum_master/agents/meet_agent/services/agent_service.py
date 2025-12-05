"""
Service for interacting with the Google ADK agent.
"""
import json
import logging
from typing import Optional

from scrum_master.agents.meet_agent.agent.agent import root_agent

logger = logging.getLogger(__name__)


class AgentService:
    """Service for sending messages to the agent and processing responses."""
    
    def __init__(self):
        self.agent = root_agent
    
    async def process_audio_to_jira(
        self, 
        audio_uri: str, 
        project_key: str,
        team_members: Optional[list[str]] = None
    ) -> dict:
        """
        Process audio file: transcribe, analyze, and create Jira tasks.
        
        Args:
            audio_uri: GCS URI of the audio file (e.g., gs://bucket/file.wav)
            project_key: Jira project key
            team_members: Optional list of team member names
        
        Returns:
            dict with status, meeting_data, and jira_results
        """
        try:
            # Construct message for the agent
            message = f"""
Обработай аудиозапись встречи и создай задачи в Jira.

Аудио файл: {audio_uri}
Проект Jira: {project_key}
"""
            
            if team_members:
                message += f"\nКоманда проекта: {', '.join(team_members)}\n"
            
            message += """
Выполни следующие шаги:
1. Транскрибируй аудио с помощью transcribe_audio()
2. Проанализируй транскрипцию и определи участников
3. Извлеки задачи и определи сложность проекта
4. Собери meeting_data в структурированном формате
5. Вызови process_meeting_tasks_to_jira(meeting_data) для создания задач в Jira

ВАЖНО: meeting_data будет автоматически выведена в консоль функцией process_meeting_tasks_to_jira.
"""
            
            logger.info(f"[AgentService] Sending message to agent for audio: {audio_uri}")
            
            # Call agent directly using generate method
            # Agent от google.adk.agents имеет метод generate для получения ответа
            response = await self.agent.generate(
                user_prompt=message,
                # Создаем новую сессию для каждого запроса (stateless)
            )
            
            logger.info(f"[AgentService] Agent response received")
            logger.info(f"[AgentService] Response type: {type(response)}")
            
            # Попытаемся извлечь текст ответа
            agent_response_text = ""
            if hasattr(response, 'text'):
                agent_response_text = response.text
            elif hasattr(response, 'content'):
                agent_response_text = response.content
            elif isinstance(response, str):
                agent_response_text = response
            else:
                agent_response_text = str(response)
            
            logger.info(f"[AgentService] Agent response complete: {agent_response_text[:200]}...")
            
            return {
                "status": "success",
                "agent_response": agent_response_text,
                "meeting_data": None,  # meeting_data выводится в логи через process_meeting_tasks_to_jira
                "message": "Audio processing initiated. Check logs for meeting_data structure."
            }
            
        except Exception as e:
            logger.error(f"[AgentService] Error processing audio: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "agent_response": None,
                "meeting_data": None
            }

