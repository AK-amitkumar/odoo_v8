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



class customer_reconcile(osv.osv):
    '''
    A customer reconcile is the document that associates already made payments with debts of the customer
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

    def _get_balance(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        amount = 0.0
        for dr in self.browse (cr, uid, ids, context=context):
            u = []
            for uac in dr.uac_ids:
                u.append({'amount': uac.amount})
            db = []
            for debt in dr.debt_ids:
                db.append({'amount': debt.amount})

            res[dr.id] = self._compute_balance (cr, uid, u, db)
        return res

    def _compute_balance(self, cr, uid, uac_ids, debt_ids):
        currency_obj = self.pool.get('res.currency')

        balance = 0.0
        for uac in uac_ids:
            balance += uac['amount']
        for debt in debt_ids:
            balance -= debt['amount']

        return balance

    _name = 'numa_ar_base.customer_reconcile'
    _description = 'Deffered documents receipt'
    _order = "date desc, id desc"
    _columns = {
        'name':fields.char('Identification', size=256, readonly=True, states={'draft':[('readonly',False)]}),
        'date':fields.date('Date', readonly=True, select=True, states={'draft':[('readonly',False)]}, help="Efective operation date"),
        'journal_id':fields.many2one('account.journal', 'Journal', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'account_id':fields.many2one('account.account', 'Account', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'uac_ids':fields.one2many('numa_ar_base.customer_reconcile_uac','cr_id','Non reconciled credits', readonly=True, states={'draft':[('readonly',False)]}),
        'debt_ids':fields.one2many('numa_ar_base.customer_reconcile_debt','cr_id','Applied debts', readonly=True, states={'draft':[('readonly',False)]}),
        'narration':fields.text('Notas', readonly=True, states={'draft':[('readonly',False)]}),
        'currency_id': fields.many2one('res.currency', string='Moneda', readonly=True, states={'draft':[('readonly',False)]}),
        'company_id': fields.related('journal_id','company_id', type='many2one', relation='res.company', string='Company', store=False, readonly=True),
        'state':fields.selection(
            [('draft','Draft'),
             ('posted','Posted'),
             ('cancel','Canceled')
            ], 'State', readonly=True, size=32,
            help=' * \'Draft\' state is used on new document entry. \
                        \n* \'Posted\' is used when the document is registered and account moves are generated \
                        \n* \'Cancel\' is used for canceled documents.'),
        'partner_id':fields.many2one('res.partner', 'Customer', change_default=1, readonly=True, states={'draft':[('readonly',False)]}),
        'balance': fields.function(_get_balance, method=True, string='Balance', type='float', readonly=True),
        'move_line_ids': fields.many2many('account.move.line', 'customer_reconcile_movements', 'cr_id', 'move_line_id', string='Reconcile', readonly=True, states={'draft':[('readonly',False)]}),
    }
    _defaults = {
        'name':_get_name,
        'journal_id':_get_journal,
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
        customer_reconciles = self.browse (cr, uid, ids)
        return [(dr.id, "%s [%s]" % (dr.name, dr.company_id.name)) for dr in customer_reconciles]

    def onchange_line_ids(self, cr, uid, ids, uac_ids, debt_ids, context=None):
        uac_obj = self.pool.get('numa_ar_base.customer_reconcile_uac')
        debt_obj = self.pool.get('numa_ar_base.customer_reconcile_debt')

        u = resolve_o2m_operations(cr, uid, uac_obj, uac_ids, ['amount'], context=context)
        db = resolve_o2m_operations(cr, uid, debt_obj, debt_ids, ['amount'], context=context)
        
        return {'value': {'balance': self._compute_balance(cr, uid, u, db)}}

    def onchange_journal (self, cr, uid, ids, journal_id, partner_id, date, currency_id, context=None):
        default = {
            'value':{},
        }

        if not partner_id and not journal_id:
            return default

        cash_obj = self.pool.get('numa_ar_base.customer_reconcile_cash')
        journal_obj = self.pool.get('account.journal')
        period_obj = self.pool.get('account.period')

        journal = journal_obj.browse (cr, uid, journal_id, context=context)
        
        default['value']['currency_id'] = journal.currency.id or journal.company_id.currency_id.id
        default['value']['account_id'] = journal.default_debit_account_id.id
        default['value']['company_id'] = journal.company_id.id
            
        if partner_id:
            change_set = self.onchange_partner_id(cr, uid, ids, partner_id, journal_id, date, default['value']['currency_id'], context=context)
            default['value'].update(change_set['value'])

        return default

    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, date, currency_id, context=None):
        if context is None:
            context = {}

        if not partner_id or not journal_id:
            return {}

        currency_pool = self.pool.get('res.currency')
        move_line_pool = self.pool.get('account.move.line')
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')

        journal = journal_pool.browse (cr, uid, journal_id)
        company_id = journal.company_id.id

        company_currency_id = (journal.currency and journal.currency.id) or journal.company_id.currency_id.id

        total_debit = 0.0
        total_credit = 0.0

        default = {'value': {'debt_ids': [], 'uac_ids': []}}

        domain = [('state','=','valid'), ('account_id.type', '=', 'receivable'), ('reconcile_id', '=', False), 
                  ('partner_id', '=', partner_id), ('company_id', '=', company_id)]
        ids = move_line_pool.search(cr, uid, domain, context=context)    
        moves = move_line_pool.browse(cr, uid, ids, context=context)

        credits = []
        debits = []

        for line in moves:
            original_amount = line.debit or line.credit or 0.0
            amount_unreconciled = currency_pool.compute(cr, uid, line.currency_id.id or company_currency_id, currency_id, abs(line.amount_residual))
            amount_original = currency_pool.compute(cr, uid, line.currency_id.id or company_currency_id, currency_id, original_amount)
            rs = {
                'name':line.move_id.name,
                'move_line_id':line.id,
                'account_id':line.account_id.id,
                'analytic_account_id':line.analytic_account_id.id,
                'amount_original': amount_original,
                'date_original':line.date,
                'date_due':line.date_maturity,
                'amount_unreconciled': amount_unreconciled,
                'company_id': journal.company_id.id,
            }

            if line.credit:
                if not (line.reconcile_id or line.reconcile_partial_id):
                    rs['amount'] = amount_unreconciled
                    total_credit += amount_unreconciled
                    credits.append(rs)
            elif line.debit:
                rs['amount'] = 0
                debits.append(rs)

        credits.sort(key=lambda line: line['date_original'])
        debits.sort(key=lambda line: line['date_original'])

        #Apply credit in order to debts
        for debt in debits:
            applied_amount = min(debt['amount_unreconciled'], total_credit)
            debt['amount'] = applied_amount
            total_credit -= applied_amount

        default['value']['uac_ids'] = credits
        default['value']['debt_ids'] = debits

        return default

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
            raise osv.except_osv(_('Error!'), _('No period for receipt date!'))

        return res

    def unlink(self, cr, uid, ids, context=None):
        for t in self.read(cr, uid, ids, ['state'], context=context):
            if t['state'] not in ('draft', 'canceled'):
                raise osv.except_osv(_('Error!'), _('Posted documents could not be cancelled!'))
        return super(customer_reconcile, self).unlink(cr, uid, ids, context=context)

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
        property_obj = self.pool.get('ir.property')
        period_obj = self.pool.get('account.period')

        for receipt in self.browse(cr, uid, ids, context=context):
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
                raise osv.except_osv(_('Error !'), _('No valid period for the entered date!'))

            ref = name.replace('/','')

            self.write (cr, uid, [receipt.id], {'name': name})

            company_currency = receipt.journal_id.company_id.currency_id.id
            current_currency = receipt.currency_id.id

            debit = 0.0
            #Compute the total amount to be payed
            total_credit = 0.0

            for uac in receipt.uac_ids:
                total_credit += uac.amount

            if total_credit == 0:
                    raise osv.except_osv(_('Not complete document!'),
                        _('No credit was entered!'))

            applicable_debts = []
            for line in receipt.debt_ids:
                if line.amount:
                    applicable_debts.append(line)

            debt_index = 0
            if len(applicable_debts):
                debt = applicable_debts[debt_index]
                left_to_apply = min (debt.amount_unreconciled, debt.amount)

            reconcile_lines = []
            reconcile_new_lines = []

            #Process unassigned credit entries

            #pdb.set_trace()

            for uac in receipt.uac_ids:

                amount_to_apply = uac.amount

                if amount_to_apply and debt_index < len(applicable_debts):
                    #Apply this amount to debts not yet covered

                    while debt_index < len(applicable_debts) and amount_to_apply > 0:
                        #Taking the amount to apply, try to cover as many docs as possible
                        #we check if the voucher line is fully paid or not and create a move line to balance the payment and initial invoice if needed

                        to_apply = min (amount_to_apply, left_to_apply)

                        if to_apply:
                            old = uac.move_line_id
                            if (uac.amount_original-uac.amount+amount_to_apply) > to_apply:
                                new_line_data = {
                                    'move_id': old.move_id.id,
                                    'account_id': old.account_id.id,
                                    'partner_id': old.partner_id.id,
                                    'name': old.name,
                                    'ref': old.ref,
                                    'date_maturity': old.date_maturity,
                                    'credit': to_apply,
                                    'debit': 0.0,
                                    'state': 'valid',
                                }

                                new_line_id = move_line_obj.create (cr, uid, new_line_data, check=False)

                                reconcile_new_lines.append(new_line_id)

                                if debt.move_line_id.id:
                                    rec_ids = [new_line_id, debt.move_line_id.id]
                                    reconcile_lines.append(rec_ids)
                            else:
                                move_line_obj.write(cr, uid, [old.id], {
                                                    'credit': to_apply, 
                                                    'debit': 0.0}, check=False, update_check=False)
                                reconcile_new_lines.append(old.id)

                                if debt.move_line_id.id:
                                    rec_ids = [old.id, debt.move_line_id.id]
                                    reconcile_lines.append(rec_ids)

                            amount_to_apply -= to_apply
                            left_to_apply -= to_apply


                        if not left_to_apply or not to_apply:
                            debt_index += 1
                            if debt_index < len(applicable_debts):
                                debt = applicable_debts[debt_index]
                                left_to_apply = min (debt.amount_unreconciled, debt.amount)

                    if (uac.amount_original-uac.amount+amount_to_apply) > 0:
                        move_line_obj.write(cr, uid, [uac.move_line_id.id], {
                                            'credit': uac.amount_original-uac.amount+amount_to_apply, 
                                            'debit': 0.0}, check=False, update_check=False)

            #Trigger reconcile on all affected debts

            self.write (cr, uid, [receipt.id], {'state': 'posted', 'move_line_ids': [(6, 0, reconcile_new_lines)]})

            for rec_ids in reconcile_lines:
                if len(rec_ids) >= 2:
                    move_line_obj.reconcile_partial(cr, uid, rec_ids)

        return True

    def copy(self, cr, uid, id, default={}, context=None):
        default.update({
            'state': 'draft',
            'number': False,
            'move_id': False,
            'qm_ids': False,
            #'doc_ids': False,
            'debt_ids': False,
            'reference': False
        })
        if 'date' not in default:
            default['date'] = time.strftime('%Y-%m-%d')
        return super(customer_reconcile, self).copy(cr, uid, id, default, context)


customer_reconcile()

class customer_reconcile_debt(osv.osv):
    _name = 'numa_ar_base.customer_reconcile_debt'
    _description = 'Document receipt Debts'
    _order = "move_line_id"

    _columns = {
        'cr_id':fields.many2one('numa_ar_base.customer_reconcile', 'Receipt', ondelete='cascade'),
        'name':fields.char('Description', size=256),
        'account_id':fields.many2one('account.account','Account', required=True),
        'partner_id':fields.related('cr_id', 'partner_id', type='many2one', relation='res.partner', string='Customer'),
        'amount_original': fields.float('Importe original', digits_compute=dp.get_precision('Account'), required=True), 
        'amount_unreconciled': fields.float('Deuda no cancelada', digits_compute=dp.get_precision('Account'), required=True), 
        'amount':fields.float('Importe a aplicar', digits_compute=dp.get_precision('Account')),
        'analytic_account_id':  fields.many2one('account.analytic.account', 'Cuenta analítica'),
        'move_line_id': fields.many2one('account.move.line', 'Move line'),
        'date_original': fields.related('move_line_id','date', type='date', relation='account.move.line', string='Date', readonly=1),
        'date_due': fields.date(string='Due date', readonly=1),
        'company_id': fields.related('cr_id','company_id', relation='res.company', type='many2one', string='Company', readonly=True),
    }
    _defaults = {
        'name': '',

    }

    def onchange_move_line_id(self, cr, user, ids, move_line_id, context=None):
        """
        Returns a dict that contains new values and context

        @param move_line_id: latest value from user input for field move_line_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone

        @return: Returns a dict which contains new values, and context
        """
        res = {}
        move_line_pool = self.pool.get('account.move.line')
        if move_line_id:
            move_line = move_line_pool.browse(cr, user, move_line_id, context=context)
            if move_line.credit:
                ttype = 'dr'
            else:
                ttype = 'cr'
            account_id = move_line.account_id.id
            res.update({
                'account_id':account_id,
                'type': ttype
            })
        return {
            'value':res,
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
        values = super(customer_reconcile_debt, self).default_get(cr, user, fields_list, context=context)
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
customer_reconcile_debt()

class customer_reconcile_uac(osv.osv):
    _name = 'numa_ar_base.customer_reconcile_uac'
    _description = 'Document receipt Unassigned Credits'
    _order = "move_line_id"

    _columns = {
        'cr_id':fields.many2one('numa_ar_base.customer_reconcile', 'Receipt', ondelete='cascade'),
        'name':fields.char('Description', size=256),
        'account_id':fields.many2one('account.account','Account', required=True),
        'partner_id':fields.related('cr_id', 'partner_id', type='many2one', relation='res.partner', string='Cliente'),
        'amount_original': fields.float('Original ammount', digits_compute=dp.get_precision('Account'), required=True), 
        'amount_unreconciled': fields.float('Non applied ammount', digits_compute=dp.get_precision('Account'), required=True), 
        'amount':fields.float('Amount to be applied', digits_compute=dp.get_precision('Account')),
        'analytic_account_id':  fields.many2one('account.analytic.account', 'Analitic account'),
        'move_line_id': fields.many2one('account.move.line', 'Move line'),
        'date_original': fields.related('move_line_id','date', type='date', relation='account.move.line', string='Date', readonly=1),
        'date_due': fields.date(string='Due date', readonly=1),
        'company_id': fields.related('cr_id','company_id', relation='res.company', type='many2one', string='Company', readonly=True),
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
        values = super(customer_reconcile_uac, self).default_get(cr, user, fields_list, context=context)
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
customer_reconcile_uac()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
