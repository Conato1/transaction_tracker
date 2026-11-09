# -*- coding: utf-8 -*-
{
    'name': "Transaction Link Tracker - Audit & Variance Analysis",
    'summary': """
        The Ultimate Audit Tool: Track Purchase Variance, True Manufacturing Cost (HPP), 
        Orphan Invoices, and Full Document Lifecycle (PO/SO/MO/Picking).
    """,
    'description': """
Transaction Link Tracker (Community Audit Edition)
=================================================
Are you losing money due to unmatched invoices, hidden price variances, or inaccurate manufacturing costs? 
This module provides a 360-degree audit view to track the full lifecycle of your transactions 
across Sales, Purchasing, Inventory, Manufacturing, and Accounting.

TOP 5 KEY FEATURES:
-------------------
1. Financial Variance Detection (Price Leakage)
   - Automatically calculates price differences between Purchase Orders and Vendor Bills.
   - Handles Multi-Currency conversions accurately.
   - Smart logic to isolate Net Price from Tax/VAT differences for pure price auditing.
   - Highlights discrepancies in RED instantly.

2. True Manufacturing Cost (Real HPP)
   - Calculates the Real HPP including Raw Material + Labor Cost + Machine Overhead (Workcenter Costs).
   - Compares Production Cost vs Sales Price in one centralized view.

3. Smart Discovery for "Orphan" Documents
   - Detects Direct Invoices/Bills that have no source document (PO/SO).
   - Identifies blind spots in expenses (direct utility bills, unapproved purchases).

4. Full Logistics Audit
   - Track Internal Transfers chain (Source -> Transit -> Destination).
   - Detect Scrap Orders (broken/damaged goods) linked to specific stock moves.

5. Enterprise Audit Dashboard
   - Fullscreen dashboard with interactive filters by date, company, and document type.
   - Dedicated "Audit Guide & Legend" panel for compliance teams and external auditors.

100% Free and Open Source under LGPL-3 by XodetiStudio (https://xodetistudio.id).
    """,
    'author': "XodetiStudio",
    'website': "https://xodetistudio.id",
    'category': 'Accounting/Audit',
    'version': '18.0.1.0.0',
    'license': 'LGPL-3',

    'depends': ['base', 'sale', 'purchase', 'stock', 'account', 'mrp'],

    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/transaction_tracker_views.xml',
    ],

    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
