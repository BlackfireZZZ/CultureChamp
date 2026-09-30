"""Offline first-admin bootstrap: python -m app.infrastructure.db.bootstrap_admin USERNAME."""

import argparse
import asyncio
from getpass import getpass

from app.application.identity import IdentityService
from app.infrastructure.db.identity_store import SqlIdentityStore
from app.infrastructure.db.session import engine, session_factory
from app.infrastructure.passwords import Argon2PasswordCodec


async def _bootstrap(username: str, password: str) -> None:
    store = SqlIdentityStore(session_factory)
    codec = Argon2PasswordCodec()
    service = IdentityService(store, codec, codec.dummy_hash)
    await service.bootstrap_admin(username, password)
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the first administrator offline")
    parser.add_argument("username")
    args = parser.parse_args()
    password = getpass("New administrator password: ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        parser.error("passwords do not match")
    asyncio.run(_bootstrap(args.username, password))
    print("First administrator created")


if __name__ == "__main__":
    main()
