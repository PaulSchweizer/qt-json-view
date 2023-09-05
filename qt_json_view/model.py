from Qt import QtGui, QtCore
from collections import OrderedDict

from qt_json_view import datatypes

from qt_json_view.datatypes import match_type, TypeRole, ListType, DictType, SchemaRole


class JsonModel(QtGui.QStandardItemModel):
    """Represent JSON-serializable data."""

    NON_DEFAULT_COLOR = QtCore.Qt.yellow

    def __init__(
            self,
            parent=None,
            data=None,
            editable_keys=False,
            editable_values=False,
            schema=None):
        super(JsonModel, self).__init__(parent=parent)
        self.data_object = data
        self.schema = schema
        if data is not None:
            self.init(data, editable_keys, editable_values, schema)

    def init(self, data, editable_keys=False, editable_values=False, schema=None):
        """Convert the data to items and populate the model."""
        self.clear()
        self.setHorizontalHeaderLabels(['Key', 'Value'])
        self.data_object = data
        self.editable_keys = editable_keys
        self.editable_values = editable_values
        self.schema = schema or {}
        self.current_schema = self.schema
        self.prev_schemas = []
        parent = self.invisibleRootItem()
        type_ = match_type(data)
        parent.setData(type_, TypeRole)
        type_.next(model=self, data=data, parent=parent)

    def serialize(self):
        """Assemble the model back into a dict or list."""
        parent = self.invisibleRootItem()
        type_ = parent.data(TypeRole)
        data = type_.empty_container()
        type_.serialize(model=self, item=parent, data=data, parent=parent)
        return data

    def data(self, index, role):
        if index.column() == 1 and role == QtCore.Qt.ForegroundRole:
            schema = index.data(SchemaRole) or {}
            default = schema.get('default')
            if default is not None and default != index.data(QtCore.Qt.DisplayRole):
                return QtGui.QBrush(self.NON_DEFAULT_COLOR)

        return super(JsonModel, self).data(index, role)


class JsonSortFilterProxyModel(QtCore.QSortFilterProxyModel):
    """Show ALL occurences by keeping the parents of each occurence visible."""

    def __init__(self, parent=None):
        super(JsonSortFilterProxyModel, self).__init__(parent=parent)
        self.keep_children = False

    def filterAcceptsRow(self, sourceRow, sourceParent):
        """Accept the row if the parent has been accepted."""
        index = self.sourceModel().index(sourceRow, self.filterKeyColumn(), sourceParent)
        return self.accept_index(index)

    def accept_index(self, index):
        if index.isValid():
            text = str(index.data(self.filterRole()))
            if self.filterRegExp().indexIn(text) >= 0:
                return True
            if self.keep_children:
                parent = index.parent()
                while parent.isValid():
                    parent_text = str(parent.data(self.filterRole()))
                    if self.filterRegExp().indexIn(parent_text) >= 0:
                        return True
                    parent = parent.parent()
            for row in range(index.model().rowCount(index)):
                if self.accept_index(index.model().index(row, self.filterKeyColumn(), index)):
                    return True
        return False
