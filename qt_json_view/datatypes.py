import os
import re
import webbrowser
from collections import OrderedDict
from functools import partial

import six
from Qt import QtCore, QtGui, QtWidgets

TypeRole = QtCore.Qt.UserRole + 1
SchemaRole = QtCore.Qt.UserRole + 2


class DataType(object):
    """Base class for data types."""

    COLOR = QtCore.Qt.white
    INACTIVE_COLOR = QtCore.Qt.lightGray

    DEFAULT = None
    ITEM = QtGui.QStandardItem

    def matches(self, data):
        """Logic to define whether the given data matches this type."""
        raise NotImplementedError

    def empty_container(self):
        """Return an empty container object for the children of this type."""
        raise NotImplementedError

    def next(self, model, data, parent):
        """Implement if this data type has to add child items to itself."""
        pass

    def actions(self, index):
        """Re-implement to return custom QActions."""
        model = index.model()
        copy = QtWidgets.QAction('Copy', None)
        copy.triggered.connect(partial(self.copy, index))
        actions = [copy]
        if isinstance(model, QtCore.QAbstractProxyModel):
            index = model.mapToSource(index)
            model = model.sourceModel()
        if model.editable_values and index.data(SchemaRole).get('editable', True):
            reset = QtWidgets.QAction('Reset', None)
            reset.triggered.connect(partial(self.reset, index))
            actions.append(reset)
        return actions

    def paint(self, delegate, painter, option, index):
        """Optionally re-implement for use by the delegate."""
        raise NotImplementedError

    def createEditor(self, delegate, parent, option, index):
        """Optionally re-implement for use by the delegate."""
        raise NotImplementedError

    def reset(self, index):
        model = index.model()
        if isinstance(model, QtCore.QAbstractProxyModel):
            index = model.mapToSource(index)
            model = model.sourceModel()
        schema = index.data(SchemaRole)
        default = schema.get("default", self.__class__.DEFAULT)
        model.itemFromIndex(index).setData(default, QtCore.Qt.DisplayRole)

    def copy(self, index):
        """Put the given display value into the clipboard."""
        model = index.model()
        if isinstance(model, QtCore.QAbstractProxyModel):
            index = model.mapToSource(index)
            model = model.sourceModel()
        value = str(index.data(QtCore.Qt.DisplayRole))
        QtWidgets.QApplication.clipboard().setText(value)

    def setModelData(self, delegate, editor, model, index):
        """Optionally re-implement for use by the delegate."""
        if isinstance(model, QtCore.QAbstractProxyModel):
            index = model.mapToSource(index)
            model = model.sourceModel()
        return_value = super(delegate.__class__, delegate).setModelData(editor, model, index)
        model.data_object.update(model.serialize())
        return return_value

    def serialize(self, model, item, data, parent):
        """Serialize this data type."""
        value_item = parent.child(item.row(), 1)
        value = value_item.data(QtCore.Qt.DisplayRole)
        if isinstance(data, dict):
            key_item = parent.child(item.row(), 0)
            key = key_item.data(QtCore.Qt.DisplayRole)
            data[key] = value
        elif isinstance(data, list):
            data.append(value)

    def key_item(self, key, model, datatype=None, editable=True):
        """Create an item for the key column for this data type."""
        item = QtGui.QStandardItem(key)
        item.setData(datatype, TypeRole)
        item.setData(datatype.__class__.__name__, QtCore.Qt.ToolTipRole)
        item.setData(
            QtGui.QBrush(datatype.COLOR), QtCore.Qt.ForegroundRole)
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        if editable and model.editable_keys:
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        return item

    def value_item(self, value, model, key=None):
        """Create an item for the value column for this data type."""
        display_value = value
        item = self.ITEM(display_value)
        item.setData(display_value, QtCore.Qt.DisplayRole)
        item.setData(value, QtCore.Qt.UserRole)
        item.setData(self, TypeRole)
        item.setData(QtGui.QBrush(self.COLOR), QtCore.Qt.ForegroundRole)

        schema = model.current_schema.get(key, {})
        item.setData(schema, SchemaRole)
        item.setData(schema.get('tooltip', self.__class__.__name__),
                     QtCore.Qt.ToolTipRole)
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        if model.editable_values and schema.get('editable', True):
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        else:
            item.setData(QtGui.QBrush(self.INACTIVE_COLOR), QtCore.Qt.ForegroundRole)
        return item

    def clicked(self, parent, index, pos, rect):
        pass

    def hovered(self, index, pos, rect):
        pass


