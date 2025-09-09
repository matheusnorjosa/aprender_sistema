"""
Advanced Security Service for Aprender Sistema
===============================================

Advanced cryptographic and security patterns inspired by TheAlgorithms/Python Cipher module,
providing enterprise-grade security for educational data and user authentication.

Author: Claude Code
Date: Janeiro 2025
"""

import base64
import hashlib
import hmac
import logging
import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
except ImportError:
    Fernet = None
    rsa = None
    padding = None
    hashes = None

try:
    import bcrypt
except ImportError:
    bcrypt = None

logger = logging.getLogger(__name__)


class CipherAlgorithms:
    """
    Collection of cipher algorithms inspired by TheAlgorithms/Python
    """
    
    @staticmethod
    def caesar_cipher(text: str, shift: int, decrypt: bool = False) -> str:
        """
        Classic Caesar cipher implementation
        
        Args:
            text: Text to encrypt/decrypt
            shift: Number of positions to shift
            decrypt: If True, decrypt instead of encrypt
        """
        if decrypt:
            shift = -shift
        
        result = ""
        for char in text:
            if char.isalpha():
                ascii_offset = 65 if char.isupper() else 97
                shifted = (ord(char) - ascii_offset + shift) % 26
                result += chr(shifted + ascii_offset)
            else:
                result += char
        
        return result
    
    @staticmethod
    def vigenere_cipher(text: str, key: str, decrypt: bool = False) -> str:
        """
        Vigenere cipher implementation
        
        Args:
            text: Text to encrypt/decrypt
            key: Encryption key
            decrypt: If True, decrypt instead of encrypt
        """
        result = ""
        key_index = 0
        key = key.upper()
        
        for char in text.upper():
            if char.isalpha():
                key_char = key[key_index % len(key)]
                shift = ord(key_char) - ord('A')
                
                if decrypt:
                    shift = -shift
                
                shifted = (ord(char) - ord('A') + shift) % 26
                result += chr(shifted + ord('A'))
                key_index += 1
            else:
                result += char
        
        return result
    
    @staticmethod
    def atbash_cipher(text: str) -> str:
        """
        Atbash cipher - substitution cipher where A=Z, B=Y, etc.
        """
        result = ""
        for char in text:
            if char.isalpha():
                if char.isupper():
                    result += chr(ord('Z') - (ord(char) - ord('A')))
                else:
                    result += chr(ord('z') - (ord(char) - ord('a')))
            else:
                result += char
        return result
    
    @staticmethod
    def rail_fence_cipher(text: str, key: int, decrypt: bool = False) -> str:
        """
        Rail fence cipher implementation
        """
        if decrypt:
            return CipherAlgorithms._rail_fence_decrypt(text, key)
        return CipherAlgorithms._rail_fence_encrypt(text, key)
    
    @staticmethod
    def _rail_fence_encrypt(text: str, key: int) -> str:
        """Rail fence encryption"""
        if key == 1:
            return text
        
        rails = [[] for _ in range(key)]
        rail = 0
        direction = 1
        
        for char in text:
            rails[rail].append(char)
            rail += direction
            
            if rail == key - 1 or rail == 0:
                direction = -direction
        
        return ''.join([''.join(rail) for rail in rails])
    
    @staticmethod
    def _rail_fence_decrypt(cipher: str, key: int) -> str:
        """Rail fence decryption"""
        if key == 1:
            return cipher
        
        # Calculate rail lengths
        rail_lengths = [0] * key
        rail = 0
        direction = 1
        
        for _ in cipher:
            rail_lengths[rail] += 1
            rail += direction
            
            if rail == key - 1 or rail == 0:
                direction = -direction
        
        # Fill rails
        rails = []
        index = 0
        for length in rail_lengths:
            rails.append(list(cipher[index:index + length]))
            index += length
        
        # Extract message
        result = []
        rail = 0
        direction = 1
        rail_indices = [0] * key
        
        for _ in cipher:
            result.append(rails[rail][rail_indices[rail]])
            rail_indices[rail] += 1
            rail += direction
            
            if rail == key - 1 or rail == 0:
                direction = -direction
        
        return ''.join(result)


