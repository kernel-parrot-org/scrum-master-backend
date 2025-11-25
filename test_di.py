import asyncio
from scrum_master.ioc import create_container
from scrum_master.modules.google_meet.application.interactors.connect_to_meet import ConnectToMeetInteractor

async def test():
    container = create_container()
    async with container() as request_container:
        interactor = await request_container.get(ConnectToMeetInteractor)
        print(f'✓ Interactor resolved: {type(interactor).__name__}')
        print(f'✓ Has adapter: {interactor.google_meet_adapter is not None}')

asyncio.run(test())
