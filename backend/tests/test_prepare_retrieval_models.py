"""Provisioning must reuse verified local weights without network requests."""

import sys
from types import SimpleNamespace

from app.infrastructure.vector import prepare_models


def test_verified_cache_never_requests_network(monkeypatch):
    calls = []

    def download(repo, **kwargs):
        calls.append(kwargs)
        assert kwargs['local_files_only'] is True
        return '/cached'

    monkeypatch.setitem(sys.modules, 'huggingface_hub', SimpleNamespace(snapshot_download=download))
    monkeypatch.setattr(prepare_models, '_validate_snapshot', lambda path, repo, digest: None)
    prepare_models.main()
    assert len(calls) == 2


def test_empty_cache_downloads_then_verifies(monkeypatch):
    calls = []
    verified = []

    def download(repo, **kwargs):
        calls.append(kwargs)
        if kwargs.get('local_files_only'):
            raise FileNotFoundError
        return '/downloaded'

    monkeypatch.setitem(sys.modules, 'huggingface_hub', SimpleNamespace(snapshot_download=download))
    monkeypatch.setattr(
        prepare_models, '_validate_snapshot', lambda path, repo, digest: verified.append(path)
    )
    prepare_models.main()
    assert len(calls) == 4
    assert verified == ['/downloaded', '/downloaded']


def test_weights_only_cache_is_incomplete(tmp_path):
    import pytest

    (tmp_path / 'model.safetensors').write_bytes(b'weights')
    with pytest.raises(FileNotFoundError, match='config.json'):
        prepare_models._validate_snapshot(str(tmp_path), prepare_models.ENCODER_REPO, 'hash')
