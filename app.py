# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import os
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import io # For in-memory file operations

# Import Google Sheets libraries
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Import openpyxl for Excel generation
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

# --- Flask App Initialization ---
app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here' # Change this to a strong, random key in production

# --- Configuration ---
# Admin credentials (for demonstration - use a proper database in production)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'password123') # Hash this in production!

# Arkesel SMS API Key (for demonstration - keep this secure in production, e.g., environment variable)
ARKESEL_API_KEY = os.environ.get('ARKESEL_API_KEY', 'b0FrYkNNVlZGSmdrendVT3hwUHk')
ARKESEL_SENDER_ID = os.environ.get('ARKESEL_SENDER_ID', 'FarmApp') # Your registered sender ID

# Google Sheet Configuration
# Changed to use Google Sheet ID for more robust access
GOOGLE_SHEET_ID = "1D1rsEMAtVhUcyMYyQkrMcl9_5thgWD4ACNtRQ0JcmDA" 
GOOGLE_SHEET_KEY_FILE = "service_account.json" # Path to your GCP service account JSON key

# --- Google Sheets Integration ---
def init_google_sheets_client():
    """Initializes Google Sheets client."""
    try:
        # Define the scope for accessing Google Sheets and Google Drive
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        # Load credentials from the service account JSON key file
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEET_KEY_FILE, scope)
        # Authorize the client
        client = gspread.authorize(creds)
        print("Google Sheets client initialized successfully.")
        return client
    except FileNotFoundError:
        print(f"Error: Service account key file not found at {GOOGLE_SHEET_KEY_FILE}. Please ensure it's in the correct directory.")
        return None
    except Exception as e:
        print(f"Error initializing Google Sheets client: {e}")
        return None

def get_sheet(client, sheet_id):
    """Gets a specific worksheet using the spreadsheet ID."""
    try:
        # Open the spreadsheet by ID
        spreadsheet = client.open_by_key(sheet_id)
        # Get the first worksheet (default)
        worksheet = spreadsheet.sheet1
        print(f"Successfully opened sheet with ID: {sheet_id}")
        return worksheet
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Error: Spreadsheet with ID '{sheet_id}' not found. Please ensure the ID is correct and the sheet is shared with the service account.")
        return None
    except Exception as e:
        print(f"Error opening sheet with ID {sheet_id}: {e}")
        return None

def append_to_sheet(sheet, data):
    """Appends a row of data to the Google Sheet."""
    try:
        sheet.append_row(data)
        print(f"Successfully appended data to Google Sheet: {data}")
        return True
    except Exception as e:
        print(f"Error appending data to sheet: {e}")
        return False

def get_all_records_from_sheet(sheet):
    """Retrieves all records from the Google Sheet."""
    try:
        # get_all_records() returns a list of dictionaries, excluding the header row.
        records = sheet.get_all_records()
        print(f"Successfully retrieved {len(records)} records from Google Sheet.")
        return records
    except Exception as e:
        print(f"Error retrieving records from sheet: {e}")
        return []

