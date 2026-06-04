import sqlite3
import os
import hashlib
import time
from configs.config import DB_FILE, IMAGES_DIR, DATA_DIR, MAX_HISTORY
from configs.settings_manager import settings
from core import crypto

def get_db_path():
    path = settings.get('db_path', DATA_DIR)
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, "history.db")

def get_images_path():
    path = settings.get('db_path', DATA_DIR)
    img_path = os.path.join(path, "images")
    os.makedirs(img_path, exist_ok=True)
    return img_path

def get_connection():
    db_file = get_db_path()
    conn = sqlite3.connect(db_file)
    return conn

def init_db():
    get_images_path()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clipboard_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,          -- 'text' ou 'image'
            content TEXT NOT NULL,       -- texto bruto ou caminho do arquivo da imagem
            hash TEXT UNIQUE,            -- hash sha256 para evitar duplicatas consecutivas/gerais
            is_pinned INTEGER DEFAULT 0, -- 1 para fixado, 0 senão
            created_at REAL NOT NULL     -- timestamp unix
        )
    """)
    conn.commit()
    conn.close()

def cleanup_history(conn):
    """Remove os registros mais antigos não fixados além do limite MAX_HISTORY e expira por tempo."""
    cursor = conn.cursor()
    
    retention_days = settings.get('retention_days', 30)
    cutoff_time = time.time() - (retention_days * 86400)
    
    # 1. Identifica e deleta arquivos de imagem correspondentes aos registros a serem apagados
    cursor.execute("""
        SELECT content FROM clipboard_history 
        WHERE type = 'image' 
          AND is_pinned = 0 
          AND (
              created_at < ? 
              OR id NOT IN (
                  SELECT id FROM clipboard_history 
                  ORDER by is_pinned DESC, created_at DESC 
                  LIMIT ?
              )
          )
    """, (cutoff_time, settings.get('max_history', MAX_HISTORY)))
    
    files_to_delete = [row[0] for row in cursor.fetchall()]
    for filepath in files_to_delete:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"[FastPaste] Erro ao deletar imagem antiga no disco: {e}")
                
    # 2. Deleta os registros do banco
    cursor.execute("""
        DELETE FROM clipboard_history 
        WHERE is_pinned = 0 
          AND (
              created_at < ?
              OR id NOT IN (
                  SELECT id FROM clipboard_history 
                  ORDER BY is_pinned DESC, created_at DESC 
                  LIMIT ?
              )
          )
    """, (cutoff_time, settings.get('max_history', MAX_HISTORY)))

def add_text(text):
    """Adiciona um novo texto ao histórico, tratando duplicatas consecutivas e gerais."""
    if not text or not text.strip():
        return

    from core.variables import load_variables
    vars_dict = load_variables()
    for v in vars_dict.values():
        if v.get('is_secret') and v.get('value') == text:
            return # Não salva variáveis secretas no histórico

    init_db()
    hash_val = hashlib.sha256(text.encode('utf-8')).hexdigest()
    now = time.time()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Verifica duplicata consecutiva no topo
    cursor.execute("SELECT hash FROM clipboard_history ORDER BY created_at DESC LIMIT 1")
    last_row = cursor.fetchone()
    if last_row and last_row[0] == hash_val:
        conn.close()
        return  # Ignora se for idêntico ao último item copiado
        
    # Verifica se já existe em qualquer posição
    cursor.execute("SELECT id FROM clipboard_history WHERE hash = ?", (hash_val,))
    existing = cursor.fetchone()
    
    if existing:
        # Apenas atualiza a data para mover para o topo do histórico
        cursor.execute("UPDATE clipboard_history SET created_at = ? WHERE hash = ?", (now, hash_val))
    else:
        # Insere novo registro de texto
        encrypted_text = crypto.encrypt_text(text)
        cursor.execute("""
            INSERT INTO clipboard_history (type, content, hash, created_at)
            VALUES ('text', ?, ?, ?)
        """, (encrypted_text, hash_val, now))
        
    conn.commit()
    cleanup_history(conn)
    conn.commit()
    conn.close()

def add_image(image_bytes):
    """Adiciona uma imagem ao histórico, salvando o arquivo e tratando duplicatas."""
    if not image_bytes:
        return

    init_db()
    hash_val = hashlib.sha256(image_bytes).hexdigest()
    now = time.time()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Verifica duplicata consecutiva no topo
    cursor.execute("SELECT hash FROM clipboard_history ORDER BY created_at DESC LIMIT 1")
    last_row = cursor.fetchone()
    if last_row and last_row[0] == hash_val:
        conn.close()
        return  # Ignora se for idêntico ao último item copiado
        
    # Verifica se já existe em qualquer posição
    cursor.execute("SELECT id, content FROM clipboard_history WHERE hash = ?", (hash_val,))
    existing = cursor.fetchone()
    
    if existing:
        # Apenas atualiza a data para mover para o topo do histórico
        cursor.execute("UPDATE clipboard_history SET created_at = ? WHERE hash = ?", (now, hash_val))
    else:
        # Salva o arquivo PNG criptografado no disco
        filename = f"{hash_val}.png"
        filepath = os.path.join(get_images_path(), filename)
        try:
            encrypted_bytes = crypto.encrypt_bytes(image_bytes)
            with open(filepath, 'wb') as f:
                f.write(encrypted_bytes)
                
            # Insere novo registro de imagem
            cursor.execute("""
                INSERT INTO clipboard_history (type, content, hash, created_at)
                VALUES ('image', ?, ?, ?)
            """, (filepath, hash_val, now))
        except Exception as e:
            print(f"[FastPaste] Erro ao gravar arquivo de imagem: {e}")
            
    conn.commit()
    cleanup_history(conn)
    conn.commit()
    conn.close()

def load_history(search_query=None):
    """Carrega o histórico do banco de dados, descriptografando o texto e aplicando filtro em memória."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    import datetime
    
    limit = settings.get('max_history', MAX_HISTORY)
    cursor.execute("""
        SELECT id, type, content, is_pinned, created_at 
        FROM clipboard_history 
        ORDER BY is_pinned DESC, created_at DESC
        LIMIT ?
    """, (limit,))
        
    rows = cursor.fetchall()
    conn.close()
    
    history_list = []
    for row in rows:
        item_type = row[1]
        content = row[2]
        
        # Descriptografa texto
        if item_type == 'text':
            content = crypto.decrypt_text(content)
            
        if search_query:
            q = search_query.lower()
            dt_str = datetime.datetime.fromtimestamp(row[4]).strftime('%d/%m/%Y %H:%M')
            
            matches = False
            if q in dt_str.lower():
                matches = True
            elif item_type == 'text' and q in content.lower():
                matches = True
                
            if not matches:
                continue

        history_list.append({
            "id": row[0],
            "type": item_type,
            "content": content,
            "is_pinned": bool(row[3]),
            "created_at": row[4]
        })
        
    return history_list

