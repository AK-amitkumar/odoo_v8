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

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import time


from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp import netsvc
from openerp.exceptions import Warning
import string
import base64
from xlrd import open_workbook
import StringIO

import pdb
import logging


logger = logging.getLogger(__name__)

class res_partner(osv.osv):
    _name = "res.partner"
    _inherit = "res.partner"


    def check_vat_ar(self, vat):
        return True

    def check_vat(self, cr, uid, ids, context=None):
        user_company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        if user_company.vat_check_vies:
            # force full VIES online check
            check_func = self.vies_vat_check
        else:
            # quick and partial off-line checksum validation
            check_func = self.simple_vat_check
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner.vat:
                continue

            vat_country = False
            if user_company.country_id and user_company.country_id.code:
                vat_country = user_company.country_id.code.lower()
            vat_number = partner.vat

            if not check_func(cr, uid, vat_country, vat_number, context=context):
                logger.info(_("Importing VAT Number [%s] is not valid !" % vat_number))
                return False
        return True

    def _construct_constraint_msg(self, cr, uid, ids, context=None):

        def default_vat_check(cn, vn):
            return cn[0] in string.ascii_lowercase and cn[1] in string.ascii_lowercase

        vat_country, vat_number = self._split_vat(self.browse(cr, uid, ids)[0].vat)
        vat_no = "'CC##' (CC=Country Code, ##=VAT Number)"
        error_partner = self.browse(cr, uid, ids, context=context)
        if default_vat_check(vat_country, vat_number):
            vat_no = _ref_vat[vat_country] if vat_country in _ref_vat else vat_no
            if self.pool['res.users'].browse(cr, uid, uid).company_id.vat_check_vies:
                return '\n' + _('The VAT number [%s] for partner [%s] either failed the VIES VAT validation check or did not respect the expected format %s.') % (error_partner[0].vat, error_partner[0].name, vat_no)
        return '\n' + _('The VAT number [%s] for partner [%s] does not seem to be valid. \nNote: the expected format is %s') % (error_partner[0].vat, error_partner[0].name, vat_no)

    _constraints = [(check_vat, _construct_constraint_msg, ["vat"])]

    def check_vat_es(self, vat):
        return True

    def _get_default_country(self, cr, uid, context=None):
        country_obj = self.pool.get('res.country')

        arg_ids = country_obj.search(cr, uid, [('code','=','AR')], context=context)
        if arg_ids:
            return arg_ids[0]
        else:
            return False

    def _get_default_state(self, cr, uid, context=None):
        fed_state_obj = self.pool.get('res.country.state')

        arg_ids = fed_state_obj.search(cr, uid, [('name','=','Córdoba')], context=context)
        if arg_ids:
            return arg_ids[0]
        else:
            return False

    def _get_balance(self, cr, uid, ids, field_names, arg, context=None):
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        res = {}
        for pid in ids:
            res[pid] = {}.fromkeys(field_names, 0)

            cr.execute("""SELECT l.partner_id as partner, SUM(l.debit-l.credit) as balance
                          FROM account_move_line l
                          LEFT JOIN account_account a ON (l.account_id=a.id)
                          WHERE a.type IN ('receivable','payable')
                          AND l.partner_id IN %s
                          AND l.reconcile_id IS NULL
                          AND """ + query + """
                          GROUP BY partner
                          """,
                       (tuple(self.get_partner_domain(cr, uid, pid)),))

            total = 0.0
            for partner,balance in cr.fetchall():
                if not balance: balance = 0.0
                total += balance
            res[pid]['balance'] = total
        return res

    def _get_credit(self, cr, uid, ids, field_names, arg, context=None):
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        map_days = {
            'f0-30':   'credit_30',
            'f31-60':  'credit_60',
            'f61-90':  'credit_90',
            'f91plus': 'credit_90plus',
            '0-30':    'ocredit_30',
            '31-60':   'ocredit_60',
            '61-90':   'ocredit_90',
            '91plus':  'ocredit_90plus',
        }

        res = {}
        for pid in ids:
            res[pid] = {}.fromkeys(field_names, 0)

            cr.execute("""SELECT CASE
                            when (current_date - COALESCE(l.date_maturity,l.date)) < -90 then 'f91plus'
                            when (current_date - COALESCE(l.date_maturity,l.date)) < -60 then 'f61-90'
                            when (current_date - COALESCE(l.date_maturity,l.date)) < -30 then 'f31-60'
                            when (current_date - COALESCE(l.date_maturity,l.date)) < 0   then 'f0-30'
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 30 then '0-30'
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 60 then '31-60'
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 90 then '61-90'
                            else '91plus'
                            end as days, SUM(l.debit-l.credit) as amount
                          FROM account_move_line l
                          LEFT JOIN account_account a ON (l.account_id=a.id)
                          WHERE a.type IN ('receivable')
                          AND l.partner_id IN %s
                          AND l.reconcile_id IS NULL
                          AND l.reconcile_partial_id IS NULL
                          AND """ + query + """
                          GROUP BY days
                          """,
                       (tuple(self.get_partner_domain(cr, uid, pid)),))

            for days,amount in cr.fetchall():
                if amount is None: amount=0
                res[pid][map_days[days]] = amount

        for pid in res.keys():
            res[pid]['credit_invoice'] = \
                res[pid].get('credit_30', 0) + \
                res[pid].get('credit_60', 0) + \
                res[pid].get('credit_90', 0) + \
                res[pid].get('credit_90plus', 0)
            res[pid]['ocredit'] = \
                res[pid].get('ocredit_30', 0) + \
                res[pid].get('ocredit_60', 0) + \
                res[pid].get('ocredit_90', 0) + \
                res[pid].get('ocredit_90plus', 0)

        return res

    def _get_partial_credit(self, cr, uid, ids, field_names, arg, context=None):
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        map_days = {
            'f0-30': 'partial_credit_30',
            'f31-60': 'partial_credit_60',
            'f61-90': 'partial_credit_90',
            'f91plus': 'partial_credit_90plus',
            '0-30': 'partial_ocredit_30',
            '31-60': 'partial_ocredit_60',
            '61-90': 'partial_ocredit_90',
            '91plus': 'partial_ocredit_90plus',
        }

        res = {}
        for pid in ids:
            res[pid] = {}.fromkeys(field_names, 0)

            cr.execute("""SELECT CASE
                                when (current_date - issued_on) < -90 then 'f91plus'
                                when (current_date - issued_on) < -60 then 'f61-90'
                                when (current_date - issued_on) < -30 then 'f31-60'
                                when (current_date - issued_on) < 0   then 'f0-30'
                                when (current_date - issued_on) <= 30 then '0-30'
                                when (current_date - issued_on) <= 60 then '31-60'
                                when (current_date - issued_on) <= 90 then '61-90'
                                else '91plus'
                                end as days, SUM(left_amount) as amount
                          FROM (
                              SELECT l.reconcile_partial_id as rp, MIN(COALESCE(l.date_maturity,l.date)) as issued_on, SUM(l.debit - l.credit) as left_amount
                              FROM account_move_line l
                              LEFT JOIN account_account a ON (l.account_id=a.id)
                              WHERE a.type IN ('receivable')
                              AND l.partner_id IN %s
                              AND l.reconcile_id IS NULL
                              AND l.reconcile_partial_id IS NOT NULL
                              AND """ + query + """
                              GROUP BY rp
                          ) AS s
                          GROUP BY days
                          """,
                       (tuple(self.get_partner_domain(cr, uid, pid)),))

            for days,amount in cr.fetchall():
                if amount is None: amount=0
                if not res[pid].get(map_days[days], False):
                    res[pid][map_days[days]] = 0
                res[pid][map_days[days]] += amount

        for pid in res.keys():
            res[pid]['partial_credit'] = \
                res[pid].get('partial_credit_30', 0) + \
                res[pid].get('partial_credit_60', 0) + \
                res[pid].get('partial_credit_90', 0) + \
                res[pid].get('partial_credit_90plus', 0)
            res[pid]['partial_ocredit'] = \
                res[pid].get('partial_ocredit_30', 0) + \
                res[pid].get('partial_ocredit_60', 0) + \
                res[pid].get('partial_ocredit_90', 0) + \
                res[pid].get('partial_ocredit_90plus', 0)

        return res

    def _get_document_credit(self, cr, uid, ids, field_names, arg, context=None):
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        map_days = {
            'f0-30':   'document_credit_30',
            'f31-60':  'document_credit_60',
            'f61-90':  'document_credit_90',
            'f91plus': 'document_credit_90plus',
            '0-30':    'document_ocredit_30',
            '31-60':   'document_ocredit_60',
            '61-90':   'document_ocredit_90',
            '91plus':  'document_ocredit_90plus',
        }

        res = {}
        for pid in ids:
            res[pid] = {}.fromkeys(field_names, 0)

            cr.execute("""SELECT CASE
                            when (current_date - COALESCE(l.date_maturity,l.date)) < -90 then 'f91plus'
                            when (current_date - COALESCE(l.date_maturity,l.date)) < -60 then 'f61-90'
                            when (current_date - COALESCE(l.date_maturity,l.date)) < -30 then 'f31-60'
                            when (current_date - COALESCE(l.date_maturity,l.date)) < 0   then 'f0-30'
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 30 then '0-30'
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 60 then '31-60'
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 90 then '61-90'
                            else '91plus'
                            end as days, SUM(l.debit-l.credit) as amount
                          FROM account_move_line l
                          LEFT JOIN account_account a ON (l.account_id=a.id)
                          WHERE a.type IN ('document_rec')
                          AND l.partner_id IN %s
                          AND l.reconcile_id IS NULL
                          AND l.reconcile_partial_id IS NULL
                          AND """ + query + """
                          GROUP BY days
                          """,
                       (tuple(self.get_partner_domain(cr, uid, pid)),))

            for days,amount in cr.fetchall():
                if amount is None: amount=0
                res[pid][map_days[days]] = amount

        for pid in res.keys():
            res[pid]['document_credit'] = \
                res[pid].get('document_credit_30', 0) + \
                res[pid].get('document_credit_60', 0) + \
                res[pid].get('document_credit_90', 0) + \
                res[pid].get('document_credit_90plus', 0)
            res[pid]['document_ocredit'] = \
                res[pid].get('document_ocredit_30', 0) + \
                res[pid].get('document_ocredit_60', 0) + \
                res[pid].get('document_ocredit_90', 0) + \
                res[pid].get('document_ocredit_90plus', 0)

        return res

    def _get_debt(self, cr, uid, ids, field_names, arg, context=None):
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        map_days = {
            'f0-30':   'debt_30',
            'f31-60':  'debt_60',
            'f61-90':  'debt_90',
            'f91plus': 'debt_90plus',
            '0-30':    'odebt_30',
            '31-60':   'odebt_60',
            '61-90':   'odebt_90',
            '91plus':  'odebt_90plus',
        }

        res = {}
        for pid in ids:
            res[pid] = {}.fromkeys(field_names, 0)

            cr.execute("""SELECT CASE
                            when (current_date - COALESCE(l.date_maturity,l.date)) < -90 then 'f91plus'
                            when (current_date - COALESCE(l.date_maturity,l.date)) < -60 then 'f61-90'
                            when (current_date - COALESCE(l.date_maturity,l.date)) < -30 then 'f31-60'
                            when (current_date - COALESCE(l.date_maturity,l.date)) < 0   then 'f0-30'
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 30 then '0-30'
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 60 then '31-60'
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 90 then '61-90'
                            else '91plus'
                            end as days, SUM(l.debit-l.credit) as amount
                          FROM account_move_line l
                          LEFT JOIN account_account a ON (l.account_id=a.id)
                          WHERE a.type IN ('payable')
                          AND l.partner_id IN %s
                          AND l.reconcile_id IS NULL
                          AND l.reconcile_partial_id IS NULL
                          AND """ + query + """
                          GROUP BY days
                          """,
                       (tuple(self.get_partner_domain(cr, uid, pid)),))

            for days,amount in cr.fetchall():
                if amount is None: amount=0
                res[pid][map_days[days]] = amount

        for pid in res.keys():
            res[pid]['debt_invoice'] = \
                res[pid].get('debt_30', 0) + \
                res[pid].get('debt_60', 0) + \
                res[pid].get('debt_90', 0) + \
                res[pid].get('debt_90plus', 0)
            res[pid]['odebt'] = \
                res[pid].get('odebt_30', 0) + \
                res[pid].get('odebt_60', 0) + \
                res[pid].get('odebt_90', 0) + \
                res[pid].get('odebt_90plus', 0)

        return res

    def _get_partial_debt(self, cr, uid, ids, field_names, arg, context=None):
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        map_days = {
            'f0-30': 'partial_debt_30',
            'f31-60': 'partial_debt_60',
            'f61-90': 'partial_debt_90',
            'f91plus': 'partial_debt_90plus',
            '0-30': 'partial_odebt_30',
            '31-60': 'partial_odebt_60',
            '61-90': 'partial_odebt_90',
            '91plus': 'partial_odebt_90plus',
        }

        res = {}
        for pid in ids:
            res[pid] = {}.fromkeys(field_names, 0)

            cr.execute("""SELECT CASE
                                when (current_date - issued_on) < -90 then 'f91plus'
                                when (current_date - issued_on) < -60 then 'f61-90'
                                when (current_date - issued_on) < -30 then 'f31-60'
                                when (current_date - issued_on) < 0   then 'f0-30'
                                when (current_date - issued_on) <= 30 then '0-30'
                                when (current_date - issued_on) <= 60 then '31-60'
                                when (current_date - issued_on) <= 90 then '61-90'
                                else '91plus'
                                end as days, SUM(left_amount) as amount
                          FROM (
                              SELECT l.reconcile_partial_id as rp, MIN(COALESCE(l.date_maturity,l.date)) as issued_on, SUM(l.debit - l.credit) as left_amount
                              FROM account_move_line l
                              LEFT JOIN account_account a ON (l.account_id=a.id)
                              WHERE a.type IN ('payable')
                              AND l.partner_id IN %s
                              AND l.reconcile_id IS NULL
                              AND l.reconcile_partial_id IS NOT NULL
                              AND """ + query + """
                              GROUP BY rp
                          ) AS s
                          GROUP BY days
                          """,
                       (tuple(self.get_partner_domain(cr, uid, pid)),))

            for days,amount in cr.fetchall():
                if amount is None: amount=0
                if not res[pid].get(map_days[days], False):
                    res[pid][map_days[days]] = 0
                res[pid][map_days[days]] += amount

        for pid in res.keys():
            res[pid]['partial_debt'] = \
                res[pid].get('partial_debt_30', 0) + \
                res[pid].get('partial_debt_60', 0) + \
                res[pid].get('partial_debt_90', 0) + \
                res[pid].get('partial_debt_90plus', 0)
            res[pid]['partial_odebt'] = \
                res[pid].get('partial_odebt_30', 0) + \
                res[pid].get('partial_odebt_60', 0) + \
                res[pid].get('partial_odebt_90', 0) + \
                res[pid].get('partial_odebt_90plus', 0)

        return res

    def _get_document_debt(self, cr, uid, ids, field_names, arg, context=None):
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        map_days = {
            'f0-30':   'document_debt_30',
            'f31-60':  'document_debt_60',
            'f61-90':  'document_debt_90',
            'f91plus': 'document_debt_90plus',
            '0-30':    'document_odebt_30',
            '31-60':   'document_odebt_60',
            '61-90':   'document_odebt_90',
            '91plus':  'document_odebt_90plus',
        }

        res = {}
        for pid in ids:
            res[pid] = {}.fromkeys(field_names, 0)

            cr.execute("""SELECT CASE
                            when (current_date - COALESCE(l.date_maturity,l.date)) < -90 then 'f91plus'
                            when (current_date - COALESCE(l.date_maturity,l.date)) < -60 then 'f61-90'
                            when (current_date - COALESCE(l.date_maturity,l.date)) < -30 then 'f31-60'
                            when (current_date - COALESCE(l.date_maturity,l.date)) < 0   then 'f0-30'
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 30 then '0-30'
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 60 then '31-60'
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 90 then '61-90'
                            else '91plus'
                            end as days, SUM(l.debit-l.credit) as amount
                          FROM account_move_line l
                          LEFT JOIN account_account a ON (l.account_id=a.id)
                          WHERE a.type IN ('document_pay')
                          AND l.partner_id IN %s
                          AND l.reconcile_id IS NULL
                          AND l.reconcile_partial_id IS NULL
                          AND """ + query + """
                          GROUP BY days
                          """,
                       (tuple(self.get_partner_domain(cr, uid, pid)),))

            for days,amount in cr.fetchall():
                if amount is None: amount=0
                res[pid][map_days[days]] = amount


        for pid in res.keys():
            res[pid]['document_debt'] = \
                res[pid].get('document_debt_30', 0) + \
                res[pid].get('document_debt_60', 0) + \
                res[pid].get('document_debt_90', 0) + \
                res[pid].get('document_debt_90plus', 0)
            res[pid]['document_odebt'] = \
                res[pid].get('document_odebt_30', 0) + \
                res[pid].get('document_odebt_60', 0) + \
                res[pid].get('document_odebt_90', 0) + \
                res[pid].get('document_odebt_90plus', 0)

        return res

    def _get_rejected(self, cr, uid, ids, field_names, arg, context=None):
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        res = {}
        for pid in ids:
            res[pid] = {}.fromkeys(field_names, 0)

            map_days = {
                '0-30':    'rej_rec_doc_30',
                '31-60':   'rej_rec_doc_60',
                '61-90':   'rej_rec_doc_90',
                '91plus':  'rej_rec_doc_90plus',
            }

            cr.execute("""SELECT CASE
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 30 then '0-30'
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 60 then '31-60'
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 90 then '61-90'
                            else '91plus'
                            end as days, SUM(l.debit-l.credit) as amount
                          FROM account_move_line l
                          LEFT JOIN account_account a ON (l.account_id=a.id)
                          WHERE a.type IN ('document_rec_rej')
                          AND l.partner_id IN %s
                          AND l.reconcile_id IS NULL
                          AND l.reconcile_partial_id IS NULL
                          AND l.debit > 0
                          AND """ + query + """
                          GROUP BY days
                          """,
                       (tuple(self.get_partner_domain(cr, uid, pid)),))

            for days,amount in cr.fetchall():
                if amount is None: amount=0
                res[pid][map_days[days]] = amount

            map_days = {
                '0-30':    'rej_pay_doc_30',
                '31-60':   'rej_pay_doc_60',
                '61-90':   'rej_pay_doc_90',
                '91plus':  'rej_pay_doc_90plus',
            }

            cr.execute("""SELECT CASE
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 30 then '0-30'
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 60 then '31-60'
                            when (current_date - COALESCE(l.date_maturity,l.date)) <= 90 then '61-90'
                            else '91plus'
                            end as days, SUM(l.debit-l.credit) as amount
                          FROM account_move_line l
                          LEFT JOIN account_account a ON (l.account_id=a.id)
                          WHERE a.type IN ('document_pay_rej')
                          AND l.partner_id IN %s
                          AND l.reconcile_id IS NULL
                          AND l.reconcile_partial_id IS NULL
                          AND l.credit > 0
                          AND """ + query + """
                          GROUP BY days
                          """,
                       (tuple(self.get_partner_domain(cr, uid, pid)),))

            for days,amount in cr.fetchall():
                if amount is None: amount=0
                res[pid][map_days[days]] = amount

            cr.execute("""SELECT a.type as type, SUM(l.debit-l.credit) as amount
                          FROM account_move_line l
                          LEFT JOIN account_account a ON (l.account_id=a.id)
                          WHERE a.type IN ('document_pay_rej','document_rec_rej')
                          AND l.partner_id IN %s
                          AND l.credit > 0
                          AND """ + query + """
                          GROUP BY type
                          """,
                       (tuple(self.get_partner_domain(cr, uid, pid)),))

            for type,amount in cr.fetchall():
                if amount is None: amount=0
                if type in ['document_rec_rej']:
                    res[pid]['rej_rec_doc_balance'] = amount
                else:
                    res[pid]['rej_pay_doc_balance'] = amount

        for pid in res.keys():
            res[pid]['rej_rec_doc'] = \
                res[pid].get('rej_rec_doc_30', 0) + \
                res[pid].get('rej_rec_doc_60', 0) + \
                res[pid].get('rej_rec_doc_90', 0) + \
                res[pid].get('rej_rec_doc_90plus', 0)
            res[pid]['rej_pay_doc'] = \
                res[pid].get('rej_pay_doc_30', 0) + \
                res[pid].get('rej_pay_doc_60', 0) + \
                res[pid].get('rej_pay_doc_90', 0) + \
                res[pid].get('rej_pay_doc_90plus', 0)

        return res

    def _get_downpayments(self, cr, uid, ids, field_names, arg, context=None):
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)

        map_type = {
            'customer_dp':   'total_customer_dp',
            'supplier_dp':   'total_supplier_dp',
        }

        res = {}
        for pid in ids:
            res[pid] = {}.fromkeys(field_names, 0)

            cr.execute("""SELECT SUM(l.debit-l.credit) as amount, a.type as type
                          FROM account_move_line l
                          LEFT JOIN account_account a ON (l.account_id=a.id)
                          WHERE a.type IN ('customer_dp', 'supplier_dp')
                          AND l.partner_id IN %s
                          AND l.reconcile_id IS NULL
                          AND l.reconcile_partial_id IS NULL
                          AND """ + query + """
                          GROUP BY type
                          """,
                       (tuple(self.get_partner_domain(cr, uid, pid)),))

            for amount, type in cr.fetchall():
                if amount is None: amount=0
                res[pid][map_type[type]] = amount

        return res


    def _get_payments_this_month(self, cr, uid, ids, field_names, arg, context=None):
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        today = date.today()
        year = today.year
        month = today.month
        cr.execute("""SELECT l.partner_id as pid, SUM(l.debit) as payments, SUM(l.credit) as debt
                          FROM account_move_line l
                          LEFT JOIN account_account a ON (l.account_id=a.id)
                          WHERE a.type IN ('payable')
                          AND l.partner_id IN %s
                          AND EXTRACT(YEAR FROM l.date) = %s AND EXTRACT(MONTH FROM l.date) = %s
                          AND """ + query + """
                          GROUP BY pid
                      """,
                   (tuple(ids), str(year), str(month)))

        res = {}
        for pid in ids:
            res[pid] = 0.0

        for pid, payments, debts in cr.fetchall():
            if payments is None: total=0
            res[pid] = payments

        return res

    def _get_rg_gan_retentions_this_month(self, cr, uid, ids, field_names, arg, context=None):
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        today = date.today()
        year = today.year
        month = today.month
        cr.execute("""SELECT l.partner_id as pid, SUM(l.debit) as payments, SUM(l.credit) as debts
                          FROM numa_ar_base_payment AS p
                          INNER JOIN account_move m ON p.move_id = m.id
                          INNER JOIN account_move_line l ON m.id = l.move_id
                          WHERE l.name = 'AFIPRGGANRET'
                          AND l.partner_id IN %s
                          AND EXTRACT(YEAR FROM p.date) = %s AND EXTRACT(MONTH FROM p.date) = %s
                          AND """ + query + """
                          GROUP BY pid
                      """,
                   (tuple(ids), str(year), str(month)))

        res = {}
        for pid in ids:
            res[pid] = 0.0

        for pid, payments, debts in cr.fetchall():
            if payments is None: total=0
            res[pid] = payments

        return res

    def _get_payments_last_year(self, cr, uid, ids, field_names, arg, context=None):
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        today = date.today()
        last_year = today.year - 1
        limit_date = "%04d-%02d-%02d" % (last_year, today.month, today.day)

        cr.execute("""SELECT l.partner_id as pid, SUM(l.debit) as payments, SUM(l.credit) as debt
                          FROM account_move_line l
                          LEFT JOIN account_account a ON (l.account_id=a.id)
                          WHERE a.type IN ('payable')
                          AND l.partner_id IN %s
                          AND l.date > %s
                          AND """ + query + """
                          GROUP BY pid
                      """,
                   (tuple(ids), limit_date))

        res = {}
        for pid in ids:
            res[pid] = 0.0

        for pid, payments, debts in cr.fetchall():
            if payments is None: total=0
            res[pid] = payments

        return res

    def _asset_doc_difference_search(self, cr, uid, obj, name, type, args, context=None):
        if not args:
            return []
        having_values = tuple(map(itemgetter(2), args))
        where = ' AND '.join(
            map(lambda x: '(SUM(debit-credit) %(operator)s %%s)' % {
                                'operator':x[1]},args))
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        cr.execute(('SELECT partner_id FROM account_move_line l '\
                    'WHERE account_id IN '\
                        '(SELECT id FROM account_account '\
                        'WHERE type=%s AND active) '\
                    'AND reconcile_id IS NULL '\
                    'AND '+query+' '\
                    'AND partner_id IS NOT NULL '\
                    'GROUP BY partner_id HAVING '+where),
                   (type,) + having_values)
        res = cr.fetchall()
        if not res:
            return [('id','=','0')]
        return [('id','in',map(itemgetter(0), res))]

    def _credit_doc_search(self, cr, uid, obj, name, args, context=None):
        return self._asset_difference_search(cr, uid, obj, name, 'document_rec', args, context=context)

    def _debit_doc_search(self, cr, uid, obj, name, args, context=None):
        return self._asset_difference_search(cr, uid, obj, name, 'document_pay', args, context=context)

    def _get_default_rg830_code (self, cr, uid, context=None):
        context = context or {}

        rg830_rate_obj = self.pool.get('numa_ar_base.rg830_rate')

        rate_ids = rg830_rate_obj.search (cr, uid, [('codigo_de_regimen','=', '78')])
        return rate_ids and rate_ids[0] or False

    def _get_default_legal_country_id(self, cr, uid, context=None):
        country_obj = self.pool.get('res.country')
        arg_ids = country_obj.search(cr, uid, [('code','=','AR')], context=context)
        return arg_ids[0] if arg_ids else False

    def _get_default_legal_state_id(self, cr, uid, context=None):
        fed_state_obj = self.pool.get('res.country.state')
        arg_ids = fed_state_obj.search(cr, uid, [('name','=','Córdoba')], context=context)
        return arg_ids[0] if arg_ids else False

    _columns = {
                'rg2226_exception': fields.boolean ('Exceptuado RG2226', help='Exeptuado de percepciones y retenciones de Ganancias e IVA por la RG 2226'),
                'rg2226_exc_from': fields.date ('Excepcion valida desde', help='Fecha inicial de la excepción bajo la RG 2226'),
                'rg2226_exc_til': fields.date ('Excepción valida hasta', help='Fecha final de la excepción bajo la RG 2226'),

                'rg830_exception': fields.boolean ('Exceptuado RG830', help='Exeptuado de retenciones de Ganancias, régimen general, RG 830/00'),
                'rg830_exc_from': fields.date ('Excepcion valida desde', help='Fecha inicial de la excepción bajo la RG 830/00'),
                'rg830_exc_til': fields.date ('Excepción valida hasta', help='Fecha final de la excepción bajo la RG 830/00'),

                'document_type_id': fields.many2one(
                    'afip.document_type',
                    'Document type',
                ),
                'cuit_dni': fields.char('CUIT/CUIL/DNI',size=14),

                'vat_condition' : fields.selection([
                                ('01','IVA Resp. Inscripto'),
                                ('02','IVA Resp. no Inscripto'),
                                ('03','IVA no responsable'),
                                ('04','IVA Sujeto Exento'),
                                ('05','Consumidor final'),
                                ('06','Responsable Monotributo'),
                                ('07','Sujeto no Categorizado'),
                                ('08','Proveedor del Exterior'),
                                ('09','Cliente del Exterior'),
                                ('10','IVA Liberado - Ley 19640'),
                                ('11','IVA Resp.Inscripto, Agente de Percepción'),
                                ('12','Pequeño Contribuyente Eventual'),
                                ('13','Monotributista Social'),
                                ('14','Pequeño Contribuyente Eventual Social'),
                                ], 'VAT condition', select=True, required=True),

                'rs_type': fields.selection ([
                                ('00','No aplicable'),
                                ('01','Monotributista, venta de bienes'),
                                ('02','Monotributista, venta de servicios'),
                                ], 'RS type'),

                'legal_country_id': fields.many2one('res.country', 'Legal country', required=True),
                'legal_state_id': fields.many2one('res.country.state', 'Legal state', required=True),

                'default_rg830_code': fields.many2one('numa_ar_base.rg830_rate', 'Default RG830 code', help='RG830 code to be used as default on payments to this supplier'),

                'balance': fields.function(_get_balance, method=True, string='Partner balance'),

                'credit_invoice': fields.function(_get_credit, method=True, string='Total credit, not due', multi='c'),
                'credit_30': fields.function(_get_credit, method=True, string='Total credit, not due (0-30 days)', multi='c'),
                'credit_60': fields.function(_get_credit, method=True, string='Total credit, not due (31-60 days)', multi='c'),
                'credit_90': fields.function(_get_credit, method=True, string='Total credit, not due (61-90 days)', multi='c'),
                'credit_90plus': fields.function(_get_credit, method=True, string='Total credit, not due (91+ days)', multi='c'),
                'ocredit': fields.function(_get_credit, method=True, string='Total credit, overrun', multi='c'),
                'ocredit_30': fields.function(_get_credit, method=True, string='Total credit, overrun (0-30 days)', multi='c'),
                'ocredit_60': fields.function(_get_credit, method=True, string='Total credit, overrun (31-60 days)', multi='c'),
                'ocredit_90': fields.function(_get_credit, method=True, string='Total credit, overrun (61-90 days)', multi='c'),
                'ocredit_90plus': fields.function(_get_credit, method=True, string='Total credit, overrun (91+ days)', multi='c'),

                'partial_credit': fields.function(_get_partial_credit, method=True, string='Total partially paid credit, not due', multi='pc'),
                'partial_credit_30': fields.function(_get_partial_credit, method=True, string='Total partially paid credit, not due (0-30 days)', multi='pc'),
                'partial_credit_60': fields.function(_get_partial_credit, method=True, string='Total partially paid credit, not due (31-60 days)', multi='pc'),
                'partial_credit_90': fields.function(_get_partial_credit, method=True, string='Total partially paid credit, not due (61-90 days)', multi='pc'),
                'partial_credit_90plus': fields.function(_get_partial_credit, method=True, string='Total partially paid credit, not due (91+ days)', multi='pc'),
                'partial_ocredit': fields.function(_get_partial_credit, method=True, string='Total partially paid credit, overrun', multi='pc'),
                'partial_ocredit_30': fields.function(_get_partial_credit, method=True, string='Total partially paid credit, overrun (0-30 days)', multi='pc'),
                'partial_ocredit_60': fields.function(_get_partial_credit, method=True, string='Total partially paid credit, overrun (31-60 days)', multi='pc'),
                'partial_ocredit_90': fields.function(_get_partial_credit, method=True, string='Total partially paid credit, overrun (61-90 days)', multi='pc'),
                'partial_ocredit_90plus': fields.function(_get_partial_credit, method=True, string='Total partially paid credit, overrun (91+ days)', multi='pc'),

                'document_credit': fields.function(_get_document_credit, method=True, string='Total received documents, not due', multi='dc'),
                'document_credit_30': fields.function(_get_document_credit, method=True, string='Total received documents, not due (0-30 days)', multi='dc'),
                'document_credit_60': fields.function(_get_document_credit, method=True, string='Total received documents, not due (31-60 days)', multi='dc'),
                'document_credit_90': fields.function(_get_document_credit, method=True, string='Total received documents, not due (61-90 days)', multi='dc'),
                'document_credit_90plus': fields.function(_get_document_credit, method=True, string='Total received documents, not due (91+ days)', multi='dc'),
                'document_ocredit': fields.function(_get_document_credit, method=True, string='Total received documents, overrun', multi='dc'),
                'document_ocredit_30': fields.function(_get_document_credit, method=True, string='Total received documents, overrun (0-30 days)', multi='dc'),
                'document_ocredit_60': fields.function(_get_document_credit, method=True, string='Total received documents, overrun (31-60 days)', multi='dc'),
                'document_ocredit_90': fields.function(_get_document_credit, method=True, string='Total received documents, overrun (61-90 days)', multi='dc'),
                'document_ocredit_90plus': fields.function(_get_document_credit, method=True, string='Total received documents, overrun (91+ days)', multi='dc'),

                'debt_invoice': fields.function(_get_debt, method=True, string='Total debt, not due', multi='c'),
                'debt_30': fields.function(_get_debt, method=True, string='Total debt, not due (0-30 days)', multi='d'),
                'debt_60': fields.function(_get_debt, method=True, string='Total debt, not due (31-60 days)', multi='d'),
                'debt_90': fields.function(_get_debt, method=True, string='Total debt, not due (61-90 days)', multi='d'),
                'debt_90plus': fields.function(_get_debt, method=True, string='Total debt, not due (91+ days)', multi='d'),
                'odebt': fields.function(_get_debt, method=True, string='Total debt, overrun', multi='d'),
                'odebt_30': fields.function(_get_debt, method=True, string='Total debt, overrun (0-30 days)', multi='d'),
                'odebt_60': fields.function(_get_debt, method=True, string='Total debt, overrun (31-60 days)', multi='d'),
                'odebt_90': fields.function(_get_debt, method=True, string='Total debt, overrun (61-90 days)', multi='d'),
                'odebt_90plus': fields.function(_get_debt, method=True, string='Total debt, overrun (91+ days)', multi='d'),

                'partial_debt': fields.function(_get_partial_debt, method=True, string='Total partially paid debt, not due', multi='pd'),
                'partial_debt_30': fields.function(_get_partial_debt, method=True, string='Total partially paid debt, not due (0-30 days)', multi='pd'),
                'partial_debt_60': fields.function(_get_partial_debt, method=True, string='Total partially paid debt, not due (31-60 days)', multi='pd'),
                'partial_debt_90': fields.function(_get_partial_debt, method=True, string='Total partially paid debt, not due (61-90 days)', multi='pd'),
                'partial_debt_90plus': fields.function(_get_partial_debt, method=True, string='Total partially paid debt, not due (91+ days)', multi='pd'),
                'partial_odebt': fields.function(_get_partial_debt, method=True, string='Total partially paid debt, overrun', multi='pd'),
                'partial_odebt_30': fields.function(_get_partial_debt, method=True, string='Total partially paid debt, overrun (0-30 days)', multi='pd'),
                'partial_odebt_60': fields.function(_get_partial_debt, method=True, string='Total partially paid debt, overrun (31-60 days)', multi='pd'),
                'partial_odebt_90': fields.function(_get_partial_debt, method=True, string='Total partially paid debt, overrun (61-90 days)', multi='pd'),
                'partial_odebt_90plus': fields.function(_get_partial_debt, method=True, string='Total partially paid debt, overrun (91+ days)', multi='pd'),

                'document_debt': fields.function(_get_document_debt, method=True, string='Total received documents, not due', multi='dd'),
                'document_debt_30': fields.function(_get_document_debt, method=True, string='Total received documents, not due (0-30 days)', multi='dd'),
                'document_debt_60': fields.function(_get_document_debt, method=True, string='Total received documents, not due (31-60 days)', multi='dd'),
                'document_debt_90': fields.function(_get_document_debt, method=True, string='Total received documents, not due (61-90 days)', multi='dd'),
                'document_debt_90plus': fields.function(_get_document_debt, method=True, string='Total received documents, not due (91+ days)', multi='dd'),
                'document_odebt': fields.function(_get_document_debt, method=True, string='Total received documents, overrun', multi='dd'),
                'document_odebt_30': fields.function(_get_document_debt, method=True, string='Total received documents, overrun (0-30 days)', multi='dd'),
                'document_odebt_60': fields.function(_get_document_debt, method=True, string='Total received documents, overrun (31-60 days)', multi='dd'),
                'document_odebt_90': fields.function(_get_document_debt, method=True, string='Total received documents, overrun (61-90 days)', multi='dd'),
                'document_odebt_90plus': fields.function(_get_document_debt, method=True, string='Total received documents, overrun (91+ days)', multi='dd'),

                'rej_rec_doc_balance': fields.function(_get_rejected, method=True, string='Total rejected received documents balance', multi='rd'),
                'rej_rec_doc': fields.function(_get_rejected, method=True, string='Total rejected received documents (0-30 days)', multi='rd'),
                'rej_rec_doc_30': fields.function(_get_rejected, method=True, string='Total rejected received documents (0-30 days)', multi='rd'),
                'rej_rec_doc_60': fields.function(_get_rejected, method=True, string='Total rejected received documents (31-60 days)', multi='rd'),
                'rej_rec_doc_90': fields.function(_get_rejected, method=True, string='Total rejected received documents (61-90 days)', multi='rd'),
                'rej_rec_doc_90plus': fields.function(_get_rejected, method=True, string='Total rejected received documents (91+ days)', multi='rd'),
                'rej_pay_doc_balance': fields.function(_get_rejected, method=True, string='Total rejected issued documents balance', multi='rd'),
                'rej_pay_doc': fields.function(_get_rejected, method=True, string='Total rejected received documents (0-30 days)', multi='rd'),
                'rej_pay_doc_30': fields.function(_get_rejected, method=True, string='Total rejected received documents (0-30 days)', multi='rd'),
                'rej_pay_doc_60': fields.function(_get_rejected, method=True, string='Total rejected issued documents (31-60 days)', multi='rd'),
                'rej_pay_doc_90': fields.function(_get_rejected, method=True, string='Total rejected issued documents (61-90 days)', multi='rd'),
                'rej_pay_doc_90plus': fields.function(_get_rejected, method=True, string='Total rejected issued documents (91+ days)', multi='rd'),

                'total_customer_dp': fields.function(_get_downpayments, method=True, string='Customer dowmpayments', multi='dp'),
                'total_supplier_dp': fields.function(_get_downpayments, method=True, string='Supplier downpayments', multi='dp'),

                'payments_this_month': fields.function(_get_payments_this_month, method=True, string="Payments this month"),
                # 'rg_gan_retentions_this_month': fields.function(_get_rg_gan_retentions_this_month, method=True, string="AFIP RG GAN retentions this month"),
                'payments_last_year': fields.function(_get_payments_last_year, method=True, string="Payments last year"),

                'parent_id': fields.many2one ('res.partner', 'Parent'),
                'salesmen_ids': fields.one2many ('res.partner', 'parent_id', 'Salesmen'),
    }

    _defaults = {
        'vat_condition': '05',
        'cuit_dni': '**************',
        'rs_type': '00',
        'default_rg830_code': _get_default_rg830_code,
        'legal_country_id': _get_default_legal_country_id,
        'legal_state_id': _get_default_legal_country_id,
    }

    def onchange_vat_condition (self, cr, uid, ids, vat_condition, context=None):
        context = context or {}
        dt_obj = self.pool.get('afip.document_type')
        if vat_condition in ['06','12','13','14']:
            res = {'rs_type': '01'}
            d_ids = dt_obj.search(cr, uid, [('code','=','DNI')], context=context)
            if d_ids:
                res['document_type_id'] = d_ids[0]
        else:
            res = {'cuit_dni': '**************', 'rs_type': '00'}
            d_ids = dt_obj.search(cr, uid, [('code','=','CUIT')], context=context)
            if d_ids:
                res['document_type_id'] = d_ids[0]

        return {'value': res}

    def onchange_document_type_id (self, cr, uid, ids, document_type_id, vat_condition, context=None):
        context = context or {}
        dt_obj = self.pool.get('afip.document_type')
        if not document_type_id:
            return False

        # dt = dt_obj.browse(cr, uid, document_type_id, context=context)
        # if vat_condition in ['06','12','13','14']:
        #     if dt.code not in ['DNI', 'PAS', 'LE', 'LC', 'CDI'] and \
        #        not dt.code.startswith('CI'):
        #         raise osv.except_osv(_('Error !'),
        #                              _('Only DNI, PAS, LC, LE, CI or CDI!'))
        # else:
        #     if dt.code not in ['CUIL', 'CUIT', 'Sigd']:
        #         raise osv.except_osv(_('Error !'),
        #                              _('Only CUIT or CUIL!'))
        return False

    def onchange_cuit_dni (self, cr, uid, ids, cuit_dni, vat_condition, context=None):
        context = context or {}

        if not (cuit_dni and vat_condition):
            return False

        if vat_condition not in ('01', '04', '06', '10', '11', '12', '13', '14', '35', '25'):
            if cuit_dni[:14] == '**************':
                # Default value
                return False

            if cuit_dni and len(cuit_dni)==8:
                # Es un DNI (longitud == 8) y solo dígitos?

                for posicion in range(len(cuit_dni)):
                    letter = cuit_dni[posicion]
                    if letter < '0' or letter > '9':
                        raise osv.except_osv(_('Error !'), _('Only numbers are allowed on DNI!'))

                return {'value': {'vat': cuit_dni}}
            elif cuit_dni:
                raise osv.except_osv(_('Error !'), _('Depending on VAT condition, you could enter a CUIT, CUIL or DNI. For non mandatory categories, just fill the field with "*"'))

        if (not cuit_dni) or len(cuit_dni) != 11:
            raise osv.except_osv(_('Error !'), _('CUIT/CUIL number should have 11 digits, without hypens!'))

        verificador = int(cuit_dni[10])
        posicion = 9
        multiplicador = 2
        acumulado = 0
        while posicion >= 0:
            letter = cuit_dni[posicion]
            if letter < '0' or letter > '9':
                raise osv.except_osv(_('Error !'), _('Only numbers are allowed on CUIT/CUIL!'))

            acumulado = acumulado + int(letter) * multiplicador
            multiplicador += 1
            if multiplicador > 7:
                multiplicador = 2
            posicion = posicion - 1
        oncemenos = 11 - (acumulado % 11)
        digito = oncemenos
        if digito == 11:
            digito = 0
        if digito == 10:
            digito = 9

        if verificador != digito:
            raise osv.except_osv(_('Error !'), _('Invalid CUIT/CUIL. Please check'))

        return {'value': {'vat': cuit_dni}}

    def get_pricelist (self, cr, uid, ids, context=None):
        assert ids and len(ids)==1

        partner = self.browse (cr, uid, ids[0], context=context)

        while partner:
            if partner.property_product_pricelist:
                return partner.property_product_pricelist
            if not partner.parent_id:
                return None
            partner = partner.parent_id

        return None

    def get_partner_domain (self, cr, uid, id, context=None):
        # Hook to implement partner hierarchies
        # It should return a list of partners to be considered in the aggregate functions

        ids = self.search (cr, uid, [('id','child_of', [id])])
        res = [id]
        return res + ids

