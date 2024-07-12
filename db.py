# 本文件下所有函数都是封装sqlite数据库，为适配后续bot进一步功能而写。
# 以QQ号查询row_id后，查询有关数据。每个函数都有使用实例。


import sqlite3
from typing import List, Tuple, Any


class SQLiteDBHandler:
    def __init__(self, db_path: str):
        """初始化，连接到SQLite数据库"""
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()

    def fetch_data(self, query: str, params: Tuple[Any, ...] = ()) -> List[Tuple]:
        """执行SELECT查询并返回所有结果"""
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def execute_query(self, query: str, params: Tuple[Any, ...] = ()) -> None:
        """执行INSERT或UPDATE查询"""
        self.cursor.execute(query, params)
        self.connection.commit()

    def insert_data(self, table: str, column_values: dict) -> int:
        """向指定表插入数据，并返回新行的rowid"""
        columns = ', '.join(column_values.keys())
        placeholders = ', '.join(['?' for _ in column_values])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        self.execute_query(query, tuple(column_values.values()))
        return self.cursor.lastrowid  # 返回插入行的rowid

    def update_data(self, table: str, column: str, value: Any, row_id: int) -> None:
        """根据rowid和列名更新指定表的数据项"""
        query = f"UPDATE {table} SET {column} = ? WHERE rowid = ?"
        self.execute_query(query, (value, row_id))

    def delete_data(self, table: str, row_id: int) -> None:
        """根据rowid删除指定表的数据"""
        query = f"DELETE FROM {table} WHERE rowid = ?"
        self.execute_query(query, (row_id,))

    def get_data_by_rowid(self, table: str, column: str, row_id: int) -> Any:
        """根据rowid和列名查询指定表的数据项"""
        query = f"SELECT {column} FROM {table} WHERE rowid = ?"
        result = self.fetch_data(query, (row_id,))
        return result[0][0] if result else None

    def get_row_id_by_qq_id(self, table: str, qq_id: str) -> int:
        """根据qq_id查询指定表，返回对应的行ID (rowid)"""
        query = f"SELECT rowid FROM {table} WHERE qq_id = ?"
        result = self.fetch_data(query, (qq_id,))
        return result[0][0] if result else None

    def __del__(self):
        """确保关闭数据库连接"""
        self.connection.close()


# 使用例子
if __name__ == "__main__":
    db = SQLiteDBHandler('example.db')

    # 插入数据并获取rowid
    row_id = db.insert_data('some_table', {'name': 'Alice', 'age': 30})
    print(f"Inserted row ID: {row_id}")

    # 根据rowid和列名查询数据
    name = db.get_data_by_rowid('some_table', 'name', row_id)
    print("Name retrieved by row ID:", name)

    # 根据rowid和列名更新数据
    db.update_data('some_table', 'name', 'Bob', row_id)

    # 根据rowid查询更新后的名字
    updated_name = db.get_data_by_rowid('some_table', 'name', row_id)
    print("Updated Name:", updated_name)

    # 根据rowid删除数据
    db.delete_data('some_table', row_id)
