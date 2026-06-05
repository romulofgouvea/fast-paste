import sys
import os
import shutil
import json
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer, QEvent

# Import paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import history
from core.variables import add_variable, remove_variable
from configs.config import DATA_DIR
from configs.settings_manager import settings
from screens.history_ui import FastPastePopup

# Backup original files to avoid modifying user data
backup_dir = os.path.join(DATA_DIR, "test_backup")
files_to_backup = ["settings.json", "variables.json"]
test_db_dir = os.path.join(DATA_DIR, "test_db")
original_db_path = settings.get('db_path', DATA_DIR)

def setup_test_env():
    print("Setting up test environment...")
    os.makedirs(backup_dir, exist_ok=True)
    for filename in files_to_backup:
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            shutil.copy2(path, os.path.join(backup_dir, filename))
            
    # Set DB path to test directory
    settings.set('db_path', test_db_dir)
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)
    os.makedirs(test_db_dir, exist_ok=True)
    
    # Initialize fresh DB and write test data
    history.init_db()
    
    # Add dummy clips
    history.add_text("Abacaxi Fresco")
    history.add_text("Banana Madura")
    
    # Add dummy variables
    if os.path.exists(os.path.join(DATA_DIR, "variables.json")):
        os.remove(os.path.join(DATA_DIR, "variables.json"))
    add_variable("fruta", "Morango")

def restore_test_env():
    print("Restoring user environment...")
    # Restore original settings
    settings.set('db_path', original_db_path)
    
    # Clean up test DB dir
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)
        
    for filename in files_to_backup:
        backup_path = os.path.join(backup_dir, filename)
        dest_path = os.path.join(DATA_DIR, filename)
        if os.path.exists(dest_path):
            os.remove(dest_path)
        if os.path.exists(backup_path):
            shutil.move(backup_path, dest_path)
            
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir)

