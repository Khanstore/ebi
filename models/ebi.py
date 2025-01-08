# -*- coding: utf-8 -*-
import csv,psycopg2
import io
import base64
import xmlrpc.client
from odoo import models, fields
import os,pandas as pd



class ebiFields(models.TransientModel):
    _name = 'ebi.fields'
    _description = 'fields to import'

    name = fields.Char("Name")
    model_id = fields.Many2one('ir.model', string='Model', required=True)
    source = fields.Char("Source")
    target = fields.Char("target")




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
    # field_ids = fields.Many2many('ir.model.fields', string='Fields', domain="[('model_id', '=', model_id)]")
    field_ids = fields.Many2many('ebi.fields', string='Fields', domain="[('model_id', '=', model_id)]")

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
            fields_to_export = []
            fields_to_import = []
            fields_to_export.extend([field.source for field in self.field_ids])
            fields_to_import.extend([field.target for field in self.field_ids])

            # Fetch data using XML-RPC and pagination
            limit = 1000
            offset = 0
            all_source_records = []

            target_connection = psycopg2.connect(
                host="localhost",
                database=self.target_database,
                user=self.postgre_uid,
                password=self.postgre_pass,
                port='5432'
            )
            target_connection.autocommit = True
            target_cr = target_connection.cursor()





            while True:
                res = source_object.execute_kw(db, uid, password, model_name, 'search_read', [[('id', '>', 0)]],
                                                {'fields': fields_to_export, 'order': 'id asc', 'limit': limit, 'offset': offset})
                if not res:
                    break
                all_source_records.extend(res)
                offset += limit

            # fixme here to correct the field names which is different from the source
            df=pd.DataFrame.from_dict(all_source_records)
            df=df.rename(columns={key: value for key, value in zip(fields_to_export, fields_to_import)})
            all_source_records = df.to_dict('records')
            if self.export_type == 'direct':
                for record in all_source_records:
                    targ = target_object.execute_kw(target_db, target_uid, target_password, model_name, 'search_read',
                                                    [[('id', '=', record['id'])]])
                    if not targ:


                        targ=target_object.execute_kw(target_db, target_uid, target_password, model_name,
                                                        'create',[record])
                        # update ID
                        target_cr.execute("update " + self.model_id.model.replace('.','_')  +" set id="+str(record['id']) +" where id ="+str(targ))

                    else:
                        # update record
                        targ=target_object.execute_kw(target_db, target_uid, target_password, model_name,
                                                 'write',[[targ[0]['id']], record] )


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
                save_path = self.server_path
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

        except Exception as e:
            print(f"Error during XML-RPC export: {e}")
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