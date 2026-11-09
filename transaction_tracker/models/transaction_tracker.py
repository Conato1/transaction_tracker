# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import timedelta
import re  # Import Regex untuk pencarian teks yang akurat

class TransactionTracker(models.Model):
    _name = 'transaction.tracker'
    _description = 'Transaction Link Tracker Header'
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    date_from = fields.Date(string='Date From', required=True, default=fields.Date.today)
    date_to = fields.Date(string='Date To', required=True, default=fields.Date.today)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    
    # 1. SCOPE
    tracking_type = fields.Selection([
        ('all', 'All Transactions'),
        ('purchase', 'Purchase Only'),
        ('sale', 'Sales Only'),
        ('manufacturing', 'Manufacturing (MO)'),
        ('internal', 'Internal Transfer & Scrap')
    ], string='Scanning Scope', default='all', required=True)

    # 2. FILTER
    view_filter = fields.Selection([
        ('all', 'Show All'),
        ('sale', 'Sales Only'),
        ('purchase', 'Purchase Only'),
        ('direct', 'Direct / Orphan Only'),
        ('manufacturing', 'Manufacturing Only'),
        ('internal', 'Internal/Scrap Only')
    ], string='View Filter', default='all', required=True)

    # MASTER DATA
    line_ids = fields.One2many('transaction.tracker.line', 'tracker_id', string='All Lines')
    
    # DISPLAY DATA
    visible_line_ids = fields.Many2many('transaction.tracker.line', compute='_compute_visible_lines', string='Visible Lines')

    @api.depends('line_ids', 'view_filter')
    def _compute_visible_lines(self):
        for record in self:
            if record.view_filter == 'all':
                record.visible_line_ids = record.line_ids
            elif record.view_filter == 'direct':
                record.visible_line_ids = record.line_ids.filtered(lambda l: l.is_direct)
            else:
                record.visible_line_ids = record.line_ids.filtered(lambda l: l.transaction_type == record.view_filter)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('transaction.tracker') or 'New'
        return super(TransactionTracker, self).create(vals)

    # -------------------------------------------------------------------------
    # HELPER: PRE-FETCHING (SOLUSI N+1 QUERY)
    # -------------------------------------------------------------------------
    def _prefetch_candidate_invoices(self, move_type):
        """
        Mengambil semua Invoice 'Orphan' (Tanpa Link PO/SO) dalam range tanggal + buffer.
        Dilakukan SEKALI di awal untuk menghindari query berulang di dalam loop.
        """
        # Buffer 60 hari karena invoice mungkin datang telat
        min_date = self.date_from
        max_date = self.date_to + timedelta(days=60)

        domain = [
            ('move_type', '=', move_type),
            ('state', '=', 'posted'),
            ('payment_state', '!=', 'reversed'),
            ('company_id', '=', self.company_id.id),
            ('invoice_date', '>=', min_date),
            ('invoice_date', '<=', max_date),
            # Hanya ambil yang tidak punya relasi standar (Orphan)
            ('invoice_origin', '=', False) 
        ]
        
        # Tambahan filter spesifik agar tidak mengambil invoice yang sudah link via Line
        if move_type == 'out_invoice':
            domain.append(('invoice_line_ids.sale_line_ids', '=', False))
        elif move_type == 'in_invoice':
            domain.append(('invoice_line_ids.purchase_line_id', '=', False))
            
        return self.env['account.move'].search(domain)

    # -------------------------------------------------------------------------
    # HELPER: CURRENCY CONVERTER
    # -------------------------------------------------------------------------
    def _convert_amount(self, amount, from_curr, to_curr, date):
        """
        Mengkonversi nilai uang dengan aman.
        """
        if not amount or from_curr == to_curr:
            return amount
        return from_curr._convert(amount, to_curr, self.company_id, date or fields.Date.today())

    # -------------------------------------------------------------------------
    # MAIN SCANNING ACTION
    # -------------------------------------------------------------------------
    def action_scan_transactions(self):
        self.ensure_one()
        self.line_ids.unlink()
        lines_to_create = []

        # PRE-FETCH DATA (Solusi N+1)
        # Tarik data sekali saja ke RAM
        candidate_bills = self.env['account.move']
        candidate_invoices = self.env['account.move']
        
        if self.tracking_type in ['all', 'purchase']:
            candidate_bills = self._prefetch_candidate_invoices('in_invoice')
        
        if self.tracking_type in ['all', 'sale']:
            candidate_invoices = self._prefetch_candidate_invoices('out_invoice')

        # ===============================================
        # 1. SCAN PURCHASE ORDERS
        # ===============================================
        if self.tracking_type in ['all', 'purchase']:
            purchase_orders = self.env['purchase.order'].search([
                ('date_order', '>=', self.date_from),
                ('date_order', '<=', self.date_to),
                ('company_id', '=', self.company_id.id),
                ('state', 'in', ['purchase', 'done'])
            ])
            
            for po in purchase_orders:
                picking_names = ", ".join(po.picking_ids.mapped('name'))
                
                # A. Standard Linked Bills
                linked_bills = po.invoice_ids.filtered(lambda x: x.move_type in ('in_invoice', 'in_refund') and x.state != 'cancel')
                
                is_manual_match = False
                ambiguous_match = False
                
                # B. Smart Discovery (Jika belum lunas/tidak ada link)
                # Menggunakan Python Filtering (RAM) bukan SQL Search (DB) -> CEPAT
                if not linked_bills or all(b.payment_state != 'paid' for b in linked_bills):
                    # Filter kandidat yang Partnernya sama
                    potential_matches = candidate_bills.filtered(lambda b: b.partner_id == po.partner_id)
                    
                    found_bills = self.env['account.move']
                    for bill in potential_matches:
                        # LOGIKA MATCHING YANG LEBIH KETAT (False Positive Fix)
                        # Cek Ref/Origin menggunakan Regex Word Boundary (\b)
                        # Agar "PO10" TIDAK match dengan "PO100"
                        text_to_search = (bill.ref or '') + ' ' + (bill.invoice_origin or '')
                        pattern = r'\b' + re.escape(po.name) + r'\b'
                        
                        if re.search(pattern, text_to_search, re.IGNORECASE):
                            found_bills |= bill
                        # Fallback: Match by Exact Amount (Hanya jika tanggal valid)
                        elif bill.amount_total == po.amount_total and not bill.ref:
                             found_bills |= bill

                    if found_bills:
                        if len(found_bills) > 1:
                            ambiguous_match = True
                        linked_bills |= found_bills
                        is_manual_match = True

                invoice_names = ", ".join(linked_bills.mapped('name'))
                if ambiguous_match: invoice_names += " (AMBIGUOUS)"
                elif is_manual_match: invoice_names += " (Smart Match)"

                # C. Financial Calculation (Currency & Refund Fix)
                payment_status = 'not_paid'
                balance_due = 0.0
                total_invoiced_in_po_currency = 0.0
                due_date = False
                
                if linked_bills:
                    # Status Pembayaran
                    bill_states = linked_bills.mapped('payment_state')
                    if 'paid' in bill_states: payment_status = 'paid'
                    elif 'partial' in bill_states: payment_status = 'partial'
                    elif 'reversed' in bill_states: payment_status = 'reversed'
                    
                    # Due Date (Terkecil dari yang belum lunas)
                    unpaid_bills = linked_bills.filtered(lambda x: x.payment_state not in ['paid', 'reversed'])
                    if unpaid_bills:
                        due_date = min(unpaid_bills.mapped('invoice_date_due'))

                    # LOOP CALCULATIONS
                    for bill in linked_bills:
                        # 1. Tentukan Tanda (Positif/Negatif)
                        sign = -1 if bill.move_type == 'in_refund' else 1
                        
                        # 2. Konversi Kurs (Bill Currency -> PO Currency)
                        converted_amount = self._convert_amount(
                            bill.amount_total, 
                            bill.currency_id, 
                            po.currency_id, 
                            bill.invoice_date or fields.Date.today()
                        )
                        converted_residual = self._convert_amount(
                            bill.amount_residual, 
                            bill.currency_id, 
                            po.currency_id, 
                            bill.invoice_date or fields.Date.today()
                        )

                        total_invoiced_in_po_currency += (converted_amount * sign)
                        balance_due += (converted_residual * sign)
                
                # D. Variance Calculation (Akurat karena sudah satu mata uang)
                # Variance = Tagihan Real - Nilai PO
                variance = total_invoiced_in_po_currency - po.amount_total
                # Abaikan selisih kecil (pembulatan)
                if abs(variance) < 1.0: 
                    variance = 0.0

                # E. Delivery Progress
                total_qty = sum(po.order_line.mapped('product_qty'))
                received_qty = sum(po.order_line.mapped('qty_received'))
                progress = (received_qty / total_qty * 100) if total_qty > 0 else 0.0
                if progress > 100: progress = 100

                lines_to_create.append({
                    'tracker_id': self.id,
                    'transaction_type': 'purchase',
                    'is_direct': False,
                    'date': po.date_order,
                    'reference': po.name,
                    'partner_id': po.partner_id.id,
                    'user_id': po.user_id.id,
                    'amount_total': po.amount_total,
                    'amount_variance': variance, 
                    'balance_due': balance_due,
                    'invoice_date_due': due_date,
                    'delivery_progress': progress,
                    'currency_id': po.currency_id.id,
                    'source_doc_id': f'{po._name},{po.id}',
                    'related_picking_display': picking_names,
                    'related_invoice_display': invoice_names,
                    'status_display': dict(self.env['purchase.order'].fields_get(allfields=['state'])['state']['selection']).get(po.state),
                    'payment_status': payment_status,
                })

        # ===============================================
        # 2. SCAN SALES ORDERS
        # ===============================================
        if self.tracking_type in ['all', 'sale']:
            sales_orders = self.env['sale.order'].search([
                ('date_order', '>=', self.date_from),
                ('date_order', '<=', self.date_to),
                ('company_id', '=', self.company_id.id),
                ('state', 'in', ['sale', 'done'])
            ])

            for so in sales_orders:
                picking_names = ", ".join(so.picking_ids.mapped('name'))
                linked_invoices = so.invoice_ids.filtered(lambda x: x.move_type in ('out_invoice', 'out_refund') and x.state != 'cancel')
                
                is_manual_match = False
                ambiguous_match = False

                if not linked_invoices or all(i.payment_state != 'paid' for i in linked_invoices):
                    # Smart Discovery via RAM (Fast)
                    potential_matches = candidate_invoices.filtered(lambda i: i.partner_id == so.partner_id)
                    found_invoices = self.env['account.move']
                    
                    for inv in potential_matches:
                        text_to_search = (inv.ref or '') + ' ' + (inv.invoice_origin or '')
                        pattern = r'\b' + re.escape(so.name) + r'\b' # Regex Exact Match
                        
                        if re.search(pattern, text_to_search, re.IGNORECASE):
                            found_invoices |= inv
                        elif inv.amount_total == so.amount_total and not inv.ref:
                             found_invoices |= inv

                    if found_invoices:
                        if len(found_invoices) > 1: ambiguous_match = True
                        linked_invoices |= found_invoices
                        is_manual_match = True
                
                invoice_names = ", ".join(linked_invoices.mapped('name'))
                if ambiguous_match: invoice_names += " (AMBIGUOUS)"
                elif is_manual_match: invoice_names += " (Smart Match)"
                
                payment_status = 'not_paid'
                balance_due = 0.0
                total_invoiced_in_so_currency = 0.0
                due_date = False
                
                if linked_invoices:
                    inv_states = linked_invoices.mapped('payment_state')
                    if 'paid' in inv_states: payment_status = 'paid'
                    elif 'partial' in inv_states: payment_status = 'partial'
                    elif 'reversed' in inv_states: payment_status = 'reversed'
                    
                    unpaid_inv = linked_invoices.filtered(lambda x: x.payment_state not in ['paid', 'reversed'])
                    if unpaid_inv:
                        due_date = min(unpaid_inv.mapped('invoice_date_due'))

                    for inv in linked_invoices:
                        # 1. Tanda Refund (Credit Note)
                        sign = -1 if inv.move_type == 'out_refund' else 1
                        
                        # 2. Konversi Kurs
                        converted_amount = self._convert_amount(inv.amount_total, inv.currency_id, so.currency_id, inv.invoice_date)
                        converted_residual = self._convert_amount(inv.amount_residual, inv.currency_id, so.currency_id, inv.invoice_date)
                        
                        total_invoiced_in_so_currency += (converted_amount * sign)
                        balance_due += (converted_residual * sign)

                # Variance (Invoice - SO)
                variance = total_invoiced_in_so_currency - so.amount_total
                if abs(variance) < 1.0: variance = 0.0

                total_qty = sum(so.order_line.mapped('product_uom_qty'))
                delivered_qty = sum(so.order_line.mapped('qty_delivered'))
                progress = (delivered_qty / total_qty * 100) if total_qty > 0 else 0.0
                if progress > 100: progress = 100

                lines_to_create.append({
                    'tracker_id': self.id,
                    'transaction_type': 'sale',
                    'is_direct': False,
                    'date': so.date_order,
                    'reference': so.name,
                    'partner_id': so.partner_id.id,
                    'user_id': so.user_id.id,
                    'amount_total': so.amount_total, 
                    'amount_variance': variance,
                    'balance_due': balance_due,
                    'invoice_date_due': due_date,
                    'delivery_progress': progress,
                    'currency_id': so.currency_id.id,
                    'source_doc_id': f'{so._name},{so.id}', 
                    'related_picking_display': picking_names,
                    'related_invoice_display': invoice_names,
                    'status_display': dict(self.env['sale.order'].fields_get(allfields=['state'])['state']['selection']).get(so.state),
                    'payment_status': payment_status,
                })

        # ===============================================
        # 3. SCAN MANUFACTURING ORDERS (FIX HPP LENGKAP)
        # ===============================================
        if self.tracking_type in ['all', 'manufacturing']:
            production_orders = self.env['mrp.production'].search([
                ('date_start', '>=', self.date_from),
                ('date_start', '<=', self.date_to),
                ('company_id', '=', self.company_id.id),
                ('state', 'in', ['confirmed', 'progress', 'to_close', 'done'])
            ])

            for mo in production_orders:
                # 1. MATERIAL COST (Bahan Baku)
                material_cost = 0.0
                for move in mo.move_raw_ids:
                    # Pastikan ambil unit cost yang benar dari stock move
                    # Kalau move done, ambil value actual, kalau belum ambil standard price
                    if move.state == 'done':
                        # Di Odoo enterprise ada field stock_valuation_layer_ids, tapi agar aman di community:
                        # Kita estimasi: qty * price_unit
                        material_cost += sum(move.stock_valuation_layer_ids.mapped('value')) or (move.quantity * move.price_unit)
                    else:
                        material_cost += (move.product_uom_qty * move.product_id.standard_price)

                # 2. OPERATION/LABOR COST (Tenaga Kerja & Mesin)
                # Diambil dari Work Orders (Duration * Cost per Hour Workcenter)
                operation_cost = 0.0
                if mo.workorder_ids:
                    for wo in mo.workorder_ids:
                        # duration (menit) / 60 * cost_per_hour
                        # Gunakan real duration jika ada, atau expected
                        duration = wo.duration or wo.duration_expected
                        cost_hour = wo.workcenter_id.costs_hour or 0.0
                        operation_cost += (duration / 60.0) * cost_hour

                total_hpp = material_cost + operation_cost

                # Sales Value Calculation
                sales_value = 0.0
                linked_so_name = mo.origin
                linked_so = False
                if linked_so_name:
                    linked_so = self.env['sale.order'].search([('name', '=', linked_so_name)], limit=1)
                
                if linked_so:
                    so_line = linked_so.order_line.filtered(lambda l: l.product_id == mo.product_id)
                    if so_line:
                        sales_value = sum(so_line.mapped('price_subtotal'))
                    else:
                        sales_value = linked_so.amount_total
                else:
                    sales_value = mo.product_qty * mo.product_id.list_price

                mo_status = dict(self.env['mrp.production'].fields_get(allfields=['state'])['state']['selection']).get(mo.state)

                lines_to_create.append({
                    'tracker_id': self.id,
                    'transaction_type': 'manufacturing',
                    'is_direct': False,
                    'date': mo.date_start,
                    'reference': f"{mo.name} ({mo.product_id.default_code or ''})",
                    'partner_id': False,
                    'user_id': mo.user_id.id,
                    'amount_total': sales_value,
                    'material_cost': total_hpp, # Sekarang mencakup Material + Ops
                    'amount_variance': 0,
                    'balance_due': 0, 
                    'delivery_progress': mo.qty_producing / mo.product_qty * 100 if mo.product_qty else 0,
                    'currency_id': self.env.company.currency_id.id,
                    'source_doc_id': f'{mo._name},{mo.id}',
                    'related_picking_display': f"Src: {mo.origin or 'N/A'}",
                    'related_invoice_display': '-',
                    'status_display': mo_status,
                    'payment_status': 'not_paid',
                })

        # ===============================================
        # 4. SCAN INTERNAL TRANSFERS & SCRAPS
        # ===============================================
        if self.tracking_type in ['all', 'internal']:
            internal_pickings = self.env['stock.picking'].search([
                ('picking_type_code', '=', 'internal'),
                ('scheduled_date', '>=', self.date_from),
                ('scheduled_date', '<=', self.date_to),
                ('company_id', '=', self.company_id.id),
                ('state', '!=', 'cancel')
            ])

            for pick in internal_pickings:
                next_moves = pick.move_ids.mapped('move_dest_ids')
                next_pickings = next_moves.mapped('picking_id')
                next_picking_names = ", ".join(next_pickings.mapped('name'))
                scraps = self.env['stock.scrap'].search([('picking_id', '=', pick.id)])
                scrap_names = ", ".join([f"{s.name} (Qty: {s.scrap_qty})" for s in scraps])
                transfer_value = sum([m.quantity * m.price_unit for m in pick.move_ids])
                loc_info = f"{pick.location_id.name} -> {pick.location_dest_id.name}"
                
                related_info = ""
                if next_picking_names: related_info += f"Next: {next_picking_names}. "
                if scrap_names: related_info += f"SCRAP: {scrap_names}"
                if not related_info: related_info = "-"

                total_demand = sum(pick.move_ids.mapped('product_uom_qty'))
                total_done = sum(pick.move_ids.mapped('quantity'))
                progress = (total_done / total_demand * 100) if total_demand > 0 else 0.0

                lines_to_create.append({
                    'tracker_id': self.id,
                    'transaction_type': 'internal',
                    'is_direct': False,
                    'date': pick.scheduled_date,
                    'reference': f"{pick.name} ({loc_info})",
                    'partner_id': pick.partner_id.id,
                    'user_id': pick.user_id.id,
                    'amount_total': transfer_value,
                    'amount_variance': 0,
                    'balance_due': 0, 
                    'delivery_progress': progress,
                    'currency_id': self.env.company.currency_id.id,
                    'source_doc_id': f'{pick._name},{pick.id}',
                    'related_picking_display': related_info,
                    'related_invoice_display': '-',
                    'status_display': dict(self.env['stock.picking'].fields_get(allfields=['state'])['state']['selection']).get(pick.state),
                    'payment_status': 'not_paid',
                })

        # ===============================================
        # 5. SCAN DIRECT INVOICES (DIRECT / ORPHAN)
        # ===============================================
        def get_payment_status(state):
            if state == 'paid': return 'paid'
            if state == 'partial': return 'partial'
            if state == 'reversed': return 'reversed'
            return 'not_paid'

        # Direct Sales (Tagihan Customer Tanpa SO)
        if self.tracking_type in ['all', 'sale']:
            # Gunakan Candidate yang sudah di-prefetch jika ada, atau search ulang
            direct_invoices = candidate_invoices if candidate_invoices else self._prefetch_candidate_invoices('out_invoice')
            
            # Filter ulang untuk memastikan benar-benar Orphan (karena prefetch bisa saja mengambil yang Smart Match)
            # Logika: Invoice ini tidak boleh ada di list 'linked_invoices' manapun.
            # Namun untuk simplifikasi performa: Kita cek relasi Line-nya (Hard link)
            direct_invoices = direct_invoices.filtered(lambda i: not i.invoice_line_ids.sale_line_ids)

            for inv in direct_invoices:
                # Perhitungan saldo langsung (Direct tidak ada variance karena tidak ada SO pembanding)
                sign = -1 if inv.move_type == 'out_refund' else 1
                lines_to_create.append({
                    'tracker_id': self.id,
                    'transaction_type': 'sale',
                    'is_direct': True,
                    'date': inv.invoice_date,
                    'reference': f"{inv.name}",
                    'partner_id': inv.partner_id.id,
                    'user_id': inv.invoice_user_id.id or inv.user_id.id,
                    'amount_total': inv.amount_total * sign,
                    'amount_variance': 0,
                    'balance_due': inv.amount_residual * sign,
                    'invoice_date_due': inv.invoice_date_due,
                    'delivery_progress': 100.0,
                    'currency_id': inv.currency_id.id,
                    'source_doc_id': f'{inv._name},{inv.id}',
                    'related_picking_display': '-',
                    'related_invoice_display': 'Direct Invoice',
                    'status_display': 'Posted' if inv.state == 'posted' else 'Draft',
                    'payment_status': get_payment_status(inv.payment_state),
                })

        # Direct Bills (Tagihan Vendor Tanpa PO)
        if self.tracking_type in ['all', 'purchase']:
            direct_bills = candidate_bills if candidate_bills else self._prefetch_candidate_invoices('in_invoice')
            direct_bills = direct_bills.filtered(lambda b: not b.invoice_line_ids.purchase_line_id)

            for bill in direct_bills:
                sign = -1 if bill.move_type == 'in_refund' else 1
                lines_to_create.append({
                    'tracker_id': self.id,
                    'transaction_type': 'purchase',
                    'is_direct': True,
                    'date': bill.invoice_date,
                    'reference': f"{bill.name}",
                    'partner_id': bill.partner_id.id,
                    'user_id': bill.invoice_user_id.id or bill.user_id.id,
                    'amount_total': bill.amount_total * sign,
                    'amount_variance': 0,
                    'balance_due': bill.amount_residual * sign,
                    'invoice_date_due': bill.invoice_date_due,
                    'delivery_progress': 100.0,
                    'currency_id': bill.currency_id.id,
                    'source_doc_id': f'{bill._name},{bill.id}',
                    'related_picking_display': '-',
                    'related_invoice_display': 'Direct Bill',
                    'status_display': 'Posted' if bill.state == 'posted' else 'Draft',
                    'payment_status': get_payment_status(bill.payment_state),
                })

        if lines_to_create:
            self.env['transaction.tracker.line'].create(lines_to_create)
        
        return True


