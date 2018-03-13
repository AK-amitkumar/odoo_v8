# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
import re
from openerp.report import report_sxw
from common_report_header import common_report_header
import pdb
from openerp.osv import fields
from datetime import date, datetime, timedelta
import logging

logger = logging.getLogger(__name__)

DT_FORMAT = "%Y-%m-%d"

class partner_ledger_report_fecha_vencimiento(report_sxw.rml_parse, common_report_header):

    def __init__(self, cr, uid, name, context=None):
        super(partner_ledger_report_fecha_vencimiento, self).__init__(cr, uid, name, context=context)
        self.init_bal_sum = 0.0
        self.localcontext.update({
            'time': time,
            'lines': self.lines,
            'comma_me': self.comma_me,
            'get_today': self._get_today,
            'get_start_date': self._get_start_date,
            'get_fiscalyear': self._get_fiscalyear,
        })

    def _get_today(self):
        return date.today().strftime(DT_FORMAT)

    def _get_start_date(self):
        return self.start_date
        
    def _get_fiscalyear(self):
        return self.fiscalyear_id
        
    def set_context(self, objects, data, ids, report_type=None):
        
        self.partner_ids = data['form'].get('partner_ids', [])
        self.fiscalyear_ids = data['form'].get('fiscalyear_ids', False)
        
        self.reconcil = data['form'].get('reconcil', True)
        self.result_selection = data['form'].get('result_selection', 'customer')
        self.include_docs = data['form'].get('include_docs', True)
        self.docs_on_maturity = data['form'].get('docs_on_maturity', True)
        self.include_children = data['form'].get('include_children', False)
        self.start_date = data['form'].get('start_date', False)

        return super(partner_ledger_report_fecha_vencimiento, self).set_context(objects, data, ids, report_type)

    def comma_me(self, amount):
        if type(amount) is float:
            amount = str('%.2f' % amount)
        else:
            amount = str(amount)
        if (amount == '0'):
             return ' '
        orig = amount
        new = re.sub("^(-?\d+)(\d{3})", "\g<1>'\g<2>", amount)
        if orig == new:
            return new
        else:
            return self.comma_me(new)

    def process_moves(self, l, moves, prefix):
        inv_obj = self.pool.get('account.invoice')
        current_partner = None
        current_date_due = None
        invoice_date_due = None
        invoice_date_due = None
        current_doc = None
        current_desc = None
        current_doc_type = None
        start_balance = None
        acum_debit = 0.0
        acum_credit = 0.0
        balance = 0.0

        d = []
        for m in moves:
#             print "FACTURA ======= %s" % (m.invoice.date_due)
#             date = self.docs_on_maturity and (m.date_maturity or m.date) or m.date
            
            # Agregado
            date_due = self.docs_on_maturity and (m.date_maturity or m.invoice.date_due) or m.invoice.date_due
