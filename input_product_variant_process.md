1.import user access res.groups.csv
2. import product catagory
        without parent product.catagory.csv 
            table name 'product.category' fields name
        with parent product.catagory.csv 
            table name 'product.category' fields name,parent_id
3. import product attributes
    import product.attribute.csv
4. import product attribute values
    import product.attribute.value
5. import Product templates
    import product.template.csv
6. input product.template.attribute.line.csv
     

install module with RPC
    https://github.com/maclarensg/odoo_module_install_script


get database list with xmlrpc
    db_list=xmlrpc.client.ServerProxy(your_url +"/xmlrpc/db").list()
get table list with xmlrpc
    db_list=xmlrpc.client.ServerProxy(your_url +"/xmlrpc/db").list()



information for import
    https://www.youtube.com/watch?v=tWFZWw3uY4k
https://www.youtube.com/watch?v=goh6swXRYns


<h1>python direct import process with psycopg3</h1>

src_pool = ConnectionPool(kwargs=src_db_credentials)
dst_pool = ConnectionPool(kwargs=dst_db_credentials)

with src_pool.connection() as src_conn, dst_pool.connection() as dst_conn:
    dst_conn.execute("CREATE TABLE IF NOT EXISTS dst_table(col1 INT PRIMARY KEY, col2 TEXT)")
    with src_conn.cursor().copy(
        "COPY (SELECT col1,col2 FROM src_table WHERE col1=123) TO STDOUT (FORMAT BINARY)"
    ) as src_copy:
        with dst_conn.cursor().copy("COPY dst_table (col1,col2) FROM STDIN (FORMAT BINARY)") as dst_copy:
            for data in src_copy:
                dst_copy.write(data)
Using write() instead of write_row(), there will be no conversion of the data to and from Python objects.
FORMAT BINARY is more efficient than the implicit default FORMAT TEXT, but it can only be used if the tables have identical schema; see the docs for details.
We can skip on the cursors context blocks to avoid to drift too much on the right. Client-side cursors don't take resources to require an explicit finalization apart from normal GC.
Unrelated to the question, but the connection pool can take a kwargs argument to avoid the use of make_conninfo().


<h1>try it for psycopg2</h1>
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_SERIALIZABLE
import sys
import cStringIO

con = psycopg2.connect(database="xxxx", user="xxxx", password="xxxx", host="localhost")
cur = con.cursor()

input = cStringIO.StringIO()
cur.copy_expert('COPY (select * from Orders) TO STDOUT', input)
input.seek(0)
cur.copy_expert('COPY Orders2 FROM STDOUT', input)
con.commit()