res_partner()


SUPERUSER = 1

class magento_fix (osv.osv_memory):

    _name="wineem.magento_fix"

    def action_magento_fix (self, cr, uid, ids, context=None):

        logger.info("inicio %s" % datetime.now())
        # cr.execute("UPDATE stock_picking SET invoice_state='2binvoiced'")
        partner_obj = self.pool.get('res.partner')
        sale_commission_obj = self.pool.get('sale.commission')
        field_obj = self.pool.get('ir.model.fields')
        property_obj = self.pool.get('ir.property')
        company_obj = self.pool.get('res.company')
        account_obj = self.pool.get('account.account')
        account_type_obj = self.pool.get('account.account.type')
        cat_obj = self.pool.get('res.partner.category')
        sale_order_obj = self.pool.get('sale.order')
        stock_move_obj = self.pool.get('stock.move')

        #Esto lo hice para act. el client_partner_id de los mov. de stock que no tenian el dato.
        #p_ids = stock_move_obj.search(cr, SUPERUSER, [('client_partner_id', '=', False)], context=context)
        #for move in stock_move_obj.browse(cr, SUPERUSER, p_ids, context=context):
        #    if move.picking_id and move.picking_id.partner_id:
        #        move.write({'client_partner_id': move.picking_id.partner_id.id}, context=context)


        root_company_ids = company_obj.search(cr, SUPERUSER, [('name', 'ilike', 'Lived')], context=context)
        root_company = root_company_ids and company_obj.browse(cr, SUPERUSER, root_company_ids[0], context=context) or None
        root_company_alfa_id = company_obj.search(cr, SUPERUSER, [('name', 'ilike', 'ALFA')], context=context)[0]
        root_company_alfa = company_obj.browse(cr, SUPERUSER, root_company_alfa_id,
                                                               context=context) or None

        receivable_ids = account_type_obj.search(cr, SUPERUSER, [('name', 'ilike','A cobrar')], context=context)
        if not receivable_ids:
            raise osv.except_osv(_('Error !'), _("No account user type 'Receivable' found! Please check it"))
        receivable_id = receivable_ids[0]

        parfield_ids = field_obj.search(cr, SUPERUSER, [('name','=','property_account_receivable'),('model','=','res.partner')])
        parfield = field_obj.browse(cr, SUPERUSER, parfield_ids[0], context=context)

        parfield_ids = field_obj.search(cr, SUPERUSER, [('name','=','property_product_pricelist'),('model','=','res.partner')])
        parfield_pricelist = field_obj.browse(cr, SUPERUSER, parfield_ids[0], context=context)

        ######################################################################
        inicio = datetime.now()
        logger.info(u"Les pongo consumidor final a todos lo que no tienen responsability_id %s" % datetime.now())
        p_ids = partner_obj.search(cr, SUPERUSER, [('responsability_id', '=', False), ('active','=',True)], context=context)
        for partner in partner_obj.browse(cr, SUPERUSER, p_ids, context=context):
            partner.write({'responsability_id': 6}, context=context)


        ######################################################################
        logger.info(u"Les pongo datos a los que les faltan dni %s" % datetime.now())
        p_ids = partner_obj.search(cr, SUPERUSER, [('document_type_id', '=', False), ('active','=',True)], context=context)
        for partner in partner_obj.browse(cr, SUPERUSER, p_ids, context=context):
            partner.write({'document_type_id': 111, 'document_number': partner.cuit_dni}, context=context)

        logger.info(u"pongo como active = False a los tipo contact porque a veces los trae mal magento %s" % datetime.now())
        p_ids = partner_obj.search(cr, SUPERUSER, [('type', '=', 'contact'), ('active','=',True)], context=context)
        for partner in partner_obj.browse(cr, SUPERUSER, p_ids, context=context):
            partner.write({'active': False}, context=context)

        ######################################################################
        ######################################################################
        logger.info(u"pongo como active = False a los tipo invoice que no tienen grupo porque a veces los tre mal magento %s" % datetime.now())
        p_ids = partner_obj.search(cr, SUPERUSER, [('type', '=', 'invoice'), ('active','=',True)], context=context)
        for partner in partner_obj.browse(cr, SUPERUSER, p_ids, context=context):
            category_id = partner.category_id
            if not category_id:
                partner.write({'active': False}, context=context)
            else:
                partner.write({'type': "default"}, context=context)

        ######################################################################

        ###################################################
        ##########Pongo todos los representantes con mayuscula y les pongo agente comercial###############
        #logger.info("Mayuscula inicio %s" % datetime.now())
        # p_ids = partner_obj.search(cr, SUPERUSER, [('group_id.name','=','RESPONSABLES'), ('active','=',True)], context=context)
        # for partner in partner_obj.browse(cr, SUPERUSER, p_ids, context=context):
        #     vals = {'name': partner.name.upper(), "agent": True}
        #     # Esto va en duro.. traigo la commision con id 1
        #     sale_com = sale_commission_obj.browse(cr, SUPERUSER, [1], context=context)
        #     if sale_com and not partner.commission:
        #         vals['commission'] = sale_com.id
        #     partner.write(vals, context=context)

        ##################################################

        #testtttt
        #########Ajustando group_id segun categoria_id del vendedor###############
        logger.info("Ajustando group_id segun categoria_id %s" % datetime.now())
        p_ids = partner_obj.search(cr, SUPERUSER, [('group_id','=',False), ('active','=',True)], context=context)

        for partner in partner_obj.browse(cr, SUPERUSER, p_ids, context=context):
            category_id = partner.category_id
            logger.info(u"Ajustando group_id segun categoria_id del vendedor [%s]" % partner.name)
            partner.write({'group_id': category_id.id}, context=context)
        ######################################################################


        ######################################################################
        logger.info("Ajustando responsables %s" % datetime.now())
        deudores_por_ventas = account_obj.search(cr, SUPERUSER,[('code', '=', '110201')], context=context)

        #10482 110201008 MATHIAS ISAYA  26664
        #deudores_por_ventas = account_obj.search(cr, SUPERUSER,[('code', '=', '110201008')], context=context)
        for root_account in account_obj.browse(cr, SUPERUSER, deudores_por_ventas, context=context):
            company = root_account.company_id

            # logger.info(u"Ajustando responsables para la compañía [%s]" % company.name)
            logger.info(u"cta [%s]" % root_account.name)

            p_ids = partner_obj.search(cr, SUPERUSER,
                                       [('parent_id', '=', False), ('group_id.name', '=', 'RESPONSABLES'), ('active','=',True)],
                                       context=context)

            for partner in partner_obj.browse(cr, SUPERUSER, p_ids, context=context):
                logger.info(u"Ajustando responsable [%s]" % partner.name)

                account_ids = account_obj.search(cr, SUPERUSER,
                                                 [('name', '=', partner.name), ('company_id', '=', company.id)],
                                                 context=context)
                if not account_ids:
                    children_ids = account_obj.search(cr, SUPERUSER, [('parent_id', '=', root_account.id)],
                                                      order="code desc", limit=1, context=context)
                    if children_ids:
                        last_child = account_obj.browse(cr, SUPERUSER, children_ids[0], context=context)
                        next_code = str(int(last_child.code) + 1)
                    else:
                        next_code = root_account.code[0:-1] + '00001'
                    account_id = account_obj.create(cr, SUPERUSER, {
                        'code': next_code,
                        'name': partner.name,
                        'type': 'receivable',
                        'user_type': receivable_id,
                        'parent_id': root_account.id,
                        'company_id': company.id,
                        'reconcile': True
                    }, context=context)
                    account_ids = [account_id]
                    logger.info(u"Creando cuenta para responsable [%s] en compañía [%s]" % (partner.name, company.name))

                if account_ids:
                    account = account_obj.browse(cr, SUPERUSER, account_ids[0], context=context)
                    current_ids = property_obj.search(cr, SUPERUSER, [('name', '=', 'property_account_receivable'),
                                                                      ('company_id', '=', company.id),
                                                                      ('res_id', '=', 'res.partner,%d' % partner.id)])
                    if current_ids:
                        property_obj.unlink(cr, SUPERUSER, current_ids)

                    # esto es para que se asigne todo sobre las cuentas root_company.id tambien sobre DEMO
                    # if company.id == root_company.id:
                    property_obj.create(cr, SUPERUSER, {
                        'name': 'property_account_receivable',
                        'company_id': company.id,
                        'fields_id': parfield.id,
                        'res_id': 'res.partner,%d' % partner.id,
                        'type': 'many2one',
                        'value': account.id
                    })

        ##########Ajustando parent_id de vendedor###############
        logger.info("Ajustando parent_id %s" % datetime.now())
        p_ids = partner_obj.search(cr, SUPERUSER, [('parent_id','=',False),('group_id.name','!=','RESPONSABLES'),('group_id','!=',False), ('active','=',True)], context=context)
        for partner in partner_obj.browse(cr, SUPERUSER, p_ids, context=context):
            rep_ids = partner_obj.search(cr, SUPERUSER, [('name','=',partner.group_id.name.replace('_',' ')),('group_id.name','=','RESPONSABLES')], context=context)
            logger.info(u"Ajustando parent_id de vendedor [%s %s]" % (partner.name, partner.id))
            if rep_ids:
                parent = partner_obj.browse(cr, SUPERUSER, rep_ids[0], context=context)
                partner.write({'parent_id': parent.id}, context=context)
                current_ids = property_obj.search(cr, SUPERUSER, [('name','=','property_product_pricelist'),('res_id','=','res.partner,%d'%partner.id)])
                if current_ids:
                    property_obj.unlink(cr, SUPERUSER, current_ids)

                for prop_id in property_obj.search(cr, SUPERUSER, [('name','=','property_product_pricelist'),('res_id','=','res.partner,%d'%parent.id)]):
                    partner_prop = property_obj.browse(cr, SUPERUSER, prop_id, context=context)
                    property_obj.create(cr, SUPERUSER, {
                            'name': 'property_product_pricelist',
                            'company_id': partner_prop.company_id.id,
                            'fields_id': parfield_pricelist.id,
                            'res_id': 'res.partner,%d'%partner.id,
                            'type': 'many2one',
                            'value': parent.property_product_pricelist and parent.property_product_pricelist.id or False,
                    })

        ######################################################################
        logger.info(u"Ajustando property_account_receivable de vendedores %s" % datetime.now())

        p_ids = partner_obj.search(cr, SUPERUSER, [('parent_id', '!=', False), ('group_id.name', '!=', 'RESPONSABLES'),
                                                   ('active', '=', True)], context=context)

        for partner in partner_obj.browse(cr, SUPERUSER, p_ids, context=context):
            logger.info(u"Ajustando vendedor [%s]" % partner.name)
            account_ids = account_obj.search(cr, SUPERUSER, [('name','=', partner.parent_id.name)], context=context)
            for account in account_obj.browse(cr, SUPERUSER, account_ids, context=context):
                current_ids = property_obj.search(cr, SUPERUSER, [('name', '=', 'property_account_receivable'),
                                                                  ('company_id', '=', account.company_id.id),
                                                                  ('res_id', '=', 'res.partner,%d' % partner.id)])
                # borra y crea los links nuevamente por si aguien toco algo
                property_obj.unlink(cr, SUPERUSER, current_ids)
                # if not current_ids:
                property_obj.create(cr, SUPERUSER, {
                        'name': 'property_account_receivable',
                        'company_id': account.company_id.id,
                        'fields_id': parfield.id,
                        'res_id': 'res.partner,%d'%partner.id,
                        'type': 'many2one',
                        'value': account.id,
                })

                #Aca para alfa
                # current_ids = property_obj.search(cr, SUPERUSER, [('name', '=', 'property_account_receivable'),
                #                                                   ('company_id', '=', root_company_alfa.id),
                #                                                   ('res_id', '=', 'res.partner,%d' % partner.id)])
                # if not current_ids:
                #     property_obj.create(cr, SUPERUSER, {
                #         'name': 'property_account_receivable',
                #         'company_id': root_company_alfa.id,
                #         'fields_id': parfield.id,
                #         'res_id': 'res.partner,%d' % partner.id,
                #         'type': 'many2one',
                #         'value': account.id,
                #     })

        ######################################################################
        logger.info(u"linkear todas las cuentas sin  A Pagar con 210101001 %s" % datetime.now())
        #linkear todas las cuentas sin  A Pagar con 210101001 Proveedores Varios
        account_obj = self.pool.get('account.account')

        parfield_ids = field_obj.search(cr, SUPERUSER, [('name','=','property_account_payable'),('model','=','res.partner')])
        parfield_payable = field_obj.browse(cr, SUPERUSER, parfield_ids[0], context=context)

        p_ids = partner_obj.search(cr, SUPERUSER, [('type', '=', 'default'), ('active','=',True)], context=context)
        #p_ids = partner_obj.search(cr, SUPERUSER, [], context=context)


        ######################################################################
        for partner in partner_obj.browse(cr, SUPERUSER, p_ids, context=context):
            logger.info(u"Ajustando cuenta de [%s]" % partner.name)

            account_ids = account_obj.search(cr, SUPERUSER,
                                             [('code', '=', '210101001')],
                                             context=context)
            for account in account_obj.browse(cr, SUPERUSER, account_ids, context=context):
                current_ids = property_obj.search(cr, SUPERUSER, [('name', '=', 'property_account_payable'),
                                                                  ('company_id', '=', account.company_id.id),
                                                                  ('res_id', '=', 'res.partner,%d' % partner.id)])
                # borra y crea los links nuevamente por si aguien toco algo
                property_obj.unlink(cr, SUPERUSER, current_ids)
                # if not current_ids:
                property_obj.create(cr, SUPERUSER, {
                        'name': 'property_account_payable',
                        'company_id': account.company_id.id,
                        'fields_id': parfield_payable.id,
                        'res_id': 'res.partner,%d'%partner.id,
                        'type': 'many2one',
                        'value': account.id,
                })

                # # Aca para alfa
                # current_ids = property_obj.search(cr, SUPERUSER, [('name', '=', 'property_account_payable'),
                #                                                   ('company_id', '=', root_company_alfa.id),
                #                                                   ('res_id', '=', 'res.partner,%d' % partner.id)])
                # if not current_ids:
                #     property_obj.create(cr, SUPERUSER, {
                #         'name': 'property_account_payable',
                #         'company_id': root_company_alfa.id,
                #         'fields_id': parfield_payable.id,
                #         'res_id': 'res.partner,%d' % partner.id,
                #         'type': 'many2one',
                #         'value': account.id,
                #     })

        ######################################################################
        logger.info(u"linkear todas las cuentas sin  A Pagar con 210101001 para los tipo contact  %s" % datetime.now())
        p_ids = partner_obj.search(cr, SUPERUSER, [('type', '=', 'contact'), ('active','=',True)], context=context)

        accounts_id = account_obj.search(cr, SUPERUSER, [('code', '=', '210101001')], context=context)
        # account = account_obj.browse(cr, SUPERUSER, accounts_id, context=context)

        for partner in partner_obj.browse(cr, SUPERUSER, p_ids, context=context):
            if partner.parent_id:
                parent = partner_obj.browse(cr, SUPERUSER, [partner.parent_id.id], context=context)
                logger.info(u"Ajustando cuenta de [%s]" % partner.name)

                for account in account_obj.browse(cr, SUPERUSER, account_ids, context=context):

                    current_ids = property_obj.search(cr, SUPERUSER, [('name', '=', 'property_account_payable'),
                                                                      ('company_id', '=', account.company_id.id),
                                                                      ('res_id', '=', 'res.partner,%d' % partner.id)])

                    # borra y crea los links nuevamente por si aguien toco algo
                    property_obj.unlink(cr, SUPERUSER, current_ids)
                    try:
                        property_obj.create(cr, SUPERUSER, {
                            'name': 'property_account_payable',
                            'company_id': account.company_id.id,
                            'fields_id': parent.property_account_payable.id,
                            'res_id': 'res.partner,%d' % partner.id,
                            'type': 'many2one',
                            'value': account.id,
                        })
                    except:
                        # todo no se porque pasa esto
                        pass

                    current_ids = property_obj.search(cr, SUPERUSER, [('name', '=', 'property_account_receivable'),
                                                                      ('company_id', '=', account.company_id.id),
                                                                      ('res_id', '=', 'res.partner,%d' % partner.id)])
                    # borra y crea los links nuevamente por si aguien toco algo
                    property_obj.unlink(cr, SUPERUSER, current_ids)
                    # if not current_ids:
                    property_obj.create(cr, SUPERUSER, {
                        'name': 'property_account_receivable',
                        'company_id': account.company_id.id,
                        'fields_id': parfield.id,
                        'res_id': 'res.partner,%d' % partner.id,
                        'type': 'many2one',
                        'value': parent.property_account_receivable.id,
                    })

                    # #Aca para alfa
                    # current_ids = property_obj.search(cr, SUPERUSER, [('name', '=', 'property_account_payable'),
                    #                                                   ('company_id', '=', root_company_alfa.id),
                    #                                                   ('res_id', '=', 'res.partner,%d' % partner.id)])
                    # if not current_ids:
                    #     try:
                    #         property_obj.create(cr, SUPERUSER, {
                    #             'name': 'property_account_payable',
                    #             'company_id': root_company_alfa.id,
                    #             'fields_id': parent.property_account_payable.id,
                    #             'res_id': 'res.partner,%d' % partner.id,
                    #             'type': 'many2one',
                    #             'value': account.id,
                    #         })
                    #     except:
                    #         # todo no se porque pasa esto
                    #         pass
                    #
                    # current_ids = property_obj.search(cr, SUPERUSER, [('name', '=', 'property_account_receivable'),
                    #                                                   ('company_id', '=', root_company_alfa.id),
                    #                                                   ('res_id', '=', 'res.partner,%d' % partner.id)])
                    # if not current_ids:
                    #     property_obj.create(cr, SUPERUSER, {
                    #         'name': 'property_account_receivable',
                    #         'company_id': root_company_alfa.id,
                    #         'fields_id': parfield.id,
                    #         'res_id': 'res.partner,%d' % partner.id,
                    #         'type': 'many2one',
                    #         'value': parent.property_account_receivable.id,
                    #     })

        ######################################################################
        logger.info(u"agregar cuentas a los productos que no los tengan %s" % datetime.now())
        product_obj = self.pool.get('product.product')
        product_ids = product_obj.search(cr, uid, [('property_account_income', '=', False),('active','=',True)])

        for prod in product_obj.browse(cr, SUPERUSER, product_ids, context=context):
            logger.info(u"Ajustando cuenta de [%s]" % prod.name)
            accounts_id = account_obj.search(cr, SUPERUSER, [('code', '=', '410101000'),
                                                             ('company_id', '=', prod.company_id.id)],
                                             context=context)
            account = account_obj.browse(cr, SUPERUSER, accounts_id, context=context)
            vals = {'property_account_income': account.id}
            prod.write(vals)

            accounts_id = account_obj.search(cr, SUPERUSER, [('code', '=', '110401000'),
                                                             ('company_id', '=', prod.company_id.id)],
                                             context=context)
            account = account_obj.browse(cr, SUPERUSER, accounts_id, context=context)
            vals = {'property_account_expense': account.id}
            prod.write(vals)

        product_ids = product_obj.search(cr, uid, [('property_account_income', '=', False), ('active', '=', False)])

        for prod in product_obj.browse(cr, SUPERUSER, product_ids, context=context):
            logger.info(u"Ajustando cuenta de [%s]" % prod.name)
            accounts_id = account_obj.search(cr, SUPERUSER, [('code', '=', '410101000'),
                                                             ('company_id', '=', prod.company_id.id)],
                                             context=context)
            account = account_obj.browse(cr, SUPERUSER, accounts_id, context=context)
            vals = {'property_account_income': account.id}
            prod.write(vals)

            accounts_id = account_obj.search(cr, SUPERUSER, [('code', '=', '110401000'),
                                                             ('company_id', '=', prod.company_id.id)],
                                             context=context)
            account = account_obj.browse(cr, SUPERUSER, accounts_id, context=context)
            vals = {'property_account_expense': account.id}
            prod.write(vals)


        ##########Pongo todas las ctas de los representantes reconcile': True###############
        # logger.info(u"Pongo todas las ctas de los representantes reconcile %s" % datetime.now())
        # p_ids = partner_obj.search(cr, SUPERUSER, [('group_id.name','=','RESPONSABLES'), ('active','=',True)], context=context)
        # for partner in partner_obj.browse(cr, SUPERUSER, p_ids, context=context):
        #     if partner.property_account_receivable:
        #         logger.info(u"reconcile de [%s]" % partner.name)
        #         account = account_obj.browse(cr, SUPERUSER, [partner.property_account_receivable.id], context=context)
        #         account.write({'reconcile': True}, context=context)

        logger.info(u"listas de precios todos %s" % datetime.now())
        p_ids = partner_obj.search(cr, SUPERUSER, [('active','=',True), ('group_id.name','=','RESPONSABLES'), ('property_product_pricelist.id', '=', 1 )], context=context)
        total = len(p_ids)
        i = 0
        for partner in partner_obj.browse(cr, SUPERUSER, p_ids, context=context):
            i += 1
            logger.info(u"registro %s de %s Nombre %s %s" % (i, total, partner.name, partner.id))
            partner.write({'property_product_pricelist': 10}, context=context)

        logger.info(u"listas de precios %s" % datetime.now())
        p_ids = partner_obj.search(cr, SUPERUSER, [('active','=',True), ('group_id.name','!=','RESPONSABLES'), ('property_product_pricelist.id', '=', 1)], context=context)
        total = len(p_ids)
        i = 0
        for partner in partner_obj.browse(cr, SUPERUSER, p_ids, context=context):
            i += 1
            logger.info(u"registro %s de %s Nombre %s %s" % (i, total, partner.name, partner.id))
            if partner.parent_id and partner.parent_id.property_product_pricelist:
                partner.write({'property_product_pricelist': partner.parent_id.property_product_pricelist.id}, context=context)
            else:
                partner.write({'property_product_pricelist': 10}, context=context)
        logger.info(u"Recomputo todas las ordenes de venta (solo act. lista de precios) %s" % datetime.now())

        sale_ids = sale_order_obj.search(cr, SUPERUSER, [('state','=','prepared'),('pricelist_id','=',1)], context=context)
        total = len(sale_ids)
        i = 0
        for sale in sale_order_obj.browse(cr, SUPERUSER, sale_ids, context=context):
            i += 1
            logger.info(u"registro %s de %s sale %s" % (i, total, sale))
            sale.write({'pricelist_id': sale.partner_id.property_product_pricelist.id})
            # if sale.pricelist_id.id != sale.partner_id.property_product_pricelist.id:
            #     logger.info(u"sale %s" % sale)
            #     sale.write({'pricelist_id': sale.partner_id.property_product_pricelist.id})
            #     # todo: demora mucho...#########Recomputo todas las ordenes de venta': True###############
            #     # sale.action_recompute_pricelist()

        ######################################################################
        logger.info(u"iva a los productos que no los tengan %s" % datetime.now())
        product_obj = self.pool.get('product.product')
        account_tax_obj = self.pool.get('account.tax')
        product_ids = product_obj.search(cr, uid, [('taxes_id', '=', False), ('active', '=', True)])
        account_tax_id = account_tax_obj.search(cr, uid, [('company_id', '=', root_company.id), ['amount', '=', 0.21]])
        account_tax = account_tax_obj.browse(cr, SUPERUSER, account_tax_id, context=context)
        for prod in product_obj.browse(cr, SUPERUSER, product_ids, context=context):
            logger.info(u"Ajustando producto de [%s]" % prod.name)
            prod.write({'taxes_id': [(6, 0, [account_tax.id])]})

        product_ids = product_obj.search(cr, uid, [('taxes_id', '=', False), ('active', '=', False)])
        account_tax_id = account_tax_obj.search(cr, uid, [('company_id', '=', root_company.id), ['amount', '=', 0.21]])
        account_tax = account_tax_obj.browse(cr, SUPERUSER, account_tax_id, context=context)
        for prod in product_obj.browse(cr, SUPERUSER, product_ids, context=context):
            logger.info(u"Ajustando producto de [%s]" % prod.name)
            prod.write({'taxes_id': [(6, 0, [account_tax.id])]})


        logger.info(u"Partner fix terminado inicio (%s) fin (%s)" % (inicio, datetime.now()))
        return {
            'type': 'ir.actions.act_window_close',
        }

