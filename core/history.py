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

def edit_text(item_id: int, new_text: str):
    """Atualiza o conteúdo de um item de texto existente no histórico."""
    if not new_text or not new_text.strip():
        return
        
    init_db()
    hash_val = hashlib.sha256(new_text.encode('utf-8')).hexdigest()
    encrypted_text = crypto.encrypt_text(new_text)
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE clipboard_history 
        SET content = ?, hash = ?
        WHERE id = ? AND type = 'text'
    """, (encrypted_text, hash_val, item_id))
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

def export_backup(filepath: str):
    """Exporta todo o diretório de dados para um arquivo ZIP padrão."""
    import zipfile
    import os
    from configs.config import DATA_DIR
    
    with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(DATA_DIR):
            for file in files:
                # Evita fazer backup de sockets e PIDs se existirem na pasta
                if file.endswith('.sock') or file.endswith('.pid'):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, DATA_DIR)
                zf.write(file_path, arcname)

def import_backup(filepath: str) -> bool:
    """Importa o backup extraindo o ZIP padrão sobre o diretório de dados."""
    import zipfile
    import os
    import shutil
    from configs.config import DATA_DIR
    
    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            # Extrai para temp dir primeiro
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                zf.extractall(tmpdir)
                
                # Move tudo para o DATA_DIR, sobrescrevendo
                for item in os.listdir(tmpdir):
                    s = os.path.join(tmpdir, item)
                    d = os.path.join(DATA_DIR, item)
                    if os.path.isdir(s):
                        if os.path.exists(d):
                            shutil.rmtree(d)
                        shutil.copytree(s, d)
                    else:
                        # Backup the current file just in case? No, it's a restore.
                        shutil.copy2(s, d)
                        
        # Força o settings_manager a recarregar as novas settings recém-copiadas
        from configs.settings_manager import settings
        settings.load()
        return True
    except Exception as e:
        print(f"Import error: {e}")
        return False

def copy_item_to_clipboard(item_data):
    """Copia o conteúdo do item para a área de transferência do sistema (com suporte a Wayland/X11 e fallback)."""
    import subprocess
    import shutil
    
    has_wl = shutil.which('wl-copy') is not None
    has_xclip = shutil.which('xclip') is not None
    
    if item_data["type"] == "text":
        text = item_data["content"]
        try:
            if has_wl:
                proc = subprocess.Popen(['wl-copy'], stdin=subprocess.PIPE)
                proc.communicate(text.encode('utf-8'))
            elif has_xclip:
                proc = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
                proc.communicate(text.encode('utf-8'))
            else:
                from PyQt6.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    app.clipboard().setText(text)
            add_text(text)
        except Exception as e:
            print(f"[FastPaste] Erro ao copiar texto: {e}")
            
    elif item_data["type"] == "image":
        filepath = item_data["content"]
        try:
            img_data = get_image_bytes(filepath)
            if not img_data:
                raise Exception("Não foi possível carregar os bytes da imagem (provavelmente apagada ou corrompida).")
                
            if has_wl:
                proc = subprocess.Popen(['wl-copy', '--type', 'image/png'], stdin=subprocess.PIPE)
                proc.communicate(img_data)
            elif has_xclip:
                proc = subprocess.Popen(['xclip', '-selection', 'clipboard', '-t', 'image/png'], stdin=subprocess.PIPE)
                proc.communicate(img_data)
            else:
                from PyQt6.QtWidgets import QApplication
                from PyQt6.QtGui import QPixmap
                app = QApplication.instance()
                if app:
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                    app.clipboard().setImage(pixmap.toImage())
            add_image(img_data)
        except Exception as e:
            print(f"[FastPaste] Erro ao copiar imagem: {e}")

def load_history_with_variables(query=""):
    """Carrega o histórico filtrado e inclui variáveis se a query começar com '/'."""
    if query.startswith('/'):
        from core.variables import load_variables
        vars_dict = load_variables()
        search_key = query[1:].lower()
        filtered = []
        for k, v in vars_dict.items():
            val_str = v.get("value", "")
            if search_key in k.lower() or search_key in val_str.lower():
                filtered.append({
                    'id': f"var_{k}",
                    'type': 'text',
                    'content': val_str,
                    'is_pinned': 0,
                    'created_at': 0,
                    'is_variable': True,
                    'var_name': k,
                    'is_secret': v.get("is_secret", False)
                })
        return filtered
    else:
        return load_history(query)
