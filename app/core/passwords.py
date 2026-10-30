
from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """注册时将明文密码转换为安全哈希。"""
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """登录时验证用户输入的密码。"""
    return password_hash.verify(
        plain_password,
        hashed_password,
    )
