from typing import Annotated, cast

from fastapi import Depends, Request

from mdm_demo.application.use_cases.category import CategoryUseCases
from mdm_demo.application.use_cases.category_log import CategoryLogUseCases


def category_use_cases(request: Request) -> CategoryUseCases:
    return cast(CategoryUseCases, request.app.state.category_use_cases)


def category_log_use_cases(request: Request) -> CategoryLogUseCases:
    return cast(CategoryLogUseCases, request.app.state.category_log_use_cases)


CategoryService = Annotated[CategoryUseCases, Depends(category_use_cases)]
CategoryLogService = Annotated[CategoryLogUseCases, Depends(category_log_use_cases)]
