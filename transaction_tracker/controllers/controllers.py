# -*- coding: utf-8 -*-
# from odoo import http


# class TransactionTracker(http.Controller):
#     @http.route('/transaction_tracker/transaction_tracker', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/transaction_tracker/transaction_tracker/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('transaction_tracker.listing', {
#             'root': '/transaction_tracker/transaction_tracker',
#             'objects': http.request.env['transaction_tracker.transaction_tracker'].search([]),
#         })

#     @http.route('/transaction_tracker/transaction_tracker/objects/<model("transaction_tracker.transaction_tracker"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('transaction_tracker.object', {
#             'object': obj
#         })

