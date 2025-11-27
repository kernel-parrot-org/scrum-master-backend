from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from scrum_master.modules.auth.config import AuthModuleConfig
from scrum_master.modules.google_meet.application.interactors.connect_to_meet import \
    ConnectToMeetInteractor
from scrum_master.modules.google_meet.application.interactors.disconnect_from_meet import \
    DisconnectFromMeetInteractor
from scrum_master.modules.google_meet.application.interactors.get_meetings import \
    GetMeetingsInteractor
from scrum_master.modules.google_meet.application.interfaces import (
    IGoogleMeetAdapter, IMeetingRepository)
from scrum_master.modules.google_meet.config import (GoogleMeetConfig,
                                                     GoogleMeetModuleConfig)
from scrum_master.modules.google_meet.infrastructure.calendar import GoogleCalendarService
from scrum_master.modules.google_meet.infrastructure.repositories.meeting_repository import \
    MeetingRepository
from scrum_master.modules.google_meet.infrastructure.scheduler import MeetingScheduler
from scrum_master.modules.google_meet.infrastructure.selenium.meet_adapter import \
    GoogleMeetAdapter


class GoogleMeetModuleProvider(Provider):
    @provide(scope=Scope.APP)
    def get_google_meet_config(self) -> GoogleMeetModuleConfig:
        return GoogleMeetModuleConfig()

    @provide(scope=Scope.APP)
    def get_google_meet_adapter_config(
        self, config: GoogleMeetModuleConfig
    ) -> GoogleMeetConfig:
        return config.google_meet

    @provide(scope=Scope.REQUEST, provides=IMeetingRepository)
    def get_meeting_repository(self, session: AsyncSession) -> MeetingRepository:
        return MeetingRepository(session)

    @provide(scope=Scope.APP, provides=IGoogleMeetAdapter)
    def get_google_meet_adapter(self, config: GoogleMeetConfig) -> GoogleMeetAdapter:
        return GoogleMeetAdapter(config)

    @provide(scope=Scope.REQUEST)
    def get_connect_to_meet_interactor(
        self,
        meeting_repo: IMeetingRepository,
        google_meet_adapter: IGoogleMeetAdapter,
    ) -> ConnectToMeetInteractor:
        return ConnectToMeetInteractor(
            meeting_repository=meeting_repo,
            google_meet_adapter=google_meet_adapter,
        )

    @provide(scope=Scope.REQUEST)
    def get_disconnect_from_meet_interactor(
        self,
        meeting_repo: IMeetingRepository,
        google_meet_adapter: IGoogleMeetAdapter,
    ) -> DisconnectFromMeetInteractor:
        return DisconnectFromMeetInteractor(
            meeting_repository=meeting_repo,
            google_meet_adapter=google_meet_adapter,
        )

    @provide(scope=Scope.REQUEST)
    def get_meetings_interactor(
        self,
        meeting_repo: IMeetingRepository,
    ) -> GetMeetingsInteractor:
        return GetMeetingsInteractor(meeting_repository=meeting_repo)

    @provide(scope=Scope.APP)
    def get_google_calendar_service(self, auth_config: AuthModuleConfig) -> GoogleCalendarService:
        return GoogleCalendarService(
            client_id=auth_config.google.client_id,
            client_secret=auth_config.google.client_secret,
        )

    @provide(scope=Scope.APP)
    def get_meeting_scheduler(self) -> MeetingScheduler:
        scheduler = MeetingScheduler(
            bot_trigger_url='http://localhost:8000/api/v1/meet/connect',
        )
        scheduler.start()
        return scheduler
