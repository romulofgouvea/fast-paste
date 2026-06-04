import sys, time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from screens.history_ui import FastPastePopup
from core import history

# add some items
history.add_text("First item")
time.sleep(0.1)
history.add_text("Second item")
time.sleep(0.1)
history.add_text("Third item")

app = QApplication(sys.argv)
popup = FastPastePopup()

def automate():
    print("Filtered History IDs:", [item['id'] for item in popup.filtered_history])
    print("Filtered History Texts:", [item['content'] for item in popup.filtered_history])
    
    # Try deleting index 0
    print("Calling history.delete_item...")
    item_id = popup.filtered_history[0]["id"]
    history.delete_item(item_id)
    popup.refresh_list()
    
    print("Filtered History IDs after:", [item['id'] for item in popup.filtered_history])
    print("Filtered History Texts after:", [item['content'] for item in popup.filtered_history])
    
    app.quit()

QTimer.singleShot(1000, automate)
popup.show()
app.exec()
