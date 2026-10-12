from typing import Annotated, cast

from fastapi import Depends, Request

from mdm_demo.application.use_cases.network import NetworkUseCases
from mdm_demo.application.use_cases.network_log import NetworkLogUseCases


def network_use_cases(request: Request) -> NetworkUseCases:
    return cast(NetworkUseCases, request.app.state.network_use_cases)


def network_log_use_cases(request: Request) -> NetworkLogUseCases:
    return cast(NetworkLogUseCases, request.app.state.network_log_use_cases)


NetworkService = Annotated[NetworkUseCases, Depends(network_use_cases)]
NetworkLogService = Annotated[NetworkLogUseCases, Depends(network_log_use_cases)]
