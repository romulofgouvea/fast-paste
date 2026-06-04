import sys, time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from configs.config import settings
from screens.history_ui import FastPastePopup

app = QApplication(sys.argv)
settings.set('interaction_mode', 2) # Force Mode 2
popup = FastPastePopup()

def automate():
    print("Is Mode 1?", settings.get('interaction_mode') == 1)
    
    # Simulate single click on first item
    item = popup.list_widget.item(1) # Item 1 is the first real item (0 is header)
    if item:
        rect = popup.list_widget.visualItemRect(item)
        print("Emitting single click on item...")
        popup.list_widget.itemClicked.emit(item)
    
    QTimer.singleShot(500, check_if_open)

def check_if_open():
    print("Is popup visible after single click?", popup.isVisible())
    
    # Simulate double click
    item = popup.list_widget.item(1)
    print("Emitting double click on item...")
    popup.list_widget.itemDoubleClicked.emit(item)
    
    QTimer.singleShot(500, check_if_open_after_double)

def check_if_open_after_double():
    print("Is popup visible after double click?", popup.isVisible())
    app.quit()

QTimer.singleShot(500, automate)
popup.show()
app.exec()