def update_record_in_sheet(row_index_in_sheet, updated_data_dict):
    """Updates a specific row in the Google Sheet."""
    client = init_google_sheets_client()
    if not client:
        flash("Google Sheets client could not be initialized for update.", "danger")
        return False

    sheet = get_sheet(client, GOOGLE_SHEET_ID) # Use GOOGLE_SHEET_ID here
    if not sheet:
        flash(f"Could not open Google Sheet with ID '{GOOGLE_SHEET_ID}' for update.", "danger")
        return False

    try:
        # Define the exact order of columns as they appear in the Google Sheet headers.
        # This is crucial for matching values to cells during update.
        # Headers in the Google Sheet: Date, Type, Category, Item, Quantity, Unit, Amount, Profit Per Unit, Total Profit
        ordered_headers = ['Date', 'Type', 'Category', 'Item', 'Quantity', 'Unit', 'Amount', 'Profit Per Unit', 'Total Profit']
        
        # Create a list of values in the correct order for the row update
        row_values = []
        for header in ordered_headers:
            # Use .get() with a default empty string for keys that might not exist in updated_data_dict
            # This handles cases where certain fields (like Quantity/Amount/Profit) might be empty for a record type.
            key_name = header.replace(' ', '_').lower() # Convert header to match Python dict keys
            
            # Special handling for missing keys if the updated_data_dict doesn't contain all possible keys
            if key_name == 'quantity':
                row_values.append(updated_data_dict.get(key_name, ''))
            elif key_name == 'amount':
                row_values.append(updated_data_dict.get(key_name, ''))
            elif key_name == 'profit_per_unit':
                row_values.append(updated_data_dict.get(key_name, ''))
            elif key_name == 'total_profit':
                row_values.append(updated_data_dict.get(key_name, ''))
            else:
                row_values.append(updated_data_dict.get(key_name, ''))

        # Use worksheet.update(range_name, values)
        # range_name example: 'A5:I5' for row 5 assuming 9 columns
        # No, row_index_in_sheet is already the actual sheet row (from loop.index + 2)
        range_name = f'A{row_index_in_sheet}:{chr(ord("A") + len(ordered_headers) - 1)}{row_index_in_sheet}'
        
        # Values must be a list of lists if updating a range, or a list if updating a single row
        sheet.update(range_name, [row_values])
        print(f"Successfully updated row {row_index_in_sheet} in Google Sheet with data: {updated_data_dict}")
        return True
    except Exception as e:
        print(f"Error updating row {row_index_in_sheet} in sheet: {e}")
        return False

# --- Helper Functions for Data (Interacts with Google Sheets) ---
def save_record(record_type, data):
    """Saves a record to the Google Sheet."""
    client = init_google_sheets_client()
    if not client:
        flash("Google Sheets client could not be initialized. Check server logs.", "danger")
        return False

    sheet = get_sheet(client, GOOGLE_SHEET_ID) # Use GOOGLE_SHEET_ID here
    if not sheet:
        flash(f"Could not open Google Sheet with ID '{GOOGLE_SHEET_ID}'. Check server logs.", "danger")
        return False
    
    # Define the order of columns as expected in the Google Sheet
    # This is crucial for gspread.append_row()
    # Headers in the Google Sheet: Date, Type, Category, Item, Quantity, Unit, Amount, Profit Per Unit, Total Profit
    if record_type == 'feed':
        row_data = [
            data['date'], data['type'], data['category'], data['item'], 
            data['quantity'], data['unit'], '', '', ''
        ]
    elif record_type == 'expenditure':
        row_data = [
            data['date'], data['type'], data['category'], data['item'], 
            '', '', data['amount'], '', ''
        ]
    elif record_type == 'profit':
        row_data = [
            data['date'], data['type'], data['category'], data['item'], 
            data['quantity'], data['unit'], '', data['profit_per_unit'], data['total_profit']
        ]
    else:
        print(f"Unknown record type: {record_type}")
        return False

    return append_to_sheet(sheet, row_data)