# -----------------------------------------------------------------------------
# Default Types
# -----------------------------------------------------------------------------


class NoneType(DataType):
    """None"""

    def matches(self, data):
        return data is None

    def value_item(self, value, model, key=None):
        item = super(NoneType, self).value_item(value, model, key)
        item.setData('None', QtCore.Qt.DisplayRole)
        return item

    def serialize(self, model, item, data, parent):
        value_item = parent.child(item.row(), 1)
        value = value_item.data(QtCore.Qt.DisplayRole)
        value = value if value != 'None' else None
        if isinstance(data, dict):
            key_item = parent.child(item.row(), 0)
            key = key_item.data(QtCore.Qt.DisplayRole)
            data[key] = value
        elif isinstance(data, list):
            data.append(value)


class StrType(DataType):
    """Strings and unicodes"""

    DEFAULT = ""

    def matches(self, data):
        return isinstance(data, six.string_types)


class IntType(DataType):
    """Integers"""

    DEFAULT = 0

    def matches(self, data):
        return isinstance(data, int) and not isinstance(data, bool)


class FloatType(DataType):
    """Floats"""

    DEFAULT = 0.0

    def matches(self, data):
        return isinstance(data, float)


class BoolType(DataType):
    """Bools are displayed as checkable items with a check box."""

    DEFAULT = False

    def matches(self, data):
        return isinstance(data, bool)

    def paint(self, delegate, painter, option, index):
        option.rect.adjust(20, 0, 0, 0)
        super(delegate.__class__, delegate).paint(painter, option, index)
        painter.save()
        checked = bool(index.model().data(index, QtCore.Qt.DisplayRole))
        options = QtWidgets.QStyleOptionButton()
        options.rect = option.rect.adjusted(-20, 0, 0, 0)
        options.state |= QtWidgets.QStyle.State_Active
        options.state |= QtWidgets.QStyle.State_On if checked else QtWidgets.QStyle.State_Off
        options.state |= (
            QtWidgets.QStyle.State_Enabled if index.flags() & QtCore.Qt.ItemIsEditable
            else QtWidgets.QStyle.State_ReadOnly)
        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_CheckBox, options, painter)
        painter.restore()

    def clicked(self, parent, index, pos, rect):
        if not index.flags() & QtCore.Qt.ItemIsEditable:
            return
        model = index.model()
        if isinstance(model, QtCore.QAbstractProxyModel):
            index = model.mapToSource(index)
            model = model.sourceModel()
        item = model.itemFromIndex(index)
        if pos.x() - rect.x() < 18:
            item.setData(not item.data(QtCore.Qt.DisplayRole), QtCore.Qt.DisplayRole)
        model.data_object.update(model.serialize())

    def createEditor(self, delegate, parent, option, index):
        pass


