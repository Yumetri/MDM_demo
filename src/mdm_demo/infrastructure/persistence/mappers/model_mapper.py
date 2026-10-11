from mdm_demo.domain.entities.model import Model
from mdm_demo.domain.value_objects.model_code import ModelCode
from mdm_demo.domain.value_objects.model_name import ModelName
from mdm_demo.infrastructure.persistence.models.model import ModelModel


def to_model(model: Model) -> ModelModel:
    return ModelModel(
        id=model.id,
        name=model.name.value,
        code=model.code.value,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def to_domain(model: ModelModel) -> Model:
    return Model(
        model.id,
        ModelName(model.name),
        ModelCode(model.code),
        model.created_at,
        model.updated_at,
    )
