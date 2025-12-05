from dishka import Provider, Scope, from_context, provide

from scrum_master.modules.jira.infrastructure.jira.jira_client import JiraClient
from scrum_master.modules.jira.infrastructure.jira.jira_service import JiraService
from scrum_master.shared.config import Settings


class JiraProvider(Provider):
    settings = from_context(provides=Settings, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def get_jira_api(self, settings: Settings) -> JiraClient:
        return JiraClient(
            url=settings.jira.api_url,
            token=settings.jira.api_token.get_secret_value(),
        )

    @provide(scope=Scope.REQUEST)
    def get_jira_service(self, api: JiraClient) -> JiraService:
        return JiraService(api)

