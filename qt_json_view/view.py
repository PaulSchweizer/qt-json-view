from functools import partial

from Qt import QtCore, QtWidgets


class JsonView(QtWidgets.QTreeView):

    def __init__(self, parent=None):
        super(JsonView, self).__init__(parent=parent)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)

    def _menu(self, position):
        menu = QtWidgets.QMenu()
        index = self.indexAt(position)
        if index.isValid():
            parent = None
            item = self.model().itemFromIndex(index)
            if item is not None:
                parent = self.model().itemFromIndex(index).parent()
            if parent is None:
                parent = self.model().invisibleRootItem()
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(partial(self._delete_item, index))

        add_action = menu.addAction("Add Item")
        if index.isValid():
            parent = self.model().itemFromIndex(index)
            if parent.data(QtCore.Qt.UserRole) not in (list, dict):
                parent = parent.parent()
            if parent is None:
                parent = self.model().invisibleRootItem()
        else:
            parent = self.model().invisibleRootItem()

        add_action.triggered.connect(partial(self._add_item, parent))
        menu.exec_(self.viewport().mapToGlobal(position))

    def _add_item(self, parent):
        dialog = SelectDataType(self)
        dialog.exec_()
        data_type = dialog.data_type
        if data_type is None:
            return

        key_label = {
            bool: "Bool", int: "Integer", float: "Float", basestring: "String",
            list: "List", dict: "Dict"
        }[data_type]
        if parent.data(QtCore.Qt.UserRole) == list:
            key_label = "-"
        key_item = self.model()._create_key_item(key_label, data_type)

        if data_type is list:
            empty_item = self.model()._create_empty_item()
            parent.appendRow([key_item, empty_item])
            self.model().items_from_list([], key_item)
        elif data_type is dict:
            empty_item = self.model()._create_empty_item()
            parent.appendRow([key_item, empty_item])
            self.model().items_from_dict({}, key_item)
        else:
            defaults = {bool: False, int: 0, float: 0.0, basestring: ""}
            value_item = self.model()._create_value_item(defaults[data_type])
            parent.appendRow([key_item, value_item])

    def _delete_item(self, index):
        parent = self.model().itemFromIndex(index).parent()
        if parent is None:
            parent = self.model().invisibleRootItem()
        parent.takeRow(index.row())


class SelectDataType(QtWidgets.QDialog):

    def __init__(self, parent=None):
        """Initialize SelectDataType."""
        super(SelectDataType, self).__init__(parent=parent)

        self.data_type = None

        self.setLayout(QtWidgets.QVBoxLayout())

        bool_btn = QtWidgets.QPushButton("Boolean")
        int_btn = QtWidgets.QPushButton("Integer")
        float_btn = QtWidgets.QPushButton("Float")
        string_btn = QtWidgets.QPushButton("String")
        list_btn = QtWidgets.QPushButton("List")
        dict_btn = QtWidgets.QPushButton("Dictionary")
        cancel_btn = QtWidgets.QPushButton("Cancel")

        self.layout().addWidget(bool_btn)
        self.layout().addWidget(int_btn)
        self.layout().addWidget(float_btn)
        self.layout().addWidget(string_btn)
        self.layout().addWidget(list_btn)
        self.layout().addWidget(dict_btn)
        self.layout().addWidget(cancel_btn)

        bool_btn.clicked.connect(partial(self._submit, bool))
        int_btn.clicked.connect(partial(self._submit, int))
        float_btn.clicked.connect(partial(self._submit, float))
        string_btn.clicked.connect(partial(self._submit, basestring))
        list_btn.clicked.connect(partial(self._submit, list))
        dict_btn.clicked.connect(partial(self._submit, dict))
        cancel_btn.clicked.connect(self.close)

    def _submit(self, data_type):
        self.data_type = data_type
        self.close()