#             date_due = m.date_maturity
#             date = self.docs_on_maturity and (m.date_maturity or m.date) or m.date
            partner_id = (m.partner_id.id in self.partner_ids) and m.partner_id or m.partner_id.parent_id

            partner_changed = (not current_partner) or current_partner.id != partner_id.id
            date_changed = partner_changed or (not current_date_due) or current_date_due != date_due
            doc_changed = date_changed or (not current_doc) or \
                          ((not (current_doc_type == 'Ventas' and m.account_id.type == 'receivable' and m.debit > 0)) and current_doc != m.ref)

            if date_due >= self.start_date:
                if start_balance == None:
                    start_balance = balance
                    
                if current_doc and doc_changed:
                    if acum_debit > acum_credit:
                        acum_debit -= acum_credit
                        acum_credit = 0.0
                    else:
                        acum_credit -= acum_debit
                        acum_debit = 0.0
                    d.append({
#                         'date': date,
                        'invoice_date_due': current_date_due,
                        'doc': current_doc_type == 'Ventas' and 'Ventas' or current_desc,
                        'debit': acum_debit,
                        'credit': acum_credit,
                        'balance': balance,
                    })
                
                if doc_changed:
                    acum_debit = 0.0
                    acum_credit = 0.0
                    current_doc = m.ref
                    current_desc = current_doc
                    current_doc_type = (m.account_id.type == 'receivable' and m.debit > 0 and 'Ventas' or 'Otros')
                    if current_doc.startswith('NC'):
                        inv_ids = inv_obj.search(self.cr, self.uid, [('name', '=', current_doc)])
                        if inv_ids:
                            inv = inv_obj.browse(self.cr, self.uid, inv_ids[0])
                            if inv.invoice_line and inv.invoice_line[0].product_id:
                                current_desc = "%s - %s" % (current_doc,
                                                           inv.invoice_line[0].product_id.name)
                    elif current_doc.startswith('ND'):
                        current_doc_type = 'Otros'
                        inv_ids = inv_obj.search(self.cr, self.uid, [('name', '=', current_doc)])
                        if inv_ids:
                            inv = inv_obj.browse(self.cr, self.uid, inv_ids[0])
                            if inv.invoice_line and inv.invoice_line[0].product_id:
                                current_desc = "%s - %s" % (current_doc,
                                                           inv.invoice_line[0].product_id.name)
                
                if date_changed:
                    current_date_due = date_due
                                       
            if current_partner and partner_changed:
                logger.warning("Current %d, %s; new %d, %s" % (current_partner.id, current_partner.name, partner_id.id, partner_id.name))
                if current_partner not in l:
                    l[current_partner] = {'entries': [], 'start_balance':0.0, 'close_balance': 0.0,
                                          'dp_entries': [], 'dp_start_balance':0.0, 'dp_close_balance': 0.0}
                l[current_partner].update({
                    prefix + 'entries': d,
                    prefix + 'start_balance': start_balance,
                    prefix + 'close_balance': balance,
                })
            if partner_changed:
                current_partner = partner_id
                if date_due >= self.start_date:
                    start_balance = 0.0
                else:                    
                    start_balance = None
                balance = 0.0
                d = []
                
            acum_debit += m.debit or 0.0
            acum_credit += m.credit or 0.0
            balance += (m.debit or 0.0) - (m.credit or 0.0)

        if start_balance == None:
            start_balance = balance

        if current_doc:
            if acum_debit > acum_credit:
                acum_debit -= acum_credit
                acum_credit = 0.0
            else:
                acum_credit -= acum_debit
                acum_debit = 0.0
            d.append({
#                 'date': current_date_due,
                'invoice_date_due': current_date_due,
                'doc': current_doc_type == 'Ventas' and 'Ventas' or current_doc,
                'debit': acum_debit,
                'credit': acum_credit,
                'balance': balance,
            })
        if current_partner:
            logger.warning("Last %d, %s" % (current_partner.id, current_partner.name))
            if current_partner not in l:
                l[current_partner] = {'entries': [], 'start_balance':0.0, 'close_balance': 0.0,
                                      'dp_entries': [], 'dp_start_balance':0.0, 'dp_close_balance': 0.0}
            l[current_partner].update({
                prefix + 'entries': d,
                prefix + 'start_balance': start_balance or 0.0,
                prefix + 'close_balance': balance,
            })
        

    def lines(self):

        aml_obj = self.pool.get('account.move.line')
        partner_obj = self.pool.get('res.partner')

        l = {p: {'entries': [], 'start_balance':0.0, 'close_balance': 0.0,
                 'dp_entries': [], 'dp_start_balance':0.0, 'dp_close_balance': 0.0}
                 for p in partner_obj.browse(self.cr, self.uid, self.partner_ids, self.localcontext)}

        # Get all normal movements
        
        sc = []
        
        if self.include_docs:
            if self.result_selection == 'supplier':
                types = ['payable', 'document_pay', 'document_pay_rej']
            elif self.result_selection == 'customer':
                types = ['receivable', 'document_rec', 'document_rec_rej']
            else:
                types = ['payable', 'document_pay', 'document_pay_rej', 'receivable', 'document_rec', 'document_rec_rej']
        else:
            if self.result_selection == 'supplier':
                types = ['payable']
            elif self.result_selection == 'customer':
                types = ['receivable']
            else:
                types = ['payable', 'receivable']
        sc.append(('account_id.type', 'in', types))

        if self.include_children:
            sc.append(('partner_id', 'child_of', self.partner_ids))
        else:
            sc.append(('partner_id', 'in', self.partner_ids))

        sc.append(('move_id.period_id.fiscalyear_id', 'in', self.fiscalyear_ids))

        sc.append(('move_id.state', '=', 'posted'))

        if not self.reconcil:
            sc.append(('reconcile_id', '=', False))
            
        m_ids = aml_obj.search(self.cr, self.uid, sc)
        
        moves = aml_obj.browse(self.cr, self.uid, m_ids)
        
#         moves = sorted(moves, key=lambda m: (m.partner_id.id in self.partner_ids and m.partner_id.id or m.partner_id.parent_id.id,
#                                              self.docs_on_maturity and (m.date_maturity or m.date) or m.date,
#                                              m.ref))
#         Ordenados por fecha de vencimiento
        moves = sorted(moves, key=lambda m: (m.partner_id.id in self.partner_ids and m.partner_id.id or m.partner_id.parent_id.id,
                                             self.docs_on_maturity and (m.date_maturity or m.invoice.date_due) or m.invoice.date_due,
                                             m.ref))
        
        
        self.process_moves(l, moves, '')
        
        # Get downpayments
        
        sc = []
        
        if self.result_selection == 'supplier':
            types = ['supplier_dp']
        elif self.result_selection == 'customer':
            types = ['customer_dp']
        else:
            types = ['supplier_dp', 'customer_dp']
        sc.append(('account_id.type', 'in', types))

        if self.include_children:
            sc.append(('partner_id', 'child_of', self.partner_ids))
        else:
            sc.append(('partner_id', 'in', self.partner_ids))

        sc.append(('move_id.period_id.fiscalyear_id', 'in', self.fiscalyear_ids))

        sc.append(('move_id.state', '=', 'posted'))
            
        if not self.reconcil:
            sc.append(('reconcile_id', '=', False))
            
        m_ids = aml_obj.search(self.cr, self.uid, sc)
        
        moves = aml_obj.browse(self.cr, self.uid, m_ids)
        
        moves = sorted(moves, key=lambda m: (m.partner_id.id in self.partner_ids and m.partner_id.id or m.partner_id.parent_id.id,
                                             self.docs_on_maturity and (m.date_maturity or m.date) or m.date,
                                             m.ref))

        self.process_moves(l, moves, 'dp_')
        
        o = sorted(l.keys(), key=lambda x: x.name)        
        return [{'partner': p, 'data': l[p]} for p in o]

report_sxw.report_sxw('report.partner_ledger_wizard_con_fecha_vencimiento', 'numa_ar_base.partner_ledger_wizard',
        'addons/numa_uniqs_base_ext_report_ledger/report/partner_ledger_con_columna_vencimiento.rml', parser=partner_ledger_report_fecha_vencimiento,
        header='internal')
# report_sxw.report_sxw('report.partner_ledger_wizard_con_fecha_vencimiento', 'numa_ar_base.partner_ledger_wizard',
#         'addons/numa_uniqs_base/report/partner_ledger.rml',parser=partner_ledger_report_fecha_vencimiento,
#         header='internal')