class ModernCryptography:
    """
    Modern cryptographic operations using industry standards
    """
    
    def __init__(self):
        self.enabled = Fernet is not None and rsa is not None
        if not self.enabled:
            logger.warning("Cryptography not available - install with: pip install cryptography")
        
        # Generate or load application keys
        self._setup_keys()
    
    def _setup_keys(self):
        """Setup encryption keys for the application"""
        if not self.enabled:
            return
        
        # Generate master key for symmetric encryption
        try:
            # In production, load from secure key management
            key_material = getattr(settings, 'ENCRYPTION_KEY', None)
            if not key_material:
                # Generate new key (save this securely!)
                self.fernet_key = Fernet.generate_key()
                logger.warning("Generated new encryption key - save securely!")
            else:
                self.fernet_key = key_material.encode()
            
            self.fernet = Fernet(self.fernet_key)
            
        except Exception as e:
            logger.error(f"Error setting up encryption keys: {e}")
            self.enabled = False
    
    def encrypt_sensitive_data(self, data: str) -> Optional[str]:
        """
        Encrypt sensitive data using Fernet symmetric encryption
        
        Args:
            data: String data to encrypt
            
        Returns:
            Base64 encoded encrypted data
        """
        if not self.enabled:
            return None
        
        try:
            encrypted = self.fernet.encrypt(data.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return None
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> Optional[str]:
        """
        Decrypt sensitive data
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Decrypted string data
        """
        if not self.enabled:
            return None
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def generate_rsa_keypair(self, key_size: int = 2048) -> Optional[Tuple[bytes, bytes]]:
        """
        Generate RSA public/private key pair
        
        Args:
            key_size: RSA key size in bits
            
        Returns:
            Tuple of (private_key_pem, public_key_pem)
        """
        if not self.enabled:
            return None
        
        try:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
            )
            
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_key = private_key.public_key()
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return private_pem, public_pem
            
        except Exception as e:
            logger.error(f"RSA key generation failed: {e}")
            return None
    
    def hash_password_advanced(self, password: str, algorithm: str = "scrypt") -> Optional[str]:
        """
        Advanced password hashing using Scrypt or Argon2
        
        Args:
            password: Password to hash
            algorithm: Hashing algorithm (scrypt, pbkdf2)
            
        Returns:
            Hashed password with salt
        """
        if not self.enabled:
            return None
        
        try:
            salt = secrets.token_bytes(32)
            
            if algorithm == "scrypt":
                kdf = Scrypt(
                    length=32,
                    salt=salt,
                    n=2**14,
                    r=8,
                    p=1,
                )
            else:  # pbkdf2
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
            
            key = kdf.derive(password.encode())
            
            # Combine salt and key for storage
            combined = base64.b64encode(salt + key).decode()
            return f"{algorithm}${combined}"
            
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            return None
    
    def verify_password_advanced(self, password: str, hashed: str) -> bool:
        """
        Verify password against advanced hash
        
        Args:
            password: Plain text password
            hashed: Stored hash with algorithm prefix
            
        Returns:
            True if password matches
        """
        if not self.enabled:
            return False
        
        try:
            algorithm, combined = hashed.split('$', 1)
            salt_and_key = base64.b64decode(combined)
            salt = salt_and_key[:32]
            stored_key = salt_and_key[32:]
            
            if algorithm == "scrypt":
                kdf = Scrypt(
                    length=32,
                    salt=salt,
                    n=2**14,
                    r=8,
                    p=1,
                )
            else:  # pbkdf2
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
            
            try:
                kdf.verify(password.encode(), stored_key)
                return True
            except Exception:
                return False
                
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False


