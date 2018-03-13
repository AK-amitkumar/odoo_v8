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


class quick_move(osv.osv):
    '''
    An account quick move is way to assign fixed accounts to repetitive movements, like witholding taxes or retentions on payment
    In a receipt or payment, they could be used to avoid repetive input of account numbers, assigning an amount to be used for credit
    and debit on the credit account and the debit account.
    Use of this quick move implies no change on the balance of the move, since the same amount will be applied as a credit or debit
    '''
    _name = "numa_ar_base.quick_move"
    _columns = {
        'name':fields.char('Name', size=20, help="Operation code", required=True),
        'description':fields.char('Description', size=50, required=True),
        'type': fields.selection([
                        ('received_retention', 'Received retention'),
                        ('performed_retention', 'Performed retention'),
                ], 'Type', required=True),
        'credit_account_id':fields.many2one('account.account', 'Credit account', required=True, domain="[('type','!=','view')]"),
        'debit_account_id':fields.many2one('account.account', 'Debit account', required=True, domain="[('type','!=','view')]"),
        'analytic_account_id':fields.many2one('account.account', 'Analytic account', domain="[('type','!=','view')]"),
    }

    _defaults = {
        'type': 'received_retention',
    }

quick_move()
