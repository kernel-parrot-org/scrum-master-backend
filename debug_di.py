import asyncio
import sys
from unittest.mock import MagicMock

sys.path.append(".")

from dishka import make_async_container, Scope
from scrum_master.modules.jira.ioc import JiraProvider
from scrum_master.shared.ioc import SharedInfrastructureProvider
from scrum_master.shared.config import Settings
from scrum_master.modules.jira.infrastructure.jira.jira_service import JiraService

async def main():
    print("Setting up container...")
    
    # Mock settings to avoid env vars issues
    settings = MagicMock()
    settings.jira.api_url = "http://jira.example.com"
    settings.jira.api_token.get_secret_value.return_value = "token"
    settings.postgres.host = "localhost" # Mock postgres config for SharedInfrastructureProvider
    
    container = make_async_container(
        SharedInfrastructureProvider(),
        JiraProvider(),
        context={Settings: settings}
    )
    
    print("Container created. Resolving JiraService...")
    
    async with container() as request_container:
        service = await request_container.get(JiraService)
        print(f"Resolved service: {service}")
        print(f"Service API: {service.api}")

if __name__ == "__main__":
    asyncio.run(main())
