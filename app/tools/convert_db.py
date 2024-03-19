import mysql.connector
import sqlite3
import json
import argparse
from decimal import Decimal

def fetch_data(table_spec, mysql_conn):
    table_name = table_spec["mysql_table"]
    cursor = mysql_conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    data = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    return data, columns

def create_table(table_spec, sqlite_conn, replace=False):
    table_name = table_spec["name"]
    columns = ", ".join([f"{col['name']} {col['type']}" for col in table_spec["columns"]])
    cursor = sqlite_conn.cursor()
    if replace:
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})")

def insert_data(table_spec, data, columns, sqlite_conn):
    table_name = table_spec["name"]
    sqlite_columns = [col["name"] for col in table_spec["columns"]]
    placeholders = ", ".join(["?"] * len(sqlite_columns))

    # Create a mapping of MySQL column names to their indexes
    column_indexes = {col: index for index, col in enumerate(columns)}

    cursor = sqlite_conn.cursor()
    for row in data:
        values = []
        for col in sqlite_columns:
            if col in column_indexes:
                value = row[column_indexes[col]]
                # Convert Decimal type to float
                if isinstance(value, Decimal):
                    value = float(value)
                values.append(value)
            else:
                values.append(None)

        try:
            cursor.execute(f"INSERT INTO {table_name} ({', '.join(sqlite_columns)}) VALUES ({placeholders})", values)
        except sqlite3.InterfaceError as e:
            print(f"Error inserting data: {e}")
            print(f"Offending data: {values}")
            break  # Or continue, depending on how you want to handle the error

    sqlite_conn.commit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert MySQL to SQLite3")
    parser.add_argument("--replace", action="store_true", help="Replace existing tables")
    args = parser.parse_args()

    with open("spec.json","r",encoding='utf8') as f:
        spec = json.load(f)

    mysql_conn = mysql.connector.connect(
        host=spec["mysql"]["host"],
        user=spec["mysql"]["user"],
        password=spec["mysql"]["password"],
        database=spec["mysql"]["database"]
    )

    sqlite_conn = sqlite3.connect(spec["sqlite"]["file"])

    for table_spec in spec["tables"]:
        data, columns = fetch_data(table_spec, mysql_conn)
        create_table(table_spec, sqlite_conn, replace=args.replace)
        insert_data(table_spec, data, columns, sqlite_conn)  # 修正された行

    mysql_conn.close()
    sqlite_conn.close()