class ListType(DataType):
    """Lists"""

    def matches(self, data):
        return isinstance(data, list)

    def empty_container(self):
        return []

    def next(self, model, data, parent):
        for i, value in enumerate(data):
            type_ = match_type(value, key=i, schema=model.current_schema)
            key_item = type_.key_item(
                str(i), datatype=type_, editable=False, model=model)
            value_item = type_.value_item(value, model=model, key=i)
            parent.appendRow([key_item, value_item])
            type_.next(model, data=value, parent=key_item)
        if model.prev_schemas:
            model.current_schema = model.prev_schemas.pop(-1)

    def value_item(self, value, model, key):
        item = QtGui.QStandardItem()
        font = QtWidgets.QApplication.instance().font()
        font.setItalic(True)
        item.setData(font, QtCore.Qt.FontRole)
        item.setData(QtGui.QBrush(QtCore.Qt.lightGray), QtCore.Qt.ForegroundRole)
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        schema = model.current_schema.get(key, {})
        item.setData(schema.get('tooltip', self.__class__.__name__),
                     QtCore.Qt.ToolTipRole)
        return item

    def key_item(self, key, model, datatype=None, editable=True):
        """Create an item for the key column for this data type."""
        item = super(ListType, self).key_item(key, model, datatype, editable)
        model.prev_schemas.append(model.current_schema)
        model.current_schema = model.current_schema.get(key, {}).get('properties', {})
        return item

    def serialize(self, model, item, data, parent):
        key_item = parent.child(item.row(), 0)
        if key_item:
            if isinstance(data, dict):
                key = key_item.data(QtCore.Qt.DisplayRole)
                data[key] = self.empty_container()
                data = data[key]
            elif isinstance(data, list):
                new_data = self.empty_container()
                data.append(new_data)
                data = new_data
        for row in range(item.rowCount()):
            child_item = item.child(row, 0)
            type_ = child_item.data(TypeRole)
            type_.serialize(
                model=self, item=child_item, data=data, parent=item)


class DictType(DataType):
    """Dictionaries"""

    def matches(self, data):
        return isinstance(data, dict)

    def empty_container(self):
        return {}

    def next(self, model, data, parent):
        for key, value in data.items():
            type_ = match_type(value, key=key, schema=model.current_schema)
            key_item = type_.key_item(key, datatype=type_, model=model)
            value_item = type_.value_item(value, model, key)
            parent.appendRow([key_item, value_item])
            type_.next(model, data=value, parent=key_item)
        if model.prev_schemas:
            model.current_schema = model.prev_schemas.pop(-1)

    def key_item(self, key, model, datatype=None, editable=True):
        """Create an item for the key column for this data type."""
        item = super(DictType, self).key_item(key, model, datatype, editable)
        model.prev_schemas.append(model.current_schema)
        model.current_schema = model.current_schema.get(key, {}).get('properties', {})
        return item

    def value_item(self, value, model, key):
        item = QtGui.QStandardItem()
        font = QtWidgets.QApplication.instance().font()
        font.setItalic(True)
        item.setData(font, QtCore.Qt.FontRole)
        item.setData(QtGui.QBrush(QtCore.Qt.lightGray), QtCore.Qt.ForegroundRole)
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        schema = model.current_schema.get(key, {})
        item.setData(schema.get('tooltip', self.__class__.__name__),
                     QtCore.Qt.ToolTipRole)
        return item

    def serialize(self, model, item, data, parent):
        key_item = parent.child(item.row(), 0)
        if key_item:
            if isinstance(data, dict):
                key = key_item.data(QtCore.Qt.DisplayRole)
                data[key] = self.empty_container()
                data = data[key]
            elif isinstance(data, list):
                new_data = self.empty_container()
                data.append(new_data)
                data = new_data
        for row in range(item.rowCount()):
            child_item = item.child(row, 0)
            type_ = child_item.data(TypeRole)
            type_.serialize(model=self, item=child_item, data=data, parent=item)


class AnyType(DataType):

    def matches(self, data):
        return True

    def value_item(self, value, model, key):
        item = super(AnyType, self).value_item(str(value), model, key)
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        return item


# -----------------------------------------------------------------------------
# Derived Types
# -----------------------------------------------------------------------------


class OrderedDictType(DictType):
    """Ordered Dictionaries"""

    def matches(self, data):
        return isinstance(data, OrderedDict)

    def empty_container(self):
        return OrderedDict()


