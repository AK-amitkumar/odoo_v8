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
import traceback

import pdb

class product_template(osv.osv):
    _inherit = "product.template"

    def _default_sale_taxes (self, cr, uid, ids, context = None):
        context = context or {}

        tax_obj = self.pool.get('account.tax')

        tax_ids = tax_obj.search (cr, uid, [('name','=','IVAV21'), ('parent_id', '=', False),('type_tax_use','in',['sale','all'])])
        return tax_ids and [tax_ids[0]]
 
    def _default_supplier_taxes (self, cr, uid, ids, context = None):
        context = context or {}

        tax_obj = self.pool.get('account.tax')

        tax_ids = tax_obj.search (cr, uid, [('name','=','IVAC21'), ('parent_id', '=', False),('type_tax_use','in',['purchase','all'])])
        return tax_ids and [tax_ids[0]]

    _defaults = {
        'type': 'product', 
        'taxes_id': _default_sale_taxes,
        'supplier_taxes_id': _default_supplier_taxes,
    }

product_template()



