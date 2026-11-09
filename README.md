# Transaction Link Tracker — Audit & Variance Analysis for Odoo 18.0

[![Odoo Version](https://img.shields.io/badge/Odoo-18.0-714B67.svg?style=flat-square&logo=odoo&logoColor=white)](https://www.odoo.com)
[![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-blue.svg?style=flat-square)](https://www.gnu.org/licenses/lgpl-3.0)
[![Author: XodetiStudio](https://img.shields.io/badge/Author-XodetiStudio-06b6d4.svg?style=flat-square)](https://xodetistudio.id)
[![Category](https://img.shields.io/badge/Category-Accounting%20%2F%20Audit-orange.svg?style=flat-square)](https://xodetistudio.id)

The Ultimate Enterprise Audit Tool for **Odoo 18.0 (Community & Enterprise)**. Detect procurement price variances, compute Real Manufacturing HPP (COGS), identify orphan invoices, and trace complete document lifecycles across Sales, Purchasing, Manufacturing, and Inventory. Distributed **100% Free and Open Source** under the LGPL-3 license by **[XodetiStudio](https://xodetistudio.id)**.

---

## 🌟 Key Features

1. **Procurement Price Variance & Leakage Audit**
   - Automatically computes price differences between Purchase Orders and Vendor Bills.
   - Accurately converts multi-currency transactions.
   - Isolates Net Unit Price from Tax/VAT differences for pure financial discrepancy analysis.
   - Highlights discrepancies in bold **RED** immediately.

2. **True Manufacturing Cost (Real HPP)**
   - Computes actual production cost combining: **Raw Material + Direct Labor + Machine Overhead / Workcenter Costs**.
   - Compares production cost directly against sales price to reveal real operating margins.

3. **Smart Orphan Document Discovery**
   - Detects direct invoices/bills that have no originating Purchase Order or Sales Order.
   - Illuminates corporate expense blind spots (e.g. direct utility bills, unauthorized local purchasing).

4. **Complete Logistics & Traceability Audit**
   - Tracks Internal Transfer chains (`Source` &rarr; `Transit` &rarr; `Destination`).
   - Detects scrap/damaged goods orders linked to specific stock moves.

5. **Auditor Workspace & Dashboard**
   - Fullscreen dashboard with date, company, and transaction stream filters.
   - Auditor guide panel and visual status indicators.

---

## 📋 Technical Requirements & Dependencies

- **Odoo Version**: 18.0 (Community or Enterprise)
- **Dependencies**:
  - `base`
  - `sale`
  - `purchase`
  - `stock`
  - `account`
  - `mrp`

---

## 🚀 Installation

1. Clone or download this repository.
2. Copy the `transaction_tracker` directory to your Odoo `custom_addons` path.
3. Restart your Odoo server.
4. Enable **Developer Mode** in Settings.
5. Navigate to **Apps** &rarr; **Update Apps List**.
6. Search for `Transaction Link Tracker` and click **Activate**.

---

## ⚙️ How to Use

1. Navigate to the **Transaction Tracker** / **Audit** menu.
2. Choose your target **Audit Period**, **Company**, and **Transaction Type** (Purchasing, Sales, Manufacturing, or Logistics).
3. Click **Scan Transactions** to initiate instant batch analysis.
4. Drill down on highlighted red variance lines or orange orphan badges to inspect document discrepancies.

---

## 💼 Explore Flagship Enterprise Suites by XodetiStudio

| Suite | Description | Pricing |
| :--- | :--- | :--- |
| **[Docu eSign Suite](https://xodetistudio.id/?deck=esign)** | PAdES-B-LT Cryptographic PDF Signing, Statutory PERURI e-Materai (UU No. 10/2020), Drag-and-Drop Coordinate Designer, Smart PIN 2FA. Zero SaaS tolls. | €600 (One-Time) |
| **[PathSFA Suite](https://xodetistudio.id)** | Enterprise Offline-First Sales Force Automation Flutter Mobile App + Odoo 18 Backend: GPS visit tracking, order booking, stock check, anti-fraud telemetry. | €2,999 (One-Time) |
| **[PathTMS Suite](https://xodetistudio.id)** | Enterprise Fleet, Dispatch & Transport Management System: delivery optimization, driver companion mobile app, fuel accounting, digital POD. | €2,999 (One-Time) |

---

## 📞 Support, Customization & Consulting

Need custom forensic audit algorithms, automated email anomaly triggers, or custom ERP integration?

- **Website**: [https://xodetistudio.id](https://xodetistudio.id)
- **WhatsApp**: [+62 878-9516-4590](https://wa.me/6287895164590?text=Halo%20XodetiStudio%2C%20saya%20tertarik%20konsultasi%20modul%20Transaction%20Link%20Tracker.)
- **Email**: [info@xodetistudio.id](mailto:info@xodetistudio.id)

---

## 📄 License

This module is licensed under the **GNU Lesser General Public License v3.0 (LGPL-3)**.  
Copyright &copy; 2026 [XodetiStudio](https://xodetistudio.id). Engineered by Muhammad Thoriq.

