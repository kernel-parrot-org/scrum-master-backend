import asyncio
import sys
from pathlib import Path

# Add project root to python path
sys.path.append(str(Path(__file__).parent))

from scrum_master.ioc import create_container
from scrum_master.modules.jira.infrastructure.jira.jira_service import JiraService

async def main():
    print("Initializing container...")
    container = create_container()
    try:
        print("Resolving JiraService...")
        async with container() as request_container:
            service = await request_container.get(JiraService)
            print(f"SUCCESS: JiraService resolved successfully: {type(service)}")
    except Exception as e:
        print(f"FAILURE: Failed to resolve JiraService: {e}")
        sys.exit(1)
    finally:
        await container.close()

if __name__ == "__main__":
    asyncio.run(main())
