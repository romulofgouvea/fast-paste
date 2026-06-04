import os
import sys
import shutil
import tempfile
import unittest

# Setup environment before importing project modules
TEST_DIR = tempfile.mkdtemp()
os.environ["FASTPASTE_DATA_DIR"] = TEST_DIR

# Backup real settings if they exist to prevent tests from modifying them
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from configs.settings_manager import settings
from core import general_settings, history_settings, data_settings

class TestSettingsRefactored(unittest.TestCase):
    def setUp(self):
        # Force a fresh settings configuration inside TEST_DIR
        settings.settings = {
            "max_history": 100,
            "retention_days": 30,
            "theme_color": "#e95420",
            "hotkey": "<ctrl>+'",
            "hotkey_mac_key_code": None,
            "db_path": TEST_DIR,
            "interaction_mode": 1
        }
        settings.save()

    def tearDown(self):
        pass

    def test_general_settings(self):
        # Test hotkey
        self.assertEqual(general_settings.get_hotkey(), "<ctrl>+'")
        general_settings.set_hotkey("<ctrl>+v")
        self.assertEqual(general_settings.get_hotkey(), "<ctrl>+v")

        # Test theme color
        self.assertEqual(general_settings.get_theme_color(), "#e95420")
        general_settings.set_theme_color("#0078D7")
        self.assertEqual(general_settings.get_theme_color(), "#0078D7")

        # Test interaction mode
        self.assertEqual(general_settings.get_interaction_mode(), 1)
        general_settings.set_interaction_mode(2)
        self.assertEqual(general_settings.get_interaction_mode(), 2)

    def test_history_settings(self):
        # Test max history
        self.assertEqual(history_settings.get_max_history(), 100)
        history_settings.set_max_history(200)
        self.assertEqual(history_settings.get_max_history(), 200)

        # Test retention days
        self.assertEqual(history_settings.get_retention_days(), 30)
        history_settings.set_retention_days(60)
        self.assertEqual(history_settings.get_retention_days(), 60)

    def test_backup_restore_with_password(self):
        # Write dummy variables or settings to zip
        settings.set("theme_color", "#8B5CF6")
        
        backup_zip = os.path.join(TEST_DIR, "test_backup.zip")
        password = "secret_test_password"
        
        # Export ZIP with password
        data_settings.export_backup_zip(backup_zip, password)
        self.assertTrue(os.path.exists(backup_zip))
        
        # Change theme color in settings
        settings.set("theme_color", "#000000")
        self.assertEqual(settings.get("theme_color"), "#000000")
        
        # Import ZIP with incorrect password (should fail)
        success = data_settings.import_backup_zip(backup_zip, "wrong_password")
        self.assertFalse(success)
        self.assertEqual(settings.get("theme_color"), "#000000")
        
        # Import ZIP with correct password (should succeed)
        success = data_settings.import_backup_zip(backup_zip, password)
        self.assertTrue(success)
        self.assertEqual(settings.get("theme_color"), "#8B5CF6")

    def test_clear_all_data(self):
        # Change settings to non-default values
        settings.set("theme_color", "#112233")
        settings.set("max_history", 999)
        self.assertEqual(settings.get("theme_color"), "#112233")
        self.assertEqual(settings.get("max_history"), 999)
        
        # Call clear_all_data
        data_settings.clear_all_data()
        
        # Assert that settings are reset to defaults
        # We need to reload to verify they are persisted as defaults
        settings.load()
        from configs.config import MAX_HISTORY
        self.assertEqual(settings.get("theme_color"), "#e95420")
        self.assertEqual(settings.get("max_history"), MAX_HISTORY)

if __name__ == "__main__":
    try:
        unittest.main(exit=False)
    finally:
        shutil.rmtree(TEST_DIR, ignore_errors=True)
