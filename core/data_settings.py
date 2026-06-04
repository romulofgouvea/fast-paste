import os
import shutil
import pyzipper
from configs.settings_manager import settings
from configs.config import DATA_DIR, DEFAULT_SETTINGS
from core import history

def get_db_path():
    return settings.get('db_path', DEFAULT_SETTINGS['db_path'])

def set_db_path(path):
    if os.path.exists(path):
        settings.set('db_path', path)
        return True
    return False

def clear_database():
    history.clear()

def clear_all_data():
    """Limpa todo o banco de dados (inclusive itens fixados), deleta imagens, variáveis e redefine configurações para o padrão."""
    from configs.settings_manager import settings, SETTINGS_FILE
    
    # 1. Deleta arquivos de imagem físicas
    conn = history.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT content FROM clipboard_history WHERE type = 'image'")
        files = [row[0] for row in cursor.fetchall()]
        for filepath in files:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"[DataSettings] Erro ao deletar imagem física {filepath}: {e}")
    except Exception as e:
        print(f"[DataSettings] Erro ao buscar imagens no banco: {e}")
        
    try:
        cursor.execute("DELETE FROM clipboard_history")
        conn.commit()
    except Exception as e:
        print(f"[DataSettings] Erro ao limpar tabela do banco: {e}")
    finally:
        conn.close()

    # 2. Deleta pasta de imagens completamente
    images_dir = os.path.join(settings.get('db_path', DEFAULT_SETTINGS['db_path']), "images")
    if os.path.exists(images_dir):
        for item in os.listdir(images_dir):
            item_path = os.path.join(images_dir, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            except Exception as e:
                print(f"[DataSettings] Erro ao remover item extra na pasta de imagens: {e}")

    # 3. Deleta arquivo de variáveis
    vars_file = os.path.join(settings.get('db_path', DEFAULT_SETTINGS['db_path']), "variables.json")
    if os.path.exists(vars_file):
        try:
            os.remove(vars_file)
        except Exception as e:
            print(f"[DataSettings] Erro ao remover variables.json: {e}")

    # 4. Redefine as configurações para o padrão e salva
    if os.path.exists(SETTINGS_FILE):
        try:
            os.remove(SETTINGS_FILE)
        except Exception as e:
            print(f"[DataSettings] Erro ao remover arquivo de configurações settings.json: {e}")
    settings.load()
    settings.save()


def export_backup_zip(filepath, password: str):
    """Exporta todo o diretório de dados para um arquivo ZIP protegido com senha usando pyzipper."""
    from configs.config import DATA_DIR
    
    with pyzipper.AESZipFile(filepath, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(password.encode('utf-8'))
        for root, dirs, files in os.walk(DATA_DIR):
            for file in files:
                # Evita sockets e pidfiles
                if file.endswith('.sock') or file.endswith('.pid'):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, DATA_DIR)
                zf.write(file_path, arcname)

def import_backup_zip(filepath, password: str) -> bool:
    """Importa o backup extraindo o ZIP protegido por senha sobre o diretório de dados."""
    import tempfile
    from configs.config import DATA_DIR
    
    try:
        with pyzipper.AESZipFile(filepath, 'r') as zf:
            zf.setpassword(password.encode('utf-8'))
            
            with tempfile.TemporaryDirectory() as tmpdir:
                # Tenta ler um arquivo para testar a senha
                zf.extractall(tmpdir)
                
                # Se descompactou com sucesso, move tudo para o DATA_DIR, sobrescrevendo
                for item in os.listdir(tmpdir):
                    s = os.path.join(tmpdir, item)
                    d = os.path.join(DATA_DIR, item)
                    if os.path.isdir(s):
                        if os.path.exists(d):
                            shutil.rmtree(d)
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                        
        # Recarrega as settings importadas
        from configs.settings_manager import settings
        settings.load()
        return True
    except Exception as e:
        print(f"[DataSettings] Import error: {e}")
        return False
