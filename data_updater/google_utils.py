from google.oauth2.service_account import Credentials
import gspread
import os
import pandas as pd
import requests
import re


def get_spreadsheet(read_only=False):
    """
    Get the main Google Spreadsheet using credentials and URL from environment variables
    
    Args:
        read_only (bool): If True, uses public CSV export when credentials are missing
    """
    spreadsheet_url = os.getenv("SPREADSHEET_URL")
    if not spreadsheet_url:
        raise ValueError("SPREADSHEET_URL environment variable is not set")
    
    # Check for credentials
    if not os.path.exists('credentials.json'):
        if read_only:
            return ReadOnlySpreadsheet(spreadsheet_url)
        else:
            raise FileNotFoundError("credentials.json not found. Use read_only=True for read-only access.")
    
    # Normal authenticated access
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_file('credentials.json', scopes=scope)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_url(spreadsheet_url)
    return spreadsheet

class ReadOnlySpreadsheet:
    """Read-only wrapper for Google Sheets using public CSV export"""
    
    def __init__(self, spreadsheet_url):
        self.spreadsheet_url = spreadsheet_url
        self.sheet_id = self._extract_sheet_id(spreadsheet_url)
        
    def _extract_sheet_id(self, url):
        """Extract sheet ID from Google Sheets URL"""
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if not match:
            raise ValueError("Invalid Google Sheets URL")
        return match.group(1)
    
    def worksheet(self, title):
        """Return a read-only worksheet"""
        return ReadOnlyWorksheet(self.sheet_id, title)

class ReadOnlyWorksheet:
    """Read-only worksheet that fetches data via CSV export"""
    
    def __init__(self, sheet_id, title):
        self.sheet_id = sheet_id
        self.title = title
        
    def get_all_records(self):
        """Get all records from the worksheet as a list of dictionaries"""
        try:
            # Use the public CSV export URL
            csv_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/gviz/tq?tqx=out:csv&sheet={self.title}"
            response = requests.get(csv_url, timeout=30)
            response.raise_for_status()
            
            # Read CSV data into DataFrame
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            
            # Convert to list of dictionaries (same format as gspread)
            return df.to_dict('records')
            
        except Exception as e:
            print(f"Warning: Could not fetch data from sheet '{self.title}': {e}")
            return []
    
    def get_all_values(self):
        """Get all values from the worksheet as a list of lists"""
        try:
            csv_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/gviz/tq?tqx=out:csv&sheet={self.title}"
            response = requests.get(csv_url, timeout=30)
            response.raise_for_status()
            
            # Read CSV and return as list of lists
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            
            # Include headers and convert to list of lists
            headers = [df.columns.tolist()]
            data = df.values.tolist()
            return headers + data
            
        except Exception as e:
            print(f"Warning: Could not fetch data from sheet '{self.title}': {e}")
            return []