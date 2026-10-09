"""Process liveness endpoint; dependency connectivity is checked separately."""

from fastapi import APIRouter, Response, status

router = APIRouter()


@router.get("/health", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def health() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
