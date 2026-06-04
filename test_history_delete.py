import sys, time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from screens.popup import FastPastePopup
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
    print("Calling delete_item(0)...")
    popup.delete_item(0)
    
    print("Filtered History IDs after:", [item['id'] for item in popup.filtered_history])
    print("Filtered History Texts after:", [item['content'] for item in popup.filtered_history])
    
    app.quit()

QTimer.singleShot(1000, automate)
popup.show()
app.exec()
