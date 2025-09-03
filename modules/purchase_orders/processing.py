import pandas as pd
import os
import glob


def load_excluded_suppliers():
    """Loads the list of excluded suppliers from the text file."""
    try:
        if os.path.exists('excluded_suppliers.txt'):
            with open('excluded_suppliers.txt', 'r') as f:
                excluded = [line.strip().lower() for line in f.readlines() if line.strip()]
                return excluded
        return []
    except Exception as e:
        print(f"Error loading excluded suppliers: {e}")
        return []


def validate_sales_report(file_path):
    """Validates a sales report file and returns validation result."""
    try:
        # Try to read as combined format first
        df = pd.read_excel(file_path, sheet_name='Sheet', skiprows=5, nrows=10)
        
        # Check if it has the combined format pattern
        if len(df.columns) > 10 and 'SKU' in str(df.columns[0]).upper():
            return {
                'valid': True,
                'file_type': 'combined',
                'message': '✅ Combined sales report detected - contains Sales, COGS, Profit, and Quantity data',
                'columns_found': len(df.columns)
            }
        
        # Try separate format
        df_separate = pd.read_excel(file_path, sheet_name='Sheet', skiprows=4, nrows=10)
        if 'SKU' in str(df_separate.columns[0]).upper() and len(df_separate.columns) >= 12:
            return {
                'valid': True,
                'file_type': 'separate',
                'message': '✅ Individual sales report detected - contains monthly data',
                'columns_found': len(df_separate.columns)
            }
        
        return {
            'valid': False,
            'file_type': 'unknown',
            'message': '❌ Invalid sales report format. Expected SKU column and monthly data.',
            'columns_found': 0
        }
    except Exception as e:
        return {
            'valid': False,
            'file_type': 'error',
            'message': f'❌ Error reading file: {str(e)}',
            'columns_found': 0
        }


def validate_replenishment_report(file_path):
    """Validates a replenishment report CSV."""
    try:
        df = pd.read_csv(file_path, nrows=5)
        required_columns = ['SKU', 'Lead time', 'Adjusted sales velocity/day', 'Cost price']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {
                'valid': False,
                'message': f'❌ Missing required columns: {", ".join(missing_columns)}',
                'columns_found': list(df.columns)
            }
        
        return {
            'valid': True,
            'message': '✅ Replenishment report validated - all required columns found',
            'columns_found': list(df.columns)
        }
    except Exception as e:
        return {
            'valid': False,
            'message': f'❌ Error reading file: {str(e)}',
            'columns_found': []
        }


def validate_inventory_list(file_path):
    """Validates an inventory list CSV."""
    try:
        df = pd.read_csv(file_path, nrows=5)
        required_columns = ['ProductCode', 'LastSuppliedBy']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {
                'valid': False,
                'message': f'❌ Missing required columns: {", ".join(missing_columns)}',
                'columns_found': list(df.columns)
            }
        
        return {
            'valid': True,
            'message': '✅ Inventory list validated - all required columns found',
            'columns_found': list(df.columns)
        }
    except Exception as e:
        return {
            'valid': False,
            'message': f'❌ Error reading file: {str(e)}',
            'columns_found': []
        }


def validate_availability_report(file_path):
    """Validates an availability report CSV."""
    try:
        df = pd.read_csv(file_path, nrows=5)
        required_columns = ['SKU', 'Location', 'Available', 'OnOrder']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {
                'valid': False,
                'message': f'❌ Missing required columns: {", ".join(missing_columns)}',
                'columns_found': list(df.columns)
            }
        
        return {
            'valid': True,
            'message': '✅ Availability report validated - all required columns found',
            'columns_found': list(df.columns)
        }
    except Exception as e:
        return {
            'valid': False,
            'message': f'❌ Error reading file: {str(e)}',
            'columns_found': []
        }


