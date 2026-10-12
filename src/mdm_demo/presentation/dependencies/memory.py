from typing import Annotated, cast

from fastapi import Depends, Request

from mdm_demo.application.use_cases.memory import MemoryUseCases
from mdm_demo.application.use_cases.memory_log import MemoryLogUseCases


def memory_use_cases(request: Request) -> MemoryUseCases:
    return cast(MemoryUseCases, request.app.state.memory_use_cases)


def memory_log_use_cases(request: Request) -> MemoryLogUseCases:
    return cast(MemoryLogUseCases, request.app.state.memory_log_use_cases)


MemoryService = Annotated[MemoryUseCases, Depends(memory_use_cases)]
MemoryLogService = Annotated[MemoryLogUseCases, Depends(memory_log_use_cases)]
