import unittest
import sys
import os
import shutil
import subprocess
import time

# Adiciona o diretório raiz ao path para podermos importar os módulos do core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.monitor import ClipboardMonitor
from core import history
from configs.config import DATA_DIR
from PyQt6.QtWidgets import QApplication

class TestClipboardMonitor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Garante que temos uma instância do QApplication ativa para os testes do PyQt6
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication(sys.argv)

    def setUp(self):
        # Limpa o banco de dados antes de cada teste
        history.clear()

    def test_xclip_exclusivity_on_wayland(self):
        """Garante que se o xclip estiver disponível no Linux/Wayland, 
        o wl-paste NUNCA seja executado no loop para prevenir o bug de piscar a dock do GNOME."""
        has_xclip = shutil.which('xclip') is not None
        has_wl = shutil.which('wl-paste') is not None
        
        if not has_xclip:
            self.skipTest("xclip não está instalado neste sistema. Não é possível validar a exclusividade.")
            
        monitor = ClipboardMonitor()
        
        # Mock de subprocess.check_output para monitorar quais comandos são executados
        original_check_output = subprocess.check_output
        executed_commands = []
        
        def mock_check_output(cmd, *args, **kwargs):
            executed_commands.append(cmd[0])
            # Retorna dados falsos de acordo com o comando
            if 'image/png' in cmd or '--type' in cmd and 'image/png' in cmd:
                raise subprocess.CalledProcessError(1, cmd) # Simula que não há imagem no clipboard
            return b"Texto de Teste"
            
        subprocess.check_output = mock_check_output
        try:
            # Executa a checagem manual do Linux
            monitor._do_linux_check()
            
            # Verifica se 'wl-paste' foi chamado
            wl_called = any('wl-paste' in cmd for cmd in executed_commands)
            self.assertFalse(wl_called, "ERRO CRÍTICO: 'wl-paste' foi chamado mesmo com o 'xclip' disponível! Isso causa o bug de piscar a dock.")
            
            # Verifica se pelo menos o 'xclip' foi chamado
            xclip_called = any('xclip' in cmd for cmd in executed_commands)
            self.assertTrue(xclip_called, "xclip deveria ter sido chamado.")
        finally:
            # Restaura a função original
            subprocess.check_output = original_check_output

    def test_database_persistence_on_copy(self):
        """Valida que quando um novo texto é capturado, ele é inserido com sucesso no banco de dados."""
        monitor = ClipboardMonitor()
        
        # Mock da leitura de dados da clipboard para retornar um texto fixo
        original_check_output = subprocess.check_output
        def mock_check_output(cmd, *args, **kwargs):
            if 'image/png' in cmd or ('wl-paste' in cmd and 'image/png' in cmd):
                raise subprocess.CalledProcessError(1, cmd)
            return b"TEXTO_UNIT_TEST_123"
            
        subprocess.check_output = mock_check_output
        try:
            # Roda a checagem que dispara a persistência
            monitor.last_text_hash = None
            monitor._do_linux_check()
            
            # Carrega o histórico e verifica se o item foi salvo
            items = history.load_history()
            self.assertTrue(len(items) > 0, "O histórico não gravou o item copiado!")
            self.assertEqual(items[0]['content'], "TEXTO_UNIT_TEST_123", "O conteúdo gravado está incorreto!")
        finally:
            subprocess.check_output = original_check_output

if __name__ == '__main__':
    unittest.main()
