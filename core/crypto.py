import os
from cryptography.fernet import Fernet, InvalidToken
from configs.config import DATA_DIR

def _get_key_path():
    return os.path.join(DATA_DIR, ".secret.key")

def _get_fernet():
    key_path = _get_key_path()
    if not os.path.exists(key_path):
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        with open(key_path, "wb") as f:
            f.write(key)
        try:
            os.chmod(key_path, 0o600)
        except Exception:
            pass
    else:
        with open(key_path, "rb") as f:
            key = f.read()
    return Fernet(key)

_fernet = None

def get_cipher():
    global _fernet
    if _fernet is None:
        _fernet = _get_fernet()
    return _fernet

def reset_cache():
    """Invalida o cache do cipher para forçar a releitura da chave do disco.
    
    Deve ser chamado após operações que substituem o .secret.key:
    - Importação de backup
    - Limpeza total de dados (clear_all_data)
    """
    global _fernet
    _fernet = None

def encrypt_text(text: str) -> str:
    if not text:
        return text
    cipher = get_cipher()
    return cipher.encrypt(text.encode('utf-8')).decode('utf-8')

def decrypt_text(encrypted_text: str) -> str:
    if not encrypted_text:
        return encrypted_text
    try:
        cipher = get_cipher()
        return cipher.decrypt(encrypted_text.encode('utf-8')).decode('utf-8')
    except InvalidToken:
        # Fallback for legacy unencrypted text in the database
        return encrypted_text
    except Exception as e:
        print(f"[Crypto] Error decrypting text: {e}")
        return encrypted_text

def encrypt_bytes(data: bytes) -> bytes:
    if not data:
        return data
    cipher = get_cipher()
    return cipher.encrypt(data)

def decrypt_bytes(encrypted_data: bytes) -> bytes:
    if not encrypted_data:
        return encrypted_data
    try:
        cipher = get_cipher()
        return cipher.decrypt(encrypted_data)
    except InvalidToken:
        # Fallback for legacy unencrypted image bytes
        return encrypted_data
    except Exception as e:
        print(f"[Crypto] Error decrypting bytes: {e}")
        return encrypted_data