magento_fix()


class res_company(osv.osv):
    _name = "res.company"
    _inherit = "res.company"


    _columns = {
        'sales_points_ids': fields.one2many('numa_ar_base.afip_sales_point', 'company_id', 'Sales points', help='Registered company sales points'),
        'store_points_ids': fields.one2many('numa_ar_base.afip_store_point', 'company_id', 'Store points', help='Registered company store points'),

        'vat': fields.related('partner_id', 'vat', string='VAT', readonly=True, type="char"),
        'vat_condition': fields.related('partner_id', 'vat_condition', string='VAT condition', readonly=True, type="char"),
        'rs_type': fields.related('partner_id', 'rs_type', string='RS type', readonly=True, type="char"),
        'iibb_number': fields.char('IIBB number', size=32),

        'taxes_on_invoice_additional': fields.many2many('account.tax', 'invoice_additional_taxes', 'company_id', 'tax_id', 'Additional taxes on invoicing and debit notes. It will be added to invoice total'),
        'taxes_on_invoice': fields.many2many('account.tax', 'invoice_taxes', 'company_id', 'tax_id', 'Taxes on invoicing and debit notes. Special processing, debit and credit account used to generate complementary move. Not added to invoice total'),
        'taxes_on_refund_additional': fields.many2many('account.tax', 'refund_additional_taxes', 'company_id', 'tax_id', 'Additional taxes on refund (credit notes). It will be added to refund total'),
        'taxes_on_refund': fields.many2many('account.tax', 'refund_taxes', 'company_id', 'tax_id', 'Taxes on credit notes. Special processing, debit and credit account used to generate complementary move. Not added to refund total'),

        'legal_country_id': fields.related('partner_id', 'legal_country_id',
                                     relation='res.country',
                                     type="many2one",
                                     string='Legal country'),
        'legal_state_id': fields.related ('partner_id', 'legal_state_id',
                                    relation='res.country.state',
                                    type="many2one",
                                    string='Legal state'),
        'start_date': fields.date('Company start date'),
    }