def load_combined_sales_report(file_path):
    """Loads and processes the combined Sales by Product Details Report."""
    try:
        # Skip the first 5 rows which contain header info
        df = pd.read_excel(file_path, sheet_name='Sheet', skiprows=5)
        
        # The first row might be empty, so let's skip it
        df = df[1:].reset_index(drop=True)
        
        # The first column is SKU
        df = df.rename(columns={df.columns[0]: 'SKU'})
        
        # Extract metrics by column pattern (every 4 columns)
        sales_data = []
        cogs_data = []
        profit_data = []
        quantity_data = []
        
        # Pattern: Sale, Quantity, COGS, Profit repeating for each month
        for i in range(1, len(df.columns), 4):
            if i < len(df.columns):
                sales_data.append(df.columns[i])      # Sale columns
            if i+1 < len(df.columns):
                quantity_data.append(df.columns[i+1]) # Quantity columns  
            if i+2 < len(df.columns):
                cogs_data.append(df.columns[i+2])     # COGS columns
            if i+3 < len(df.columns):
                profit_data.append(df.columns[i+3])   # Profit columns
        
        # Sum metrics across all months for each SKU
        results = {}
        
        # Sum Sales
        df_sales_cols = df[['SKU'] + sales_data].copy()
        for col in sales_data:
            df_sales_cols[col] = pd.to_numeric(df_sales_cols[col], errors='coerce')
        results['sales'] = df_sales_cols.groupby('SKU')[sales_data].sum().sum(axis=1).reset_index()
        results['sales'].columns = ['SKU', 'TotalSales']
        
        # Sum COGS
        df_cogs_cols = df[['SKU'] + cogs_data].copy()
        for col in cogs_data:
            df_cogs_cols[col] = pd.to_numeric(df_cogs_cols[col], errors='coerce')
        results['cogs'] = df_cogs_cols.groupby('SKU')[cogs_data].sum().sum(axis=1).reset_index()
        results['cogs'].columns = ['SKU', 'TotalCOGS']
        
        # Sum Profit
        df_profit_cols = df[['SKU'] + profit_data].copy()
        for col in profit_data:
            df_profit_cols[col] = pd.to_numeric(df_profit_cols[col], errors='coerce')
        results['profit'] = df_profit_cols.groupby('SKU')[profit_data].sum().sum(axis=1).reset_index()
        results['profit'].columns = ['SKU', 'TotalProfit']
        
        # Sum Quantity
        df_qty_cols = df[['SKU'] + quantity_data].copy()
        for col in quantity_data:
            df_qty_cols[col] = pd.to_numeric(df_qty_cols[col], errors='coerce')
        results['quantity'] = df_qty_cols.groupby('SKU')[quantity_data].sum().sum(axis=1).reset_index()
        results['quantity'].columns = ['SKU', 'TotalQuantity']
        
        return results
        
    except Exception as e:
        print(f"Error loading combined sales report: {e}")
        return None


def load_sales_report(file_pattern, value_name):
    """Loads and processes a sales report from an Excel file (backward compatibility)."""
    try:
        # Find the file that matches the pattern
        files = glob.glob(file_pattern)
        if not files:
            print(f"Warning: No file found for pattern '{file_pattern}'")
            return None
        
        file_path = files[0]
        # Skip the first 4 rows which contain header info
        df = pd.read_excel(file_path, sheet_name='Sheet', skiprows=4)
        
        # The SKU is in the first column, let's rename it
        df = df.rename(columns={df.columns[0]: 'SKU'})
        
        # Drop the second unnamed column
        if 'Unnamed: 1' in df.columns:
            df = df.drop(columns=['Unnamed: 1'])

        # Melt the dataframe to have months as rows instead of columns
        df = df.melt(id_vars='SKU', var_name='Month', value_name=value_name)
        
        # Sum up the values for each SKU across all months
        total_values = df.groupby('SKU')[value_name].sum().reset_index()
        
        return total_values
    except Exception as e:
        print(f"Error loading sales report for pattern '{file_pattern}': {e}")
        return None


def load_replenishment_report(file_pattern):
    """Loads the replenishment report CSV."""
    try:
        files = glob.glob(file_pattern)
        if not files:
            print(f"Warning: No file found for pattern '{file_pattern}'")
            return None
        df = pd.read_csv(files[0])
        # Clean up column names
        df.columns = df.columns.str.strip()
        # Clean up SKU column
        df['SKU'] = df['SKU'].astype(str).str.replace('="', '').str.replace('"', '')
        return df
    except Exception as e:
        print(f"Error loading replenishment report: {e}")
        return None


