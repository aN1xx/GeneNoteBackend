"""JWT token service."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt
from pydantic import BaseModel

from src.config import settings
from src.domain.enums import UserRole


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # User ID
    email: str
    role: UserRole
    exp: datetime
    iat: datetime
    type: str  # "access" or "refresh"


class JWTService:
    """Service for JWT token generation and validation."""

    def __init__(
        self,
        secret_key: str = settings.jwt_secret_key,
        algorithm: str = settings.jwt_algorithm,
        access_token_expire_minutes: int = settings.jwt_access_token_expire_minutes,
        refresh_token_expire_days: int = settings.jwt_refresh_token_expire_days,
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_token_expire_minutes = access_token_expire_minutes
        self._refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        user_id: UUID,
        email: str,
        role: UserRole,
    ) -> str:
        """Create an access token.

        Args:
            user_id: User UUID
            email: User email
            role: User role

        Returns:
            Encoded JWT access token
        """
        now = datetime.now(UTC)
        expire = now + timedelta(minutes=self._access_token_expire_minutes)

        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role.value,
            "exp": expire,
            "iat": now,
            "type": "access",
        }

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(
        self,
        user_id: UUID,
        email: str,
        role: UserRole,
    ) -> str:
        """Create a refresh token.

        Args:
            user_id: User UUID
            email: User email
            role: User role

        Returns:
            Encoded JWT refresh token
        """
        now = datetime.now(UTC)
        expire = now + timedelta(days=self._refresh_token_expire_days)

        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role.value,
            "exp": expire,
            "iat": now,
            "type": "refresh",
        }

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_token_pair(
        self,
        user_id: UUID,
        email: str,
        role: UserRole,
    ) -> tuple[str, str]:
        """Create access and refresh token pair.

        Args:
            user_id: User UUID
            email: User email
            role: User role

        Returns:
            Tuple of (access_token, refresh_token)
        """
        access_token = self.create_access_token(user_id, email, role)
        refresh_token = self.create_refresh_token(user_id, email, role)
        return access_token, refresh_token

    def decode_token(self, token: str) -> TokenPayload | None:
        """Decode and validate a JWT token.

        Args:
            token: Encoded JWT token

        Returns:
            Token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )
            return TokenPayload(
                sub=payload["sub"],
                email=payload["email"],
                role=UserRole(payload["role"]),
                exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
                iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
                type=payload["type"],
            )
        except JWTError:
            return None

    def verify_access_token(self, token: str) -> TokenPayload | None:
        """Verify an access token.

        Args:
            token: Encoded JWT token

        Returns:
            Token payload if valid access token, None otherwise
        """
        payload = self.decode_token(token)
        if payload and payload.type == "access":
            return payload
        return None

    def verify_refresh_token(self, token: str) -> TokenPayload | None:
        """Verify a refresh token.

        Args:
            token: Encoded JWT token

        Returns:
            Token payload if valid refresh token, None otherwise
        """
        payload = self.decode_token(token)
        if payload and payload.type == "refresh":
            return payload
        return None


# Singleton instance
jwt_service = JWTService()
