"""Password hashing service."""

import hashlib

import bcrypt


class PasswordService:
    """Service for password hashing and verification using bcrypt."""

    def __init__(self, rounds: int = 12) -> None:
        """Initialize password service.

        Args:
            rounds: Number of bcrypt rounds (default: 12)
        """
        self._rounds = rounds

    def _preprocess_password(self, password: str) -> bytes:
        """Pre-hash password with SHA-256 to handle bcrypt's 72-byte limit.

        Args:
            password: Plain text password

        Returns:
            SHA-256 digest of the password as bytes
        """
        return hashlib.sha256(password.encode("utf-8")).digest()

    def hash(self, password: str) -> str:
        """Hash a password.

        Args:
            password: Plain text password

        Returns:
            Hashed password as string
        """
        # Pre-hash with SHA-256 to avoid bcrypt's 72-byte limit
        preprocessed = self._preprocess_password(password)
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=self._rounds)
        hashed = bcrypt.hashpw(preprocessed, salt)
        # Return as string (bcrypt returns bytes)
        return hashed.decode("utf-8")

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to check against

        Returns:
            True if password matches, False otherwise
        """
        try:
            # Pre-hash with SHA-256 to match the hashing process
            preprocessed = self._preprocess_password(plain_password)
            # Verify password
            return bcrypt.checkpw(preprocessed, hashed_password.encode("utf-8"))
        except (ValueError, TypeError):
            return False

    def needs_rehash(self, hashed_password: str) -> bool:
        """Check if password hash needs to be updated.

        Args:
            hashed_password: Current password hash

        Returns:
            True if hash should be regenerated (if rounds changed)
        """
        try:
            # Extract rounds from hash
            # bcrypt hash format: $2b$12$salt+hash (where 12 is rounds)
            parts = hashed_password.split("$")
            if len(parts) >= 3 and parts[1] in ("2a", "2b", "2y"):
                rounds = int(parts[2][:2])  # First 2 digits are rounds
                return rounds != self._rounds
            return False
        except (ValueError, IndexError):
            return True


# Singleton instance
password_service = PasswordService()
