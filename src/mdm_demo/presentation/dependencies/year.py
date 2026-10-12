from typing import Annotated, cast

from fastapi import Depends, Request

from mdm_demo.application.use_cases.year import YearUseCases
from mdm_demo.application.use_cases.year_log import YearLogUseCases


def year_use_cases(request: Request) -> YearUseCases:
    return cast(YearUseCases, request.app.state.year_use_cases)


def year_log_use_cases(request: Request) -> YearLogUseCases:
    return cast(YearLogUseCases, request.app.state.year_log_use_cases)


YearService = Annotated[YearUseCases, Depends(year_use_cases)]
YearLogService = Annotated[YearLogUseCases, Depends(year_log_use_cases)]
