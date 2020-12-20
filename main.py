import os
import sqlite3
from datetime import datetime, timedelta
from typing import Union

import sys
from PyQt5 import QtCore, uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget)

from filters import TableFilter
from models import DishTableDelegateCell


class MainWindow(QMainWindow):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    MAIN_UI_FILE = os.path.join(BASE_DIR, "main.ui")
    NEW_DISH_POPUP_UI_FILE = os.path.join(BASE_DIR, "new_dish_popup.ui")
    MODIFY_DISH_POPUP_UI_FILE = os.path.join(BASE_DIR, "modify_dish_popup.ui")
    DB_FILE = os.path.join(BASE_DIR, "restaurant.db")

    def __init__(self):
        super(MainWindow, self).__init__()
        # Initialize variable
        self.db_connection = None
        self.new_dish_popup = QWidget()
        self.modify_dish_popup = QWidget()
        self.dish_table_model = QStandardItemModel(0, 6)
        self.dish_table_proxy = TableFilter()
        self.dish_name_set = set()

        # Load UI designs
        uic.loadUi(self.MAIN_UI_FILE, self)
        uic.loadUi(self.NEW_DISH_POPUP_UI_FILE, self.new_dish_popup)
        uic.loadUi(self.MODIFY_DISH_POPUP_UI_FILE, self.modify_dish_popup)
        self.init_dish_table()

        # Connect to database
        self.init_db_connection()

        # MainWindow Bind action triggers
        self.action_new_dish.triggered.connect(self.show_new_dish_popup)
        self.dish_lineEdit.textChanged.connect(
            lambda text, col_idx=1: self.dish_table_proxy.set_col_regex_filter(col_idx, text)
        )
        self.lower_price_doubleSpinBox.valueChanged.connect(
            lambda value, col_idx=2: self.dish_table_proxy.set_col_number_filter(col_idx, value, -1)
        )
        self.higher_price_doubleSpinBox.valueChanged.connect(
            lambda value, col_idx=2: self.dish_table_proxy.set_col_number_filter(col_idx, -1, value)
        )
        self.lower_week_sell_spinBox.valueChanged.connect(
            lambda value, col_idx=3: self.dish_table_proxy.set_col_number_filter(col_idx, value, -1)
        )
        self.higher_week_sell_spinBox.valueChanged.connect(
            lambda value, col_idx=3: self.dish_table_proxy.set_col_number_filter(col_idx, -1, value)
        )

        # Popup bind action triggers
        self.new_dish_popup.create_new_dish_btn.clicked.connect(self.create_new_dish)

        # Get current dishes
        self.load_dish_table()

    def init_dish_table(self):
        # Set Header data
        for col, col_name in enumerate(["ID", "菜品", "价格", "近7天总售出", "操作", "备注"]):
            self.dish_table_model.setHeaderData(col, Qt.Horizontal, col_name, Qt.DisplayRole)
        self.dish_table_proxy.setSourceModel(self.dish_table_model)
        self.dish_tableView.setModel(self.dish_table_proxy)
        self.dish_tableView.setColumnHidden(0, True)

    def init_db_connection(self):
        self.db_connection = sqlite3.connect(self.DB_FILE)
        cursor = self.db_connection.cursor()
        # check create table if not exist
        sql_create_dish_table = """ CREATE TABLE IF NOT EXISTS dish (
                                        id integer PRIMARY KEY,
                                        name text NOT NULL,
                                        price numeric Not NULL,
                                        remarks text
                                    ); """
        sql_create_dish_data_table = """ CREATE TABLE IF NOT EXISTS dish_data (
                                            dish_id integer NOT NULL,
                                            date date NOT NULL,
                                            sell_num integer DEFAULT 0,
                                            PRIMARY KEY (dish_id, date)
                                            FOREIGN KEY (dish_id) REFERENCES dish(id) ON DELETE CASCADE
                                        ); """
        cursor.execute(sql_create_dish_table)
        cursor.execute(sql_create_dish_data_table)
        cursor.close()

    def create_table_row(self, dish_id: int, dish_name: str, dish_price: float, sell_num: Union[int, str], dish_remark: str):
        # ID
        row = [QStandardItem(str(dish_id))]
        # Dish Name
        name_item = QStandardItem(dish_name)
        name_item.setTextAlignment(Qt.AlignCenter)
        row.append(name_item)
        # Dish Price
        price_item = QStandardItem("{:.2f}".format(dish_price))
        price_item.setTextAlignment(Qt.AlignCenter)
        row.append(price_item)
        # Dish Week Sell Number
        row.append(QStandardItem(str(sell_num)))
        # Dish Manipulation Button
        row.append(None)
        # Dish Remark
        row.append(QStandardItem(dish_remark))
        return row

    def load_dish_table(self):
        today = datetime.today()
        sql_select_query = """
            SELECT dish.id, dish.name, dish.price, COALESCE(SUM(dish_data.sell_num), 0), dish.remarks
            FROM dish LEFT JOIN dish_data 
            ON dish.id = dish_data.dish_id
            WHERE dish_data.date IS NULL OR dish_data.date BETWEEN {} and {}
            GROUP BY dish.id
            ORDER BY dish.name, dish.price;""".format(
            (today - timedelta(days=7)).strftime("%Y%m%d"), today.strftime("%Y%m%d")
        )
        cursor = self.db_connection.cursor()
        cursor.execute(sql_select_query)
        records = cursor.fetchall()
        dish_name_set = set()
        for row_idx, record in enumerate(records):
            print(record)
            dish_name_set.add(record[1])
            self.dish_table_model.appendRow(self.create_table_row(*record))
        cursor.close()
        self.dish_tableView.setItemDelegateForColumn(
            4, DishTableDelegateCell(self.show_modify_dish_popup, self.delete_dish, self.dish_tableView))

    def show_new_dish_popup(self):
        # Move popup to center
        point = self.rect().center()
        global_point = self.mapToGlobal(point)
        self.new_dish_popup.move(global_point - QtCore.QPoint(self.new_dish_popup.width() // 2,
                                                              self.new_dish_popup.height() // 2))
        self.new_dish_popup.show()

    def create_new_dish(self):
        cursor = self.db_connection.cursor()
        sql_insert = """ INSERT INTO dish(name, price, remarks)
                         VALUES(?,?,?)"""
        dish_name = self.new_dish_popup.dish_name.text()
        dish_price = self.new_dish_popup.dish_price.value()
        dish_remark = self.new_dish_popup.dish_remark.toPlainText()
        cursor.execute(sql_insert, (dish_name, dish_price, dish_remark))
        new_dish_id = cursor.lastrowid
        cursor.close()
        self.db_connection.commit()
        self.new_dish_popup.hide()

        # Update dish table and dish comboBox in UI
        self.dish_table_model.appendRow(self.create_table_row(new_dish_id, dish_name, dish_price, 0, dish_remark))

    def delete_dish(self, dish_id):
        cursor = self.db_connection.cursor()
        sql_delete = """ DELETE FROM dish WHERE id=?"""
        cursor.execute(sql_delete, tuple([dish_id]))
        cursor.close()
        self.db_connection.commit()

        # Update dish table and dish comboBox in UI
        index = self.dish_table_model.match(self.dish_table_model.index(0, 0), Qt.DisplayRole, str(dish_id))
        if index:
            self.dish_table_model.removeRow(index[0].row())

    def show_modify_dish_popup(self, dish_id):
        point = self.rect().center()
        global_point = self.mapToGlobal(point)
        self.modify_dish_popup.move(global_point - QtCore.QPoint(self.modify_dish_popup.width() // 2,
                                                                 self.modify_dish_popup.height() // 2))
        # Find the row and get necessary info
        index = self.dish_table_model.match(self.dish_table_model.index(0, 0), Qt.DisplayRole, str(dish_id))
        if index:
            row_idx = index[0]
            dish_name = self.dish_table_model.data(row_idx.siblingAtColumn(1))
            dish_price = self.dish_table_model.data(row_idx.siblingAtColumn(2))
            dish_remark = self.dish_table_model.data(row_idx.siblingAtColumn(5))
            self.modify_dish_popup.dish_name.setText(dish_name)
            self.modify_dish_popup.dish_price.setValue(float(dish_price))
            self.modify_dish_popup.dish_remark.setText(dish_remark)

            try:
                self.modify_dish_popup.modify_dish_btn.clicked.disconnect()
            except:
                pass
            self.modify_dish_popup.modify_dish_btn.clicked.connect(
                lambda: self.modify_dish(row_idx, dish_id)
            )
            self.modify_dish_popup.show()

    def modify_dish(self, row, dish_id):
        cursor = self.db_connection.cursor()
        sql_update = """ UPDATE dish
                         SET name = ?, price = ?, remarks = ?
                         WHERE id=?"""
        dish_name = self.modify_dish_popup.dish_name.text()
        dish_price = self.modify_dish_popup.dish_price.value()
        dish_remark = self.modify_dish_popup.dish_remark.toPlainText()
        cursor.execute(sql_update, (dish_name, dish_price, dish_remark, dish_id))
        cursor.close()
        self.db_connection.commit()
        self.modify_dish_popup.hide()

        # Update dish table and dish comboBox in UI
        sell_num = self.dish_table_model.data(row.siblingAtColumn(3))
        row_idx = row.row()
        self.dish_table_model.removeRow(row_idx)
        self.dish_table_model.insertRow(
            row_idx, self.create_table_row(dish_id, dish_name, dish_price, sell_num, dish_remark)
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
