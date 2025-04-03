import pandas as pd
import mysql.connector

# Database Connection
conn = mysql.connector.connect(
    host="localhost",       # e.g., "localhost"
    user="root",   # e.g., "root"
    password="12345678",
    database="data_s",
    autocommit=False  # Disable autocommit for performance boost
)
cursor = conn.cursor()

# Load Excel File
file_path = "Structured_data.xlsx"  # Change to your actual file path
df = pd.read_excel(file_path, sheet_name=0)

# Get Table Name from File Name (Removing Extension)
table_name = file_path.split("/")[-1].split(".")[0]

# Replace NaN with empty string or None (for NULL in MySQL)
df = df.where(pd.notna(df), None)  # Replaces NaN with NULL
df = df.fillna("") 

# Dynamically Generate SQL for Table Creation
columns = df.columns
column_definitions = ", ".join([f"`{col}` TEXT" for col in columns])  # Assign TEXT data type

create_table_query = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({column_definitions})"
cursor.execute(create_table_query)
print(f"Table `{table_name}` created successfully!")

# Prepare Insert Query Dynamically
placeholders = ", ".join(["%s"] * len(columns))
insert_query = f"INSERT INTO `{table_name}` ({', '.join([f'`{col}`' for col in columns])}) VALUES ({placeholders})"

# Convert DataFrame Rows to Tuples
data = [tuple(row) for row in df.itertuples(index=False, name=None)]

# **Insert Data in Chunks** to Avoid Overloading MySQL
batch_size = 1000  # Adjust batch size based on performance
for i in range(0, len(data), batch_size):
    batch = data[i:i + batch_size]
    cursor.executemany(insert_query, batch)
    conn.commit()  # Commit after every batch
    print(f"Inserted {i + len(batch)} rows so far...")

print(f"{len(data)} rows inserted into `{table_name}` successfully!")

# Close Connection
cursor.close()
conn.close()