def get_farm_statistics():
    """Retrieves aggregated farm data for dashboard statistics from Google Sheets."""
    client = init_google_sheets_client()
    if not client:
        return {} # Return empty stats if client not initialized

    sheet = get_sheet(client, GOOGLE_SHEET_ID) # Use GOOGLE_SHEET_ID here
    if not sheet:
        return {} # Return empty stats if sheet not found

    records = get_all_records_from_sheet(sheet)
    if not records:
        print("No records found in the Google Sheet for statistics.")
        return {
            'total_feeds_kg': 0,
            'total_expenditure': 0,
            'total_profit': 0,
            'layers_eggs_sold_crates': 0,
            'broilers_birds_sold': 0,
            'goats_sold': 0,
            'sheep_sold': 0
        }

    df = pd.DataFrame(records)
    
    # Convert numeric columns to numeric, coercing errors
    for col in ['Quantity', 'Amount', 'Profit Per Unit', 'Total Profit']: # Use actual column names from Google Sheet headers
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Rename columns to be lowercase for easier access in Python (optional, but good practice)
    df.columns = [col.replace(' ', '_').lower() for col in df.columns]

    stats = {
        'total_feeds_kg': df[df['type'] == 'feed_input']['quantity'].sum() if 'type' in df.columns and 'quantity' in df.columns else 0,
        'total_expenditure': df[df['type'] == 'expenditure']['amount'].sum() if 'type' in df.columns and 'amount' in df.columns else 0,
        'total_profit': df[df['type'] == 'profit']['total_profit'].sum() if 'type' in df.columns and 'total_profit' in df.columns else 0,
        'layers_eggs_sold_crates': df[(df['type'] == 'profit') & (df['category'] == 'Layers') & (df['item'] == 'Eggs Sold')]['quantity'].sum() if 'type' in df.columns and 'category' in df.columns and 'item' in df.columns and 'quantity' in df.columns else 0,
        'broilers_birds_sold': df[(df['type'] == 'profit') & (df['category'] == 'Broilers') & (df['item'] == 'Birds Sold')]['quantity'].sum() if 'type' in df.columns and 'category' in df.columns and 'item' in df.columns and 'quantity' in df.columns else 0,
        'goats_sold': df[(df['type'] == 'profit') & (df['category'] == 'Goats') & (df['item'] == 'Goat Meat')]['quantity'].sum() if 'type' in df.columns and 'category' in df.columns and 'item' in df.columns and 'quantity' in df.columns else 0,
        'sheep_sold': df[(df['type'] == 'profit') & (df['category'] == 'Sheep') & (df['item'] == 'Sheep Meat')]['quantity'].sum() if 'type' in df.columns and 'category' in df.columns and 'item' in df.columns and 'quantity' in df.columns else 0,
    }
    return stats