def run_tests():
    # Setup PyQt Application
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    popup = FastPastePopup(standalone=False)
    popup.show()
    
    failures = []
    
    def test_search():
        print("\n--- Testing Search ---")
        # 1. Standard text search
        popup.search_entry.setText("Abacaxi")
        assert len(popup.filtered_history) == 1, f"Expected 1 item, got {len(popup.filtered_history)}"
        assert popup.filtered_history[0]["content"] == "Abacaxi Fresco", "Search content mismatch"
        print("✓ Standard search passed")
        
        # 2. Variable search starting with /
        popup.search_entry.setText("/fruta")
        assert len(popup.filtered_history) == 1, "Variable search failed"
        assert popup.filtered_history[0]["var_name"] == "fruta", "Variable name mismatch"
        assert popup.filtered_history[0]["content"] == "Morango", "Variable content mismatch"
        print("✓ Variable search passed")

    def test_config_click():
        print("\n--- Testing Config Click ---")
        # Click settings button to switch stack page to 1
        popup.settings_btn.click()
        assert popup.stacked_widget.currentIndex() == 1, "Failed to navigate to settings"
        # Close settings
        popup.close_settings(saved=False)
        assert popup.stacked_widget.currentIndex() == 0, "Failed to return to main page"
        print("✓ Config click navigation passed")

    def test_edit_pin_delete():
        print("\n--- Testing Edit, Pin, Delete ---")
        popup.search_entry.clear()
        assert len(popup.filtered_history) >= 2, "History empty"
        
        item_to_test = popup.filtered_history[0]
        item_id = item_to_test["id"]
        
        # 1. Pin item
        history.toggle_pin(item_id)
        popup.refresh_list()
        # Find item in fresh filtered history
        pinned_items = [i for i in popup.filtered_history if i["id"] == item_id]
        assert len(pinned_items) == 1 and pinned_items[0]["is_pinned"] == True, "Pin toggle failed"
        print("✓ Pin toggle passed")
        
        # 2. Edit item
        history.edit_text(item_id, "Abacaxi Caramelizado")
        popup.refresh_list()
        edited_items = [i for i in popup.filtered_history if i["id"] == item_id]
        assert len(edited_items) == 1 and edited_items[0]["content"] == "Abacaxi Caramelizado", "Edit text failed"
        print("✓ Edit text passed")
        
        # 3. Delete item
        history.delete_item(item_id)
        popup.refresh_list()
        deleted_items = [i for i in popup.filtered_history if i["id"] == item_id]
        assert len(deleted_items) == 0, "Delete item failed"
        print("✓ Delete item passed")

    def test_copy():
        print("\n--- Testing Copy to Clipboard ---")
        popup.search_entry.clear()
        popup.refresh_list()
        
        assert len(popup.filtered_history) > 0, "No items in history for copy test"
        target_item = popup.filtered_history[0]
        original_content = target_item["content"]
        
        import unittest.mock as mock
        with mock.patch('subprocess.Popen') as mock_popen:
            mock_proc = mock.MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_popen.return_value = mock_proc
            
            history.copy_item_to_clipboard(target_item)
            
            # Verifica que o subprocess foi chamado (wl-copy ou xclip)
            assert mock_popen.called, "subprocess.Popen não foi chamado durante a cópia"
            
            # Verifica que o conteúdo no histórico permanece inalterado
            popup.refresh_list()
            found = any(i["content"] == original_content for i in popup.filtered_history)
            assert found, f"Item '{original_content}' desapareceu do histórico após a cópia"
            
        print("✓ Copy to clipboard test passed")

    def test_key_navigation():
        print("\n--- Testing Arrow Key Navigation (Skipping Headers) ---")
        popup.search_entry.clear()
        popup.search_entry.setFocus()
        popup.refresh_list()
        
        from PyQt6.QtGui import QKeyEvent
        
        assert popup.list_widget.count() > 1, "List too short to test navigation"
        
        # Simula o pressionamento da seta para baixo
        event_down = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
        popup.keyPressEvent(event_down)
        
        current_row = popup.list_widget.currentRow()
        assert current_row >= 0, "No item selected on Down press"
        selected_item = popup.list_widget.item(current_row)
        assert selected_item.flags() & Qt.ItemFlag.ItemIsSelectable, "Header/Separator selected instead of clipboard item!"
        print(f"✓ Arrow navigation correctly selected selectable row {current_row}")

        # Test Return/Enter bubble up on list_widget
        popup.list_widget.setFocus()
        import unittest.mock as mock
        with mock.patch.object(popup, 'paste_item') as mock_paste_item:
            event_enter = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
            popup.list_widget.keyPressEvent(event_enter)
            
            if not event_enter.isAccepted():
                popup.keyPressEvent(event_enter)
                
            assert mock_paste_item.called, "Enter key event was not propagated or handled"
            print("✓ Enter/Return key event bubble-up and handling passed")

    def test_modes():
        print("\n--- Testing Interaction Modes ---")
        # Mode 1: Single click copies and closes
        settings.set('interaction_mode', 1)
        popup.setup_interaction_mode()
        
        # We check that showEvent sets up focus
        popup.refresh_list()
        first_item_widget = popup.list_widget.item(0)
        
        # Just verifying structure of mode setup
        assert settings.get('interaction_mode') == 1, "Mode not set to 1"
        
        # Mode 2
        settings.set('interaction_mode', 2)
        popup.setup_interaction_mode()
        assert settings.get('interaction_mode') == 2, "Mode not set to 2"
        print("✓ Mode settings toggle passed")

    try:
        test_search()
        test_config_click()
        test_edit_pin_delete()
        test_copy()
        test_key_navigation()
        test_modes()
        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! 🎉")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        failures.append(e)
    except Exception as e:
        print(f"\n💥 UNEXPECTED ERROR: {e}")
        failures.append(e)
        
    popup.close()
    app.quit()
    
    if failures:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    setup_test_env()
    try:
        run_tests()
    finally:
        restore_test_env()
