from typing import Annotated, cast

from fastapi import Depends, Request

from mdm_demo.application.use_cases.company import CompanyUseCases
from mdm_demo.application.use_cases.company_log import CompanyLogUseCases


def company_use_cases(request: Request) -> CompanyUseCases:
    return cast(CompanyUseCases, request.app.state.company_use_cases)


def company_log_use_cases(request: Request) -> CompanyLogUseCases:
    return cast(CompanyLogUseCases, request.app.state.company_log_use_cases)


CompanyService = Annotated[CompanyUseCases, Depends(company_use_cases)]
CompanyLogService = Annotated[CompanyLogUseCases, Depends(company_log_use_cases)]
