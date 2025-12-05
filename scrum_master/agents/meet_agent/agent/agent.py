from google.adk.agents import Agent

from ..tools.jira_tool import (
    create_jira_epic,
    create_jira_issue,
    create_jira_subtask,
    process_meeting_tasks_to_jira,
    update_jira_issue,
)
from ..tools.notion_tool import export_to_notion
from ..tools.telegram_tool import send_failure_report, send_meeting_report
from ..tools.transcribe_tool import transcribe_audio
from .prompts import basic_prompt

root_agent = Agent(
    name='meeting_protocol_agent',
    model='gemini-2.0-flash',
    instruction=basic_prompt,
    tools=[
        transcribe_audio,
        # send_meeting_report,
        # export_to_notion,
        # send_failure_report,
        create_jira_issue,
        update_jira_issue,
        create_jira_epic,
        create_jira_subtask,
        process_meeting_tasks_to_jira,
    ],
)
