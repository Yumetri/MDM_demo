from mdm_demo.domain.entities.memory import Memory
from mdm_demo.domain.value_objects.memory_size import MemorySize
from mdm_demo.infrastructure.persistence.models.memory import MemoryModel


def to_model(memory: Memory) -> MemoryModel:
    return MemoryModel(
        id=memory.id,
        capacity=memory.size.capacity,
        unit=memory.size.unit,
        code=memory.size.code,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
    )


def to_domain(model: MemoryModel) -> Memory:
    size = MemorySize(model.capacity, model.unit)
    if model.code != size.code or model.capacity_gb != size.capacity_gb:
        raise ValueError("Stored Memory does not match its derived values")
    return Memory(model.id, size, model.created_at, model.updated_at)