class RangeType(DataType):
    """A range, shown as three spinboxes next to each other.

    A range is defined as a dict with start, end and step keys.
    It supports both floats and ints.
    """

    KEYS = ['start', 'end', 'step']
    DEFAULT = [0, 1, 1]

    def matches(self, data):
        if isinstance(data, dict) and len(data) == 3:
            if all([True if k in self.KEYS else False for k in data.keys()]):
                return True
        return False

    def paint(self, delegate, painter, option, index):
        data = index.data(QtCore.Qt.UserRole)

        painter.save()

        painter.setPen(QtGui.QPen(index.data(QtCore.Qt.ForegroundRole).color()))
        metrics = painter.fontMetrics()
        spinbox_option = QtWidgets.QStyleOptionSpinBox()
        start_rect = QtCore.QRect(option.rect)
        start_rect.setWidth(start_rect.width() / 3.0)
        spinbox_option.rect = start_rect
        spinbox_option.frame = True
        spinbox_option.state = option.state
        spinbox_option.buttonSymbols = QtWidgets.QAbstractSpinBox.NoButtons
        for i, key in enumerate(self.KEYS):
            if i > 0:
                spinbox_option.rect.adjust(
                    spinbox_option.rect.width(), 0,
                    spinbox_option.rect.width(), 0)
            QtWidgets.QApplication.style().drawComplexControl(
                QtWidgets.QStyle.CC_SpinBox, spinbox_option, painter)
            value = str(data[key])
            value_rect = QtCore.QRectF(
                spinbox_option.rect.adjusted(6, 1, -2, -2))
            value = metrics.elidedText(
                value, QtCore.Qt.ElideRight, value_rect.width() - 20)
            painter.drawText(value_rect, value)

        painter.restore()

    def createEditor(self, delegate, parent, option, index):
        data = index.data(QtCore.Qt.UserRole)
        wid = QtWidgets.QWidget(parent)
        wid.setLayout(QtWidgets.QHBoxLayout(parent))
        wid.layout().setContentsMargins(0, 0, 0, 0)
        wid.layout().setSpacing(0)

        start = data['start']
        end = data['end']
        step = data['step']

        if isinstance(start, float):
            start_spinbox = QtWidgets.QDoubleSpinBox(wid)
        else:
            start_spinbox = QtWidgets.QSpinBox(wid)

        if isinstance(end, float):
            end_spinbox = QtWidgets.QDoubleSpinBox(wid)
        else:
            end_spinbox = QtWidgets.QSpinBox(wid)

        if isinstance(step, float):
            step_spinbox = QtWidgets.QDoubleSpinBox(wid)
        else:
            step_spinbox = QtWidgets.QSpinBox(wid)

        start_spinbox.setRange(-16777215, 16777215)
        end_spinbox.setRange(-16777215, 16777215)
        step_spinbox.setRange(-16777215, 16777215)
        start_spinbox.setValue(start)
        end_spinbox.setValue(end)
        step_spinbox.setValue(step)
        wid.layout().addWidget(start_spinbox)
        wid.layout().addWidget(end_spinbox)
        wid.layout().addWidget(step_spinbox)
        return wid

    def setModelData(self, delegate, editor, model, index):
        if isinstance(model, QtCore.QAbstractProxyModel):
            index = model.mapToSource(index)
            model = model.sourceModel()
        data = index.data(QtCore.Qt.UserRole)
        data['start'] = editor.layout().itemAt(0).widget().value()
        data['end'] = editor.layout().itemAt(1).widget().value()
        data['step'] = editor.layout().itemAt(2).widget().value()
        model.itemFromIndex(index).setData(data, QtCore.Qt.UserRole)
        model.data_object.update(model.serialize())

    def value_item(self, value, model, key=None):
        """Item representing a value."""
        value_item = super(RangeType, self).value_item(None, model, key)
        value_item.setData(value, QtCore.Qt.UserRole)
        return value_item

    def serialize(self, model, item, data, parent):
        value_item = parent.child(item.row(), 1)
        value = value_item.data(QtCore.Qt.UserRole)
        if isinstance(data, dict):
            key_item = parent.child(item.row(), 0)
            key = key_item.data(QtCore.Qt.DisplayRole)
            data[key] = value
        elif isinstance(data, list):
            data.append(value)

    def reset(self, index):
        model = index.model()
        if isinstance(model, QtCore.QAbstractProxyModel):
            index = model.mapToSource(index)
            model = model.sourceModel()
        schema = index.data(SchemaRole)
        default = schema.get("default", self.__class__.DEFAULT)

        data = index.data(QtCore.Qt.UserRole)
        data['start'] = default[0]
        data['end'] = default[1]
        data['step'] = default[2]

        model.itemFromIndex(index).setData(data, QtCore.Qt.UserRole)

    def copy(self, index):
        """Put the given display value into the clipboard."""
        model = index.model()
        if isinstance(model, QtCore.QAbstractProxyModel):
            index = model.mapToSource(index)
            model = model.sourceModel()
        value = str(index.data(QtCore.Qt.UserRole))
        QtWidgets.QApplication.clipboard().setText(value)


