from typing import Annotated

from fastapi import Depends, Header

from scrum_master.shared.auth.jwt_service import JWTService
from scrum_master.shared.exceptions.auth import UnauthorizedException


async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
    jwt_service: JWTService = Depends(lambda: JWTService()),
) -> int:
    if not authorization:
        raise UnauthorizedException('Missing authorization header')

    if not authorization.startswith('Bearer '):
        raise UnauthorizedException('Invalid authorization header format')

    token = authorization.replace('Bearer ', '')
    return jwt_service.verify_access_token(token)


CurrentUserID = Annotated[int, Depends(get_current_user_id)]
