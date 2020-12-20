from PyQt5.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QItemDelegate)


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