def load_inventory_list(file_pattern):
    """Loads the inventory list CSV."""
    try:
        files = glob.glob(file_pattern)
        if not files:
            print(f"Warning: No file found for pattern '{file_pattern}'")
            return None
        df = pd.read_csv(files[0])
        
        # Check for required columns
        required_columns = ['ProductCode', 'LastSuppliedBy']
        optional_columns = ['Name', 'SupplierProductCode']  # Add product name and supplier product code
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"Warning: Missing required columns in inventory list: {missing_columns}")
            return None
        
        # Keep required columns plus any available optional columns
        columns_to_keep = required_columns.copy()
        for col in optional_columns:
            if col in df.columns:
                columns_to_keep.append(col)
        
        df = df[columns_to_keep]
        
        # Remove duplicates, keeping the first entry for each product
        df = df.drop_duplicates(subset=['ProductCode'], keep='first')
        return df
    except Exception as e:
        print(f"Error loading inventory list: {e}")
        return None


def load_availability_report(file_pattern, location_prefix):
    """Loads the availability report CSV and aggregates stock for a given location."""
    try:
        files = glob.glob(file_pattern)
        if not files:
            print(f"Warning: No file found for pattern '{file_pattern}'")
            return None
        df = pd.read_csv(files[0])
        # Filter for locations matching the prefix (e.g., 'NC' or 'CA')
        df_location = df[df['Location'].str.startswith(location_prefix, na=False)]
        # Group by SKU and sum Available and OnOrder stock
        agg_stock = df_location.groupby('SKU').agg(
            TotalStock=('Available', 'sum'),
            TotalOnOrder=('OnOrder', 'sum')
        ).reset_index()
        return agg_stock
    except Exception as e:
        print(f"Error loading availability report: {e}")
        return None


def calculate_profit_margin(df):
    """Calculates the profit margin for each product."""
    # Profit Margin = Total Profit / Total Sales
    # Avoid division by zero
    df['ProfitMargin'] = df.apply(
        lambda row: row['TotalProfit'] / row['TotalSales'] if row['TotalSales'] != 0 else 0,
        axis=1
    )
    return df


def adjust_sales_velocity(df):
    """Adjusts sales velocity based on profit margin and price tier."""
    
    # Clean 'Cost price' column
    df['Cost price'] = pd.to_numeric(df['Cost price'], errors='coerce').fillna(0)

    def get_adjustment(row):
        margin = row['ProfitMargin']
        price = row['Cost price']
        
        # Tier 1: Under $100
        if price < 100:
            if margin < 0.1: return -0.8
            if 0.1 <= margin < 0.2: return -0.5
            if 0.2 <= margin < 0.25: return -0.2
            if 0.26 <= margin <= 0.33: return 0
            if margin > 0.33: return 0.1
        # Tier 2: $100–$250
        elif 100 <= price < 250:
            if margin < 0.1: return -0.8
            if 0.1 <= margin < 0.2: return -0.5
            if 0.2 <= margin <= 0.3: return 0
            if margin > 0.3: return 0.05
        # Tier 3: $250–$750
        elif 250 <= price < 750:
            if margin < 0.05: return -0.8
            if 0.05 <= margin < 0.15: return -0.5
            if 0.15 <= margin <= 0.28: return 0
            if margin > 0.28: return 0.03
        # Tier 4: $750+
        elif price >= 750:
            if margin < 0.05: return -0.9
            if 0.05 <= margin < 0.12: return -0.6
            if 0.12 <= margin <= 0.25: return 0
            if margin > 0.25: return 0.02
        return 0

    df['VelocityAdjustment'] = df.apply(get_adjustment, axis=1)
    df['AdjustedSalesVelocity'] = df['Adjusted sales velocity/day'] * (1 + df['VelocityAdjustment'])
    
    return df


def calculate_po_quantity(df):
    """Calculates the final purchase order quantity."""
    # Days of Stock = Lead Time + 3 days
    df['Lead time'] = pd.to_numeric(df['Lead time'], errors='coerce').fillna(0)
    df['DaysOfStock'] = df['Lead time'] + 3
    
    # Target stock level
    df['TargetStock'] = df['AdjustedSalesVelocity'] * df['DaysOfStock']
    
    # Ensure TotalStock and TotalOnOrder are numbers and fill missing with 0
    df['TotalStock'] = pd.to_numeric(df['TotalStock'], errors='coerce').fillna(0)
    df['TotalOnOrder'] = pd.to_numeric(df['TotalOnOrder'], errors='coerce').fillna(0)
    
    # PO Quantity = Target Stock - Current Stock - On Order Stock
    df['PO_Quantity'] = df['TargetStock'] - df['TotalStock'] - df['TotalOnOrder']
    
    # Don't order if we have enough stock
    df.loc[df['PO_Quantity'] < 0, 'PO_Quantity'] = 0

    # Round up to the nearest whole number
    df['PO_Quantity'] = df['PO_Quantity'].apply(lambda x: int(x) + 1 if x > int(x) else int(x))

    return df


