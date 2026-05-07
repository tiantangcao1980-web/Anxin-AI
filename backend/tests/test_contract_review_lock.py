import pytest

from src.core.config import settings
from src.services.contract_review_lock import (
    _LOCAL_LOCKS,
    ContractReviewAlreadyRunning,
    ContractReviewLock,
)


@pytest.fixture(autouse=True)
def clear_local_review_locks():
    _LOCAL_LOCKS.clear()
    yield
    _LOCAL_LOCKS.clear()


@pytest.mark.asyncio
async def test_local_contract_review_lock_rejects_duplicate_acquire(monkeypatch) -> None:
    monkeypatch.setattr(settings, "CONTRACT_REVIEW_LOCK_BACKEND", "local")
    lock = ContractReviewLock()

    token = await lock.acquire("contract-review:1", ttl_seconds=30)

    with pytest.raises(ContractReviewAlreadyRunning):
        await lock.acquire("contract-review:1", ttl_seconds=30)

    await lock.release("contract-review:1", token)
    retry_token = await lock.acquire("contract-review:1", ttl_seconds=30)

    assert retry_token != token


@pytest.mark.asyncio
async def test_local_contract_review_lock_ignores_wrong_release_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "CONTRACT_REVIEW_LOCK_BACKEND", "local")
    lock = ContractReviewLock()

    token = await lock.acquire("contract-review:2", ttl_seconds=30)
    await lock.release("contract-review:2", "wrong-token")

    with pytest.raises(ContractReviewAlreadyRunning):
        await lock.acquire("contract-review:2", ttl_seconds=30)

    await lock.release("contract-review:2", token)
    assert "contract-review:2" not in _LOCAL_LOCKS