class UrlType(DataType):
    """Provide a link to urls."""

    REGEX = re.compile(r'(?:https?):\/\/|(?:file):\/\/')

    def matches(self, data):
        if isinstance(data, six.string_types):
            if self.REGEX.match(data) is not None:
                return True
        return False

    def actions(self, index):
        actions = super(UrlType, self).actions(index)
        explore = QtWidgets.QAction('Explore ...', None)
        explore.triggered.connect(
            partial(self._explore, index.data(QtCore.Qt.DisplayRole)))
        actions.append(explore)
        return actions

    def createEditor(self, delegate, parent, option, index):
        """Show a button to browse to the url."""
        value = index.data(QtCore.Qt.DisplayRole)
        pos = QtGui.QCursor().pos()
        popup = QtWidgets.QWidget(parent=parent)
        popup.setWindowFlags(QtCore.Qt.Popup)
        popup.setLayout(QtWidgets.QHBoxLayout(popup))
        button = QtWidgets.QPushButton("Explore: {0}".format(value))
        button.clicked.connect(partial(self._explore, value))
        button.clicked.connect(popup.close)
        button.setFlat(True)
        button.setCursor(QtCore.Qt.PointingHandCursor)
        button.setIcon(index.data(QtCore.Qt.DecorationRole))
        font = QtWidgets.QApplication.instance().font()
        font.setUnderline(True)
        button.setFont(font)
        popup.layout().addWidget(button)
        metrics = QtWidgets.QApplication.instance().fontMetrics()
        width = metrics.width(button.text())
        height = metrics.xHeight()
        popup.setGeometry(pos.x(), pos.y(), width, height)
        popup.show()

        model = index.model()
        if isinstance(model, QtCore.QAbstractProxyModel):
            index = model.mapToSource(index)
            model = model.sourceModel()

        if model.editable_values:
            if index.data(SchemaRole).get("editable", True):
                return super(delegate.__class__, delegate).createEditor(
                    parent, option, index)

    def value_item(self, value, model, key=None):
        """Create an item for the value column for this data type."""
        item = super(UrlType, self).value_item(value, model, key)
        font = QtWidgets.QApplication.instance().font()
        font.setUnderline(True)
        item.setData(font, QtCore.Qt.FontRole)
        icon = QtWidgets.QApplication.instance().style().standardIcon(
            QtWidgets.QApplication.instance().style().SP_DriveNetIcon)
        item.setData(icon, QtCore.Qt.DecorationRole)
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        return item

    def _explore(self, url):
        """Open the url"""
        webbrowser.open(url)