def get_all_farm_records_df():
    """Retrieves all farm records as a pandas DataFrame from Google Sheets and standardizes column names,
    specifically ensuring 'Date', 'Type', 'Amount', and 'Total Profit' columns for reporting."""
    client = init_google_sheets_client()
    if not client:
        flash("Google Sheets client could not be initialized for record retrieval.", "danger")
        return pd.DataFrame()

    sheet = get_sheet(client, GOOGLE_SHEET_ID) # Use GOOGLE_SHEET_ID here
    if not sheet:
        flash(f"Could not open Google Sheet with ID '{GOOGLE_SHEET_ID}' for record retrieval.", "danger")
        return pd.DataFrame()

    records = get_all_records_from_sheet(sheet)
    if not records:
        print("--- DEBUG: No records found in the Google Sheet (gspread returned empty list).")
        flash("No records found in the Google Sheet.", "info")
        return pd.DataFrame()

    df = pd.DataFrame(records)
    print(f"--- DEBUG: Initial DataFrame shape: {df.shape}")
    print(f"--- DEBUG: Initial DataFrame columns (raw from gspread): {df.columns.tolist()}")
    print(f"--- DEBUG: Initial DataFrame head:\n{df.head().to_string()}")

    # Define desired standardized column names and common variations (lowercase, no spaces)
    standardized_column_map = {
        'Date': ['date', 'recorddate', 'transactiondate', 'timestamp'],
        'Type': ['type', 'recordtype', 'recordkind', 'transactiontype'],
        'Category': ['category', 'itemcategory', 'classification'],
        'Item': ['item', 'description', 'product', 'detail'],
        'Quantity': ['quantity', 'qty', 'amountbought', 'amountsold'],
        'Unit': ['unit', 'uom', 'measure'],
        'Amount': ['amount', 'expenditureamount', 'cost', 'totalcost', 'value'], # For expenditure
        'Profit Per Unit': ['profitperunit', 'ppu', 'unitprofit', 'priceperunit'],
        'Total Profit': ['totalprofit', 'profit', 'netsales', 'revenue']
    }

    # Normalize existing column names to facilitate matching
    normalized_df_columns = {col.lower().replace(' ', ''): col for col in df.columns}
    
    # Create a mapping from current actual column names to desired standardized names
    column_renaming_dict = {}
    final_columns = set() # To keep track of columns we actually want to keep/rename to

    for desired_name, variations in standardized_column_map.items():
        found_match = False
        for var in variations:
            if var in normalized_df_columns:
                original_matched_col = normalized_df_columns[var]
                if original_matched_col != desired_name:
                    column_renaming_dict[original_matched_col] = desired_name
                else: # It's already the desired_name (case-sensitive)
                    column_renaming_dict[original_matched_col] = desired_name # Ensure it's in the dict
                found_match = True
                final_columns.add(desired_name)
                break
        
        # If a desired column is not found through variations or exact match
        if not found_match and desired_name not in df.columns:
            df[desired_name] = '' # Add as empty to prevent KeyError
            final_columns.add(desired_name) # Add to final columns list
            print(f"--- DEBUG: Critical column '{desired_name}' not found, added as empty.")
            # Flash message added below after checking all columns


    # Apply the renaming
    if column_renaming_dict:
        df.rename(columns=column_renaming_dict, inplace=True)
    
    # Reorder columns to a consistent display order (optional but good for consistency)
    # Ensure all target columns are in the list, adding any that were just created
    ordered_display_columns = [
        'Date', 'Type', 'Category', 'Item', 'Quantity', 'Unit', 
        'Amount', 'Profit Per Unit', 'Total Profit'
    ]
    
    # Filter for columns that actually exist in the DataFrame (including newly added empty ones)
    df_columns_as_set = set(df.columns)
    columns_to_reorder = [col for col in ordered_display_columns if col in df_columns_as_set]
    
    # Add any original columns that weren't part of our standardized map to the end
    for col in df.columns:
        if col not in columns_to_reorder:
            columns_to_reorder.append(col)

    df = df[columns_to_reorder]
    
    print(f"--- DEBUG: After standardization and adding missing, DataFrame columns: {df.columns.tolist()}")
    print(f"--- DEBUG: DataFrame head after column processing:\n{df.head().to_string()}")

    # Check for critical columns and flash warnings if they were added as empty
    critical_columns_for_warning = ['Date', 'Type', 'Amount', 'Total Profit']
    for col_name in critical_columns_for_warning:
        if col_name in df.columns and df[col_name].iloc[0] == '' and len(df[col_name].unique()) == 1:
            # Check if it was truly missing and added as empty (assuming first row would be representative)
            flash_message = f"Warning: The '{col_name}' column was not explicitly found or recognized in your Google Sheet. It has been added as a placeholder. Report data for this column might be missing or inaccurate. Please ensure your Google Sheet has a column specifically named '{col_name}' or a common variation (e.g., '{standardized_column_map[col_name][0]}') for best results."
            if 'Date' in col_name:
                flash_message = f"Warning: The '{col_name}' column was not explicitly found in your Google Sheet. It has been added as a placeholder. Please ensure your Google Sheet has a column specifically named '{col_name}' for accurate reporting."
            elif 'Type' in col_name:
                 flash_message = f"Warning: The '{col_name}' column was not explicitly found in your Google Sheet. It has been added as a placeholder. Report filtering might be inaccurate. Please ensure your Google Sheet has a column specifically named '{col_name}'."
            flash(flash_message, "warning")


    # Ensure 'Date' column is in datetime format AFTER ensuring it exists and is named correctly
    if 'Date' in df.columns:
        print(f"--- DEBUG: 'Date' column dtype (before convert): {df['Date'].dtype}")
        print(f"--- DEBUG: 'Date' column values (before convert, head):\n{df['Date'].head().to_string()}")

        initial_rows_before_dropna = df.shape[0]
        
        # Convert date column, coercing errors to NaT
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        print(f"--- DEBUG: After pd.to_datetime, 'Date' column dtype: {df['Date'].dtype}")
        print(f"--- DEBUG: 'Date' column values (after convert, head):\n{df['Date'].head().to_string()}")
        print(f"--- DEBUG: Count of NaT values in 'Date' column: {df['Date'].isna().sum()}")

        # Drop rows where 'Date' became NaT (invalid date)
        df.dropna(subset=['Date'], inplace=True)
        
        print(f"--- DEBUG: After dropna(subset=['Date']), DataFrame shape: {df.shape}")
        if df.shape[0] < initial_rows_before_dropna:
            dropped_rows_count = initial_rows_before_dropna - df.shape[0]
            print(f"--- DEBUG: {dropped_rows_count} rows dropped due to invalid 'Date' values.")
            if dropped_rows_count > 0 and df.empty:
                 flash(f"Warning: All records were removed because their 'Date' column contained invalid or empty date formats. Please check your Google Sheet.", "warning")
            elif dropped_rows_count > 0:
                 flash(f"Warning: Some records were removed because their 'Date' column contained invalid or empty date formats. Please check your Google Sheet. Remaining records: {df.shape[0]}", "warning")

    else:
        print("--- DEBUG: 'Date' column still missing or invalid after all checks, returning empty DataFrame.")
        flash("Error: Failed to establish a valid 'Date' column. Reports cannot be generated. Please ensure your Google Sheet has a column for dates (e.g., 'Date').", "danger")
        return pd.DataFrame()

    # Convert relevant numeric columns after date processing, as errors='coerce' might be needed
    # for columns that might have mixed types from Google Sheets.
    for col in ['Quantity', 'Amount', 'Profit Per Unit', 'Total Profit']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    print(f"--- DEBUG: Final DataFrame shape being returned: {df.shape}")
    print(f"--- DEBUG: Final DataFrame head being returned:\n{df.head().to_string()}")
    return df

