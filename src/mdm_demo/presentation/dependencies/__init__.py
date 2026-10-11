from typing import Annotated, cast
from uuid import UUID

from fastapi import Depends, Request


def request_id(request: Request) -> UUID:
    return cast(UUID, request.state.request_id)


RequestID = Annotated[UUID, Depends(request_id)]
