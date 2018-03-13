# -*- coding: utf-8 -*-
##############################################################################
#
#    NUMA
#    Copyright (C) 2012 NUMA Extreme Systems (<http:www.numaes.com>).
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
from openerp.osv import fields, osv
from lxml import etree
from openerp.tools.translate import _

class voucher(osv.osv):
    _inherit = 'account.voucher'

    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        mod_obj = self.pool.get('ir.model.data')
        if context is None: context = {}

        def get_res_id(view_type, condition):
            result = False
            if view_type == 'tree':
                result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_voucher_tree')
            elif view_type == 'form':
                if condition:
                    result = mod_obj.get_object_reference(cr, uid, 'numa_wineem_voucher', 'view_vendor_receipt_form')
                else:
                    result = mod_obj.get_object_reference(cr, uid, 'numa_wineem_voucher', 'view_vendor_payment_form')
            return result and result[1] or False

        if not view_id and context.get('invoice_type', False):
            view_id = get_res_id(view_type,context.get('invoice_type', False) in ('out_invoice', 'out_refund'))

        if not view_id and context.get('line_type', False):
            view_id = get_res_id(view_type,context.get('line_type', False) == 'customer')

        res = super(voucher, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@name='partner_id']")
        if context.get('type', 'sale') in ('purchase', 'payment'):
            for node in nodes:
                node.set('domain', "[('supplier', '=', True)]")
            res['arch'] = etree.tostring(doc)
        return res

    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):


        """
        Returns a dict that contains new values and context

        @param partner_id: latest value from user input for field partner_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone

        @return: Returns a dict which contains new values, and context
        """
        res = super(voucher, self).onchange_partner_id(
            cr, uid, ids, partner_id, journal_id, price, currency_id,ttype, date, context)

        # if context is None:
        #     context = {}
        # if not journal_id:
        #     return {}
        # context_multi_currency = context.copy()
        # if date:
        #     context_multi_currency.update({'date': date})
        #
        # line_pool = self.pool.get('account.voucher.line')
        # line_ids = ids and line_pool.search(cr, uid, [('voucher_id', '=', ids[0])]) or False
        # if line_ids:
        #     line_pool.unlink(cr, uid, line_ids)
        #
        # currency_pool = self.pool.get('res.currency')
        # move_line_pool = self.pool.get('account.move.line')
        # partner_pool = self.pool.get('res.partner')
        # journal_pool = self.pool.get('account.journal')
        # tax_id = False
        #
        # journal = journal_pool.browse(cr, uid, journal_id, context=context)
        # company_id = journal.company_id.id
        # #vals = self.onchange_journal(cr, uid, ids, journal_id, [], False, partner_id, context)
        # vals = self.onchange_journal(cr, uid, ids, journal_id, line_ids, tax_id, partner_id, time.strftime('%Y-%m-%d'), price, ttype, company_id, context)
        #
        # vals = vals.get('value')
        # currency_id = vals.get('currency_id', currency_id)
        # default = {
        #     'value':{'line_ids':[], 'line_dr_ids':[], 'line_cr_ids':[], 'pre_line': False, 'currency_id':currency_id},
        # }
        #
        # if not partner_id:
        #     return default
        #
        # if not partner_id and ids:
        #     line_ids = line_pool.search(cr, uid, [('voucher_id', '=', ids[0])])
        #     if line_ids:
        #         line_pool.unlink(cr, uid, line_ids)
        #     return default
        #
        # partner = partner_pool.browse(cr, uid, partner_id, context=context)
        # account_id = False
        # if journal.type in ('sale','sale_refund'):
        #     account_id = partner.property_account_receivable.id
        # elif journal.type in ('purchase', 'purchase_refund','expense'):
        #     account_id = partner.property_account_payable.id
        # else:
        #     account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id
        #
        # default['value']['account_id'] = account_id

        # res = super(voucher, self).onchange_amount(
        #     cr, uid, ids, price, rate, partner_id, journal_id,
        #     currency_id, ttype, date, payment_rate_currency_id, company_id,
        #     context=context)
        if len(res) > 0:
            res['value']['line_cr_ids'] = []
            res['value']['line_dr_ids'] = []

        return res

    def action_compute_debts(self, cr, uid, ids, context=None):
        """price
        Returns a dict that contains new values and context

        @param partner_id: latest value from user input for field partner_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone

        @return: Returns a dict which contains new values, and context
        """

        assert ids and len(ids)==1
        context = context or {}
        currency_pool = self.pool.get('res.currency')
        move_line_pool = self.pool.get('account.move.line')
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')

        v = self.browse(cr, uid, ids[0], context=context)

        if context is None:
            context = {}

        journal_id = v.journal_id and v.journal_id.id or False
        partner_id = v.partner_id and v.partner_id.id or False
        ttype = v.type
        price = v.amount
        currency_id = v.currency_id.id

        if not journal_id:
            return {}

        context_multi_currency = context.copy()

        date = v.date
        if date:
            context_multi_currency.update({'date': date})

        line_pool = self.pool.get('account.voucher.line')
        line_ids = ids and line_pool.search(cr, uid, [('voucher_id', '=', ids[0])]) or False
        if line_ids:
            line_pool.unlink(cr, uid, line_ids)

        currency_pool = self.pool.get('res.currency')
        move_line_pool = self.pool.get('account.move.line')
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')

        tax_id = False
        company_id = v.journal_id.company_id.id
        #vals = self.onchange_journal(cr, uid, ids, journal_id, [], False, partner_id, context)
        vals = self.onchange_journal(cr, uid, ids, journal_id, line_ids, tax_id, partner_id, time.strftime('%Y-%m-%d'), price, ttype, company_id, context)

        vals = vals.get('value')
        currency_id = vals.get('currency_id', currency_id)
        line_ids = []
        line_dr_ids = []
        line_cr_ids = []
        pre_line = False

        if not v.partner_id:
            line_ids = line_pool.search(cr, uid, [('voucher_id', '=', ids[0])])
            if line_ids:
                line_pool.unlink(cr, uid, [x.id for x in v.line_ids])
            return True

        journal = v.journal_id
        partner = v.partner_id
        account_id = False
        if journal.type in ('sale','sale_refund'):
            account_id = partner.property_account_receivable.id
        elif journal.type in ('purchase', 'purchase_refund','expense'):
            account_id = partner.property_account_payable.id
        else:
            account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id

        v.write({'account_id': account_id})

        if journal.type not in ('cash', 'bank'):
            return True

        total_credit = 0.0
        total_debit = 0.0
        account_type = 'receivable'
        if v.type == 'payment':
            account_type = 'payable'
            total_debit = price or 0.0
        else:
            total_credit = price or 0.0
            account_type = 'receivable'

        if not context.get('move_line_ids', False):
            domain = [('state','=','valid'),
                      ('account_id.type', '=', account_type),
                      ('reconcile_id', '=', False),
                      ('partner_id', 'child_of', [v.partner_id.id]),
                      ('account_id.company_id', '=', v.journal_id.company_id.id)]
            if context.get('invoice_id', False):
	            domain.append(('invoice', '=', context['invoice_id']))
            ids = move_line_pool.search(cr, uid, domain, context=context)
        else:
            ids = context['move_line_ids']
        ids.reverse()
        moves = move_line_pool.browse(cr, uid, ids, context=context)

        company_currency = v.journal_id.company_id.currency_id.id
        if company_currency != v.currency_id.id and v.type == 'payment':
            total_debit = currency_pool.compute(cr, uid, v.currency_id.id, company_currency, total_debit, context=context_multi_currency)
        elif company_currency != v.currency_id.id and v.type == 'receipt':
            total_credit = currency_pool.compute(cr, uid, v.currency_id.id, company_currency, total_credit, context=context_multi_currency)

        for line in moves:
            if line.credit and line.reconcile_partial_id and v.type == 'receipt':
                continue
            if line.debit and line.reconcile_partial_id and v.type == 'payment':
                continue
            total_credit += line.credit or 0.0
            total_debit += line.debit or 0.0
        for line in moves:
            if line.credit and line.reconcile_partial_id and v.type == 'receipt':
                continue
            if line.debit and line.reconcile_partial_id and v.type == 'payment':
                continue
            original_amount = line.credit or line.debit or 0.0
            amount_unreconciled = currency_pool.compute(cr, uid, line.currency_id and line.currency_id.id or company_currency, v.currency_id.id, abs(line.amount_residual_currency), context=context_multi_currency)
            rs = {
                'name':line.move_id.name,
                'type': line.credit and 'dr' or 'cr',
                'move_line_id':line.id,
                'account_id':line.account_id.id,
                'amount_original': currency_pool.compute(cr, uid, line.currency_id and line.currency_id.id or company_currency, v.currency_id.id, line.currency_id and abs(line.amount_currency) or original_amount, context=context_multi_currency),
                'date_original':line.date,
                'date_due':line.date_maturity,
                'amount_unreconciled': amount_unreconciled,
            }

            if line.credit:
                amount = min(amount_unreconciled, currency_pool.compute(cr, uid, company_currency, v.currency_id.id, abs(total_debit), context=context_multi_currency))
                rs['amount'] = amount
                total_debit -= amount
            else:
                amount = min(amount_unreconciled, currency_pool.compute(cr, uid, company_currency, v.currency_id.id, abs(total_credit), context=context_multi_currency))
                rs['amount'] = amount
                total_credit -= amount

            line_ids.append(rs)
            if rs['type'] == 'cr':
                line_cr_ids.append(rs)
            else:
                line_dr_ids.append(rs)

            if v.type == 'payment' and len(line_cr_ids) > 0:
                pre_line = 1
            elif v.type == 'receipt' and len(line_dr_ids) > 0:
                pre_line = 1

        v.write({
            'writeoff_amount': self._compute_writeoff_amount(cr, uid, line_dr_ids, line_cr_ids, price, ttype),
            'line_ids': [(0,0,x) for x in line_ids],
        })

        return True

    def action_move_line_create(self, cr, uid, ids, context=None):

        assert ids and len(ids)==1
        context = context or {}
        currency_pool = self.pool.get('res.currency')
        move_line_pool = self.pool.get('account.move.line')
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')

        v = self.browse(cr, uid, ids[0], context=context)

        crs = [x for x in v.line_ids if x.type == 'cr']
        drs = [x for x in v.line_ids if x.type == 'dr']

        total_credit = 0.0
        total_debit = 0.0
        for line in v.line_ids:
            if line.type == 'cr':
                total_credit += line.amount
            elif line.type == 'dr':
                total_debit += line.amount

        if (v.type == 'receipt' and total_credit > v.amount) or \
           (v.type == 'payment' and total_debit > v.amount):
                raise osv.except_osv(_('Invalid action !'),
                                      _('Payment assignment (%f) is bigger than voucher amount (%f)!') %
                                       (total_credit or total_debit, v.amount))

        if (v.type == 'receipt' and len(crs) == 0) or \
           (v.type == 'payment' and len(drs) == 0):
            # trigger autoassignment of debts
            total_credit = 0.0
            total_debit = 0.0
            account_type = v.type == 'receipt' and 'receivable' or 'payable'
            full_credit = v.amount or 0.0

            voucher_credit = v.line_ids and reduce(lambda a, b: a+b, [x.amount for x in v.line_ids]) or 0.0

            domain = [('state','=','valid'),
                      ('account_id.type', '=', account_type),
                      ('reconcile_id', '=', False),
                      ('partner_id', 'child_of', [v.partner_id.id]),
                      ('account_id.company_id', '=', v.journal_id.company_id.id)]

            if context.get('invoice_id', False):
                domain.append(('invoice', '=', context['invoice_id']))
            ids = move_line_pool.search(cr, uid, domain, order='date', context=context)

            moves = move_line_pool.browse(cr, uid, ids, context=context)

            company_currency = v.journal_id.company_id.currency_id.id
            if company_currency != v.currency_id.id:
                full_credit = currency_pool.compute(cr, uid, v.currency_id.id, company_currency, full_credit, context=context)

            for line in moves:
                if line.credit and line.reconcile_partial_id and v.type == 'receipt':
                    continue
                if line.debit and line.reconcile_partial_id and v.type == 'payment':
                    continue
                total_credit += line.credit or 0.0
                total_debit += line.debit or 0.0

            line_ids = []
            line_cr_ids = []
            line_dr_ids = []
            pre_line = False
            for line in moves:
                if line.credit and line.reconcile_partial_id and v.type == 'receipt':
                    continue
                if line.debit and line.reconcile_partial_id and v.type == 'payment':
                    continue
                original_amount = line.credit or line.debit or 0.0
                amount_unreconciled = currency_pool.compute(cr, uid, line.currency_id and line.currency_id.id or company_currency, v.currency_id.id, abs(line.amount_residual_currency), context=context)
                rs = {
                    'name':line.move_id.name,
                    'type': line.credit and 'dr' or 'cr',
                    'move_line_id':line.id,
                    'account_id':line.account_id.id,
                    'amount_original': currency_pool.compute(cr, uid, line.currency_id and line.currency_id.id or company_currency, v.currency_id.id, line.currency_id and abs(line.amount_currency) or original_amount, context=context),
                    'date_original':line.date,
                    'date_due':line.date_maturity,
                    'amount_unreconciled': amount_unreconciled,
                }

                if line.credit:
                    amount = min(amount_unreconciled, full_credit)
                    rs['amount'] = amount
                    total_debit -= amount
                else:
                    amount = min(amount_unreconciled, full_credit)
                    rs['amount'] = amount
                    total_credit -= amount

                full_credit -= amount

                line_ids.append(rs)
                if rs['type'] == 'cr':
                    line_cr_ids.append(rs)
                else:
                    line_dr_ids.append(rs)

                if (v.type == 'receipt' and len(line_dr_ids) > 0) or \
                   (v.type == 'payment' and len(line_cr_ids) > 0):
                    pre_line = True

                if not full_credit:
                    break

            v.write({
                'writeoff_amount': self._compute_writeoff_amount(cr, uid, line_dr_ids, line_cr_ids, v.amount, v.type),
                'line_ids': [(0,0,x) for x in line_ids],
                'pre_line': pre_line,
            })

        return super(voucher, self).action_move_line_create(cr, uid, [v.id], context=context)

    def onchange_journal(self, cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context=None):
        if context is None:
            context = {}
        if not journal_id:
            return False
        journal_pool = self.pool.get('account.journal')
        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        if ttype in ('sale', 'receipt'):
            account_id = journal.default_debit_account_id
        elif ttype in ('purchase', 'payment'):
            account_id = journal.default_credit_account_id
        else:
            account_id = journal.default_credit_account_id or journal.default_debit_account_id
        tax_id = False
        if account_id and account_id.tax_ids:
            tax_id = account_id.tax_ids[0].id

        vals = {'value':{} }
        if ttype in ('sale', 'purchase'):
            vals = self.onchange_price(cr, uid, ids, line_ids, tax_id, partner_id, context)
            vals['value'].update({'tax_id':tax_id,'amount': amount})
        currency_id = False
        if journal.currency:
            currency_id = journal.currency.id
        else:
            currency_id = journal.company_id.currency_id.id

        period_ids = self.pool['account.period'].find(cr, uid, dt=date, context=dict(context, company_id=company_id))
        vals['value'].update({
            'currency_id': currency_id,
            'payment_rate_currency_id': currency_id,
            'period_id': period_ids and period_ids[0] or False
        })
        #in case we want to register the payment directly from an invoice, it's confusing to allow to switch the journal
        #without seeing that the amount is expressed in the journal currency, and not in the invoice currency. So to avoid
        #this common mistake, we simply reset the amount to 0 if the currency is not the invoice currency.
        if context.get('payment_expected_currency') and currency_id != context.get('payment_expected_currency'):
            vals['value']['amount'] = 0
            amount = 0
        # if partner_id:
        #     res = self.onchange_partner_id(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context)
        #     for key in res.keys():
        #         vals[key].update(res[key])
        return vals

    def onchange_amount(self, cr, uid, ids, amount, rate, partner_id, journal_id, currency_id, ttype, date, payment_rate_currency_id, company_id, context=None):
        res = super(voucher, self).onchange_amount(
            cr, uid, ids, amount, rate, partner_id, journal_id,
            currency_id, ttype, date, payment_rate_currency_id, company_id,
            context=context)

        res['value']['line_cr_ids'] = []
        res['value']['line_dr_ids'] = []
        return res


voucher()
