from typing import Protocol


class ReadinessProbe(Protocol):
    async def is_ready(self) -> bool: ...


async def check_readiness(probe: ReadinessProbe) -> bool:
    return await probe.is_ready()
