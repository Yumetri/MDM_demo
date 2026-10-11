from typing import Annotated, cast

from fastapi import Depends, Request

from mdm_demo.application.use_cases.model import ModelUseCases
from mdm_demo.application.use_cases.model_log import ModelLogUseCases


def model_use_cases(request: Request) -> ModelUseCases:
    return cast(ModelUseCases, request.app.state.model_use_cases)


def model_log_use_cases(request: Request) -> ModelLogUseCases:
    return cast(ModelLogUseCases, request.app.state.model_log_use_cases)


ModelService = Annotated[ModelUseCases, Depends(model_use_cases)]
ModelLogService = Annotated[ModelLogUseCases, Depends(model_log_use_cases)]
