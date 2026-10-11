from typing import Annotated, cast

from fastapi import Depends, Request

from mdm_demo.application.use_cases.country import CountryUseCases
from mdm_demo.application.use_cases.country_log import CountryLogUseCases


def country_use_cases(request: Request) -> CountryUseCases:
    return cast(CountryUseCases, request.app.state.country_use_cases)


def country_log_use_cases(request: Request) -> CountryLogUseCases:
    return cast(CountryLogUseCases, request.app.state.country_log_use_cases)


CountryService = Annotated[CountryUseCases, Depends(country_use_cases)]
CountryLogService = Annotated[CountryLogUseCases, Depends(country_log_use_cases)]