def generate_po_csv(df, output_filename="purchase_order.csv"):
    """Generates the final CSV for Cin7 Core import."""
    
    # Calculate Adjusted Monthly Sales before any aggregation
    df['Adjusted Monthly Sales'] = df['Adjusted sales velocity/day'] * 30
    
    # Select and prepare columns for the PO
    available_columns = ['LastSuppliedBy', 'SKU', 'PO_Quantity', 'Cost price', 'Lead time', 'Adjusted Monthly Sales']
    
    # Check if SupplierProductCode is available and add it after supplier
    if 'SupplierProductCode' in df.columns:
        available_columns.insert(1, 'SupplierProductCode')  # Insert after LastSuppliedBy
    
    # Check if ProductName is available and add it after SKU
    if 'ProductName' in df.columns:
        sku_index = available_columns.index('SKU')
        available_columns.insert(sku_index + 1, 'ProductName')  # Insert after SKU
    
    # Select only columns that exist in the dataframe
    existing_columns = [col for col in available_columns if col in df.columns]
    po_data = df[existing_columns].copy()
    
    # Rename core columns for Cin7 import
    rename_mapping = {
        'LastSuppliedBy': 'SupplierName*',
        'SKU': 'Product*', 
        'PO_Quantity': 'Quantity*',
        'Cost price': 'Price/Amount*'
    }
    po_data.rename(columns=rename_mapping, inplace=True)
    
    # Filter out rows with no supplier or zero quantity
    po_data = po_data[po_data['SupplierName*'].notna()]
    po_data = po_data[po_data['Quantity*'] > 0]
    
    # Filter out excluded suppliers (case-insensitive)
    excluded_suppliers = load_excluded_suppliers()
    if excluded_suppliers:
        print(f"Filtering out {len(excluded_suppliers)} excluded suppliers...")
        original_count = len(po_data)
        po_data = po_data[~po_data['SupplierName*'].str.lower().isin(excluded_suppliers)]
        excluded_count = original_count - len(po_data)
        print(f"Removed {excluded_count} items from excluded suppliers.")

    # For aggregation, we need to group by columns that should be the same for each product+supplier
    group_cols = ['SupplierName*', 'Product*', 'Price/Amount*']
    agg_dict = {'Quantity*': 'sum'}
    
    # Add non-aggregated columns to the group (they should be the same for each product)
    preserve_cols = []
    for col in po_data.columns:
        if col not in group_cols and col != 'Quantity*':
            preserve_cols.append(col)
            agg_dict[col] = 'first'  # Take the first value since they should be the same
    
    # Aggregate quantities for the same product and supplier
    po_data = po_data.groupby(group_cols).agg(agg_dict).reset_index()

    # Add other required columns with default values
    po_data['RecordType*'] = 'Order'
    
    # Define the final column order
    final_columns = ['RecordType*', 'SupplierName*']
    
    # Add SupplierProductCode if it exists
    if 'SupplierProductCode' in po_data.columns:
        final_columns.append('SupplierProductCode')
    
    # Add the core required columns
    final_columns.append('Product*')
    
    # Add product name right after SKU if it exists  
    if 'ProductName' in po_data.columns:
        final_columns.append('ProductName')
    
    # Continue with remaining core columns
    final_columns.extend(['Quantity*', 'Price/Amount*'])
    
    # Add the additional informational columns at the end
    if 'Lead time' in po_data.columns:
        final_columns.append('Lead time')
    if 'Adjusted Monthly Sales' in po_data.columns:
        final_columns.append('Adjusted Monthly Sales')
    
    # Select only columns that exist in our data
    final_columns = [col for col in final_columns if col in po_data.columns]
    po_data = po_data[final_columns]

    po_data.to_csv(output_filename, index=False)
    print(f"PO file '{output_filename}' generated successfully.")