res_company()

# todo liricus ok: lo meti todo en sale.shop
# class sale_shop (osv.osv):
#     _inherit = "sale.shop"
#
#     _columns = {
#         'afip_sales_point_id': fields.many2one('numa_ar_base.afip_sales_point', 'AFIP sales point', help='AFIP sales point to be used on operations based on this shop'),
#     }
#
# sale_shop()

DT_FORMAT = "%Y-%m-%d"

class partner_ledger_wizard (osv.osv_memory):
    """
    """
    _name = 'numa_ar_base.partner_ledger_wizard'
    _description = 'Partner Ledger'

    def _get_default_fiscalyear_ids(self, cr, uid, context=None):
        now = time.strftime('%Y-%m-%d')
        fiscalyears = self.pool.get('account.fiscalyear').search(cr, uid, [('date_start', '<', now), ('date_stop', '>', now)])
        return fiscalyears

    def _get_default_start_date(self, cr, uid, context=None):
        today_dt = date.today()
        one_month_dt = today_dt + timedelta(days=-30)
        return one_month_dt.strftime(DT_FORMAT)

    _columns = {
        'fiscalyear_ids': fields.many2many('account.fiscalyear', 'ppl_fy', 'ppl_id', 'fy_id', 'Fiscal years', required=True),
        'start_date': fields.date('Start date', required=True),
        'reconcil': fields.boolean('Include Reconciled Entries', help='Consider reconciled entries'),
        'docs_on_maturity': fields.boolean('Compute documents on maturity', help='Consider documents on maturity date instead on received date'),
        'include_docs': fields.boolean('Include documents', help='Include documents, including cashing and reject moves, in ledger'),
        'include_children': fields.boolean('Include children', help='Include children partners movements'),
        'result_selection': fields.selection([
                                ('customer', 'Customer'),
                                ('supplier', 'Supplier'),
                                ('both', 'Customer and Supplier'),
                            ], 'Role', required=True),
    }
    _defaults = {
       'reconcil': True,
       'start_date': _get_default_start_date,
       'docs_on_maturity': False,
       'include_docs': False,
       'include_children': True,
       'result_selection': 'both',
       'fiscalyear_ids': _get_default_fiscalyear_ids,
    }

    def action_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        plw = self.browse(cr, uid, ids[0], context=context)

        partner_ids = context.get('active_ids',
                                  ('active_id' in context) and [context['active_id']] or [])

        data = {}
        data['ids'] = ids
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['form'] = {}
        data['form']['partner_ids'] = partner_ids
        data['form']['fiscalyear_ids'] = [f.id for f in plw.fiscalyear_ids]
        data['form']['start_date'] = plw.start_date
        data['form']['reconcil'] = plw.reconcil
        data['form']['docs_on_maturity'] = plw.docs_on_maturity
        data['form']['include_docs'] = plw.include_docs
        data['form']['include_children'] = plw.include_children
        data['form']['result_selection'] = plw.result_selection

        return {
                'type': 'ir.actions.report.xml',
                'report_name': 'partner_ledger_wizard',
                'datas': data,
        }

