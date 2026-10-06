import psycopg

conn = psycopg.connect("postgresql://CosmiCenter:testtest@localhost:5432/CosmiCenter")
cur = conn.cursor()
sql = "SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema') ORDER BY schemaname, tablename"
cur.execute(sql)
rows = cur.fetchall()
print(f"\nTotal tables: {len(rows)}\n")
for r in rows:
    print(f"  [{r[0]}] {r[1]}")
conn.close()