# --- Arkesel SMS Integration ---
def send_sms(recipient, message, api_key, sender_id):
    """Sends an SMS message using the Arkesel API."""
    url = "https://sms.arkesel.com/sms/api"
    
    # All parameters sent as query parameters in the URL
    query_params = {
        "action": "send-sms",
        "api_key": api_key,
        "to": recipient,
        "from": sender_id,
        "sms": message,
        "type": "plain",
        "unicode": 0
    }
    
    headers = {} 

    print(f"Sending SMS Request Details (GET with All parameters in URL Query String):")
    print(f"  Full URL: {url}?{requests.compat.urlencode(query_params)}")
    print(f"  Headers: {headers}")
    print(f"  No Request Body")

    try:
        # Using GET method as all parameters are in the URL query string
        response = requests.get(url, params=query_params, headers=headers)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        
        # Try to parse JSON, but gracefully handle if not JSON
        try:
            response_data = response.json()
            print(f"Arkesel SMS Raw JSON Response: {json.dumps(response_data, indent=2)}")
            if response_data.get('code') == 'ok' or response_data.get('status') == 'success':
                return True, "SMS sent successfully!"
            else:
                api_error_message = response_data.get('message', response_data.get('description', 'Unknown API error'))
                api_error_code = response_data.get('code', 'N/A')
                return False, f"SMS failed: {api_error_message}. Code: {api_error_code}"
        except json.JSONDecodeError:
            print(f"Arkesel SMS Response (Non-JSON, Status: {response.status_code}): {response.text}")
            if response.status_code >= 200 and response.status_code < 300:
                return True, "SMS sent successfully (non-JSON response)!"
            else:
                return False, f"SMS failed: Non-JSON response with status {response.status_code}. Response: {response.text}"

    except requests.exceptions.HTTPError as e:
        error_response_text = e.response.text if e.response else 'N/A'
        print(f"HTTP Error sending SMS: {e}. Status Code: {e.response.status_code if e.response else 'N/A'}. Response Content: {error_response_text}")
        return False, f"HTTP Error: {e.response.status_code} {e.response.reason}. Response: {error_response_text}"
    except requests.exceptions.RequestException as e:
        print(f"Request Error sending SMS: {e}")
        return False, f"Request Error: {e}"

