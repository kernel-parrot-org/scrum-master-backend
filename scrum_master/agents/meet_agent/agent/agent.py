from scrum_master.agents.meet_agent.agent.prompts import basic_prompt
from google.adk.agents import Agent
from scrum_master.agents.meet_agent.tools.notion_tool import export_to_notion
from scrum_master.agents.meet_agent.tools.telegram_tool import send_failure_report, send_meeting_report
from scrum_master.agents.meet_agent.tools.transcribe_tool import transcribe_audio

root_agent = Agent(
    name='meeting_protocol_agent',
    model='gemini-2.0-flash',
    instruction=basic_prompt,
    tools=[
        transcribe_audio,
        send_meeting_report,
        export_to_notion,
        send_failure_report,
    ],
)
