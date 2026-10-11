from typing import Annotated, cast

from fastapi import Depends, Request

from mdm_demo.application.use_cases.brand import BrandUseCases
from mdm_demo.application.use_cases.brand_log import BrandLogUseCases


def brand_use_cases(request: Request) -> BrandUseCases:
    return cast(BrandUseCases, request.app.state.brand_use_cases)


def brand_log_use_cases(request: Request) -> BrandLogUseCases:
    return cast(BrandLogUseCases, request.app.state.brand_log_use_cases)


BrandService = Annotated[BrandUseCases, Depends(brand_use_cases)]
BrandLogService = Annotated[BrandLogUseCases, Depends(brand_log_use_cases)]
