from dishka import Provider, Scope, from_context, provide

from scrum_master.shared.config import Settings
from scrum_master.agents.meet_agent.services.file_service import FileService
from scrum_master.agents.meet_agent.services.telegram_service import \
    TelegramService


class AppProvider(Provider):
    config = from_context(provides=Settings, scope=Scope.APP)

    @provide(scope=Scope.REQUEST)
    def get_telegram_service(self, config: Settings) -> TelegramService:
        return TelegramService(
            bot_token=config.telegram.bot_token,
            chat_id=config.telegram.chat_id,
        )

    @provide(scope=Scope.REQUEST)
    def get_file_service(self, config: Settings) -> FileService:
        return FileService(
            upload_dir=config.audio.upload_dir,
            max_upload_size=config.audio.max_upload_size,
            allowed_extensions=config.audio.allowed_extensions,
            gcs_bucket_name=config.gcs.bucket_name,
        )
