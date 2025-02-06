# -*- coding: utf-8 -*-
from pathlib import Path
import csv,psycopg2
import io
import base64
import xmlrpc.client
from odoo import models, fields,api
import os,pandas as pd
import json
import numpy as np
import logging
from contextlib import suppress


_logger = logging.getLogger(__name__)



class ebiFields(models.Model):
    _name = 'ebi.fields'
    _description = 'fields to import'

    name = fields.Char("Name")
    selected = fields.Boolean("Update?",default='True')
    sequence = fields.Integer("Sequence" ,default=10)
    model_id = fields.Many2one('ebi.model', string='Model', required=True)
    source = fields.Char("Source")
    target = fields.Char("Target")
    data_type = fields.Char("Data Type")
    default_value=fields.Char('DefaultValue')
    # _sql_constraints = [("model_field_unique", "unique(name,model_id)", "field name per model must be unique!")]


class ebiModel(models.Model):
    _name = 'ebi.model'
    _description = 'Models to import'
    _order="selected desc, sequence"
    name = fields.Char("Name")
    instruction=fields.Char("Instruction")
    no_id=fields.Boolean("ID present?")
    selected=fields.Boolean("Update?" ,default='True')
    sequence=fields.Integer("Sequence" ,default=10)
    database_id = fields.Many2one('ebi.database', string='database', required=True)
    source = fields.Char("Source")
    target = fields.Char("target")
    # fixme apply this domain, domain="[('model_id', '=', model_id)]")
    field_ids = fields.One2many('ebi.fields','model_id', string='Fields')
    # _sql_constraints = [("db_model_unique", "unique(name,db_id)", "model name per database be unique!")]

    @api.onchange('sequence')
    def rearrenge_sequences(self):
        if len(self.ids)==1 : #new record has no ids so len==0
            res = self.env['ebi.model'].search([('sequence', '>', self.sequence - 1),('database_id.id', '=', self.database_id.ids[0]), ('id', "<>", self.ids[0])])
            seq = self.sequence
            if len(res) > 0:
                for rec in res:
                    seq = seq + 1
                    rec.sequence = seq

    def update_field_list(self):
        source_conn = self.database_id.create_connection("source")
        target_conn = self.database_id.create_connection("Target")
        source_cur = source_conn.cursor()
        target_cur = target_conn.cursor()
        target_cur.execute(
            f"SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name = '{self.source.replace('.', '_')}';")
        source_cur.execute(
            f"SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name = '{self.target.replace('.', '_')}';")
        source_fields = source_cur.fetchall()

        source_field_list = []
        for rec in source_fields:
            source_field_list.append(rec[0])


        target_fields = target_cur.fetchall()
        target_field_list = []
        for rec in target_fields:
            target_field_list.append(rec[0])
        common_fields = source_fields and target_fields
        existing_fields = list(rec.target for rec in self.field_ids)
        existing_fields = [field for field in existing_fields]
        fields2Insert = [field for field in target_fields if field[0] not in existing_fields]
        index = 1
        for field in fields2Insert:

            if field[0] in source_field_list:
                source=field[0]
            else:
                source="ebi_none_"+str(index)
                index=index+1


            if not field[2] == "YES":
                selected = True
            else:
                selected = False
            vals = {"name": field[0],
                    "source": source,
                    "target": field[0],
                    "selected": selected,
                    "data_type": field[1],
                    "model_id": self.id
                    }
            self.env['ebi.fields'].create(vals
                                          )

    def import_table_data(self):
        self.database_id.import_model_data(self.id)
    def import_table_data_with_related(self):
        self.database_id.import_related_model_data(self.id)


