from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_BCRYPT_BYTES = 72


def truncate_password(password: str) -> str:
    """
    Truncate string so that UTF-8 encoded bytes <= 72.
    """
    truncated = password
    while len(truncated.encode("utf-8")) > MAX_BCRYPT_BYTES:
        truncated = truncated[:-1]
    return truncated


def hash_password(password: str) -> str:
    return pwd_context.hash(truncate_password(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(truncate_password(plain_password), hashed_password)
