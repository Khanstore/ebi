# -*- coding: utf-8 -*-
from pathlib import Path
import csv,psycopg2
import io
import base64
import xmlrpc.client
from odoo import models, fields
import os,pandas as pd
import json
import numpy as np



class ebiFields(models.Model):
    _name = 'ebi.fields'
    _description = 'fields to import'

    name = fields.Char("Name")
    selected = fields.Boolean("Update?")
    sequence = fields.Integer("Sequence" ,default=10)
    model_id = fields.Many2one('ebi.model', string='Model', required=True)
    source = fields.Char("Source")
    target = fields.Char("Target")
    data_type = fields.Char("Data Type")
    default_value=fields.Char('DefaultValue')

class ebiModel(models.Model):
    _name = 'ebi.model'
    _description = 'Models to import'
    selected=fields.Boolean("Update?")
    sequence=fields.Integer("Sequence" ,default=10)
    name = fields.Char("Name")
    database_id = fields.Many2one('ebi.database', string='database', required=True)
    source = fields.Char("Source")
    target = fields.Char("target")
    # fixme apply this domain, domain="[('model_id', '=', model_id)]")
    field_ids = fields.One2many('ebi.fields','model_id', string='Fields')




class ExportDataWizard(models.Model):
    _name = 'ebi.database'
    _description = 'Export Data with External IDs (XML-RPC)'

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

    model_ids = fields.Many2many('ebi.model','ebi_database_model_rel','database_id','model_ids', string='Model')
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
                user_id = source_common.authenticate(self.source_database, self.source_username, self.source_pass, {})
            except errno:
                message = "please Check address or Port"
            else:
                if user_id:
                    self.source_uid=user_id
                    message= "connection to source successful"
                else:message="Please check user_name or Password"
        self.source_connection=message

    def export_csv(self):
        model_name = self.model_id.model

    import xmlrpc.client
    import psycopg2
    import pandas as pd
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

    def export_jsondata(self):
        source_conn = self.create_connection("source")
        target_conn = self.create_connection("Target")
        source_cur = source_conn.cursor()
        target_cur = target_conn.cursor()

        for model in self.model_ids:
            if model.selected:
                source_table = model.source.replace(".", '_')
                target_table = model.target.replace(".", '_')

                source_fields = [field.source for field in model.field_ids if field.source]
                target_fields = [field.target for field in model.field_ids if field.source]

                source_cur.execute(f"SELECT {','.join(source_fields)} FROM {source_table}")
                source_res = source_cur.fetchall()

                df = pd.DataFrame.from_dict(source_res)
                df = df.rename(columns={index: value for index, value in enumerate(target_fields)})

                target_cur.execute(
                    f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{target_table}';"
                )
                data_type = target_cur.fetchall()

                for line in data_type:
                    if line[1] == "jsonb" and line[0] in target_fields:
                        df[line[0]] = df[line[0]].apply(json.dumps)
                    elif line[1] == "integer" and line[0] in target_fields:
                        df[line[0]] = df[line[0]].apply(
                            lambda x: int(x) if pd.notnull(x) else None
                        ).astype(pd.Int64Dtype())

                fields_to_add = [field.target for field in model.field_ids if not field.source]
                value_to_add = [field.default_value for field in model.field_ids if not field.source]
                target_fields += fields_to_add

                for index, line in enumerate(fields_to_add):
                    df[line] = value_to_add[index]

                data = [
                    tuple(None if pd.isna(value) else value.item() if isinstance(value,
                                                                                 (np.integer, np.floating)) else value
                          for value in row)
                    for row in df.itertuples(index=False)
                ]

                target_cur.execute(f"SELECT id FROM {target_table};")
                existing_rec = target_cur.fetchall()
                existing_ids = [item[0] for item in existing_rec]

                for rec in data:
                    rec_id = rec[target_fields.index("id")]
                    update_str = ', '.join([f"{key} = %s" for key in target_fields])

                    if rec_id in existing_ids:
                        target_cur.execute(
                            f"UPDATE {target_table} SET {update_str} WHERE id=%s", (*rec, rec_id)
                        )
                    else:
                        placeholders = ', '.join(['%s'] * len(target_fields))
                        target_cur.execute(
                            f"INSERT INTO {target_table} ({', '.join(target_fields)}) VALUES ({placeholders})", rec
                        )

                target_conn.commit()

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