def run_po_generation(upload_folder, location):
    """
    Main function to run the PO generation process for a specific location.
    """
    print(f"Starting PO Generation Process for {location.upper()}...")

    # Define file patterns
    sales_pattern = os.path.join(upload_folder, "Sales by Product Details Report - Sales.xlsx")
    cogs_pattern = os.path.join(upload_folder, "Sales by Product Details Report - COGS.xlsx")
    profit_pattern = os.path.join(upload_folder, "Sales by Product Details Report - Profit.xlsx")
    quantity_pattern = os.path.join(upload_folder, "Sales by Product Details Report - Quantity.xlsx")
    # Try both filename formats (with spaces and with underscores)
    replenishment_pattern1 = os.path.join(upload_folder, f"replenishment-Combined {location.upper()} Warehouses-variants-*.csv")
    replenishment_pattern2 = os.path.join(upload_folder, f"replenishment-Combined_{location.upper()}_Warehouses-variants-*.csv")
    
    # Use whichever pattern finds a file
    if glob.glob(replenishment_pattern1):
        replenishment_pattern = replenishment_pattern1
    else:
        replenishment_pattern = replenishment_pattern2
    inventory_pattern = os.path.join(upload_folder, "InventoryList_*.csv")
    availability_pattern = os.path.join(upload_folder, "AvailabilityReport_*.csv")

    # Try to load combined sales report first, fall back to separate files
    combined_sales_pattern = os.path.join(upload_folder, "Sales by Product Details Report.xlsx")
    combined_files = glob.glob(combined_sales_pattern)
    
    if combined_files:
        print("Found combined Sales by Product Details Report - using combined file...")
        combined_data = load_combined_sales_report(combined_files[0])
        if combined_data:
            sales_df = combined_data['sales']
            cogs_df = combined_data['cogs'] 
            profit_df = combined_data['profit']
            quantity_df = combined_data['quantity']
        else:
            print("Error loading combined file, aborting.")
            return None
    else:
        print("Combined file not found - looking for separate sales files...")
        # Load separate sales reports (backward compatibility)
        sales_df = load_sales_report(sales_pattern, "TotalSales")
        cogs_df = load_sales_report(cogs_pattern, "TotalCOGS")
        profit_df = load_sales_report(profit_pattern, "TotalProfit")
        quantity_df = load_sales_report(quantity_pattern, "TotalQuantity")

    replenishment_df = load_replenishment_report(replenishment_pattern)
    inventory_df = load_inventory_list(inventory_pattern)
    availability_df = load_availability_report(availability_pattern, location.upper())

    # Check if replenishment data was loaded
    if replenishment_df is None:
        print(f"Could not find replenishment file for {location.upper()}. Aborting.")
        return None

    # --- Data Merging ---
    if sales_df is not None and cogs_df is not None and profit_df is not None and quantity_df is not None:
        merged_sales = sales_df.merge(cogs_df, on="SKU", how="outer")
        merged_sales = merged_sales.merge(profit_df, on="SKU", how="outer")
        merged_sales = merged_sales.merge(quantity_df, on="SKU", how="outer")
    else:
        print("Could not merge sales data due to loading errors.")
        return

    # Ensure SKU types are consistent for merging
    replenishment_df['SKU'] = replenishment_df['SKU'].astype(str)
    merged_sales['SKU'] = merged_sales['SKU'].astype(str)
    inventory_df['ProductCode'] = inventory_df['ProductCode'].astype(str)
    availability_df['SKU'] = availability_df['SKU'].astype(str)

    # Merge replenishment data with sales data
    df = replenishment_df.merge(merged_sales, on='SKU', how='left')

    # Merge with inventory data
    df = df.merge(inventory_df, left_on='SKU', right_on='ProductCode', how='left')

    # Handle Name column conflict (both replenishment and inventory have 'Name')
    # Use inventory Name (Name_y) as it's more authoritative, rename it back to 'Name'
    if 'Name_y' in df.columns:
        df['ProductName'] = df['Name_y']  # Use inventory product name
        df = df.drop(columns=['Name_x', 'Name_y'])  # Clean up duplicate name columns
    elif 'Name_x' in df.columns:
        df['ProductName'] = df['Name_x']  # Fallback to replenishment name
        df = df.drop(columns=['Name_x'])

    # Merge with availability data
    df = df.merge(availability_df, on='SKU', how='left')
    
    # --- Profit Margin Calculation ---
    df = calculate_profit_margin(df)
    
    # --- Adjust Sales Velocity ---
    df = adjust_sales_velocity(df)

    # --- Calculate PO Quantity ---
    df = calculate_po_quantity(df)
    
    # --- Generate PO CSV ---
    output_filename = f"purchase_order_{location.lower()}.csv"
    generate_po_csv(df, output_filename)
    
    return output_filename