partner_ledger_wizard()

titles = [
    'Cliente',
    'Saldo'
]

class partner_initial_balance (osv.osv_memory):
    _name = "wineem.partner_initial_balance"

    def _get_default_fiscalyear(self, cr, uid, context=None):
        now = time.strftime('%Y-%m-%d')
        fiscalyears = self.pool.get('account.fiscalyear').search(cr, uid, [('date_start', '<', now), ('date_stop', '>', now)])
        return fiscalyears and fiscalyears[0] or False

    _columns = {
        'data': fields.binary('Data',filter="*.xls", required=True),
        'filename': fields.char('Filename', size=128),
        'company': fields.many2one('res.company', 'Company'),
        'fiscalyear': fields.many2one('account.fiscalyear', 'Fiscal year', required=True),
        'period': fields.many2one('account.period', 'Period', required=True, help="Period to set the initial movement"),
        'journal': fields.many2one('account.journal', 'Journal', required=True, help="Journal to assign the movement to"),
        'capital_account': fields.many2one('account.account', 'Capital account', required=True,
                                            help="Account to be used as Capital for closing the initial movement"),
    }

    _defaults = {
        'fiscalyear': _get_default_fiscalyear,
    }

    def onchange_fiscalyear(self, cr, uid, ids, fiscalyear_id, period_id, company_id, context=None):
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        period_obj = self.pool.get('account.period')

        res = {}

        if fiscalyear_id:
            fiscalyear = fiscalyear_obj.browse(cr, uid, fiscalyear_id, context=context)
            if fiscalyear.company_id != company_id:
                res['company'] = fiscalyear.company_id.id

            if period_id:
                period = period_obj.browse(cr, uid, period_id, context=context)
                if period.fiscalyear_id.id != fiscalyear.id:
                    res['period'] = fiscalyear.period_ids[0].id
            else:
                res['period'] = fiscalyear.period_ids[0].id

            if res:
                return {'value': res}

        return False

    def action_load_data(self, cr, uid, ids, context=None):
        assert ids and len(ids)==1
        partner_obj = self.pool.get('res.partner')
        aml_obj = self.pool.get('account.move.line')
        am_obj = self.pool.get('account.move')
        user_obj = self.pool.get('res.users')

	user = user_obj.browse(cr, 1, uid, context=context)

        pib = self.browse(cr, uid, ids[0], context=context)


        # Remove movements from user's company_id
        # ATENCION : CORRECCION TEMPORARIA PARA CARGAR NUEVOS SALDOS SIN BORRAR LOS VIEJOS
        # Solo descomentar para volver a anterior
        #cr.execute('UPDATE account_invoice SET move_id = NULL WHERE company_id = %d' % user.company_id.id)
        #cr.execute('DELETE FROM account_move_line as aml USING account_account as aa WHERE aa.id = aml.account_id AND aa.company_id = %d' % user.company_id.id)
        #cr.execute('DELETE FROM account_move WHERE company_id = %d' % user.company_id.id)

        #cr.execute("UPDATE sale_order SET state='done' WHERE company_id= %d" % user.company_id.id)
        #cr.execute("UPDATE stock_picking SET invoice_state='invoice' WHERE state='done' AND invoice_state='2binvoiced' AND company_id = %d" % user.company_id.id)

        # Upload initial data
        if pib.data:
            sio = StringIO.StringIO(base64.b64decode(pib.data))
            wb = open_workbook(file_contents = sio.getvalue())

            for s in wb.sheets():
                if s.name == 'Saldos iniciales':
                    if s.nrows < 1 and s.ncols < len(titles):
                        raise osv.except_osv(_('Error !'), _('Invalid file format. At least it should have one row! Please check it'))

                for col in xrange(len(titles)):
                    if s.cell(0, col).value != titles[col]:
                        raise osv.except_osv(_('Error !'), _('Invalid file format. In row one, column name is %(actual)s, when %(expected)s is expected! Please check it') % \
                                                            {'actual': unicode(s.cell(0, col).value), 'expected': titles[col]})

                am_id = am_obj.create(cr, uid, {
                            'name': '/',
                            'ref': 'Saldos iniciales',
                            'period_id': pib.period.id,
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'journal_id': pib.journal.id,
                        }, context=context)

                acum_amount = 0.0
                for row in range(1, s.nrows):
                    partner_name = s.cell(row, 0).value
                    partner_balance = s.cell(row, 1).value or 0.0

                    p_ids = partner_obj.search(cr, uid, [('name','=', partner_name),('group_id.name','=','RESPONSABLES')])
                    if p_ids and len(p_ids) != 1:
                        raise osv.except_osv(_('Error !'), _('Partners multiple match. Customer reference %s! Please check it') % \
                                                            partner_name)
                    elif not p_ids:
                        raise osv.except_osv(_('Error !'), _('Partner not found(Customer reference %s, MAGENTO Group RESPONSABLES)! Please check it') % \
                                                            partner_name)

                    partner = partner_obj.browse(cr, uid, p_ids[0], context=context)
                    if not partner.property_account_receivable:
                        raise osv.except_osv(_('Error !'), _('Partner has no related sales account(Customer reference %s)! Please check it') % \
                                                            partner_name)
                    if partner_balance:
                        vals = {
                            'journal_id': pib.journal.id,
                            'period_id': pib.period.id,
                            'name': "/",
                            'move_id': am_id,
                            'partner_id': partner.id,
                            'account_id': partner.property_account_receivable.id,
                            'debit': partner_balance > 0 and partner_balance or 0.0,
                            'credit': partner_balance < 0 and -partner_balance or 0.0,
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'ref': 'Saldo inicial',
                        }
                        aml_obj.create(cr, uid, vals, context=context)
                        acum_amount += partner_balance


                vals = {
                    'journal_id': pib.journal.id,
                    'period_id': pib.period.id,
                    'name': "/",
                    'partner_id': False,
                    'account_id': pib.capital_account.id,
                    'debit': 0.0,
                    'credit': acum_amount,
                    'ref': 'Saldo inicial',
                    'move_id': am_id,
                }
                aml_obj.create(cr, uid, vals, context=context)

                return {
                    'name':_("Initial movement"),
                    'view_mode': 'form',
                    'view_id': False,
                    'view_type': 'form',
                    'res_model': 'account.move',
                    'res_id': am_id,
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'domain': '[]',
                    'context': dict(context)
                }

        return {'type': 'ir.actions.act_window_close'}

partner_initial_balance()





