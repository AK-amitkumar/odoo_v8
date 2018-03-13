# -*- coding: utf-8 -*-
##############################################################################
#
#    NUMA
#    Copyright (C) 2011 NUMA Extreme Systems (<http:www.numaes.com>).
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

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp import netsvc

import pdb


# Common routine to get values from a one2many field from UI
# Copied from account_voucher

def resolve_o2m_operations(cr, uid, target_osv, operations, fields, context):
    results = []
    for operation in operations:
        result = None
        if not isinstance(operation, (list, tuple)):
            result = target_osv.read(cr, uid, operation, fields, context=context)
        elif operation[0] == 0:
            result = target_osv.default_get(cr, uid, fields, context=context)
            result.update(operation[2])
        elif operation[0] == 1:
            result = target_osv.read(cr, uid, operation[1], fields, context=context)
            if not result: result = {}
            result.update(operation[2])
        elif operation[0] == 4:
            result = target_osv.read(cr, uid, operation[1], fields, context=context)
        if result != None:
            results.append(result)
    return results

class document_receipt(osv.osv):
    '''
    A document receipt is the document that declares the reception of cash, bank transfers and Tax retentions from a partner
    '''


    def _get_name(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('name', False)

    def _get_journal(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('journal_id', False)

    def _get_narration(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('narration', False)

    def _get_reference(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('reference', False)

    def _get_cash_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for dr in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for cash in dr.cash_ids:
                amount += cash.amount
            res[dr.id] = amount
        return res

    def _get_bt_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for dr in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for bt in dr.bt_ids:
                amount += bt.amount
            res[dr.id] = amount
        return res

    def _get_qm_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for dr in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for qm in dr.qm_ids:
                amount += qm.amount
            res[dr.id] = amount
        return res

    def _get_debt_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for dr in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for debt in dr.debt_ids:
                amount += debt.amount
            res[dr.id] = amount
        return res

    def _get_balance(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        amount = 0.0
        for dr in self.browse (cr, uid, ids, context=context):
            c = []
            for cash in dr.cash_ids:
                c.append({'amount': cash.amount})
            b = []
            for bt in dr.bt_ids:
                b.append({'amount': bt.amount})
            q = []
            for qm in dr.qm_ids:
                q.append({'amount': qm.amount})
            db = []
            for debt in dr.debt_ids:
                db.append({'amount': debt.amount})

            res[dr.id] = self._compute_balance (cr, uid, c, b, q, db)
        return res

    def _compute_balance(self, cr, uid, cash_ids, bt_ids, qm_ids, debt_ids):
        currency_obj = self.pool.get('res.currency')

        balance = 0.0
        for cash in cash_ids:
            balance += cash['amount']
        for bt in bt_ids:
            balance += bt['amount']
        for qm in qm_ids:
            balance += qm['amount']
        for debt in debt_ids:
            balance -= debt['amount']

        return balance

    _name = 'numa_ar_base.document_receipt'
    _description = 'Customer receipts'
    _order = "date desc, id desc"
    _columns = {
        'name':fields.char('Identification', size=256, readonly=True, states={'draft':[('readonly',False)]}),
        'date':fields.date('Date', readonly=True, select=True, states={'draft':[('readonly',False)]}, help="Effective receipt date"),
        'journal_id':fields.many2one('account.journal', 'Journal', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'account_id':fields.many2one('account.account', 'Account', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'cash_ids':fields.one2many('numa_ar_base.document_receipt_cash','dr_id','Cash', readonly=True, states={'draft':[('readonly',False)]}),
        'bt_ids':fields.one2many('numa_ar_base.document_receipt_bt','dr_id','Bank transfers', readonly=True, states={'draft':[('readonly',False)]}),
        'qm_ids':fields.one2many('numa_ar_base.document_receipt_qm','dr_id','Received retentions', readonly=True, states={'draft':[('readonly',False)]}),
        'debt_ids':fields.one2many('numa_ar_base.document_receipt_debt','dr_id','Applied debts', readonly=True, states={'draft':[('readonly',False)]}),
        'narration':fields.text('Notes', readonly=True, states={'draft':[('readonly',False)]}),
        'company_id': fields.related('journal_id','company_id', type='many2one', relation='res.company', string='Company', store=False, readonly=True),
        'currency_id': fields.related('company_id','currency_id',type='many2one', relation='res.currency', string='Currency', store=False, readonly=True),
        'state':fields.selection(
            [('draft','Draft'),
             ('posted','Posted'),
             ('cancel','Canceled')
            ], 'State', readonly=True, size=32,
            help=' * \'Draft\' state is used on new document entry. \
                        \n* \'Posted\' is used when the document is registered and account moves are generated \
                        \n* \'Cancel\' is used for canceled documents.'),
        'reference': fields.char('Ref #', size=64, readonly=True, states={'draft':[('readonly',False)]}, help="Reference number."),
        'move_id':fields.many2one('account.move', 'Account move'),
        'move_line_ids': fields.related('move_id','line_id', type='one2many', relation='account.move.line', string='Account move lines', readonly=True),
        'cancel_move_id':fields.many2one('account.move', 'Cancel account move'),
        'cancel_move_line_ids': fields.related('cancel_move_id','line_id', type='one2many', relation='account.move.line', string='Cancel account move lines', readonly=True),
        'partner_id':fields.many2one('res.partner', 'Customer', change_default=1, readonly=True, states={'draft':[('readonly',False)]}),
        'audit': fields.related('move_id','to_check', type='boolean', relation='account.move', string='Audit ?'),
        'balance': fields.function(_get_balance, method=True, string='Balance', type='float', readonly=True),
        'cash_total': fields.function(_get_cash_total, method=True, string='Total cash', type='float', readonly=True),
        'bt_total': fields.function(_get_bt_total, method=True, string='Total transfers', type='float', readonly=True),
        'qm_total': fields.function(_get_qm_total, method=True, string='Total retentions', type='float', readonly=True),
        'debt_total': fields.function(_get_debt_total, method=True, string='Total debts', type='float', readonly=True),
        
    }
    _defaults = {
        'name':_get_name,
        'journal_id':_get_journal,
        'reference': _get_reference,
        'narration':_get_narration,
        'state': 'draft',
        'name': '',
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.account', context=c),
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if context is None: context = {}
        document_receipts = self.browse (cr, uid, ids)
        return [(dr.id, "%s [%s]" % (dr.name, dr.company_id.name)) for dr in document_receipts]

    def onchange_line_ids(self, cr, uid, ids, cash_ids, bt_ids, qm_ids, debt_ids, context=None):
        cash_obj = self.pool.get ('numa_ar_base.document_receipt_cash')
        bt_obj = self.pool.get ('numa_ar_base.document_receipt_bt')
        qm_obj = self.pool.get ('numa_ar_base.document_receipt_qm')
        debt_obj = self.pool.get ('numa_ar_base.document_receipt_debt')
        
        c = resolve_o2m_operations(cr, uid, cash_obj, cash_ids, ['amount'], context=context)
        b = resolve_o2m_operations(cr, uid, bt_obj, bt_ids, ['amount'], context=context)
        q = resolve_o2m_operations(cr, uid, qm_obj, qm_ids, ['amount'], context=context)
        db = resolve_o2m_operations(cr, uid, debt_obj, debt_ids, ['amount'], context=context)

        return {'value': {'balance': self._compute_balance(cr, uid, c, b, q, db)}}

    def onchange_journal (self, cr, uid, ids, journal_id, partner_id, date, currency_id, cash_ids, bt_ids, qm_ids, debt_ids, context=None):
        default = {
            'value':{},
        }

        if not partner_id and not journal_id:
            return default

        cash_obj = self.pool.get('numa_ar_base.document_receipt_cash')
        bt_obj = self.pool.get('numa_ar_base.document_receipt_bt')
        journal_obj = self.pool.get('account.journal')
        period_obj = self.pool.get('account.period')

        journal = journal_obj.browse (cr, uid, journal_id, context=context)
        
        default['value']['currency_id'] = journal.currency.id or journal.company_id.currency_id.id
        default['value']['company_id'] = journal.company_id.id
            
        if partner_id:
            change_set = self.onchange_partner_id(cr, uid, ids, partner_id, journal_id, date, default['value']['currency_id'], cash_ids, bt_ids, qm_ids, debt_ids, context=context)
            if change_set:
                default['value'].update(change_set['value'])
            default['value']['cash_ids'] = []
            default['value']['bt_ids'] = []

        #pdb.set_trace()

        return default

    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, date, currency_id, cash_ids, bt_ids, qm_ids, debt_ids, context=None):
        if context is None:
            context = {}

        cash_obj = self.pool.get ('numa_ar_base.document_receipt_cash')
        bt_obj = self.pool.get ('numa_ar_base.document_receipt_bt')
        qm_obj = self.pool.get ('numa_ar_base.document_receipt_qm')
        debt_obj = self.pool.get ('numa_ar_base.document_receipt_debt')
        partner_obj = self.pool.get ('res.partner')

        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')
        journal_obj = self.pool.get('account.journal')

        if not partner_id or not journal_id:
            return {}

        partner = partner_obj.browse (cr, uid, partner_id, context=context)
        journal = journal_obj.browse(cr, uid, journal_id, context=context)
        company_currency = journal.company_id.currency_id

        context_multi_currency = context.copy()
        if date:
            context_multi_currency.update({'date': date})

        total_credit = 0.0

        for d in resolve_o2m_operations(cr, uid, cash_obj, cash_ids, ['amount'], context=context):
            total_credit += d['amount']

        for d in resolve_o2m_operations(cr, uid, bt_obj, bt_ids, ['amount'], context=context):
            total_credit += d['amount']

        for d in resolve_o2m_operations(cr, uid, qm_obj, qm_ids, ['amount'], context=context):
            total_credit += d['amount']

        new_balance = total_credit

        move_line_ids = move_line_obj.search (cr, uid, [('partner_id','=',partner_id), ('company_id','=', journal.company_id.id), 
                                                        ('state','=','valid'), ('account_id.type', '=', 'receivable'), ('reconcile_id','=', False)])

        moves = move_line_obj.browse(cr, uid, move_line_ids, context=context)
        if moves:
            moves.sort(key=lambda move: move.date_maturity or move.date)

        debts = []
            
        for line in moves:
            if line.credit:
                continue
            original_amount = line.debit or 0.0
            amount_unreconciled = currency_obj.compute(cr, uid, line.currency_id and line.currency_id.id or company_currency.id, currency_id, abs(line.amount_residual_currency), context=context_multi_currency)
            if not amount_unreconciled:
                continue
            amount = min(amount_unreconciled, total_credit)
            rs = {
                'name':line.move_id.name,
                'move_line_id':line.id,
                'account_id':line.account_id.id,
                'amount_original': currency_obj.compute(cr, uid, line.currency_id and line.currency_id.id or company_currency.id, currency_id, line.currency_id and abs(line.amount_currency) or original_amount, context=context_multi_currency),
                'date_original':line.date,
                'date_due':line.date_maturity,
                'amount_unreconciled': amount_unreconciled,
                'amount' : amount,
            }

            if total_credit > amount:
                total_credit -= amount
            else:
                total_credit = 0.0

            new_balance -= amount

            debts.append(rs)

        res = {'value': {
                'balance':  new_balance,
                'debt_ids': debts,
                'account_id': partner.property_account_receivable,
              }}

        return res

    def onchange_date(self, cr, uid, ids, date, journal_id, context=None):
        """
        @param date: latest value from user input for field date
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        @return: Returns a dict which contains new values, and context
        """
        if not date:
            return False

        if not context: context = {}

        period_pool = self.pool.get('account.period')
        journal_pool = self.pool.get('account.journal')

        res = {'value':{}}

        if journal_id:
            journal = journal_pool.browse (cr, uid, journal_id)
            pids = period_pool.search(cr, uid, [('date_start', '<=', date), ('date_stop', '>=', date), ('company_id', '=', journal.company_id.id)])
        else:
            pids = period_pool.search(cr, uid, [('date_start', '<=', date), ('date_stop', '>=', date)])
        if not pids:
            raise osv.except_osv(_('Error!'), _('No period for the given date!'))

        return res

    def action_reasign_credit(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        currency_obj = self.pool.get('res.currency')
        journal_obj = self.pool.get('res.company')

        for dr in self.browse (cr, uid, ids, context=context):

            total_credit = 0.0
            for cash in dr.cash_ids:
                total_credit += cash.amount
            for bt in dr.bt_ids:
                total_credit += bt.amount
            for qm in dr.qm_ids:
                total_credit += qm.amount

            new_balance = total_credit
            debts = []

            moves = dr.debt_ids
            moves.sort(key=lambda move: move.date_due or move.date_original)
                
            for line in moves:
                amount = min(line.amount_unreconciled, total_credit)
                debts.append((1, line.id, {'amount' : amount}))

                if total_credit > amount:
                    total_credit -= amount
                else:
                    total_credit = 0.0

                new_balance -= amount


            self.write (cr, uid, [dr.id], {'debt_ids': debts})

        return True

    def cancel_receipt(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')

        for receipt in self.browse(cr, uid, ids, context=context):
            val = {
                'state':'cancel',
                'cancel_move_id': receipt.move_id and move_pool.revert(cr, uid, [receipt.move_id.id], {
                                                                            'name': 'CAN:%s' % receipt.name,
                                                                            'date': time.strftime('%Y-%m-%d'),
                                                                       }, context=context)[receipt.move_id.id] or False, 
            }
            receipt.write(val)

        return True

    def unlink(self, cr, uid, ids, context=None):
        for t in self.read(cr, uid, ids, ['state'], context=context):
            if t['state'] in ['posted', 'cancel']:
                raise osv.except_osv(_('Error!'), _('Posted or canceled receipts could not be deleted!'))
        return super(document_receipt, self).unlink(cr, uid, ids, context=context)

    def action_post(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')
        seq_obj = self.pool.get('ir.sequence')
        account_obj = self.pool.get('account.account')
        company_obj = self.pool.get('res.company')
        partner_obj = self.pool.get('res.partner')
        rec_doc_obj = self.pool.get('numa_ar_base.receivable_document')
        period_obj = self.pool.get('account.period')
        tax_obj = self.pool.get('account.tax')

        for receipt in self.browse(cr, uid, ids, context=context):
            if receipt.move_id:
                continue
            context_multi_currency = context.copy()
            context_multi_currency.update({'date': receipt.date})

            if receipt.journal_id and receipt.journal_id.sequence_id:
                name = seq_obj.get_id(cr, uid, receipt.journal_id.sequence_id.id, context={'company_id': receipt.journal_id.company_id.id})
            else:
                raise osv.except_osv(_('Error !'), _('Please define a Journal with sequence!'))

            pids = period_obj.search(cr, uid, [('date_start', '<=', receipt.date), ('date_stop', '>=', receipt.date), ('company_id', '=', receipt.journal_id.company_id.id)])
            if pids:
                period_id = pids[0]
            else:
                raise osv.except_osv(_('Error !'), _('No valid period for the given date!'))

            #Compute the total amount to be payed
            total_credit = 0.0

            for cash in receipt.cash_ids:
                total_credit += cash.amount

            for bt in receipt.bt_ids:
                total_credit += bt.amount

            for qm in receipt.qm_ids:
                total_credit += qm.amount

            if total_credit == 0:
                    raise osv.except_osv(_('Not complete!'),
                        _('No credit entered!'))

            if not receipt.reference:
                ref = name.replace('/','')
            else:
                ref = receipt.reference

            self.write (cr, uid, [receipt.id], {'name': name})

            move = {
                'name': name,
                'journal_id': receipt.journal_id.id,
                'narration': receipt.narration,
                'date': receipt.date,
                'ref': ref,
                'period_id': period_id
            }
            move_id = move_obj.create(cr, uid, move)

            company_currency = receipt.journal_id.company_id.currency_id.id
            current_currency = receipt.currency_id.id

            debit = 0.0
            applicable_debts = []
            for line in receipt.debt_ids:
                if line.amount:
                    applicable_debts.append(line)

            debt_index = 0
            if len(applicable_debts):
                debt = applicable_debts[debt_index]
                left_to_apply = min (debt.amount_unreconciled, debt.amount)

            reconcile_lines = []
            
            # Process cash

            for cash in receipt.cash_ids:
                amount_to_apply = cash.amount

                if amount_to_apply and debt_index < len(applicable_debts):
                    #Apply this amount to debts not yet covered

                    while debt_index < len(applicable_debts) and amount_to_apply > 0:
                        #Taking the amount to apply, try to cover as many docs as possible
                        #we check if the voucher line is fully paid or not and create a move line to balance the payment and initial invoice if needed

                        to_apply = min (amount_to_apply, left_to_apply)

                        if to_apply:
                            #Generate a pair of movements, one for the debit account of the journal and one for the receipt account (by default, the credit account of the journal)
                            move_line = {
                                'journal_id': receipt.journal_id.id,
                                'period_id': period_id,
                                'name': _('Cash'),
                                'account_id': receipt.journal_id.default_credit_account_id.id,
                                'move_id': move_id,
                                'partner_id': receipt.partner_id.id,
                                'currency_id': company_currency <> cash.currency_id.id and cash.currency_id.id or False,
                                'amount_currency': company_currency <> cash.currency_id.id and cash.original_amount or 0.0,
                                'analytic_account_id': False,
                                'quantity': 1,
                                'debit': to_apply,
                                'credit': 0.0,
                                'date': receipt.date,
                                'date_maturity': receipt.date,
                            }

                            move_1 = move_line_obj.create(cr, uid, move_line)

                            move_line.update({
                                'account_id': debt.account_id.id,
                                'credit': to_apply,
                                'debit': 0.0,
                            })

                            move_2 = move_line_obj.create(cr, uid, move_line)

                            reconcile_lines.append([debt.move_line_id.id, move_2])

                            amount_to_apply -= to_apply
                            left_to_apply -= to_apply

                        if not left_to_apply or not to_apply:
                            debt_index += 1
                            if debt_index < len(applicable_debts):
                                debt = applicable_debts[debt_index]
                                left_to_apply = min (debt.amount_unreconciled, debt.amount)

                if amount_to_apply > 0:
                    move_line = {
                        'journal_id': receipt.journal_id.id,
                        'period_id': period_id,
                        'name': _('Cash'),
                        'account_id': receipt.journal_id.default_credit_account_id.id,
                        'move_id': move_id,
                        'partner_id': receipt.partner_id.id,
                        'currency_id': company_currency <> cash.currency_id.id and cash.currency_id.id or False,
                        'amount_currency': company_currency <> cash.currency_id.id and cash.original_amount or 0.0,
                        'analytic_account_id': False,
                        'quantity': 1,
                        'debit': amount_to_apply,
                        'credit': 0.0,
                        'date': receipt.date,
                        'date_maturity': receipt.date,
                    }

                    move_1 = move_line_obj.create(cr, uid, move_line)

                    move_line.update({
                        'account_id': receipt.account_id.id,
                        'credit': amount_to_apply,
                        'debit': 0.0,
                    })

                    move_2 = move_line_obj.create(cr, uid, move_line)

            #Process bank transfers entries

            for bt in receipt.bt_ids:
                amount_to_apply = bt.amount

                if amount_to_apply and debt_index < len(applicable_debts):
                    #Apply this amount to debts not yet covered

                    while debt_index < len(applicable_debts) and amount_to_apply > 0:
                        #Taking the amount to apply, try to cover as many docs as possible
                        #we check if the voucher line is fully paid or not and create a move line to balance the payment and initial invoice if needed

                        to_apply = min (amount_to_apply, left_to_apply)

                        if to_apply:
                            #Generate a pair of movements, one for the debit account of the journal and one for the receipt account (by default, the credit account of the journal)
                            move_line = {
                                'journal_id': receipt.journal_id.id,
                                'period_id': period_id,
                                'name': _('Bank Transfer'),
                                'account_id': bt.bank_journal_id.default_credit_account_id.id,
                                'move_id': move_id,
                                'partner_id': receipt.partner_id.id,
                                'currency_id': company_currency <> bt.currency_id.id and bt.currency_id.id or False,
                                'amount_currency': company_currency <> bt.currency_id.id and bt.original_amount or 0.0,
                                'analytic_account_id': False,
                                'quantity': 1,
                                'debit': to_apply,
                                'credit': 0.0,
                                'date': receipt.date,
                                'date_maturity': receipt.date,
                            }

                            move_1 = move_line_obj.create(cr, uid, move_line)

                            move_line.update({
                                'account_id': debt.account_id.id,
                                'credit': to_apply,
                                'debit': 0.0,
                            })

                            move_2 = move_line_obj.create(cr, uid, move_line)

                            reconcile_lines.append([debt.move_line_id.id, move_2])

                            amount_to_apply -= to_apply
                            left_to_apply -= to_apply

                        if not left_to_apply or not to_apply:
                            debt_index += 1
                            if debt_index < len(applicable_debts):
                                debt = applicable_debts[debt_index]
                                left_to_apply = min (debt.amount_unreconciled, debt.amount)

                if amount_to_apply > 0:
                    move_line = {
                        'journal_id': receipt.journal_id.id,
                        'period_id': period_id,
                        'name': _('Bank Transfer'),
                        'account_id': bt.bank_journal_id.default_credit_account_id.id,
                        'move_id': move_id,
                        'partner_id': receipt.partner_id.id,
                        'currency_id': company_currency <> bt.currency_id.id and bt.currency_id.id or False,
                        'amount_currency': company_currency <> bt.currency_id.id and bt.original_amount or 0.0,
                        'analytic_account_id': False,
                        'quantity': 1,
                        'debit': amount_to_apply,
                        'credit': 0.0,
                        'date': receipt.date,
                        'date_maturity': receipt.date,
                    }

                    move_1 = move_line_obj.create(cr, uid, move_line)

                    move_line.update({
                        'account_id': receipt.account_id.id,
                        'credit': amount_to_apply,
                        'debit': 0.0,
                    })

                    move_2 = move_line_obj.create(cr, uid, move_line)


            #Process quick moves

            for qm in receipt.qm_ids:
                amount_to_apply = qm.amount

                if amount_to_apply and debt_index < len(applicable_debts):
                    #Apply this amount to debts not yet covered

                    while debt_index < len(applicable_debts) and amount_to_apply > 0:
                        #Taking the amount to apply, try to cover as many docs as possible
                        #we check if the voucher line is fully paid or not and create a move line to balance the payment and initial invoice if needed

                        to_apply = min (amount_to_apply, left_to_apply)

                        if to_apply:
                            #Generate a pair of movements, one for the debit account of the journal and one for the receipt account (by default, the credit account of the journal)
                            move_line = {
                                'journal_id': receipt.journal_id.id,
                                'period_id': period_id,
                                'name': _('QM'),
                                'account_id': qm.credit_account_id.id,
                                'move_id': move_id,
                                'partner_id': receipt.partner_id.id,
                                'currency_id': False,
                                'amount_currency': 0.0,
                                'analytic_account_id': qm.analytic_account_id and qm.analytic_account_id.id or False,
                                'quantity': 1,
                                'debit': to_apply,
                                'credit': 0.0,
                                'date': receipt.date,
                                'date_maturity': receipt.date,
                            }

                            move_1 = move_line_obj.create(cr, uid, move_line)

                            move_line.update({
                                'account_id': debt.account_id.id,
                                'credit': to_apply,
                                'debit': 0.0,
                            })

                            move_2 = move_line_obj.create(cr, uid, move_line)

                            reconcile_lines.append([debt.move_line_id.id, move_2])

                            amount_to_apply -= to_apply
                            left_to_apply -= to_apply

                        if not left_to_apply or not to_apply:
                            debt_index += 1
                            if debt_index < len(applicable_debts):
                                debt = applicable_debts[debt_index]
                                left_to_apply = min (debt.amount_unreconciled, debt.amount)

                if amount_to_apply > 0:
                    move_line = {
                        'journal_id': receipt.journal_id.id,
                        'period_id': period_id,
                        'name': _('QM'),
                        'account_id': qm.credit_account_id.id,
                        'move_id': move_id,
                        'partner_id': receipt.partner_id.id,
                        'currency_id': False,
                        'amount_currency': 0.0,
                        'analytic_account_id': False,
                        'quantity': 1,
                        'debit': amount_to_apply,
                        'credit': 0.0,
                        'date': receipt.date,
                        'date_maturity': receipt.date,
                    }

                    move_1 = move_line_obj.create(cr, uid, move_line)

                    move_line.update({
                        'account_id': qm.debit_account_id.id,
                        'credit': amount_to_apply,
                        'debit': 0.0,
                    })

                    move_2 = move_line_obj.create(cr, uid, move_line)

            move_obj.post(cr, uid, [move_id], context={})

            if reconcile_lines:
                for move_set in reconcile_lines:
                    if len(move_set) >= 2:
                        move_line_obj.reconcile_partial(cr, uid, move_set)

            self.write(cr, uid, ids, {'state': 'posted', 'move_id': move_id})

        return True

    def copy(self, cr, uid, id, default={}, context=None):
        default.update({
            'state': 'draft',
            'number': False,
            'move_id': False,
            'qm_ids': False,
            'reference': False
        })
        if 'date' not in default:
            default['date'] = time.strftime('%Y-%m-%d')
        return super(document_receipt, self).copy(cr, uid, id, default, context)


document_receipt()

class document_receipt_cash(osv.osv):
    _name = 'numa_ar_base.document_receipt_cash'
    _description = 'Received cash'

    def _get_currency (self, cr, uid, context=None):
        if not context: context = {}
        return context.get('currency_id', False)

    _columns = {
        'dr_id':fields.many2one('numa_ar_base.document_receipt', 'Receipt', ondelete='cascade'),
        'currency_id': fields.many2one('res.currency','Currency', required=True),
        'original_amount':fields.float('Amount on original currency', digits_compute=dp.get_precision('Account'), required=True),
        'exchange_rate':fields.float('Exchange rate', digits_compute=dp.get_precision('Account'), required=True),
        'amount':fields.float('Amount', digits_compute=dp.get_precision('Account')),
    }
    
    _defaults = {
        'currency_id': _get_currency,
    }
    
    def create (self, cr, uid, vals, context=None):
        vals['amount'] = vals.get('original_amount', 0.0) * vals.get('exchange_rate', 0.0)
        return super (document_receipt_cash, self).create (cr, uid, vals, context=context)

    def write (self, cr, uid, ids, vals, context=None):
        if vals.get('original_amount', False) or vals.get('exchange_rate', False):
            wid = isinstance(ids, (int, long)) and ids or ids[0]                
            dr = self.browse (cr, uid, wid, context=context)
            vals['amount'] = vals.get('original_amount', dr.original_amount) * vals.get('exchange_rate', dr.exchange_rate)
        vals['amount'] = vals.get('original_amount', 0.0) * vals.get('exchange_rate', 0.0)
        return super (document_receipt_cash, self).write (cr, uid, ids, vals, context=context)

    def onchange_currency_id (self, cr, uid, ids, currency_id, original_amount, dr_currency_id, context=None):
        if not context: context={}
        
        if not dr_currency_id:
            raise osv.except_osv(_("Error!"),
                _("No currency defined. Probably you didn't select the journal yet! Please check"))
                
        if not currency_id:
            return False
            
        currency_obj = self.pool.get('res.currency')
        from_currency = currency_obj.browse (cr, uid, currency_id)
        if dr_currency_id:
            to_currency = currency_obj.browse (cr, uid, dr_currency_id)
            return {'value': {
                        'exchange_rate': currency_obj._get_conversion_rate (cr, uid, from_currency, to_currency, context=context),
                        'amount': currency_obj.compute (cr, uid, currency_id, dr_currency_id, original_amount, context=context),
                    }}
        return False

    def onchange_exchange_rate (self, cr, uid, ids, exchange_rate, original_amount, context=None):
        if not context: context={}

        return {'value': {
                    'amount': (original_amount or 0.0) * (exchange_rate or 0.0),
                }}

    def onchange_original_amount (self, cr, uid, ids, original_amount, exchange_rate, context=None):
        if not context: context={}

        return {'value': {
                    'amount': (original_amount or 0.0) * (exchange_rate or 0.0),
                }}

document_receipt_cash()

class document_receipt_bt(osv.osv):
    _name = 'numa_ar_base.document_receipt_bt'
    _description = 'Received bank transfer'

    def _get_currency (self, cr, uid, context=None):
        if not context: context = {}
        return context.get('currency_id', False)

    def _get_transfer_date (self, cr, uid, context=None):
        if not context: context = {}
        return context.get('transfer_date', False)

    _columns = {
        'dr_id':fields.many2one('numa_ar_base.document_receipt', 'Receipt', ondelete='cascade'),
        'reference': fields.char('Ref #', size=64, help="Reference number."),
        'bank_journal_id':fields.many2one('account.journal', 'Bank Journal', required=True, domain=[('type','=','bank')]),
        'currency_id': fields.many2one('res.currency','Currency', required=True),
        'original_amount':fields.float('Original amount', digits_compute=dp.get_precision('Account'), required=True),
        'exchange_rate':fields.float('Exchange rate', digits_compute=dp.get_precision('Account'), required=True),
        'amount':fields.float('Amount', digits_compute=dp.get_precision('Account'), required=True),
        'transfer_date':fields.date('Transfer date', select=True, help="Effective transfer date, according to bank"),
    }

    _defaults = {
        'currency_id': _get_currency,
        'transfer_date': _get_transfer_date,
    }

    def create (self, cr, uid, vals, context=None):
        vals['amount'] = vals.get('original_amount', 0.0) * vals.get('exchange_rate', 0.0)
        return super (document_receipt_bt, self).create (cr, uid, vals, context=context)

    def write (self, cr, uid, ids, vals, context=None):
        vals['amount'] = vals.get('original_amount', 0.0) * vals.get('exchange_rate', 0.0)
        return super (document_receipt_bt, self).write (cr, uid, ids, vals, context=context)
        
    def onchange_bank_journal_id (self, cr, uid, ids, bank_journal_id, context=None):
        journal_obj = self.pool.get('account.journal')
        
        if bank_journal_id:
            bank_journal = journal_obj.browse (cr, uid, bank_journal_id, context=context)
            if (not bank_journal.default_credit_account_id) or (not bank_journal.default_debit_account_id):
                raise osv.except_osv(_("Configuration error!"),
                    _("No default account defined on bank journal for credit or debit entries!. Please configure them or select another journal!"))
        
        return False

    def onchange_currency_id (self, cr, uid, ids, currency_id, original_amount, dr_currency_id, context=None):
        if not context: context={}

        if not dr_currency_id:
            raise osv.except_osv(_("Error!"),
                _("No currency defined. Probably you didn't select the journal yet! Please check"))
                
        if not currency_id:
            return
            
        currency_obj = self.pool.get('res.currency')
        from_currency = currency_obj.browse (cr, uid, currency_id)
        if dr_currency_id:
            to_currency = currency_obj.browse (cr, uid, dr_currency_id)
            return {'value': {
                        'exchange_rate': currency_obj._get_conversion_rate (cr, uid, from_currency, to_currency, context=context),
                        'amount': currency_obj.compute (cr, uid, currency_id, dr_currency_id, original_amount, context=context),
                    }}
        return False

    def onchange_exchange_rate (self, cr, uid, ids, exchange_rate, original_amount, context=None):
        if not context: context={}

        return {'value': {
                    'amount': (original_amount or 0.0) * (exchange_rate or 0.0),
                }}

    def onchange_original_amount (self, cr, uid, ids, original_amount, exchange_rate, context=None):
        if not context: context={}

        return {'value': {
                    'amount': (original_amount or 0.0) * (exchange_rate or 0.0),
                }}

document_receipt_bt()

class document_receipt_qm(osv.osv):
    _name = 'numa_ar_base.document_receipt_qm'
    _description = 'Document receipt Quick moves'
    _order = "qm_id"

    _columns = {
        'dr_id':fields.many2one('numa_ar_base.document_receipt', 'Receipt', ondelete='cascade'),
        'qm_id':fields.many2one('numa_ar_base.quick_move', 'Code', required=True),
        'credit_account_id':fields.many2one('account.account', 'Credit account', required=1),
        'debit_account_id':fields.many2one('account.account', 'Debit account', required=1),
        'analytic_account_id':fields.many2one('account.analytic.account', 'Analitic account'),
        'description':fields.related('qm_id', 'description', type='char', string='Description'),
        'amount':fields.float('Amount', digits_compute=dp.get_precision('Account'), required=True),
    }

    def onchange_qm_id (self, cr, uid, ids, qm_id, context = None):
        if not context: context = {}

        if not qm_id:
            return False

        qm_obj = self.pool.get('numa_ar_base.quick_move')
        qm = qm_obj.browse(cr, uid, qm_id, context=context)
        res = {'value': {
                         'credit_account_id': qm.credit_account_id.id,
                         'debit_account_id': qm.debit_account_id.id,
                         'analytic_account_id': qm.analytic_account_id and qm.analytic_account_id.id or False,
                         'description': qm.description,
                        }}
        return res

document_receipt_qm()

class document_receipt_debt(osv.osv):
    _name = 'numa_ar_base.document_receipt_debt'
    _description = 'Receipt Debts'
    _order = "move_line_id"

    _columns = {
        'dr_id':fields.many2one('numa_ar_base.document_receipt', 'Receipt', ondelete='cascade'),
        'name':fields.char('Description', size=256),
        'account_id':fields.many2one('account.account','Account', required=True),
        'partner_id':fields.related('dr_id', 'partner_id', type='many2one', relation='res.partner', string='Customer'),
        'amount_original': fields.float('Original amount', digits_compute=dp.get_precision('Account'), required=True), 
        'amount_unreconciled': fields.float('Open debt', digits_compute=dp.get_precision('Account'), required=True), 
        'amount':fields.float('Amount to reconcile', digits_compute=dp.get_precision('Account')),
        'move_line_id': fields.many2one('account.move.line', 'Move line'),
        'date_original': fields.related('move_line_id','date', type='date', relation='account.move.line', string='Date', readonly=1),
        'date_due': fields.date(string='Due date', readonly=1),
        'company_id': fields.related('dr_id','company_id', relation='res.company', type='many2one', string='Company', readonly=True),
    }
    _defaults = {
        'name': '',

    }

    def default_get(self, cr, user, fields_list, context=None):
        """
        Returns default values for fields
        @param fields_list: list of fields, for which default values are required to be read
        @param context: context arguments, like lang, time zone

        @return: Returns a dict that contains default values for fields
        """
        if context is None:
            context = {}
        journal_id = context.get('journal_id', False)
        partner_id = context.get('partner_id', False)
        journal_pool = self.pool.get('account.journal')
        partner_pool = self.pool.get('res.partner')
        values = super(document_receipt_debt, self).default_get(cr, user, fields_list, context=context)
        if (not journal_id) or ('account_id' not in fields_list):
            return values
        journal = journal_pool.browse(cr, user, journal_id, context=context)
        account_id = False
        if journal.type in ('sale', 'sale_refund'):
            account_id = journal.default_credit_account_id and journal.default_credit_account_id.id or False
        elif journal.type in ('purchase', 'expense', 'purchase_refund'):
            account_id = journal.default_debit_account_id and journal.default_debit_account_id.id or False
        elif partner_id:
            partner = partner_pool.browse(cr, user, partner_id, context=context)
            account_id = partner.property_account_receivable.id

        values.update({
            'account_id':account_id,
        })
        return values

document_receipt_debt()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