def get_image_bytes(filepath):
    """Lê e descriptografa os bytes de uma imagem."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        return crypto.decrypt_bytes(data)
    except Exception as e:
        print(f"[FastPaste] Erro ao carregar imagem criptografada: {e}")
        return None

def toggle_pin(item_id):
    """Inverte o status de fixado de um item."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE clipboard_history SET is_pinned = 1 - is_pinned WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def delete_item(item_id):
    """Exclui um item específico, incluindo o arquivo físico caso seja uma imagem."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    # Se for imagem, remove o arquivo correspondente
    cursor.execute("SELECT type, content FROM clipboard_history WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if row:
        item_type, content = row
        if item_type == 'image' and os.path.exists(content):
            try:
                os.remove(content)
            except Exception as e:
                print(f"[FastPaste] Erro ao deletar imagem correspondente: {e}")
                
    cursor.execute("DELETE FROM clipboard_history WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def clear():
    """Limpa todo o histórico de clipes não fixados."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    # Deleta arquivos físicos de imagens não fixadas
    cursor.execute("SELECT content FROM clipboard_history WHERE type = 'image' AND is_pinned = 0")
    files = [row[0] for row in cursor.fetchall()]
    for filepath in files:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"[FastPaste] Erro ao limpar arquivo físico: {e}")
                
    cursor.execute("DELETE FROM clipboard_history WHERE is_pinned = 0")
    conn.commit()
    conn.close()