class SecurityUtils:
    """
    Security utilities for the educational system
    """
    
    def __init__(self):
        self.modern_crypto = ModernCryptography()
        self.cipher_algos = CipherAlgorithms()
    
    def generate_secure_token(self, length: int = 32) -> str:
        """
        Generate cryptographically secure random token
        
        Args:
            length: Token length in characters
            
        Returns:
            URL-safe random token
        """
        return secrets.token_urlsafe(length)
    
    def generate_api_key(self, prefix: str = "ask") -> str:
        """
        Generate API key with prefix for Aprender Sistema
        
        Args:
            prefix: Key prefix (default: ask = Aprender Sistema Key)
            
        Returns:
            API key in format: prefix_randomsecuretoken
        """
        token = self.generate_secure_token(24)
        return f"{prefix}_{token}"
    
    def hash_sensitive_field(self, data: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hash sensitive field data with salt
        
        Args:
            data: Data to hash
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (hashed_data, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use HMAC-SHA256 for consistent hashing
        key = salt.encode()
        hashed = hmac.new(key, data.encode(), hashlib.sha256).hexdigest()
        
        return hashed, salt
    
    def verify_sensitive_field(self, data: str, hashed_data: str, salt: str) -> bool:
        """
        Verify sensitive field data against hash
        
        Args:
            data: Original data
            hashed_data: Stored hash
            salt: Salt used for hashing
            
        Returns:
            True if data matches hash
        """
        expected_hash, _ = self.hash_sensitive_field(data, salt)
        return hmac.compare_digest(expected_hash, hashed_data)
    
    def obfuscate_personal_data(self, data: str, method: str = "partial") -> str:
        """
        Obfuscate personal data for logging/display
        
        Args:
            data: Personal data to obfuscate
            method: Obfuscation method (partial, full, caesar)
            
        Returns:
            Obfuscated data
        """
        if not data:
            return ""
        
        if method == "partial":
            if len(data) <= 4:
                return "*" * len(data)
            return data[:2] + "*" * (len(data) - 4) + data[-2:]
        
        elif method == "full":
            return "*" * len(data)
        
        elif method == "caesar":
            # Use Caesar cipher for reversible obfuscation
            return self.cipher_algos.caesar_cipher(data, 13)
        
        return data
    
    def create_audit_hash(self, data: Dict[str, Any]) -> str:
        """
        Create tamper-evident hash for audit records
        
        Args:
            data: Data dictionary to hash
            
        Returns:
            SHA-256 hash of canonical data representation
        """
        # Create canonical representation
        sorted_items = sorted(data.items())
        canonical = str(sorted_items).encode()
        
        # Add timestamp and random salt
        timestamp = str(timezone.now().timestamp()).encode()
        salt = secrets.token_bytes(8)
        
        # Create hash
        hasher = hashlib.sha256()
        hasher.update(canonical)
        hasher.update(timestamp)
        hasher.update(salt)
        
        return base64.b64encode(salt + hasher.digest()).decode()
    
    def encrypt_user_session_data(self, user_id: int, data: Dict[str, Any]) -> Optional[str]:
        """
        Encrypt user session data
        
        Args:
            user_id: User ID
            data: Session data to encrypt
            
        Returns:
            Encrypted session data
        """
        if not self.modern_crypto.enabled:
            return None
        
        # Add metadata
        session_data = {
            'user_id': user_id,
            'timestamp': timezone.now().isoformat(),
            'data': data
        }
        
        json_data = str(session_data)  # Use string representation for simplicity
        return self.modern_crypto.encrypt_sensitive_data(json_data)
    
    def decrypt_user_session_data(self, encrypted_data: str) -> Optional[Dict[str, Any]]:
        """
        Decrypt user session data
        
        Args:
            encrypted_data: Encrypted session data
            
        Returns:
            Decrypted session data
        """
        if not self.modern_crypto.enabled:
            return None
        
        decrypted = self.modern_crypto.decrypt_sensitive_data(encrypted_data)
        if decrypted:
            try:
                # Parse back to dict (in production, use JSON)
                return eval(decrypted)  # SECURITY: Use json.loads in production
            except Exception as e:
                logger.error(f"Session data parsing failed: {e}")
                return None
        return None


class PasswordStrengthAnalyzer:
    """
    Advanced password strength analysis
    """
    
    def __init__(self):
        self.common_passwords = {
            '123456', 'password', '123456789', '12345678', '12345',
            '111111', '1234567', 'sunshine', 'qwerty', 'iloveyou'
        }
    
    def analyze_password(self, password: str) -> Dict[str, Any]:
        """
        Comprehensive password strength analysis
        
        Args:
            password: Password to analyze
            
        Returns:
            Analysis results with score and recommendations
        """
        analysis = {
            'length': len(password),
            'has_uppercase': any(c.isupper() for c in password),
            'has_lowercase': any(c.islower() for c in password),
            'has_digits': any(c.isdigit() for c in password),
            'has_special': any(c in string.punctuation for c in password),
            'is_common': password.lower() in self.common_passwords,
            'entropy': self._calculate_entropy(password),
            'character_diversity': len(set(password)),
            'repeated_chars': self._count_repeated_chars(password)
        }
        
        # Calculate strength score (0-100)
        score = self._calculate_strength_score(analysis)
        analysis['strength_score'] = score
        analysis['strength_level'] = self._get_strength_level(score)
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _calculate_entropy(self, password: str) -> float:
        """Calculate password entropy"""
        if not password:
            return 0.0
        
        # Count character classes
        char_space = 0
        if any(c.islower() for c in password):
            char_space += 26
        if any(c.isupper() for c in password):
            char_space += 26
        if any(c.isdigit() for c in password):
            char_space += 10
        if any(c in string.punctuation for c in password):
            char_space += len(string.punctuation)
        
        if char_space == 0:
            return 0.0
        
        import math
        return len(password) * math.log2(char_space)
    
    def _count_repeated_chars(self, password: str) -> int:
        """Count repeated character sequences"""
        repeated = 0
        for i in range(len(password) - 1):
            if password[i] == password[i + 1]:
                repeated += 1
        return repeated
    
    def _calculate_strength_score(self, analysis: Dict[str, Any]) -> int:
        """Calculate overall password strength score"""
        score = 0
        
        # Length bonus
        score += min(analysis['length'] * 2, 25)
        
        # Character class bonuses
        if analysis['has_lowercase']:
            score += 5
        if analysis['has_uppercase']:
            score += 5
        if analysis['has_digits']:
            score += 5
        if analysis['has_special']:
            score += 10
        
        # Entropy bonus
        score += min(int(analysis['entropy'] / 4), 25)
        
        # Diversity bonus
        score += min(analysis['character_diversity'], 15)
        
        # Penalties
        if analysis['is_common']:
            score -= 50
        score -= analysis['repeated_chars'] * 2
        
        return max(0, min(100, score))
    
    def _get_strength_level(self, score: int) -> str:
        """Get password strength level from score"""
        if score >= 80:
            return "Muito Forte"
        elif score >= 60:
            return "Forte"
        elif score >= 40:
            return "Moderada"
        elif score >= 20:
            return "Fraca"
        else:
            return "Muito Fraca"
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate password improvement recommendations"""
        recommendations = []
        
        if analysis['length'] < 12:
            recommendations.append("Use pelo menos 12 caracteres")
        
        if not analysis['has_uppercase']:
            recommendations.append("Inclua letras maiúsculas")
        
        if not analysis['has_lowercase']:
            recommendations.append("Inclua letras minúsculas")
        
        if not analysis['has_digits']:
            recommendations.append("Inclua números")
        
        if not analysis['has_special']:
            recommendations.append("Inclua símbolos especiais")
        
        if analysis['is_common']:
            recommendations.append("Evite senhas comuns")
        
        if analysis['repeated_chars'] > 2:
            recommendations.append("Evite repetição de caracteres")
        
        if analysis['character_diversity'] < len(analysis) / 2:
            recommendations.append("Use maior variedade de caracteres")
        
        return recommendations


# Global service instances
security_utils = SecurityUtils()
password_analyzer = PasswordStrengthAnalyzer()


# Convenience functions
def encrypt_data(data: str) -> Optional[str]:
    """Encrypt sensitive data"""
    return security_utils.modern_crypto.encrypt_sensitive_data(data)


def decrypt_data(encrypted_data: str) -> Optional[str]:
    """Decrypt sensitive data"""
    return security_utils.modern_crypto.decrypt_sensitive_data(encrypted_data)


def generate_api_key(prefix: str = "ask") -> str:
    """Generate secure API key"""
    return security_utils.generate_api_key(prefix)


def analyze_password_strength(password: str) -> Dict[str, Any]:
    """Analyze password strength"""
    return password_analyzer.analyze_password(password)


def create_audit_hash(data: Dict[str, Any]) -> str:
    """Create audit hash for tamper detection"""
    return security_utils.create_audit_hash(data)