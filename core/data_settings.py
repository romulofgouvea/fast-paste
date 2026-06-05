import os
import shutil
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
    """Limpa todo o banco de dados (inclusive itens fixados), deleta imagens,
    variáveis e redefine as configurações para o padrão."""
    from configs.settings_manager import settings, SETTINGS_FILE
    from configs.config import DATA_DIR


    db_path = os.path.join(DATA_DIR, "history.db")
    images_dir = os.path.join(DATA_DIR, "images")
    vars_file = os.path.join(DATA_DIR, "variables.json")

    # 1. Deleta o arquivo do banco completamente (mais seguro que DELETE FROM)
    for db_file in [db_path, db_path + "-wal", db_path + "-shm"]:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception as e:
                print(f"[DataSettings] Erro ao remover {db_file}: {e}")


    # 2. Deleta a pasta de imagens completamente e recria vazia
    if os.path.exists(images_dir):
        try:
            shutil.rmtree(images_dir)
        except Exception as e:
            print(f"[DataSettings] Erro ao remover pasta de imagens: {e}")
    try:
        os.makedirs(images_dir, exist_ok=True)
    except Exception as e:
        print(f"[DataSettings] Erro ao recriar pasta de imagens: {e}")

    # 3. Deleta arquivo de variáveis
    if os.path.exists(vars_file):
        try:
            os.remove(vars_file)
        except Exception as e:
            print(f"[DataSettings] Erro ao remover variables.json: {e}")

    # 4. Remove settings.json e recarrega os valores padrão
    if os.path.exists(SETTINGS_FILE):
        try:
            os.remove(SETTINGS_FILE)
        except Exception as e:
            print(f"[DataSettings] Erro ao remover settings.json: {e}")
    settings.load()   # Carrega DEFAULT_SETTINGS (sem o arquivo, usa padrões)
    settings.save()   # Persiste os padrões em disco

    # 5. Invalida o cache do cipher para forçar a geração de uma nova chave
    from core import crypto
    crypto.reset_cache()

    # 6. Re-inicializa o schema do banco (garante estrutura correta)
    history.init_db()


