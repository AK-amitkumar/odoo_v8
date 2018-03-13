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

import pdb

class iva_report_old (osv.osv_memory):
    """
    Este wizard dispara el informe de IVA ventas.
    """
    _name = 'uniqs.iva_report_old'
    _description = 'IVA Ventas'
    
    def _get_initial_date (self, cr, uid, context=None):
        today = date.today()
        first_day_this_month = today.replace(day=1)
        first_day_previous_month = first_day_this_month.replace(year=first_day_this_month.month==1 and first_day_this_month.year-1 or first_day_this_month.year,
                                                                month=first_day_this_month.month==1 and 12 or first_day_this_month.month-1)
        return first_day_previous_month.strftime("%Y-%m-%d")
    
    def _get_final_date (self, cr, uid, context=None):
        today = date.today()
        first_day_this_month = today.replace(day=1)
        return date.fromordinal(first_day_this_month.toordinal()-1).strftime("%Y-%m-%d")

    _columns = {
        'initial_date': fields.date ('Fecha inicial', required=True),
        'final_date': fields.date ('Fecha final', required=True),
        'initial_page': fields.integer('Pag. inicial'),
    }
    _defaults = {
       'initial_date': _get_initial_date,
       'final_date': _get_final_date,
       'initial_page': 1,
    }

    def action_print_report(self, cr, uid, ids, data, context=None):
        context = context or {}
        data = {}
        data['ids'] = ids
        data['model'] = 'uniqs.iva_report_old'
        data['header'] = 'external'
        data['report_type'] = 'sxw'
        return {
                'type': 'ir.actions.report.xml',
                'report_name': 'vat_report_print',
                'datas': data,
        }

iva_report_old()