# --- Routes ---

@app.route('/')
def index():
    """Renders the landing page."""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles admin login."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Logged in successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logs out the admin."""
    session.pop('logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.before_request
def require_login():
    """Middleware to require login for admin dashboard and view_records."""
    if request.endpoint in ['admin_dashboard', 'view_records', 'export_records', 'edit_record', 'view_monthly_report', 'view_weekly_report'] and not session.get('logged_in'):
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))

@app.route('/admin')
def admin_dashboard():
    """Renders the admin dashboard with statistics."""
    stats = get_farm_statistics() # Get simulated statistics
    return render_template('admin.html', stats=stats)

@app.route('/admin/add_record', methods=['POST'])
def add_record():
    """Handles adding daily records (feeds, expenditure, profit)."""
    if not session.get('logged_in'):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    record_type = request.form['record_type']
    data = {'date': datetime.now().strftime('%Y-%m-%d')} # Add current date

    try:
        if record_type == 'feed':
            data['type'] = 'feed_input'
            data['category'] = request.form['feed_category']
            data['item'] = request.form['feed_type']
            data['quantity'] = float(request.form['feed_quantity'])
            data['unit'] = 'kg'
            success = save_record('feed', data)
            if success:
                flash('Feed record added successfully!', 'success')
            else:
                flash('Failed to add feed record. Please check the sheet name and sharing permissions, and server logs for details.', 'danger')
        elif record_type == 'expenditure':
            data['type'] = 'expenditure'
            data['category'] = request.form['exp_category']
            data['item'] = request.form['exp_item']
            data['amount'] = float(request.form['exp_amount'])
            success = save_record('expenditure', data)
            if success:
                flash('Expenditure record added successfully!', 'success')
            else:
                flash('Failed to add expenditure record. Please check the sheet name and sharing permissions, and server logs for details.', 'danger')
        elif record_type == 'profit':
            data['type'] = 'profit'
            data['category'] = request.form['profit_category']
            data['item'] = request.form['profit_item']
            data['quantity'] = int(request.form['profit_quantity'])
            data['profit_per_unit'] = float(request.form['profit_per_unit'])
            data['total_profit'] = data['quantity'] * data['profit_per_unit']
            data['unit'] = 'crates' if 'Eggs' in data['item'] else ('birds' if 'Birds' in data['item'] else 'units') # Refined unit logic
            success = save_record('profit', data)
            if success:
                flash('Profit record added successfully!', 'success')
            else:
                flash('Failed to add profit record. Please check the sheet name and sharing permissions, and server logs for details.', 'danger')
        else:
            flash('Invalid record type.', 'danger')
    except ValueError:
        flash('Invalid input for quantity, amount, or profit per unit. Please enter numbers.', 'danger')
    except Exception as e:
        flash(f'An unexpected error occurred: {e}', 'danger')
        print(f"Error adding record: {e}")

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/send_sms', methods=['POST'])
def send_custom_sms():
    """Handles sending custom SMS messages to field workers."""
    if not session.get('logged_in'):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    recipient = request.form['recipient_number']
    message = request.form['sms_message']

    if not recipient or not message:
        flash('Recipient number and message are required!', 'warning')
        return redirect(url_for('admin_dashboard'))

    success, msg = send_sms(recipient, message, ARKESEL_API_KEY, ARKESEL_SENDER_ID)
    if success:
        flash(f'SMS sent successfully: {msg}', 'success')
    else:
        flash(f'Failed to send SMS: {msg}', 'danger')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/view_records')
