import csv
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Union

import sys
from PyQt5 import QtCore, uic
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis
from PyQt5.QtCore import Qt, QDate, QDateTime
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QPainter, QCursor
from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget, QFileDialog, QMessageBox, QTableWidgetItem, QSpinBox,
                             QHeaderView, QToolTip)

from filters import TableFilter
from models import DishTableDelegateCell, DishDataTableDelegateCell


def str_type(text):
    try:
        int(text)
        return int
    except ValueError:
        try:
            float(text)
            return float
        except ValueError:
            try:
                complex(text)
                return complex
            except ValueError:
                return str


def create_dish_data_table_row(dish_id: int, date: str, dish_name: str, dish_price: float,
                               sell_num: Union[int, str], choose=0):
    # ID
    row = [QStandardItem(str(dish_id))]
    # Data Date
    date_item = QStandardItem(date)
    date_item.setTextAlignment(Qt.AlignCenter)
    row.append(date_item)
    # Dish Name
    name_item = QStandardItem(dish_name)
    name_item.setTextAlignment(Qt.AlignCenter)
    row.append(name_item)
    # Dish Price
    price_item = QStandardItem("{:.2f}".format(dish_price if dish_price else -0.01))
    price_item.setTextAlignment(Qt.AlignCenter)
    row.append(price_item)
    # Dish Sell Number on date
    sell_item = QStandardItem(str(sell_num))
    sell_item.setTextAlignment(Qt.AlignCenter)
    row.append(sell_item)
    # Choose
    row.append(QStandardItem(str(choose)))
    return row


def create_dish_table_row(dish_id: int, dish_name: str, dish_price: float, sell_num: Union[int, str], dish_remark: str):
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
    sell_item = QStandardItem(str(sell_num))
    sell_item.setTextAlignment(Qt.AlignCenter)
    row.append(sell_item)
    # Dish Manipulation Button
    row.append(None)
    # Dish Remark
    row.append(QStandardItem(dish_remark))
    return row