class TransactionTrackerLine(models.Model):
    _name = 'transaction.tracker.line'
    _description = 'Transaction Link Tracker Details'
    _order = 'date desc'

    tracker_id = fields.Many2one('transaction.tracker', string='Tracker Reference', ondelete='cascade')
    
    transaction_type = fields.Selection([
        ('sale', 'Sales'),
        ('purchase', 'Purchase'),
        ('manufacturing', 'Manufacturing'),
        ('internal', 'Internal Transfer')
    ], string='Type', required=True)

    is_direct = fields.Boolean(string='Is Direct/Orphan', default=False)
    
    direct_label = fields.Char(compute='_compute_direct_label', string='Transaction Type')

    @api.depends('transaction_type', 'is_direct')
    def _compute_direct_label(self):
        for line in self:
            if line.is_direct:
                if line.transaction_type == 'sale':
                    line.direct_label = 'DIRECT SALE'
                elif line.transaction_type == 'purchase':
                    line.direct_label = 'DIRECT BILL'
                else:
                    line.direct_label = 'DIRECT'
            else:
                line.direct_label = False

    date = fields.Datetime(string='Date')
    reference = fields.Char(string='Document Number')
    partner_id = fields.Many2one('res.partner', string='Partner')
    user_id = fields.Many2one('res.users', string='Responsible')
    
    amount_total = fields.Monetary(string='Total Amount / Value', currency_field='currency_id')
    amount_variance = fields.Monetary(string='Variance', currency_field='currency_id')
    material_cost = fields.Monetary(string='Total Cost (Mat+Ops)', currency_field='currency_id')
    balance_due = fields.Monetary(string='Balance Due', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency')

    status_display = fields.Char(string='Doc Status')
    delivery_progress = fields.Float(string='Progress %')

    payment_status = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
        ('reversed', 'Reversed')
    ], string='Payment Status', default='not_paid')
    
    invoice_date_due = fields.Date(string='Due Date')

    related_picking_display = fields.Text(string='Deliveries/Next Step')
    related_invoice_display = fields.Text(string='Invoices/Scraps')
    
    source_doc_id = fields.Char(string='Source Document ID') 

    def action_open_source_document(self):
        self.ensure_one()
        if not self.source_doc_id:
            return
        
        model, res_id = self.source_doc_id.split(',')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Source Document',
            'res_model': model,
            'res_id': int(res_id),
            'view_mode': 'form',
            'target': 'current',
        }