import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from screens.variables_ui import VariablesManagerDialog
from core.variables import load_variables

app = QApplication(sys.argv)
dialog = VariablesManagerDialog()

def automate():
    print("Initial:", [dialog.list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(dialog.list_widget.count())])
    
    # Select first
    dialog.list_widget.setCurrentRow(0)
    print("Selected:", dialog.list_widget.selectedItems()[0].data(Qt.ItemDataRole.UserRole))
    
    # Click remove
    dialog.remove_btn.click()
    
    print("After remove:", [dialog.list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(dialog.list_widget.count())])
    
    app.quit()

QTimer.singleShot(1000, automate)
dialog.show()
app.exec()