class ExportDatabase(models.Model):
    _name = 'ebi.database'
    _description = 'Export Data with External IDs (XML-RPC)'

    name = fields.Char("Name")
    source_address = fields.Char(string="Source Address", required=True, default="http://localhost:8069")
    source_database = fields.Char(string="Source Database", required=True)
    source_email = fields.Char(string="User Eamil", required=True)
    source_uid = fields.Integer(string="Source UID")
    source_pass = fields.Char(string="Source Password", required=True)

    target_address = fields.Char(string="Target Address", required=True, default="http://localhost:8000")
    target_database = fields.Char(string="Target Database", required=True, default='odoo18')
    target_email = fields.Char(string="Target Eamil", required=True)
    target_uid = fields.Integer(string="Target UID")
    target_pass = fields.Char(string="Target Password", required=True)

    source_pg_user = fields.Char(string="postgree User")
    source_pg_port = fields.Char(string="postgree port")
    source_pg_pass = fields.Char(string="Postgree Password", required=True)
    source_pg_host=fields.Char("Host")

    target_pg_user = fields.Char(string="postgree User")
    target_pg_port = fields.Char(string="postgree port")
    target_pg_pass = fields.Char(string="Postgree Password", required=True)
    target_pg_host=fields.Char("Host")

    def update_khan_store_bd_state(self):
        target_conn = self.create_connection("Target")
        target_cur = target_conn.cursor()
        target_cur.execute("DELETE FROM public.res_country_state    WHERE id =1461;")
        target_cur.execute("DELETE FROM public.ir_model_data WHERE id IN (20995);")
        target_cur.execute("UPDATE public.res_partner SET state_id = '1476'::integer WHERE state_id = 1455;")
        target_cur.execute("DELETE FROM public.res_country_state WHERE id IN (1455);")
        target_cur.execute("DELETE FROM public.ir_model_data WHERE id IN (20989);")
        target_cur.execute("UPDATE public.ir_model_data SET name = 'state_bd_chapai'::character varying WHERE id = 1941774;")
        target_cur.execute("UPDATE public.ir_config_parameter SET value = '2045-02-18 11:58:37'::text WHERE key = 'database.expiration_date';")
        target_cur.execute("UPDATE ir_model_data SET name = replace(name, 'bd_', 'state_bd_'),module='__export__' WHERE model='res.country.state' and name ILIKE 'bd_%'  and res_id>1410 and res_id< 1477;")

        target_conn.commit()

    def update_all_sequences(self):
        """Automatically updates all sequences in the PostgreSQL database."""
        dbname=self.target_database
        user=self.target_pg_user
        password=self.target_pg_pass
        host=self.target_pg_host
        port=self.target_pg_port
        query = """
            DO $$ 
            DECLARE r RECORD;
            BEGIN
                FOR r IN 
                    SELECT s.schemaname, s.sequencename, col.table_name, col.column_name
                    FROM pg_sequences s
                    JOIN information_schema.columns col 
                    ON col.column_default LIKE '%' || s.sequencename || '%'
                LOOP
                    EXECUTE format(
                        'SELECT setval(''%s'', COALESCE((SELECT MAX(%I) FROM %I), 1), false)', 
                        r.sequencename, r.column_name, r.table_name
                    );
                END LOOP;
            END $$;
            """

        try:
            # Connect to PostgreSQL
            conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
            cursor = conn.cursor()

            # Execute sequence update query
            cursor.execute(query)
            conn.commit()
            # ir attachment sequence reset
            sql="""SELECT setval(
                    pg_get_serial_sequence('ir_attachment', 'id'),
                    (SELECT COALESCE(MAX(id), 1) FROM ir_attachment),
                    false
                );"""
            cursor.execute(query)
            conn.commit()

            print("✅ Sequences updated successfully!")

        except Exception as e:
            print(f"❌ Error updating sequences: {e}")
            conn.rollback()

        finally:
            cursor.close()
            conn.close()


    def delete_previous_product_data(self):
        target_conn = self.create_connection("Target")
        target_cur = target_conn.cursor()
        sql_statements = [
            "DELETE FROM public.sale_order_template_option",
            "DELETE FROM public.loyalty_reward",
            "DELETE FROM public.sale_order_template_line",
            "DELETE FROM public.product_wishlist",
            "DELETE FROM public.mrp_bom_line",
            "DELETE FROM public.delivery_carrier",
            "DELETE FROM public.product_product",
            "DELETE FROM public.product_template",
            "DELETE FROM public.product_attribute_value",
            "DELETE FROM public.product_attribute",
            "DELETE FROM public.product_category",
        ]

        # Execute each SQL statement
        for statement in sql_statements:
            try:
                target_cur.execute(statement)
                print(f"Executed: {statement}")
                target_conn.commit()
            except Exception as e:
                target_conn.close()
                target_conn = self.create_connection("Target")
                target_cur = target_conn.cursor()
                print(f"An error occurred while executing: {statement}\nError: {e}")
                # Optionally, log the error to a file or logging system
                # logging.error(f"An error occurred while executing: {statement}\nError: {e}")

    def delete_previous_data(self):

        target_conn = self.create_connection("Target")
        target_cur = target_conn.cursor()
        sql_statements = [
            "DELETE FROM public.account_bank_statement_line",
            "ALTER SEQUENCE account_bank_statement_line_id_seq RESTART WITH 1",
            "DELETE FROM public.account_batch_payment",
            "ALTER SEQUENCE account_batch_payment_id_seq RESTART WITH 1",
            "DELETE FROM public.account_fiscal_position_tax",
            "ALTER SEQUENCE account_fiscal_position_tax_id_seq RESTART WITH 1",
            "DELETE FROM public.account_fiscal_position_tax_template",
            "ALTER SEQUENCE account_fiscal_position_tax_template_id_seq RESTART WITH 1",
            "DELETE FROM public.account_partial_reconcile",
            "ALTER SEQUENCE account_partial_reconcile_id_seq RESTART WITH 1",
            "DELETE FROM public.account_move",
            "ALTER SEQUENCE account_move_id_seq RESTART WITH 1",
            "DELETE FROM public.mail_message",
            "ALTER SEQUENCE mail_message_id_seq RESTART WITH 1",
            "DELETE FROM public.mrp_production",
            "ALTER SEQUENCE mrp_production_id_seq RESTART WITH 1",
            "DELETE FROM public.payment_transaction",
            "ALTER SEQUENCE payment_transaction_id_seq RESTART WITH 1",
            "DELETE FROM public.pos_order_line",
            "ALTER SEQUENCE pos_order_line_id_seq RESTART WITH 1",
            "DELETE FROM public.pos_payment",
            "ALTER SEQUENCE pos_payment_id_seq RESTART WITH 1",
            "DELETE FROM public.pos_order",
            "ALTER SEQUENCE pos_order_id_seq RESTART WITH 1",
            "DELETE FROM public.pos_session",
            "ALTER SEQUENCE pos_session_id_seq RESTART WITH 1",
            "DELETE FROM public.purchase_order",
            "ALTER SEQUENCE purchase_order_id_seq RESTART WITH 1",
            "DELETE FROM public.sale_order",
            "ALTER SEQUENCE sale_order_id_seq RESTART WITH 1",
            "DELETE FROM public.stock_move",
            "ALTER SEQUENCE stock_move_id_seq RESTART WITH 1",
            "DELETE FROM public.stock_picking",
            "ALTER SEQUENCE stock_picking_id_seq RESTART WITH 1",
            "DELETE FROM public.stock_quant",
            "ALTER SEQUENCE stock_quant_id_seq RESTART WITH 1",
            "DELETE FROM public.stock_valuation_layer",
            "ALTER SEQUENCE stock_valuation_layer_id_seq RESTART WITH 1",
            "DELETE FROM public.account_account_template",
            "ALTER SEQUENCE account_account_template_id_seq RESTART WITH 1",
            "DELETE FROM public.account_account_account_tag",
            "DELETE FROM public.account_account_tag_account_tax_repartition_line_rel",
            "DELETE FROM public.account_account_tag",
            "ALTER SEQUENCE account_account_tag_id_seq RESTART WITH 1",
            "DELETE FROM public.mail_followers",
            "ALTER SEQUENCE mail_followers_id_seq RESTART WITH 1",
            "UPDATE public.ir_sequence SET number_next=1 WHERE name='Sales Order'",
            # Delete attachments
            "DELETE FROM public.ir_attachment WHERE res_model IN ('account.move','sale.order')"
        ]

        # Execute each SQL statement
        for statement in sql_statements:
            try:
                target_cur.execute(statement)
                print(f"Executed: {statement}")
                target_conn.commit()
            except Exception as e:
                target_conn.close()
                target_conn = self.create_connection("Target")
                target_cur = target_conn.cursor()
                print(f"An error occurred while executing: {statement}\nError: {e}")
                # Optionally, log the error to a file or logging system
                # logging.error(f"An error occurred while executing: {statement}\nError: {e}")

    def update_table_list(self):
        source_conn = self.create_connection("source")
        target_conn = self.create_connection("Target")
        source_cur = source_conn.cursor()
        target_cur = target_conn.cursor()
        target_cur.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema';")
        source_cur.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema';")
        source_tables=source_cur.fetchall()
        target_tables=target_cur.fetchall()
        common_tables=source_tables and target_tables
        existing_tables=list(rec.source.replace('.','_') for rec in self.model_ids)
        existing_tables = [(table,) for table in existing_tables]
        table2Insert = [table for table in common_tables if table not in existing_tables]
        for table in table2Insert:
            self.env['ebi.model'].create({"name":table[0],"source":table[0],"target":table[0],"selected":False,"database_id":self.id})


    def get_default_downloads_path(self):
        """
        Gets the default downloads folder path in Windows.

        Returns:
          str: The path to the downloads folder.
        """
        try:
            return str(Path.home() / "Downloads")
        except:
            return None  # Handle potential errors

    download_path = fields.Char(string="download_path", required=True, default=get_default_downloads_path)
    export_type=fields.Selection([('download', 'Download Only'),
                                    ('direct', 'Direct DB to DB'),
                                    ('server', 'Export')],
                                   string='Backup Type')

    model_ids = fields.One2many('ebi.model','database_id', string='Model')
    # field_ids = fields.Many2many('ir.model.fields', string='Fields', domain="[('model_id', '=', model_id)]")
    # field_ids = fields.Many2many('ebi.fields', string='Fields', domain="[('model_id', '=', model_id)]")



    def direct_db_db_export(self):
        pass

    def test_source_connection(self):
        try:
            source_common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.source_address))
        except OSError as e:
            message=e
        else:
            try:
                user_id = source_common.authenticate(self.source_database, self.source_email, self.source_pass, {})
            except errno:
                message = "please Check address or Port"
            else:
                if user_id:
                    self.source_uid=user_id
                    message= "connection to source successful"
                else:message="Please check user_name or Password"
        self.source_connection=message

    def update_image_url(self):
        source_conn = self.create_connection("source")
        target_conn = self.create_connection("Target")
        source_cur = source_conn.cursor()
        target_cur = target_conn.cursor()
        target_cur.execute("SELECT id FROM product_product;")
        records = target_cur.fetchall()
        for rec in records:
            print(rec[0])
            target_cur.execute(f"update product_product set image_url=https://www.khan-store.com/web/image/product.product/{rec[0]}/image_1920 where id={rec[0]}")
        target_conn.commit()

    def export_csv(self):
        model_name = self.model_id.model


    def create_connection(self,db_type):
        if db_type=="source":
            database=self.source_database
            password = self.source_pg_pass
            host=self.source_pg_host
            user=self.source_pg_user
            port = self.source_pg_port
        else:
            database=self.target_database
            password = self.target_pg_pass
            host=self.target_pg_host
            user=self.target_pg_user
            port = self.target_pg_port
        conn=psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port)
        return conn

    def reset_external_id(self, source_model_name,target_model_name,source_cursor,target_cursor,target_connection):
        target_cursor.execute(f"delete from ir_model_data where model='{target_model_name.replace('_','.')}'")
        target_connection.commit()
        target_fields= ['res_id', 'module', 'model', 'name', 'noupdate']
        source_cursor.execute(f"select {', '.join(target_fields)} from ir_model_data where model='{source_model_name.replace('_','.')}'")
        source_ids=source_cursor.fetchall()
        placeholders = ', '.join(['%s'] * len(target_fields))
        for rec in source_ids:
            target_cursor.execute(
                f"INSERT INTO ir_model_data ({', '.join(target_fields)}) VALUES ({placeholders})", rec
            )
        target_connection.commit()

    def import_related_model_data(self,model_id):
        # Fetch the Odoo model based on the provided model_id
        model = self.env['ebi.model'].search([('id', '=', model_id)])

        imported_models=[]

        # Using "with" ensures that connections close automatically when done.
        with self.create_connection("source") as source_conn, self.create_connection("Target") as target_conn:
            with source_conn.cursor() as source_cur, target_conn.cursor() as target_cur:
                try:
                    target_cur.execute(f"SELECT name, model, relation  FROM ir_model_fields WHERE model = '{model.name.replace('_','.')}' AND relation IS NOT NULL;")
                    related_models = target_cur.fetchall()
                    for rec in related_models:
                        if  rec[2]not in imported_models:
                            # todo get model id to import data
                            model_to_import = self.env['ebi.model'].search([('target', '=', rec[2].replace('.','_'))])
                            self.import_model_data(model_to_import.id)
                            # mark the model imported
                            imported_models.append(rec[2])

                except Exception as e:
                    # If any error occurs, rollback the transaction to avoid partial inserts
                    target_conn.rollback()
                    _logger.error(f"Error during import: {e}")


    def import_model_data(self, model_id):
        """
        This function imports data from a source database table to a target table based on an Odoo model configuration.
        It handles:
        - Fetching source data
        - Mapping fields (including default values)
        - Handling data types (JSON, integer, etc.)
        - Upserting data into the target database
        - Resetting sequences for auto-increment fields
        """

        # Fetch the Odoo model based on the provided model_id
        model = self.env['ebi.model'].search([('id', '=', model_id)])

        # Using "with" ensures that connections close automatically when done.
        with self.create_connection("source") as source_conn, self.create_connection("Target") as target_conn:
            with source_conn.cursor() as source_cur, target_conn.cursor() as target_cur:
                try:
                    # Prepare table names by replacing dots with underscores
                    source_table = model.source.replace(".", '_')
                    target_table = model.target.replace(".", '_')

                    # Extract source and target field mappings based on user selection in the model
                    source_fields = [field.source for field in model.field_ids if field.source and field.selected]
                    target_fields = [field.target for field in model.field_ids if field.source and field.selected]

                    # Handling default values for fields with 'ebi_none' placeholder
                    for rec in source_fields:
                        if 'ebi_none' in rec:
                            idx = source_fields.index(rec)
                            default_value = [field.default_value for field in model.field_ids if
                                             field.source == rec and field.selected]
                            # Assigning the default value as a constant SQL expression
                            field_name = f"'{default_value[0]}' AS {target_fields[idx]}"
                            source_fields[idx] = field_name  # Replace 'ebi_none' with actual default value

                    source_cur.execute(f"SELECT {','.join(source_fields)} FROM {source_table}")
                    source_res = source_cur.fetchall()

                    # Convert the fetched data into a Pandas DataFrame for easy manipulation
                    df = pd.DataFrame(source_res, columns=target_fields)

                    # Retrieve column data types from the target table to ensure proper type conversion
                    target_cur.execute(
                        f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{target_table}';")
                    data_type = dict(target_cur.fetchall())

                    # Convert data types accordingly (important for database constraints)
                    for col, dtype in data_type.items():
                        if col in df.columns:
                            if dtype == "jsonb":
                                df[col] = df[col].apply(json.dumps)  # Convert Python objects to JSON strings
                            elif dtype == "integer":
                                # Convert NaN to None for PostgreSQL
                                df[col] = df[col].apply(lambda x: int(x) if pd.notnull(x) else None)

                    # Convert DataFrame to list of tuples while ensuring None for NaN values
                    data_with_null = [
                        tuple(None if pd.isna(value) else value for value in row)
                        for row in df.itertuples(index=False, name=None)
                    ]

                    # Using executemany() to perform bulk insertions
                    placeholders = ', '.join(['%s'] * len(target_fields))
                    if 'id' in target_fields:
                        query = f"""
                            INSERT INTO {target_table} ({', '.join(target_fields)}) 
                            VALUES ({placeholders}) 
                            ON CONFLICT (id) DO UPDATE SET 
                            {', '.join([f"{key} = EXCLUDED.{key}" for key in target_fields])}
                        """
                    else:query = f"""
                            INSERT INTO {target_table} ({', '.join(target_fields)}) 
                            VALUES ({placeholders}) 
                        """
                    target_cur.executemany(query, data_with_null)

                    # Reset sequence for auto-increment primary keys
                    if 'id' in target_fields:
                        target_cur.execute(
                            f"SELECT setval(pg_get_serial_sequence('{target_table}', 'id'), "
                            f"COALESCE((SELECT MAX(id) FROM {target_table}), 1, 1));"
                        )
                        # reset external Ids
                        self.reset_external_id( source_table, target_table, source_cur, target_cur,
                                          target_conn)
                        # Commit the transaction
                        target_conn.commit()

                except Exception as e:
                    # If any error occurs, rollback the transaction to avoid partial inserts
                    target_conn.rollback()
                    _logger.error(f"Error during import: {e}")

    def export_jsondata(self):
        for model in self.model_ids:
            if model.selected:
                self.import_model_data(model.id)



    def export_data(self):
        # IRMD for ir.model.data
        IRMD = {'source': {}, 'destination': {}}
        # IRMF for ir.model.field.data
        IRMF = {'source': {}, 'destination': {}}
        try:
            source_common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.source_address))
            source_object = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.source_address))
            uid = self.source_uid
            password = self.source_pass
            db = self.source_database

            target_common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.target_address))
            target_object = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.target_address))
            target_uid = self.target_uid
            target_password = self.target_pass
            target_db = self.target_database

            model_name = self.model_id.model
            fields_to_export = [field.source for field in self.field_ids]
            fields_to_import = [field.target for field in self.field_ids]

            limit = 1000
            offset = 0
            all_source_records = []

            target_connection = psycopg2.connect(
                host="localhost",
                database=self.target_database,
                user=self.source_pg_user,
                password=self.postgre_pass,
                port='5432'
            )
            target_connection.autocommit = True
            target_cr = target_connection.cursor()

            while True:
                res = source_object.execute_kw(db, uid, password, model_name, 'search_read',
                                               [[('id', '>', 0)]],
                                               {'fields': fields_to_export, 'order': 'id asc', 'limit': limit,
                                                'offset': offset})
                if not res:
                    break
                all_source_records.extend(res)
                offset += limit

            df = pd.DataFrame.from_dict(all_source_records)
            df = df.rename(columns={key: value for key, value in zip(fields_to_export, fields_to_import)})
            all_source_records = df.to_dict('records')

            if self.export_type == 'direct':
                # alter id sequence of the table
                target_cr.execute(f"ALTER SEQUENCE {self.model_id.model.replace('.', '_')}_id_seq OWNED BY NONE")
                self.insert_pandas_to_postgres(df, model_name, "localhost", self.target_database, self.source_pg_user, self.postgre_pass)


                for record in all_source_records:
                    targ = target_object.execute_kw(target_db, target_uid, target_password, model_name,
                                                    'search_read', [[('id', '=', record['id'])]])
                    if not targ:
                        targ_id = target_object.execute_kw(target_db, target_uid, target_password, model_name,
                                                           'create', [record])
                        # target_cr.execute(
                        #     f"UPDATE {self.model_id.model.replace('.', '_')} SET id = {record['id']} WHERE id = {targ_id}")
                    else:
                        target_object.execute_kw(target_db, target_uid, target_password, model_name,
                                                 'write', [[targ[0]['id']], record])
                # alter id sequence of the table
                target_cr.execute(
                    f"ALTER SEQUENCE {self.model_id.model.replace('.', '_')}_id_seq OWNED BY {self.model_id.model.replace('.', '_')}.id;")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if target_connection:
                target_cr.close()
                target_connection.close()
                print("Target PostgreSQL connection is closed")


            elif self.export_type == 'download':
                output = io.StringIO()
                writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_ALL)

                # Write header row
                header = []
                for field_name in fields_to_export:
                    header.append(field_name.replace("/", "."))
                writer.writerow(header)

                # Write data rows
                for record in all_source_records:
                    row = []
                    for field_name in fields_to_export:
                        if field_name == 'id':
                            row.append(record.get('id'))
                        elif field_name == '__export_id':
                            external_id = source_object.execute_kw(db, uid, password, model_name, 'get_external_id', [record.get('id')])
                            if external_id and record.get('id') in external_id:
                                row.append(external_id.get(record.get('id')))
                            else:
                                row.append(None)
                        elif "/" in field_name:
                            related_fields = field_name.split("/")
                            related_record_id = record.get(related_fields[0])
                            if related_record_id:
                                related_record = source_object.execute_kw(db, uid, password, related_fields[0], 'read', [related_record_id], {'fields':[related_fields[-1]]})
                                if related_record:
                                    row.append(related_record[0].get(related_fields[-1])) # Access the first element of the list because XMLRPC read returns a list
                                else:
                                    row.append(None)
                            else:
                                row.append(None)
                        else:
                            row.append(record.get(field_name))
                    writer.writerow(row)

                output.seek(0)
                filecontent = output.getvalue()
                output.close()

                filename = f'{model_name}.csv'
                filecontent = base64.b64encode(filecontent.encode())

                return {
                    'type': 'ir.actions.act_url',
                    'url': '/web/content/?model=export.data.wizard&id=%s&filename=%s&download=true' % (
                    self.id, filename),
                    'target': 'new',
                }
            elif self.export_type == 'server':
                filename = f'{model_name}.csv'
                save_path = self.download_path
                if not os.path.exists(save_path):
                    os.makedirs(save_path)
                full_path = os.path.join(save_path, filename)
                try:
                    with open(full_path, 'w', newline='', encoding='utf-8') as csvfile:
                        csvwriter = csv.writer(csvfile)
                        header = []
                        for field_name in fields_to_export:
                            header.append(field_name.replace("/", "."))
                        csvwriter.writerow(header)
                        for record in all_source_records:
                            row = []
                            for field_name in fields_to_export:
                                if field_name == 'id':
                                    row.append(record.get('id'))
                                elif field_name == '__export_id':
                                    external_id = source_object.execute_kw(db, uid, password, model_name, 'get_external_id', [record.get('id')])
                                    if external_id and record.get('id') in external_id:
                                        row.append(external_id.get(record.get('id')))
                                    else:
                                        row.append(None)
                                elif "/" in field_name:
                                    related_fields = field_name.split("/")
                                    related_record_id = record.get(related_fields[0])
                                    if related_record_id:
                                        related_record = source_object.execute_kw(db, uid, password, related_fields[0], 'read', [related_record_id], {'fields':[related_fields[-1]]})
                                        if related_record:
                                            row.append(related_record[0].get(related_fields[-1])) # Access the first element of the list because XMLRPC read returns a list
                                        else:
                                            row.append(None)
                                    else:
                                        row.append(None)
                                else:
                                    row.append(record.get(field_name))
                            csvwriter.writerow(row)
                    print(f"File saved to {full_path}")

                    #
                    # filecontent_b64=base64.b64encode(open(full_path, 'rb').read())
                    # attachment = self.env['ir.attachment'].create({
                    #     'name': filename,
                    #     'datas': filecontent_b64,
                    #     'type': 'binary',
                    #     'res_model': self._name,  # Current model
                    #     'res_id': self.id if self.id else None ,      # Current record ID (if applicable)
                    # })
                    # return {
                    #     'type': 'ir.ui.message',
                    #     'title': 'File Saved',
                    #     'message': f'File saved to {full_path} and also saved as attachment.',
                    #     'sticky': False
                    # }
                except Exception as e:
                    print(f"Error saving file: {e}")
                    return {
                        'type': 'ir.ui.message',
                        'title': 'Error',
                        'message': f'An error occurred during export: {e}',
                        'sticky': True
                    }

        # except Exception as e:
        #     print(f"Error during XML-RPC export: {e}")
            # return {
            #     'type': 'ir.ui.message',
            #     'title': 'Error',
            #     'message': f'An error occurred during export: {e}',
            #     'sticky': True
            # }



    def fetch_data_with_external_ids(self):
        """Fetches data with external IDs using XML-RPC and pagination."""
        source_object = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.source_address))
        uid = self.source_uid
        password = self.source_pass
        db = self.source_database
        model_name = self.model_id.model
        fields_to_export = []

        all_source_records = []
        limit=1000
        offset = 0
        while True:
            res = source_object.execute_kw(db, uid, password, model_name, 'search_read', [[('id', '>', 0)]],
                                           {'fields': fields_to_export, 'order': 'id asc', 'limit': limit,
                                            'offset': offset})
            if not res:
                break

            # Get IDs of fetched records for batch external ID retrieval
            record_ids = [record['id'] for record in res]

            # Batch retrieve external IDs for main records
            external_ids = source_object.execute_kw(db, uid, password, model_name, 'get_external_id', [record_ids])
            if external_ids:
                external_ids = {k: f"{model_name},{v}" for k, v in external_ids.items()}  # format external ids

            # Process related fields and fetch their external ids
            for record in res:
                record['__export_id'] = external_ids.get(record['id'])  # add external id to the record
                for field_name in fields_to_export:
                    if "/" in field_name:
                        related_model, related_field = field_name.split("/")
                        related_record_id = record.get(related_model)
                        if related_record_id:
                            related_external_ids = source_object.execute_kw(db, uid, password, related_model,
                                                                            'get_external_id', [related_record_id])
                            if related_external_ids:
                                related_external_ids = {k: f"{related_model},{v}" for k, v in
                                                        related_external_ids.items()}  # format external ids
                                record[field_name + '/__export_id'] = related_external_ids.get(related_record_id)
                            else:
                                record[field_name + '/__export_id'] = None
                        else:
                            record[field_name + '/__export_id'] = None
            all_source_records.extend(res)
            offset += limit

        return all_source_records

    def insert_pandas_to_postgres(self,df, table_name, host, database, user, password):
        """
        Inserts all records from a pandas DataFrame into a PostgreSQL table.

        Args:
          df: pandas DataFrame containing the data to be inserted.
          table_name: Name of the target table in the PostgreSQL database.
          host: Hostname or IP address of the PostgreSQL server.
          database: Name of the PostgreSQL database.
          user: Username for the PostgreSQL database.
          password: Password for the PostgreSQL database.

        Returns:
          None
        """

        try:
            conn = psycopg2.connect(
                host="localhost",
                database=database,
                user=self.source_pg_user,
                password=self.postgre_pass
            )
            cur = conn.cursor()

            # Construct the SQL INSERT statement dynamically
            columns = ', '.join(df.columns)
            placeholders = ', '.join(['%s'] * len(df.columns))  # Correctly create placeholders
            sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

            # Use psycopg2.extras.execute_values for efficient bulk insertion
            psycopg2.extras.execute_values(cur, sql, list(df.itertuples(index=False, name=None)))
            conn.commit()
            print("Data inserted successfully!")

        except (Exception, psycopg2.Error) as error:
            print(f"Error while inserting data to PostgreSQL: {error}")

        except (Exception, psycopg2.Error) as error:
            print(f"Error while inserting data to PostgreSQL: {error}")

        finally:
            # Close the communication with the PostgreSQL
            if conn:
                cur.close()
                conn.close()
                print("PostgreSQL connection is closed")
# cur.execute(sql)
# # Fetch all rows from the executed query
# rows = cursor.fetchall()
# for row in rows: # Assuming 'name' is a JSON field, parse it using json.loads
# id = row[0]
# name_json = json.loads(row[1])
# print(f"ID: {id}, Name: {name_json}"