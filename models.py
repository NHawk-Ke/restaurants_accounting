from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QItemDelegate, QCheckBox)


class DishTableDelegateCell(QItemDelegate):
    def __init__(self, modify_func, delete_func, parent=None):
        super(DishTableDelegateCell, self).__init__(parent)
        self.modify_func = modify_func
        self.delete_func = delete_func

    def paint(self, painter, option, index):
        if not self.parent().indexWidget(index):
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            id_idx = index.siblingAtColumn(0)
            dish_id = self.parent().model().data(id_idx)
            modify_btn = QPushButton("修改", self.parent())
            modify_btn.clicked.connect(lambda *args, row_dish_id=dish_id: self.modify_func(row_dish_id))
            layout.addWidget(modify_btn)
            delete_btn = QPushButton("删除", self.parent())
            delete_btn.clicked.connect(lambda *args, row_dish_id=dish_id: self.delete_func(row_dish_id))
            layout.addWidget(delete_btn)
            widget = QWidget()
            widget.setLayout(layout)
            self.parent().setIndexWidget(
                index,
                widget
            )


class DishDataTableDelegateCell(QItemDelegate):
    def __init__(self, parent=None):
        super(DishDataTableDelegateCell, self).__init__(parent)

    def paint(self, painter, option, index):
        index_widget = self.parent().indexWidget(index)
        if not index_widget:
            layout = QHBoxLayout()
            layout.setAlignment(Qt.AlignCenter)

            check_state = int(self.parent().model().data(index))
            check_box = QCheckBox()
            check_box.setChecked(check_state == 2)
            check_box.stateChanged.connect(lambda state: self.parent().model().setData(index, str(state), Qt.DisplayRole))
            layout.addWidget(check_box)
            widget = QWidget()
            widget.setLayout(layout)
            self.parent().setIndexWidget(index, widget)
        else:
            check_box = index_widget.layout().itemAt(0).widget()
            check_box.setChecked(int(self.parent().model().data(index)) == 2)