def export_backup(filepath: str, password: str):
    """Exporta o banco e as imagens descriptografados para um arquivo JSON criptografado com senha."""
    import json
    import base64
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    from cryptography.fernet import Fernet
    
    history_items = load_history()
    
    export_data = []
    for item in history_items:
        export_item = {
            "type": item["type"],
            "is_pinned": int(item["is_pinned"]),
            "created_at": item["created_at"]
        }
        if item["type"] == "text":
            export_item["content"] = item["content"]
        elif item["type"] == "image":
            img_data = get_image_bytes(item["content"])
            if img_data:
                export_item["content"] = base64.b64encode(img_data).decode('utf-8')
            else:
                continue
        export_data.append(export_item)
        
    json_str = json.dumps(export_data)
    
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend())
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    f = Fernet(key)
    
    encrypted_data = f.encrypt(json_str.encode('utf-8'))
    
    with open(filepath, 'wb') as f_out:
        f_out.write(salt + encrypted_data)

def import_backup(filepath: str, password: str) -> bool:
    """Importa o backup. Descriptografa com a senha, faz parse do JSON e mescla no banco."""
    import json
    import base64
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    from cryptography.fernet import Fernet
    from cryptography.fernet import InvalidToken
    
    try:
        with open(filepath, 'rb') as f_in:
            data = f_in.read()
            
        salt = data[:16]
        encrypted_data = data[16:]
        
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend())
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        f = Fernet(key)
        
        try:
            json_str = f.decrypt(encrypted_data).decode('utf-8')
        except InvalidToken:
            return False # Senha incorreta
            
        import_data = json.loads(json_str)
        
        init_db()
        conn = get_connection()
        cursor = conn.cursor()
        
        for item in import_data:
            if item["type"] == "text":
                hash_val = hashlib.sha256(item["content"].encode('utf-8')).hexdigest()
                cursor.execute("SELECT id FROM clipboard_history WHERE hash = ?", (hash_val,))
                if not cursor.fetchone():
                    from core import crypto
                    enc_text = crypto.encrypt_text(item["content"])
                    cursor.execute("""
                        INSERT INTO clipboard_history (type, content, hash, is_pinned, created_at)
                        VALUES ('text', ?, ?, ?, ?)
                    """, (enc_text, hash_val, item["is_pinned"], item["created_at"]))
            
            elif item["type"] == "image":
                img_data = base64.b64decode(item["content"])
                hash_val = hashlib.sha256(img_data).hexdigest()
                cursor.execute("SELECT id FROM clipboard_history WHERE hash = ?", (hash_val,))
                if not cursor.fetchone():
                    filename = f"{hash_val}.png"
                    img_filepath = os.path.join(get_images_path(), filename)
                    try:
                        from core import crypto
                        encrypted_bytes = crypto.encrypt_bytes(img_data)
                        with open(img_filepath, 'wb') as f_img:
                            f_img.write(encrypted_bytes)
                        
                        cursor.execute("""
                            INSERT INTO clipboard_history (type, content, hash, is_pinned, created_at)
                            VALUES ('image', ?, ?, ?, ?)
                        """, (img_filepath, hash_val, item["is_pinned"], item["created_at"]))
                    except Exception as e:
                        print(f"Error saving imported image: {e}")
                        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Import error: {e}")
        return False
