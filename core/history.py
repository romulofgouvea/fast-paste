import sqlite3
import os
import hashlib
import time
from configs.config import DB_FILE, IMAGES_DIR, DATA_DIR, MAX_HISTORY
from configs.settings_manager import settings

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
    """Remove os registros mais antigos não fixados além do limite MAX_HISTORY, limpando também arquivos de imagem."""
    cursor = conn.cursor()
    
    # 1. Identifica e deleta arquivos de imagem correspondentes aos registros a serem apagados
    cursor.execute("""
        SELECT content FROM clipboard_history 
        WHERE type = 'image' 
          AND is_pinned = 0 
          AND id NOT IN (
              SELECT id FROM clipboard_history 
              ORDER by is_pinned DESC, created_at DESC 
              LIMIT ?
          )
    """, (settings.get('max_history', MAX_HISTORY),))
    
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
          AND id NOT IN (
              SELECT id FROM clipboard_history 
              ORDER BY is_pinned DESC, created_at DESC 
              LIMIT ?
          )
    """, (settings.get('max_history', MAX_HISTORY),))

def add_text(text):
    """Adiciona um novo texto ao histórico, tratando duplicatas consecutivas e gerais."""
    if not text or not text.strip():
        return

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
        cursor.execute("""
            INSERT INTO clipboard_history (type, content, hash, created_at)
            VALUES ('text', ?, ?, ?)
        """, (text, hash_val, now))
        
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
        # Salva o arquivo PNG de forma limpa no disco
        filename = f"{hash_val}.png"
        filepath = os.path.join(get_images_path(), filename)
        try:
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
                
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
    """Carrega o histórico do banco de dados, aplicando busca por conteúdo ou por data se especificado."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    if search_query:
        # Busca no conteúdo de texto ou na data formatada
        # strftime formatará o timestamp unix armazenado em 'created_at' no fuso local
        q = f"%{search_query}%"
        cursor.execute("""
            SELECT id, type, content, is_pinned, created_at 
            FROM clipboard_history 
            WHERE (type = 'text' AND content LIKE ?)
               OR (strftime('%d/%m/%Y %H:%M', created_at, 'unixepoch', 'localtime') LIKE ?)
            ORDER BY is_pinned DESC, created_at DESC
        """, (q, q))
    else:
        cursor.execute("""
            SELECT id, type, content, is_pinned, created_at 
            FROM clipboard_history 
            ORDER BY is_pinned DESC, created_at DESC
            LIMIT ?
        """, (settings.get('max_history', MAX_HISTORY),))
        
    rows = cursor.fetchall()
    conn.close()
    
    history_list = []
    for row in rows:
        history_list.append({
            "id": row[0],
            "type": row[1],
            "content": row[2],
            "is_pinned": bool(row[3]),
            "created_at": row[4]
        })
    return history_list

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