def view_records():
    """Displays all farm records."""
    if not session.get('logged_in'):
        flash('Please log in to view records.', 'warning')
        return redirect(url_for('login'))

    df_records = get_all_farm_records_df()
    if df_records.empty:
        flash("No records available to display.", "info")
        return render_template('view_records.html', records=[], columns=[])

    # Convert DataFrame to list of dictionaries for Jinja2 template
    # `to_dict(orient='records')` creates a list of dictionaries.
    # The `row_index` passed to the template needs to correspond to the actual sheet row number.
    # Since get_all_records() skips the header, records[0] is sheet row 2.
    # So, for records_list[i], the sheet row is i + 2.
    records_list = df_records.to_dict(orient='records')
    columns = df_records.columns.tolist()

    return render_template('view_records.html', records=records_list, columns=columns)

@app.route('/admin/edit_record/<int:record_index>', methods=['GET', 'POST'])
def edit_record(record_index):
    """
    Displays a form to edit a specific record or handles the submission of edited data.
    `record_index` is 0-indexed from the list of records (records_list),
    which corresponds to actual sheet row `record_index + 2`.
    """
    if not session.get('logged_in'):
        flash('Please log in to edit records.', 'warning')
        return redirect(url_for('login'))

    df_records = get_all_farm_records_df()
    if df_records.empty or record_index < 0 or record_index >= len(df_records):
        flash("Record not found.", "danger")
        return redirect(url_for('view_records'))

    # The record to edit (as a dictionary)
    record_to_edit = df_records.iloc[record_index].to_dict()
    
    # Adjust column names back to lowercase with underscores for easy access in template form fields
    # Example: 'Profit Per Unit' -> 'profit_per_unit'
    formatted_record = {k.replace(' ', '_').lower(): v for k, v in record_to_edit.items()}

    # Calculate the actual row number in the Google Sheet (1-based)
    # If records_list[record_index] is the record, then its actual row in GSheet is record_index + 2
    sheet_row_number = record_index + 2

    if request.method == 'POST':
        # Get updated data from the form
        updated_data = {
            'date': request.form['date'],
            'type': request.form['type'],
            'category': request.form['category'],
            'item': request.form['item'],
            'quantity': request.form.get('quantity', ''), # Use .get to handle missing fields gracefully
            'unit': request.form.get('unit', ''),
            'amount': request.form.get('amount', ''),
            'profit_per_unit': request.form.get('profit_per_unit', ''),
            'total_profit': request.form.get('total_profit', '')
        }
        
        # Convert numeric fields to float/int if they are not empty
        for key in ['quantity', 'amount', 'profit_per_unit', 'total_profit']:
            if updated_data[key]:
                try:
                    updated_data[key] = float(updated_data[key])
                    if key == 'quantity': # Quantity can be int for birds/crates
                         updated_data[key] = int(updated_data[key])
                except ValueError:
                    flash(f"Invalid number for {key.replace('_', ' ').title()}. Please enter a valid number.", "danger")
                    return render_template('edit_record.html', record=formatted_record, record_index=record_index)
            else:
                updated_data[key] = '' # Ensure empty strings for blank fields

        # Calculate total_profit if quantity and profit_per_unit are available
        if updated_data.get('quantity') and updated_data.get('profit_per_unit'):
            try:
                updated_data['total_profit'] = float(updated_data['quantity']) * float(updated_data['profit_per_unit'])
            except ValueError:
                updated_data['total_profit'] = '' # If conversion fails, keep it blank

        success = update_record_in_sheet(sheet_row_number, updated_data)
        if success:
            flash('Record updated successfully!', 'success')
            return redirect(url_for('view_records'))
        else:
            flash('Failed to update record. Check server logs for details.', 'danger')
            return render_template('edit_record.html', record=formatted_record, record_index=record_index)

    return render_template('edit_record.html', record=formatted_record, record_index=record_index)


