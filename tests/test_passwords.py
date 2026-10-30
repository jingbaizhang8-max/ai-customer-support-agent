
from app.core.passwords import (
    hash_password,
    verify_password,
)


def test_password_is_hashed():
    password = "MyStrongPassword2026!"

    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2id$")


def test_correct_password():
    password = "MyStrongPassword2026!"

    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_wrong_password():
    password = "MyStrongPassword2026!"

    hashed = hash_password(password)

    assert verify_password(
        "WrongPassword123!",
        hashed,
    ) is False


def test_password_hash_uses_random_salt():
    password = "MyStrongPassword2026!"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash

    assert verify_password(password, first_hash)
    assert verify_password(password, second_hash)
