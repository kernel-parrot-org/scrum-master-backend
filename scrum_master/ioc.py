from dishka import AsyncContainer, make_async_container

from scrum_master.modules.auth.ioc import AuthModuleProvider
from scrum_master.modules.google_meet.ioc import GoogleMeetModuleProvider
from scrum_master.modules.jira.ioc import JiraProvider
from scrum_master.shared.config import Settings, get_settings
from scrum_master.shared.ioc import SharedInfrastructureProvider


def create_container() -> AsyncContainer:
    settings = get_settings()

    container = make_async_container(
        SharedInfrastructureProvider(),
        AuthModuleProvider(),
        GoogleMeetModuleProvider(),
        JiraProvider(),
        context={Settings: settings}
    )

    return container
