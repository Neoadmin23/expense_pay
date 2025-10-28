# Copyright (c) 2025, Ahmad Pasha
# Author: Ahmad Pasha
# License: MIT

import frappe
import os

def set_new_saudi_riyal_symbol():
    """
    Updates the SAR currency symbol in the Currency doctype to the new SVG-based symbol.
    This function is intended to be run on app installation.
    """
    # Dynamically get the app name from the file's path
    # __file__ is the path to the current script (utils.py)
    # os.path.dirname() gets the directory of the file
    # os.path.basename() gets the folder name, which is the app name
    app_name = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Check if the Currency Doctype and SAR currency existb  
    if frappe.db.exists("DocType", "Currency") and frappe.db.exists("Currency", "SAR"):
        try:
            # Construct the path to the self-hosted SVG symbol
            svg_path = f"/assets/{app_name}/images/sar-symbol.svg"
            symbol_html = f'<img src="{svg_path}" style="height: 0.9em; vertical-align: middle;">'

            # Get the SAR currency document
            sar_doc = frappe.get_doc("Currency", "SAR")
            
            # Update the symbol if it's not already the new one
            if sar_doc.symbol != symbol_html:
                sar_doc.symbol = symbol_html
                sar_doc.save(ignore_permissions=True)
                frappe.db.commit()
                print(f"Successfully updated the Saudi Riyal (SAR) currency symbol for app: {app_name}.")
            else:
                print(f"Saudi Riyal (SAR) currency symbol is already up-to-date for app: {app_name}.")

        except Exception as e:
            print(f"An error occurred while updating the SAR currency symbol for app {app_name}: {e}")

