from Qt import QtCore, QtWidgets, QtGui

from qt_json_view import delegate
from qt_json_view.datatypes import TypeRole


class JsonView(QtWidgets.QTreeView):
    """Tree to display the JsonModel."""

    def __init__(self, parent=None):
        super(JsonView, self).__init__(parent=parent)
        self.setMouseTracking(True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.setItemDelegate(delegate.JsonDelegate())
        ctrl_c = QtWidgets.QShortcut(
            QtGui.QKeySequence(self.tr("Ctrl+c")), self)
        ctrl_c.activated.connect(self.copy)
        self.clicked.connect(self._on_clicked)

    def _menu(self, position):
        """Show the actions of the DataType (if any)."""
        menu = QtWidgets.QMenu()
        actions = self.actions()

        expand_all = QtWidgets.QAction("Expand All", self)
        expand_all.triggered.connect(self.expandAll)
        actions.append(expand_all)
        collapse_all = QtWidgets.QAction("Collapse All", self)
        collapse_all.triggered.connect(self.collapseAll)
        actions.append(collapse_all)

        index = self.indexAt(position)
        data = index.data(TypeRole)
        if data is not None:
            actions += data.actions(index)
        for action in actions:
            menu.addAction(action)
        menu.exec_(self.viewport().mapToGlobal(position))

    def copy(self):
        """Copy the currently selected value to the clipboard."""
        for index in self.selectedIndexes():
            if index.column() == 1:
                model = self.model()
                if isinstance(model, QtCore.QAbstractProxyModel):
                    index = model.mapToSource(index)
                    model = model.sourceModel()
                type_ = index.data(TypeRole)
                if type_ is not None:
                    type_.copy(index)
                return

    def _on_clicked(self, index):
        if index.column() == 1:
            type_ = index.data(TypeRole)
            if type_ is not None:
                pos = self.mapFromGlobal(QtGui.QCursor().pos())
                type_.clicked(self, index, pos, self.visualRect(index))

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.pos())
        if index.column() == 1:
            type_ = index.data(TypeRole)
            if type_ is not None:
                type_.hovered(index, event.pos(), self.visualRect(index))
        event.accept()
