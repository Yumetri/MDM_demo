"""Process liveness endpoint; dependency connectivity is checked separately."""

from fastapi import APIRouter, Response, status

router = APIRouter()


@router.get(
    "/health",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="프로세스 생존 확인",
    description="GET 요청만 보내면 정상 시204, 본문 없음. DB·Redis 연결 상태는 보장하지 않습니다. "
    "요청 본문·파라미터가 없으므로 입력 예제는 없습니다.",
    responses={204: {"description": "성공:204 No Content. 본문 예제 없음."}},
)
async def health() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
