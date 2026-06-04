import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from core.variables import load_variables, add_variable, remove_variable
from screens.variables_ui import VariablesManagerDialog

app = QApplication(sys.argv)
add_variable("primeiro", "111")
add_variable("segundo", "222")

print("Before:", load_variables())

dialog = VariablesManagerDialog()
dialog.list_widget.setCurrentRow(0)
dialog.remove_var()

print("After:", load_variables())
