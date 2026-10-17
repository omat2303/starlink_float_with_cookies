from pathlib import Path

import session_store


def test_roundtrip_encrypted(tmp_path):
    f, k = tmp_path / "s.enc", tmp_path / "k.key"
    cookies = {"Starlink.Com.Sso": "abcdef", "starlink.com.account_number": "ACC-1"}
    session_store.save(cookies, path=f, key_path=k)
    assert b"abcdef" not in f.read_bytes()  # no queda texto plano
    assert session_store.load(path=f, key_path=k) == cookies


def test_load_missing_returns_empty(tmp_path):
    assert session_store.load(path=tmp_path / "nope.enc", key_path=tmp_path / "k") == {}


def test_clear(tmp_path):
    f, k = tmp_path / "s.enc", tmp_path / "k.key"
    session_store.save({"a": "b"}, path=f, key_path=k)
    session_store.clear(path=f)
    assert session_store.load(path=f, key_path=k) == {}
    assert not Path(f).exists()


def test_session_dir_env_mueve_los_ficheros(tmp_path, monkeypatch):
    import importlib

    monkeypatch.setenv("SESSION_DIR", str(tmp_path))
    recargado = importlib.reload(session_store)
    try:
        assert recargado.SESSION_FILE.parent == tmp_path
        assert recargado.KEY_FILE.parent == tmp_path
    finally:
        monkeypatch.delenv("SESSION_DIR", raising=False)
        importlib.reload(session_store)
