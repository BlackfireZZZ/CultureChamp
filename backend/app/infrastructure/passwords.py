"""Argon2id password codec with bounded pilot parameters."""

import asyncio

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError


class Argon2PasswordCodec:
    def __init__(self) -> None:
        self.hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, type=Type.ID)
        self.dummy_hash = self.hasher.hash("invalid-account-dummy-password")

    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(self.hasher.hash, password)

    async def verify(self, password_hash: str, password: str) -> bool:
        try:
            return await asyncio.to_thread(self.hasher.verify, password_hash, password)
        except (VerificationError, InvalidHashError):
            return False
