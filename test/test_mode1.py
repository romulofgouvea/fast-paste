import sys, time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from configs.settings_manager import settings
from screens.popup import FastPastePopup

app = QApplication(sys.argv)
settings.set('interaction_mode', 1)
popup = FastPastePopup()

def automate():
    print("Is Mode 1?", settings.get('interaction_mode') == 1)
    
    item = popup.list_widget.item(1)
    if item:
        print("Emitting single click on item...")
        popup.list_widget.itemClicked.emit(item)
    
    QTimer.singleShot(500, check_if_open)

def check_if_open():
    print("Is popup visible after single click in Mode 1?", popup.isVisible())
    app.quit()

QTimer.singleShot(500, automate)
popup.show()
app.exec()
