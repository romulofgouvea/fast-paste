import sys, time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from configs.settings_manager import settings
from screens.popup import FastPastePopup
from core import history

history.add_text("test item 1")
app = QApplication(sys.argv)
settings.set('interaction_mode', 2)
popup = FastPastePopup(standalone=False)

def simulate_single_click():
    print("Simulating single click in Mode 2...")
    item = popup.list_widget.item(0) # or whatever index is the actual item
    if item:
        popup.list_widget.itemClicked.emit(item)
    else:
        print("No item found")

    QTimer.singleShot(500, check_status)

def check_status():
    print("Is popup visible after single click?", popup.isVisible())
    app.quit()

QTimer.singleShot(1000, simulate_single_click)
popup.show()
app.exec()
