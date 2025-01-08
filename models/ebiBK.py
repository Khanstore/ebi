# -*- coding: utf-8 -*-
import csv,psycopg2
import io
import base64
import xmlrpc.client
from odoo import models, fields
import os

class ExportDataWizard(models.TransientModel):
    _name = 'export.data.wizard'
    _description = 'Export Data with External IDs (XML-RPC)'

    source_address = fields.Char(string="Source Address", required=True, default="http://localhost:8069")
    source_database = fields.Char(string="Source Database", required=True)
    source_email = fields.Char(string="User Eamil", required=True)
    server_path = fields.Char(string="server_path", required=True)
    source_uid = fields.Integer(string="Source UID")
    source_pass = fields.Char(string="Source Password", required=True)

    target_address = fields.Char(string="Target Address", required=True, default="http://localhost:8000")
    target_database = fields.Char(string="Target Database", required=True, default='odoo18')
    target_email = fields.Char(string="Target Eamil", required=True)
    target_uid = fields.Integer(string="Target UID")
    target_pass = fields.Char(string="Target Password", required=True)

    postgre_uid = fields.Char(string="postgree User")
    postgre_pass = fields.Char(string="Postgree Password", required=True)

    export_type=fields.Selection([('download', 'Download Only'),
                                    ('direct', 'Direct DB to DB'),
                                    ('server', 'Export')],
                                   string='Backup Type')

    model_id = fields.Many2one('ir.model', string='Model', required=True)
    field_ids = fields.Many2many('ir.model.fields', string='Fields', domain="[('model_id', '=', model_id)]")

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

    def export_data(self):
        # Establish connections (combine and improve error handling)
        try:
            source_connection = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.source_address))
            source_object = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.source_address))
            target_connection = psycopg2.connect(
                host="localhost",
                database=self.target_database,
                user=self.postgre_uid,
                password=self.postgre_pass,
                port='5432'
            )
            target_connection.autocommit = True
            target_cr = target_connection.cursor()
        except Exception as e:
            print(f"Error connecting to servers: {e}")
            return

        # Fetch data using a single RPC call (assuming limit is large enough)
        model_name = self.model_id.model
        fields_to_export = [field.name for field in self.field_ids]
        all_source_records = source_object.execute_kw(self.source_database, self.source_uid, self.source_pass,
                                                      model_name, 'search_read',
                                                      [[('id', '>', 0)]], {'fields': fields_to_export})

        # Prepare insert/update logic

        # Process records
        for record in all_source_records:
            insert_stmt = f"INSERT INTO {self.model_id.model.replace('.', '_')} ({', '.join(record.keys())}) VALUES ({', '.join(['%s'] * len(record))})"
            update_stmt = f"UPDATE {self.model_id.model.replace('.', '_')} SET {', '.join([f'{key} = %s' for key in record.keys() if key != 'id'])} WHERE id = %s"

            target_cr.execute("SELECT id FROM " + self.model_id.model.replace('.', '_') + " WHERE id = %s",
                              (record['id'],))
            if not target_cr.fetchone():
                # Insert
                target_cr.execute(insert_stmt, tuple(record.values()))
            else:
                # Update (excluding the 'id' field)
                target_cr.execute(update_stmt, tuple(record.values()[1:]))  # Skip 'id'

        #     elif self.export_type == 'download':
        #         output = io.StringIO()
        #         writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_ALL)
        #
        #         # Write header row
        #         header = []
        #         for field_name in fields_to_export:
        #             header.append(field_name.replace("/", "."))
        #         writer.writerow(header)
        #
        #         # Write data rows
        #         for record in all_source_records:
        #             row = []
        #             for field_name in fields_to_export:
        #                 if field_name == 'id':
        #                     row.append(record.get('id'))
        #                 elif field_name == '__export_id':
        #                     external_id = source_object.execute_kw(db, uid, password, model_name, 'get_external_id', [record.get('id')])
        #                     if external_id and record.get('id') in external_id:
        #                         row.append(external_id.get(record.get('id')))
        #                     else:
        #                         row.append(None)
        #                 elif "/" in field_name:
        #                     related_fields = field_name.split("/")
        #                     related_record_id = record.get(related_fields[0])
        #                     if related_record_id:
        #                         related_record = source_object.execute_kw(db, uid, password, related_fields[0], 'read', [related_record_id], {'fields':[related_fields[-1]]})
        #                         if related_record:
        #                             row.append(related_record[0].get(related_fields[-1])) # Access the first element of the list because XMLRPC read returns a list
        #                         else:
        #                             row.append(None)
        #                     else:
        #                         row.append(None)
        #                 else:
        #                     row.append(record.get(field_name))
        #             writer.writerow(row)
        #
        #         output.seek(0)
        #         filecontent = output.getvalue()
        #         output.close()
        #
        #         filename = f'{model_name}.csv'
        #         filecontent = base64.b64encode(filecontent.encode())
        #
        #         return {
        #             'type': 'ir.actions.act_url',
        #             'url': '/web/content/?model=export.data.wizard&id=%s&filename=%s&download=true' % (
        #             self.id, filename),
        #             'target': 'new',
        #         }
        #     elif self.export_type == 'server':
        #         filename = f'{model_name}.csv'
        #         save_path = self.server_path
        #         if not os.path.exists(save_path):
        #             os.makedirs(save_path)
        #         full_path = os.path.join(save_path, filename)
        #         try:
        #             with open(full_path, 'w', newline='', encoding='utf-8') as csvfile:
        #                 csvwriter = csv.writer(csvfile)
        #                 header = []
        #                 for field_name in fields_to_export:
        #                     header.append(field_name.replace("/", "."))
        #                 csvwriter.writerow(header)
        #                 for record in all_source_records:
        #                     row = []
        #                     for field_name in fields_to_export:
        #                         if field_name == 'id':
        #                             row.append(record.get('id'))
        #                         elif field_name == '__export_id':
        #                             external_id = source_object.execute_kw(db, uid, password, model_name, 'get_external_id', [record.get('id')])
        #                             if external_id and record.get('id') in external_id:
        #                                 row.append(external_id.get(record.get('id')))
        #                             else:
        #                                 row.append(None)
        #                         elif "/" in field_name:
        #                             related_fields = field_name.split("/")
        #                             related_record_id = record.get(related_fields[0])
        #                             if related_record_id:
        #                                 related_record = source_object.execute_kw(db, uid, password, related_fields[0], 'read', [related_record_id], {'fields':[related_fields[-1]]})
        #                                 if related_record:
        #                                     row.append(related_record[0].get(related_fields[-1])) # Access the first element of the list because XMLRPC read returns a list
        #                                 else:
        #                                     row.append(None)
        #                             else:
        #                                 row.append(None)
        #                         else:
        #                             row.append(record.get(field_name))
        #                     csvwriter.writerow(row)
        #             print(f"File saved to {full_path}")
        #
        #             #
        #             # filecontent_b64=base64.b64encode(open(full_path, 'rb').read())
        #             # attachment = self.env['ir.attachment'].create({
        #             #     'name': filename,
        #             #     'datas': filecontent_b64,
        #             #     'type': 'binary',
        #             #     'res_model': self._name,  # Current model
        #             #     'res_id': self.id if self.id else None ,      # Current record ID (if applicable)
        #             # })
        #             # return {
        #             #     'type': 'ir.ui.message',
        #             #     'title': 'File Saved',
        #             #     'message': f'File saved to {full_path} and also saved as attachment.',
        #             #     'sticky': False
        #             # }
        #         except Exception as e:
        #             print(f"Error saving file: {e}")
        #             return {
        #                 'type': 'ir.ui.message',
        #                 'title': 'Error',
        #                 'message': f'An error occurred during export: {e}',
        #                 'sticky': True
        #             }
        #
        # except Exception as e:
        #     print(f"Error during XML-RPC export: {e}")
        #     # return {
        #     #     'type': 'ir.ui.message',
        #     #     'title': 'Error',
        #     #     'message': f'An error occurred during export: {e}',
        #     #     'sticky': True
        #     # }
        #


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