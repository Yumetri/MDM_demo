from mdm_demo.domain.entities.network import Network
from mdm_demo.domain.value_objects.network_code import NetworkCode
from mdm_demo.domain.value_objects.network_name import NetworkName
from mdm_demo.infrastructure.persistence.models.network import NetworkModel


def to_model(network: Network) -> NetworkModel:
    return NetworkModel(
        id=network.id,
        name=network.name.value,
        code=network.code.value,
        created_at=network.created_at,
        updated_at=network.updated_at,
    )


def to_domain(network: NetworkModel) -> Network:
    return Network(
        network.id,
        NetworkName(network.name),
        NetworkCode(network.code),
        network.created_at,
        network.updated_at,
    )
