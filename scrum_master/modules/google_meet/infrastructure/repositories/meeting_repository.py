from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scrum_master.modules.google_meet.domain.entities import Meeting, MeetingStatus


class MeetingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: UUID,
        meet_url: str,
        bot_name: str | None = None,
    ) -> Meeting:
        meeting = Meeting(
            user_id=user_id,
            meet_url=meet_url,
            bot_name=bot_name,
            status=MeetingStatus.PENDING,
        )
        self.session.add(meeting)
        await self.session.commit()
        await self.session.refresh(meeting)
        return meeting

    async def get_by_id(self, meeting_id: UUID) -> Meeting | None:
        result = await self.session.execute(
            select(Meeting).where(Meeting.id == meeting_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: UUID) -> list[Meeting]:
        result = await self.session.execute(
            select(Meeting)
            .where(Meeting.user_id == user_id)
            .order_by(Meeting.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        meeting_id: UUID,
        status: MeetingStatus,
        error_message: str | None = None,
    ) -> Meeting | None:
        meeting = await self.get_by_id(meeting_id)
        if meeting:
            meeting.update_status(status, error_message)
            await self.session.commit()
            await self.session.refresh(meeting)
        return meeting

    async def delete(self, meeting_id: UUID) -> bool:
        meeting = await self.get_by_id(meeting_id)
        if meeting:
            await self.session.delete(meeting)
            await self.session.commit()
            return True
        return False
