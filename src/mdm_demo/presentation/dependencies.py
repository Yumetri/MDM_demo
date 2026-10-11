from typing import Annotated, cast
from uuid import UUID

from fastapi import Depends, Request

from mdm_demo.application.use_cases.brand import BrandUseCases
from mdm_demo.application.use_cases.brand_log import BrandLogUseCases
from mdm_demo.application.use_cases.company import CompanyUseCases
from mdm_demo.application.use_cases.company_log import CompanyLogUseCases
from mdm_demo.application.use_cases.country import CountryUseCases
from mdm_demo.application.use_cases.country_log import CountryLogUseCases
from mdm_demo.application.use_cases.model import ModelUseCases
from mdm_demo.application.use_cases.model_log import ModelLogUseCases


def company_use_cases(request: Request) -> CompanyUseCases:
    return cast(CompanyUseCases, request.app.state.company_use_cases)


def request_id(request: Request) -> UUID:
    return cast(UUID, request.state.request_id)


CompanyService = Annotated[CompanyUseCases, Depends(company_use_cases)]
RequestID = Annotated[UUID, Depends(request_id)]


def company_log_use_cases(request: Request) -> CompanyLogUseCases:
    return cast(CompanyLogUseCases, request.app.state.company_log_use_cases)


CompanyLogService = Annotated[CompanyLogUseCases, Depends(company_log_use_cases)]


def model_use_cases(request: Request) -> ModelUseCases:
    return cast(ModelUseCases, request.app.state.model_use_cases)


ModelService = Annotated[ModelUseCases, Depends(model_use_cases)]


def model_log_use_cases(request: Request) -> ModelLogUseCases:
    return cast(ModelLogUseCases, request.app.state.model_log_use_cases)


ModelLogService = Annotated[ModelLogUseCases, Depends(model_log_use_cases)]


def country_use_cases(request: Request) -> CountryUseCases:
    return cast(CountryUseCases, request.app.state.country_use_cases)


CountryService = Annotated[CountryUseCases, Depends(country_use_cases)]


def country_log_use_cases(request: Request) -> CountryLogUseCases:
    return cast(CountryLogUseCases, request.app.state.country_log_use_cases)


CountryLogService = Annotated[CountryLogUseCases, Depends(country_log_use_cases)]


def brand_use_cases(request: Request) -> BrandUseCases:
    return cast(BrandUseCases, request.app.state.brand_use_cases)


BrandService = Annotated[BrandUseCases, Depends(brand_use_cases)]


def brand_log_use_cases(request: Request) -> BrandLogUseCases:
    return cast(BrandLogUseCases, request.app.state.brand_log_use_cases)


BrandLogService = Annotated[BrandLogUseCases, Depends(brand_log_use_cases)]
