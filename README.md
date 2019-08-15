# Qt JSON View

This widget allows to display and edit JSON-serializable data in a Qt view. The system is easily extensible with custom types.

An example to get you started is [here](example.py).

![Qt JSON View](qt-json-view.png)

## Overview

A provided JSON-serializable dict or list is converted to a QStandardItemModel.
During conversion, each entry in the source data is mapped to a [DataType](qt_json_view/datatypes/).
The DataType defines how the entry is added to the model, how it is serialized. The delegate.JsonDelegate draws on the optional DataType implementations to display the item. The DataType can also define custom right-click actions for the item.
The model can then be serialized back into a dictionary after editing.

## DataTypes

A number of data types are already implemented, but it is easy to implement and inject your own on the fly, please see section below.

*Standard JSON Types:*

* NoneType: None
* BoolType: bool
* IntType: int
* FloatType: float
* StrType: str and unicode
* ListType: list
* DictType: dict

*Custom Types:*

* UrlType: Detects urls and provides an "Explore ..." action opening the web browser.
* FilepathType: Detects file paths and provides an "Explore ..." action opening the file browser
* IntRangeType: A range has to be a dict in the form of:
```json
{
    "start": 0,
    "end": 100,
    "step": 2
}
```
It is displayed in one row.

* FloatRangeType: A range has to be a dict in the form of:
```json
{
    "start": 0.0,
    "end": 100.0,
    "step": 0.5
}
```
It is displayed in one row.

* ChoicesType: The user can choose from a range of choices. It is shown as a combobox. The data has to be a dict in the form:
```json
{
    "value": "A",
    "choices": ["A", "B", "C"]
}
```

### Implement custom DataTypes

Subclass the datatypes.DataType base class and implement what you need.
Then inject an instance of your DataType into datatypes.DATA_TYPES so it is found when the model is initialized.
Make sure to inject it at the right position in the list DATA_TYPES list since the model uses the first match it finds.

```python
from qt_json_view import datatypes

class TestType(object):

    def matches(self, data):
        if data == "TEST":
            return True
        return False

idx = [i for i in datatypes.DATA_TYPES if isinstance(i, datatypes.StrType)][0]
datatypes.DATA_TYPES.insert(idx, TestType())
```

## View

The view.JsonView is a QTreeView with the delegate.JsonDelegate.

## Model

The model.JsonModel is a QStandardItemModel. It can be initialized from a JSON-serializable object and serialized to a JSON-serializable object.

## Filtering

The mdoel.JsonSortFilterProxyModel is a QSortFilterProxyModel extended to filter through the entire tree.

## Delegate

The delegate draws on the DataTypes of the items to determine how they are drawn. The datatype.DataType uses the paint, createEditor and setModelData methods if they are available on the DataType.
