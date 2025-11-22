from agent.prompts import basic_prompt
from google.adk.agents import Agent
from tools.notion_tool import export_to_notion
from tools.telegram_tool import send_failure_report, send_meeting_report
from tools.transcribe_tool import transcribe_audio

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