@app.route('/admin/export_records')
def export_records():
    """Exports all farm records to an Excel file."""
    if not session.get('logged_in'):
        flash('Please log in to export records.', 'warning')
        return redirect(url_for('login'))

    df_records = get_all_farm_records_df()
    if df_records.empty:
        flash("No records available to export.", "warning")
        return redirect(url_for('view_records'))

    output = io.BytesIO()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Farm Records"

    headers = df_records.columns.tolist()
    sheet.append(headers)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4CAF50", end_color="4CAF50", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")

    for col_idx, header in enumerate(headers, 1):
        cell = sheet.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment

    for r_idx, row in df_records.iterrows():
        row_data = row.tolist()
        sheet.append(row_data)

    for column in sheet.columns:
        max_length = 0
        column_name = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        sheet.column_dimensions[column_name].width = adjusted_width


    workbook.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'Farm_Records_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@app.route('/admin/reports/monthly')
def view_monthly_report():
    """Displays monthly profit and expenditure report."""
    if not session.get('logged_in'):
        flash('Please log in to view reports.', 'warning')
        return redirect(url_for('login'))

    df = get_all_farm_records_df()
    if df.empty:
        flash("No records available for reports.", "info")
        return render_template('monthly_report.html', report_data={'month': datetime.now().strftime('%B %Y'), 'total_profit': 0, 'total_expenditure': 0, 'records': []}, report_title="Monthly Report")

    # Ensure 'Date' column is in datetime format
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df.dropna(subset=['Date'], inplace=True) # Drop rows where date conversion failed

    # Filter for the current month
    current_month = datetime.now().month
    current_year = datetime.now().year
    monthly_records = df[(df['Date'].dt.month == current_month) & (df['Date'].dt.year == current_year)]

    # Calculate total profit and expenditure for the month
    # Ensure 'Type' is 'Type' and 'Total Profit'/'Amount' are correct
    total_monthly_profit = monthly_records[monthly_records['Type'] == 'Profit']['Total Profit'].sum()
    total_monthly_expenditure = monthly_records[monthly_records['Type'] == 'Expenditure']['Amount'].sum()

    report_data = {
        'month': datetime.now().strftime('%B %Y'),
        'total_profit': total_monthly_profit,
        'total_expenditure': total_monthly_expenditure,
        'records': monthly_records.to_dict(orient='records')
    }

    return render_template('monthly_report.html', report_data=report_data, report_title="Monthly Profit & Expenditure Report")


@app.route('/admin/reports/weekly')
def view_weekly_report():
    """Displays weekly profit and expenditure report."""
    if not session.get('logged_in'):
        flash('Please log in to view reports.', 'warning')
        return redirect(url_for('login'))

    df = get_all_farm_records_df()
    if df.empty:
        flash("No records available for reports.", "info")
        return render_template('weekly_report.html', report_data={'week_range': 'Current Week', 'total_profit': 0, 'total_expenditure': 0, 'records': []}, report_title="Weekly Report")

    # Ensure 'Date' column is in datetime format
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df.dropna(subset=['Date'], inplace=True) # Drop rows where date conversion failed

    # Filter for the current week (start from Monday)
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday()) # Monday
    end_of_week = start_of_week + timedelta(days=6) # Sunday

    weekly_records = df[(df['Date'].dt.date >= start_of_week) & (df['Date'].dt.date <= end_of_week)]

    # Calculate total profit and expenditure for the week
    # Ensure 'Type' is 'Type' and 'Total Profit'/'Amount' are correct
    total_weekly_profit = weekly_records[weekly_records['Type'] == 'Profit']['Total Profit'].sum()
    total_weekly_expenditure = weekly_records[weekly_records['Type'] == 'Expenditure']['Amount'].sum()

    report_data = {
        'week_range': f"{start_of_week.strftime('%Y-%m-%d')} to {end_of_week.strftime('%Y-%m-%d')}",
        'total_profit': total_weekly_profit,
        'total_expenditure': total_weekly_expenditure,
        'records': weekly_records.to_dict(orient='records')
    }

    return render_template('weekly_report.html', report_data=report_data, report_title="Weekly Profit & Expenditure Report")


# --- Main entry point ---
if __name__ == '__main__':
    app.run(debug=True)
