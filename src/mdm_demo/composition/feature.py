from collections.abc import Callable
from dataclasses import dataclass

from fastapi import APIRouter, FastAPI

from mdm_demo.composition.runtime import RuntimeResources


@dataclass(frozen=True)
class FeatureModule:
    name: str
    routers: tuple[APIRouter, ...]
    configure: Callable[[FastAPI, RuntimeResources], None]
    state_names: tuple[str, ...]
