import re
from PyQt5.QtCore import QSortFilterProxyModel, QModelIndex, QDate


class TableFilter(QSortFilterProxyModel):

    def __init__(self, parent=None):
        super(TableFilter, self).__init__(parent)
        self.filter_column = {}
        self.filter_method = {}

    def set_col_number_filter(self, col, min_number, max_number):
        self.filter_method[col] = "Number"
        if col not in self.filter_column:
            self.filter_column[col] = (0, 0)
        min_num, max_num = self.filter_column[col]
        if min_number != -1:
            min_num = min_number
        if max_number != -1:
            max_num = max_number
        self.filter_column[col] = (min_num, max_num)
        self.invalidateFilter()

    def set_col_regex_filter(self, col, regex):
        self.filter_method[col] = "Regex"
        if isinstance(regex, str):
            regex = re.compile(regex)
        self.filter_column[col] = regex
        self.invalidateFilter()

    def set_col_date_filter(self, col, lower_date, higher_date):
        self.filter_method[col] = "Date"
        if col not in self.filter_column:
            self.filter_column[col] = (QDate.currentDate().addDays(-7), QDate.currentDate())
        low_date, high_date = self.filter_column[col]
        if isinstance(lower_date, QDate):
            low_date = lower_date
        if isinstance(higher_date, QDate):
            high_date = higher_date
        self.filter_column[col] = (low_date, high_date)
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        for col, item in self.filter_column.items():
            index = self.sourceModel().index(source_row, col, source_parent)
            if index.isValid():
                data = self.sourceModel().data(index)
                method = self.filter_method[col]
                if method == "Number" and not self.col_number_in_range(col, float(data)):
                    return False
                elif method == "Regex" and not self.col_regex(col, data):
                    return False
                elif method == "Date" and not self.col_date_in_range(col, QDate.fromString(data, "yyyy-MM-dd")):
                    return False

        return True

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        left_data = self.sourceModel().data(left)
        right_data = self.sourceModel().data(right)

        col = left.column()
        if col in self.filter_method:
            method = self.filter_method[col]
            if method == "Number":
                return float(left_data) < float(right_data)
            elif method == "Regex":
                return left_data < right_data
            elif method == "Date":
                left_data = QDate.fromString(left_data, "yyyy-MM-dd")
                right_data = QDate.fromString(right_data, "yyyy-MM-dd")
                return left_data < right_data
        return False

    def col_number_in_range(self, col, number):
        min_number, max_number = self.filter_column[col]
        if max_number > 0 and max_number > min_number:
            return min_number <= number <= max_number
        return True

    def col_date_in_range(self, col, date):
        min_date, max_date = self.filter_column[col]
        return min_date <= date <= max_date

    def col_regex(self, col, text):
        regex = self.filter_column[col]
        return False if regex.search(text) is None else True