class FilepathType(UrlType):
    """Files and paths can be opened."""

    REGEX = re.compile(r'(\/.*)|([A-Z]:\\.*)')

    def matches(self, data):
        if isinstance(data, six.string_types):
            if self.REGEX.match(data) is not None:
                return True
        return False

    def actions(self, index):
        actions = super(UrlType, self).actions(index)
        explore_path = QtWidgets.QAction('Explore Path ...', None)
        actions.append(explore_path)
        path = index.data(QtCore.Qt.DisplayRole)
        if os.path.isfile(path):
            open_file = QtWidgets.QAction('Open File ...', None)
            actions.append(open_file)
            open_file.triggered.connect(partial(self._explore, path))
            path = os.path.dirname(path)
        explore_path.triggered.connect(partial(self._explore, path))
        return actions

    def value_item(self, value, model, key=None):
        """Create an item for the value column for this data type."""
        item = super(FilepathType, self).value_item(value, model, key)
        if os.path.isfile(value):
            icon = QtWidgets.QApplication.instance().style().standardIcon(
                QtWidgets.QApplication.instance().style().SP_FileIcon)
        elif os.path.isdir(value):
            icon = QtWidgets.QApplication.instance().style().standardIcon(
                QtWidgets.QApplication.instance().style().SP_DirIcon)
        else:
            return item
        item.setData(icon, QtCore.Qt.DecorationRole)
        return item


class ChoiceType(DataType):
    """A combobox that allows for a number of choices.

    The data has to be a dict with a value and a choices key.
    {
        "value": "A",
        "choices": ["A", "B", "C"]
    }
    """

    KEYS = ['value', 'choices']

    def matches(self, data):
        if isinstance(data, dict) and len(data) == 2:
            if all([True if k in self.KEYS else False for k in data.keys()]):
                return True
        return False

    def createEditor(self, delegate, parent, option, index):
        data = index.data(QtCore.Qt.UserRole)
        cbx = QtWidgets.QComboBox(parent)
        cbx.addItems([str(d) for d in data['choices']])
        cbx.setCurrentIndex(cbx.findText(str(data['value'])))
        return cbx

    def setModelData(self, delegate, editor, model, index):
        if isinstance(model, QtCore.QAbstractProxyModel):
            index = model.mapToSource(index)
            model = model.sourceModel()
        data = index.data(QtCore.Qt.UserRole)
        data['value'] = data['choices'][editor.currentIndex()]
        model.itemFromIndex(index).setData(data['value'] , QtCore.Qt.DisplayRole)
        model.itemFromIndex(index).setData(data, QtCore.Qt.UserRole)
        model.data_object.update(model.serialize())

    def value_item(self, value, model, key=None):
        """Item representing a value."""
        item = super(ChoiceType, self).value_item(value['value'], model, key)
        item.setData(value, QtCore.Qt.UserRole)
        return item

    def serialize(self, model, item, data, parent):
        value_item = parent.child(item.row(), 1)
        value = value_item.data(QtCore.Qt.UserRole)
        value['value'] = value_item.data(QtCore.Qt.DisplayRole)
        if isinstance(data, dict):
            key_item = parent.child(item.row(), 0)
            key = key_item.data(QtCore.Qt.DisplayRole)
            data[key] = value
        elif isinstance(data, list):
            data.append(value)


# Add any custom DataType to this list
#
DATA_TYPES = [
    NoneType(),
    UrlType(),
    FilepathType(),
    StrType(),
    IntType(),
    FloatType(),
    BoolType(),
    ListType(),
    RangeType(),
    ChoiceType(),
    OrderedDictType(),
    DictType(),
    AnyType()
]


def match_type(data, key=None, schema=None):
    """Try to match the given data object to a DataType"""

    if key and schema:
        type_cls = schema.get(key, {}).get("type", None)
        if type_cls is not None:
            for type_ in DATA_TYPES:
                if isinstance(type_, type_cls):
                    return type_
            new_type = type_cls()
            DATA_TYPES.append(new_type)
            return new_type

    for type_ in DATA_TYPES:
        if type_.matches(data):
            return type_
    return AnyType()
