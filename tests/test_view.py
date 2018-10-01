
import sys
sys.path.append("C:\\PROJECTS\\qt-json-view")

from Qt import QtCore, QtWidgets
from qt_json_view.view import JsonView
from qt_json_view.model import JsonModel


app = QtWidgets.QApplication([])

data = {
    "none": None,
    "bool": True,
    "int": 666,
    "float": 1.23,
    "list1": [
        1,
        2,
        3
    ],
    "dict": {
        "key": "value"
    },
}

widget = QtWidgets.QWidget()
widget.setLayout(QtWidgets.QVBoxLayout())
button = QtWidgets.QPushButton("Serialize")
view = JsonView()
widget.layout().addWidget(view)
widget.layout().addWidget(button)

model = JsonModel()
model.items_from_dict(data=data)
view.setModel(model)

def serialize():
    import json
    print json.dumps(model.serialize(), indent=2)

button.clicked.connect(serialize)

widget.show()
view.expandAll()
widget.setGeometry(100, 100, 400, 400)

app.exec_()