class MainWindow(QMainWindow):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    MAIN_UI_FILE = os.path.join(BASE_DIR, "main.ui")
    NEW_DISH_POPUP_UI_FILE = os.path.join(BASE_DIR, "new_dish_popup.ui")
    NEW_DISH_MULTI_POPUP_UI_FILE = os.path.join(BASE_DIR, "new_dish_multi_popup.ui")
    NEW_DISH_DATA_POPUP_UI_FILE = os.path.join(BASE_DIR, "new_dish_data_popup.ui")
    MODIFY_DISH_POPUP_UI_FILE = os.path.join(BASE_DIR, "modify_dish_popup.ui")
    DB_FILE = os.path.join(BASE_DIR, "restaurant.db")

    def __init__(self):
        super(MainWindow, self).__init__()
        # Initialize variable
        self.db_connection = None
        self.new_dish_popup = QWidget()
        self.new_dish_multi_popup = QWidget()
        self.new_dish_data_popup = QWidget()
        self.modify_dish_popup = QWidget()
        self.dish_table_model = QStandardItemModel(0, 6)
        self.dish_table_proxy = TableFilter()
        self.dish_data_table_model = QStandardItemModel(0, 6)
        self.dish_data_table_proxy = TableFilter()
        self.graph_chart = None
        self.graph_line_series = {}

        # Load UI designs
        uic.loadUi(self.MAIN_UI_FILE, self)
        uic.loadUi(self.NEW_DISH_POPUP_UI_FILE, self.new_dish_popup)
        uic.loadUi(self.NEW_DISH_MULTI_POPUP_UI_FILE, self.new_dish_multi_popup)
        uic.loadUi(self.NEW_DISH_DATA_POPUP_UI_FILE, self.new_dish_data_popup)
        uic.loadUi(self.MODIFY_DISH_POPUP_UI_FILE, self.modify_dish_popup)
        self.init_dish_table()
        self.init_dish_data_table()
        self.init_graph()

        # Connect to database
        self.init_db_connection()

        # MainWindow Bind action triggers
        self.action_new_dish.triggered.connect(self.show_new_dish_popup)
        self.action_new_dish_multi.triggered.connect(self.show_new_dish_multi_popup)
        self.action_new_data_multi.triggered.connect(lambda: self.modify_new_dish_data_popup_table(show=True))
        self.tabWidget.currentChanged.connect(self.update_graph)

        # Dish Table filter bind
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

        # Dish Data Table filter bind
        self.lower_data_dateEdit.dateChanged.connect(
            lambda date, col_idx=1: self.dish_data_table_proxy.set_col_date_filter(col_idx, date, -1)
        )
        self.higher_data_dateEdit.dateChanged.connect(
            lambda date, col_idx=1: self.dish_data_table_proxy.set_col_date_filter(col_idx, -1, date)
        )
        self.data_lineEdit.textChanged.connect(
            lambda text, col_idx=2: self.dish_data_table_proxy.set_col_regex_filter(col_idx, text)
        )
        self.lower_data_doubleSpinBox.valueChanged.connect(
            lambda value, col_idx=3: self.dish_data_table_proxy.set_col_number_filter(col_idx, value, -1)
        )
        self.higher_data_doubleSpinBox.valueChanged.connect(
            lambda value, col_idx=3: self.dish_data_table_proxy.set_col_number_filter(col_idx, -1, value)
        )
        self.lower_data_spinBox.valueChanged.connect(
            lambda value, col_idx=4: self.dish_data_table_proxy.set_col_number_filter(col_idx, value, -1)
        )
        self.higher_data_spinBox.valueChanged.connect(
            lambda value, col_idx=4: self.dish_data_table_proxy.set_col_number_filter(col_idx, -1, value)
        )
        self.data_all_check_checkBox.stateChanged.connect(
            lambda state, col_idx=5: self.data_table_check_state(state, col_idx)
        )
        self.dish_data_table_model.itemChanged.connect(self.update_series)

        # Popup bind action triggers
        self.new_dish_popup.create_new_dish_btn.clicked.connect(self.create_new_dish)
        self.new_dish_multi_popup.pushButton_ok.clicked.connect(self.create_new_dish_multi)
        self.new_dish_data_popup.dateEdit.dateChanged.connect(self.modify_new_dish_data_popup_table)
        self.new_dish_data_popup.pushButton_ok.clicked.connect(self.create_new_dish_data)

        # Get current dishes
        self.load_dish_table()
        self.load_dish_data_table()
        self.new_dish_data_popup.dateEdit.setDate(QtCore.QDate.currentDate())

    def init_dish_table(self):
        self.dish_tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Set Header data and stretch
        for col, col_name in enumerate(["ID", "菜品", "价格", "近7天总售出", "操作", "备注"]):
            self.dish_table_model.setHeaderData(col, Qt.Horizontal, col_name, Qt.DisplayRole)
        self.dish_table_proxy.setSourceModel(self.dish_table_model)
        self.dish_tableView.setModel(self.dish_table_proxy)
        self.dish_tableView.setColumnHidden(0, True)
        for (col, method) in [(1, "Regex"), (2, "Number"), (3, "Number"), (5, "Regex")]:
            self.dish_table_proxy.filter_method[col] = method

    def init_dish_data_table(self):
        self.data_tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for col, col_name in enumerate(["Dish_ID", "日期", "菜品", "价格", "售出", "选择"]):
            self.dish_data_table_model.setHeaderData(col, Qt.Horizontal, col_name, Qt.DisplayRole)
        self.dish_data_table_proxy.setSourceModel(self.dish_data_table_model)
        self.data_tableView.setModel(self.dish_data_table_proxy)
        self.data_tableView.setColumnHidden(0, True)
        for (col, method) in [(1, "Date"), (2, "Regex"), (3, "Number"), (4, "Number")]:
            self.dish_data_table_proxy.filter_method[col] = method

    def init_graph(self):
        self.graph_chart = QChart(title="售出图")
        self.graph_chart.legend().setVisible(True)
        self.graph_chart.setAcceptHoverEvents(True)

        graph_view = QChartView(self.graph_chart)
        graph_view.setRenderHint(QPainter.Antialiasing)
        self.gridLayout_5.addWidget(graph_view)

    def init_db_connection(self):
        self.db_connection = sqlite3.connect(self.DB_FILE)
        cursor = self.db_connection.cursor()
        # check create table if not exist
        sql_create_dish_table = """ CREATE TABLE IF NOT EXISTS dish (
                                        id integer PRIMARY KEY,
                                        name text NOT NULL,
                                        price numeric Not NULL,
                                        remarks text,
                                        UNIQUE (name, price)
                                    ); """
        sql_create_dish_data_table = """ CREATE TABLE IF NOT EXISTS dish_data (
                                            dish_id integer NOT NULL REFERENCES dish(id) ON DELETE CASCADE,
                                            date date,
                                            sell_num integer DEFAULT 0,
                                            PRIMARY KEY (dish_id, date),
                                            CONSTRAINT dish_fk 
                                                FOREIGN KEY (dish_id) 
                                                REFERENCES dish (id) ON DELETE CASCADE 
                                        ); """
        sql_trigger = """
            CREATE TRIGGER IF NOT EXISTS place_holder_data
            AFTER INSERT ON dish
            BEGIN
                INSERT INTO dish_data (dish_id, date, sell_num) VALUES(new.id, null, 0);
            END;
        """
        cursor.execute(sql_create_dish_table)
        cursor.execute(sql_create_dish_data_table)
        cursor.execute("PRAGMA FOREIGN_KEYS = on")
        cursor.execute(sql_trigger)

        cursor.close()

    def load_dish_table(self):
        today = datetime.today()
        sql_select_query = """
            SELECT dish.id, dish.name, dish.price, COALESCE(SUM(dish_data.sell_num), 0), dish.remarks
            FROM dish LEFT JOIN dish_data 
            ON dish.id = dish_data.dish_id
            WHERE dish_data.date IS NULL OR dish_data.date BETWEEN date('{}') and date('{}')
            GROUP BY dish.id
            ORDER BY dish.name, dish.price;""".format(
            (today - timedelta(days=7)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
        )
        cursor = self.db_connection.cursor()
        cursor.execute(sql_select_query)
        records = cursor.fetchall()
        for row_idx, record in enumerate(records):
            self.dish_table_model.appendRow(create_dish_table_row(*record))
        cursor.close()
        self.dish_tableView.setItemDelegateForColumn(
            4, DishTableDelegateCell(self.show_modify_dish_popup, self.delete_dish, self.dish_tableView))

    def load_dish_data_table(self):
        sql_select_query = """
            SELECT dish_data.dish_id, dish_data.date, dish.name, dish.price, dish_data.sell_num
            FROM dish_data LEFT JOIN dish  
            ON dish_data.dish_id = dish.id
            WHERE dish_data.date IS NOT NULL
            ORDER BY dish_data.date DESC, dish.name, dish.price, dish_data.sell_num;"""
        cursor = self.db_connection.cursor()
        cursor.execute(sql_select_query)
        records = cursor.fetchall()
        for row_idx, record in enumerate(records):
            self.dish_data_table_model.appendRow(create_dish_data_table_row(*record))
        cursor.close()
        self.lower_data_dateEdit.setDate(QDate.currentDate().addDays(-7))
        self.higher_data_dateEdit.setDate(QDate.currentDate())
        self.data_tableView.setItemDelegateForColumn(5, DishDataTableDelegateCell(self.data_tableView))

    def data_table_check_state(self, state, col):
        for row in range(self.dish_data_table_proxy.rowCount()):
            index = self.dish_data_table_proxy.mapToSource(self.dish_data_table_proxy.index(row, col))
            if index.isValid():
                self.dish_data_table_model.setData(index, str(state), Qt.DisplayRole)

    def show_new_dish_popup(self):
        # Move popup to center
        point = self.rect().center()
        global_point = self.mapToGlobal(point)
        self.new_dish_popup.move(global_point - QtCore.QPoint(self.new_dish_popup.width() // 2,
                                                              self.new_dish_popup.height() // 2))
        self.new_dish_popup.show()

    def show_new_dish_multi_popup(self):
        file_name = QFileDialog().getOpenFileName(None, "选择文件", "", self.tr("CSV文件 (*.csv)"))[0]
        self.new_dish_multi_popup.tableWidget.setRowCount(0)
        if file_name:
            with open(file_name, "r") as file:
                csv_reader = csv.reader(file, delimiter=",")
                for idx, row_data in enumerate(csv_reader):
                    if len(row_data) == 2:
                        name, price = row_data
                        remark = ""
                    elif len(row_data) == 3:
                        name, price, remark = row_data
                    else:
                        QMessageBox.warning(
                            self, "格式错误",
                            self.tr('格式为"菜品 价格"或者"菜品 价格 备注"\n第{}行输入有误'.format(idx))
                        )
                        return
                    self.new_dish_multi_popup.tableWidget.insertRow(self.new_dish_multi_popup.tableWidget.rowCount())
                    self.new_dish_multi_popup.tableWidget.setItem(idx, 0, QTableWidgetItem(name))
                    price_type = str_type(price)
                    if price_type == str or (isinstance(price_type, (float, int)) and float(price) < 0):
                        QMessageBox.warning(self, "格式错误", self.tr('第{}行价格输入有误'.format(idx+1)))
                        return
                    self.new_dish_multi_popup.tableWidget.setItem(idx, 1,
                                                                  QTableWidgetItem("{:.2f}".format(float(price))))
                    self.new_dish_multi_popup.tableWidget.setItem(idx, 2, QTableWidgetItem(remark))
            self.new_dish_multi_popup.show()

    def modify_new_dish_data_popup_table(self, *args, show=False):
        sql_select_query = """
                    SELECT id, name, price, dish_data.sell_num
                    FROM dish LEFT JOIN dish_data
                    ON dish.id=dish_data.dish_id
                    WHERE dish_data.date IS NULL OR dish_data.date = date('{}')
                    GROUP BY id, name, price
                    ORDER BY dish.name, dish.price;""".format(
            self.new_dish_data_popup.dateEdit.date().toString("yyyy-MM-dd"))

        cursor = self.db_connection.cursor()
        cursor.execute(sql_select_query)
        records = cursor.fetchall()
        self.new_dish_data_popup.tableWidget.setRowCount(len(records))
        self.new_dish_data_popup.tableWidget.setColumnHidden(0, True)
        for row_idx, record in enumerate(records):
            dish_id, name, price, sell_num = record
            self.new_dish_data_popup.tableWidget.setItem(row_idx, 0, QTableWidgetItem(str(dish_id)))
            self.new_dish_data_popup.tableWidget.setItem(row_idx, 1, QTableWidgetItem(name))
            self.new_dish_data_popup.tableWidget.setItem(row_idx, 2, QTableWidgetItem("{:.2f}".format(price)))
            spin_box = QSpinBox()
            spin_box.setMaximum(9999)
            spin_box.setValue(sell_num)
            self.new_dish_data_popup.tableWidget.setCellWidget(row_idx, 3, spin_box)
        cursor.close()
        if show:
            self.new_dish_data_popup.show()

    def create_new_dish(self):
        cursor = self.db_connection.cursor()
        sql_insert = """ INSERT INTO dish(name, price, remarks)
                         VALUES(?,?,?)"""
        dish_name = self.new_dish_popup.dish_name.text()
        dish_price = self.new_dish_popup.dish_price.value()
        dish_remark = self.new_dish_popup.dish_remark.toPlainText()
        try:
            cursor.execute(sql_insert, (dish_name, dish_price, dish_remark))
            new_dish_id = cursor.lastrowid
            cursor.close()
            self.db_connection.commit()
            # Update dish table and dish comboBox in UI
            self.dish_table_model.appendRow(create_dish_table_row(new_dish_id, dish_name, dish_price, 0, dish_remark))
            self.new_dish_popup.hide()
        except sqlite3.Error:
            cursor.close()
            QMessageBox.warning(self, "菜品价格重复", self.tr('菜品价格组合重复，请检查'))

    def create_new_dish_multi(self):
        cursor = self.db_connection.cursor()
        sql_insert = """ 
            INSERT INTO dish(name, price, remarks)     
            VALUES (?, ?, ?)"""
        for row in range(self.new_dish_multi_popup.tableWidget.rowCount()):
            dish_name = self.new_dish_multi_popup.tableWidget.item(row, 0).text()
            dish_price = float(self.new_dish_multi_popup.tableWidget.item(row, 1).text())
            dish_remark = self.new_dish_multi_popup.tableWidget.item(row, 2).text()
            try:
                cursor.execute(sql_insert, (dish_name, dish_price, dish_remark))
                new_dish_id = cursor.lastrowid
                self.dish_table_model.appendRow(create_dish_table_row(
                    new_dish_id, dish_name, dish_price, 0, dish_remark))
            except sqlite3.Error:
                cursor.close()
                QMessageBox.warning(self, "菜品价格重复", self.tr(
                    '前{}行已插入。\n第{}行菜品价格组合重复，请检查'.format(row, row+1)))
                return
        cursor.close()
        self.db_connection.commit()
        self.new_dish_multi_popup.hide()

    def create_new_dish_data(self):
        current_date = self.new_dish_data_popup.dateEdit.date().toString("yyyy-MM-dd")
        table_filter = TableFilter()
        table_filter.setSourceModel(self.dish_data_table_model)
        table_filter.set_col_regex_filter(1, current_date)
        for row in range(table_filter.rowCount()):
            index = table_filter.mapToSource(table_filter.index(0, 1))
            if index.isValid():
                self.dish_data_table_model.removeRow(index.row())
        del table_filter
        cursor = self.db_connection.cursor()
        sql_insert = """ 
            INSERT OR REPLACE INTO dish_data(dish_id, date, sell_num)     
            VALUES (?, ?, ?)"""
        for row in range(self.new_dish_data_popup.tableWidget.rowCount()):
            dish_id = int(self.new_dish_data_popup.tableWidget.item(row, 0).text())
            name = self.new_dish_data_popup.tableWidget.item(row, 1).text()
            price = float(self.new_dish_data_popup.tableWidget.item(row, 2).text())
            sell_num = self.new_dish_data_popup.tableWidget.cellWidget(row, 3).value()
            cursor.execute(sql_insert, (dish_id, current_date, sell_num))
            self.dish_data_table_model.appendRow(create_dish_data_table_row(
                dish_id, current_date, name, price, sell_num))
        cursor.close()
        self.db_connection.commit()
        self.new_dish_data_popup.hide()

    def delete_dish(self, dish_id):
        cursor = self.db_connection.cursor()
        sql_delete = """ DELETE FROM dish WHERE id=?"""
        cursor.execute(sql_delete, tuple([dish_id]))
        cursor.close()
        self.db_connection.commit()

        # Update dish table and dish comboBox in UI
        for row in self.dish_data_table_model.findItems(str(dish_id)):
            index = row.index()
            if index.isValid():
                self.dish_data_table_model.removeRow(index.row())

        for row in self.dish_table_model.findItems(str(dish_id)):
            index = row.index()
            if index.isValid():
                self.dish_table_model.removeRow(index.row())

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
            except TypeError:
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
        old_name = self.dish_table_model.data(row.siblingAtColumn(1))
        old_price = self.dish_table_model.data(row.siblingAtColumn(2))
        sell_num = self.dish_table_model.data(row.siblingAtColumn(3))
        row_idx = row.row()
        self.dish_table_model.removeRow(row_idx)
        self.dish_table_model.insertRow(
            row_idx, create_dish_table_row(dish_id, dish_name, dish_price, sell_num, dish_remark)
        )

        for row in self.dish_data_table_model.findItems(str(dish_id)):
            index = row.index()
            if index.isValid():
                self.dish_data_table_model.setData(index.siblingAtColumn(2), dish_name)
                self.dish_data_table_model.setData(index.siblingAtColumn(3), "{:.2f}".format(dish_price))
        old_key = old_name + '(' + old_price + ')'
        if old_key in self.graph_line_series:
            self.graph_line_series[dish_name + '(' + str(dish_price) + ')'] = self.graph_line_series[old_key]
            del self.graph_line_series[old_key]

    def update_series(self, item: QStandardItem):
        def get_index(data_point, sorted_list):
            start = 0
            end = len(sorted_list) - 1
            if end < start:
                return 0
            mid = (end - start) // 2
            while end - start > 1:
                if data_point < sorted_list[mid]:
                    end = mid
                else:
                    start = mid
                mid = (end - start) // 2
            if sorted_list[start] > data_point:
                return start
            elif sorted_list[end] < data_point:
                return end
            else:
                return start + 1

        if item.column() == 5:  # check for checkbox column
            item_idx = item.index()
            date = self.dish_data_table_model.data(item_idx.siblingAtColumn(1))
            dish_name = self.dish_data_table_model.data(item_idx.siblingAtColumn(2))
            dish_price = self.dish_data_table_model.data(item_idx.siblingAtColumn(3))
            sell_num = self.dish_data_table_model.data(item_idx.siblingAtColumn(4))
            series_name = dish_name + "(" + dish_price + ")"
            if series_name not in self.graph_line_series:
                self.graph_line_series[series_name] = []

            point = (QDateTime(QDate.fromString(date, "yyyy-MM-dd")).toMSecsSinceEpoch(), int(sell_num))
            if int(item.text()) == 0:
                try:
                    self.graph_line_series[series_name].remove(point)
                    if len(self.graph_line_series[series_name]) == 0:
                        del self.graph_line_series[series_name]
                except ValueError:
                    pass
            else:
                if point not in self.graph_line_series[series_name]:
                    target_idx = get_index(point, self.graph_line_series[series_name])
                    self.graph_line_series[series_name].insert(target_idx, point)

    def update_graph(self, index):
        if index == 2:
            self.graph_chart.removeAllSeries()

            axis_x = QDateTimeAxis()
            axis_x.setFormat("yyyy年MM月dd日")
            axis_x.setTitleText("日期")
            if self.graph_chart.axisX():
                self.graph_chart.removeAxis(self.graph_chart.axisX())
            self.graph_chart.addAxis(axis_x, Qt.AlignBottom)

            axis_y = QValueAxis()
            axis_y.setLabelFormat("%i")
            axis_y.setTitleText("售出量")
            if self.graph_chart.axisY():
                self.graph_chart.removeAxis(self.graph_chart.axisY())
            self.graph_chart.addAxis(axis_y, Qt.AlignLeft)

            max_num = 0
            min_time = QDateTime.currentDateTime().toMSecsSinceEpoch()
            max_time = 0
            for key, data in self.graph_line_series.items():
                series = QLineSeries()
                series.setName(key)
                series.setPointsVisible(True)
                series.hovered.connect(self.graph_tooltip)
                for point in data:
                    series.append(*point)
                    max_num = max(max_num, point[1])
                    max_time = max(max_time, point[0])
                    min_time = min(min_time, point[0])
                self.graph_chart.addSeries(series)
                series.attachAxis(axis_x)
                series.attachAxis(axis_y)
            axis_y.setMax(max_num+1)
            axis_y.setMin(0)
            axis_x.setMax(QDateTime.fromMSecsSinceEpoch(max_time))
            axis_x.setMin(QDateTime.fromMSecsSinceEpoch(min_time))

    def graph_tooltip(self, point, state):
        series = self.sender()
        if state:
            QToolTip.showText(QCursor.pos(), "{}\n日期: {}\n售出: {}".format(
                series.name(), QDateTime.fromMSecsSinceEpoch(point.x()).toString("yyyy年MM月dd日"), round(point.y())))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
