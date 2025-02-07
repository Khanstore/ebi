User Manual for Eagle Base Import (EBI) Data Import Module (Odoo)
This manual provides a comprehensive guide on how to use the EBI Data Import Module, which allows users to import databases, models, and fields into Odoo via XML-RPC.

1. Introduction
The EBI Data Import Module helps users migrate and synchronize data between different Odoo instances using XML-RPC and PostgreSQL connections. It includes features for:
✅ Importing databases, models, and fields
✅ Mapping source and target databases
✅ Handling PostgreSQL connections
✅ Exporting and importing data

2. Module Access
2.1 Menu Navigation
The module is located under "Import Data" in the Odoo main menu.

📂 Import Data
🔹 Import (Main Section)

📌 Database (Import and manage database connections)
📌 Models (Import data models)
📌 Fields (Import field mappings)
➡️ Only administrators (base.group_system) can access this module.

3. Features and Functionalities
3.1 Import Database
📍 Navigation: Import Data → Database
✅ This section allows users to define source and target database connections.
✅ It includes authentication settings for XML-RPC and PostgreSQL.

Fields
Field Name	Description
name	Name of the import session
source_address	URL of the source Odoo instance
source_database	Source database name
source_email	Email of source Odoo user
source_uid	User ID for source database
source_pass	Password for source user
target_address	URL of the target Odoo instance
target_database	Target database name
target_email	Email for target Odoo user
target_uid	User ID for target database
target_pass	Password for target user
Actions (Buttons)
Button Name	Function
🔄 update_khan_store_bd_state	Updates Khan Store BD state
🗑️ delete_previous_data	Deletes old records before import
🗑️ delete_previous_product_data	Deletes product-related data
3.2 PostgreSQL Database Credentials
📍 Navigation: Import Data → Database → PostgreSQL Credentials
✅ Allows users to define PostgreSQL connections for direct database imports.

Fields
Field Name	Description
source_pg_host	Host of the source database
source_pg_port	Port number of source PostgreSQL
source_pg_user	Username for source database
source_pg_pass	Password for source user
target_pg_host	Host of the target database
target_pg_port	Port number of target PostgreSQL
target_pg_user	Username for target database
target_pg_pass	Password for target user
Actions (Buttons)
Button Name	Function
🔄 update_table_list	Updates the list of tables for import
🔄 update_all_sequences	Resets sequence numbers in PostgreSQL
3.3 Importing Models
📍 Navigation: Import Data → Models
✅ Users can manage and import specific data models from the source database to the target.

Fields
Field Name	Description
name	Name of the model
selected	Checkbox to include the model for import
sequence	Order of import execution
database_id	Related database connection
source	Source model name
target	Target model name
Actions (Buttons)
Button Name	Function
🔄 update_field_list	Refreshes available fields for mapping
3.4 Importing Fields
📍 Navigation: Import Data → Fields
✅ Users can define field mappings between the source and target databases.

Fields
Field Name	Description
name	Field name
selected	Checkbox to include the field for import
model_id	Associated model
source	Field name in source database
target	Field name in target database
default_value	Default value if source data is missing
data_type	Type of data (Integer, Char, Many2one, etc.)
3.5 Importing Tables
📍 Navigation: Import Data → Database → Tables
✅ Users can import entire tables from the source to the target database.

Actions (Buttons)
Button Name	Function
🔄 import_all_table	Imports all selected tables
📥 import_table_data	Imports data from a specific table
📥 import_table_data_with_related	Imports data including related records
3.6 Data Export Options
📍 Navigation: Import Data → Database → Operation Type
✅ Allows users to export data in different formats.

Fields
Field Name	Description
export_type	Type of export (JSON, XML, Direct DB to DB)
download_path	File path for export
Actions (Buttons)
Button Name	Function
📤 export_jsondata	Exports selected fields to JSON
🔄 direct_db_db_export	Directly exports data between databases
🔎 fetch_data_with_external_ids	Fetches data while keeping external IDs
🔄 test_source_connection	Tests the source database connection
📤 export_data	Starts the export process
4. User Permissions
🔹 Administrator (base.group_system) users can access all features.
🔹 Regular users do not have access to this module.

5. Troubleshooting
🔴 Problem: Connection Error When Importing
✔ Solution: Ensure the source and target database credentials are correct.
✔ Solution: Test the connection using the test_source_connection button.

🔴 Problem: Some Data Is Missing After Import
✔ Solution: Check if all required models and fields are selected for import.
✔ Solution: Click update_table_list before importing.

🔴 Problem: PostgreSQL Sequences Are Not Updated
✔ Solution: Click update_all_sequences to reset sequence numbers.

6. Summary
✅ The EBI Data Import Module allows users to import, export, and synchronize data between Odoo databases.
✅ It supports XML-RPC and PostgreSQL connections for flexible data transfer.
✅ The interface is organized into Database, Models, and Fields sections.

✅ Now you're ready to use the EBI Data Import Module efficiently!