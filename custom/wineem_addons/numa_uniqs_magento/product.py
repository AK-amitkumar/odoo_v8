# -*- coding: utf-8 -*-
##############################################################################
#
#    NUMA
#    Copyright (C) 2013 NUMA Extreme Systems (<http:www.numaes.com>).
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

from openerp.osv import fields, osv
from openerp.tools.translate import _


class product_product (osv.osv):
    _inherit = "product.product"
    
    def create(self, cr, user, vals, context=None):
        uid = user.id

        account_obj = self.pool.get('account.account')
        product_obj = self.pool.get('product.product')
        company_obj = self.pool.get('res.company')

        demo_ids = company_obj.search(cr, uid, [('name', 'ilike', 'ALFA')], context=context)
        demo_company = demo_ids and company_obj.browse(cr, uid, demo_ids[0], context=context) or None

        product_ids = product_obj.search(cr, uid, [('property_account_income', '=', False)])

        for prod in product_obj.browse(cr, uid, product_ids, context=context):
            accounts_id = account_obj.search(cr, uid, [('code', '=', '410101000'),
                                                             ('company_id', '=', demo_company.id)],
                                             context=context)
            account = account_obj.browse(cr, uid, accounts_id, context=context)
            vals = {'property_account_income': account.id}
            # prod.write(vals)

            accounts_id = account_obj.search(cr, uid, [('code', '=', '110401000'),
                                                             ('company_id', '=', demo_company.id)],
                                             context=context)
            account = account_obj.browse(cr, uid, accounts_id, context=context)

            vals = {'property_account_expense': account.id}
            # vals['partner_id'] = sale.partner_id.id
            # prod.write(vals)

        return super(product_product, self).create(cr, user, vals, context)

product_product()
