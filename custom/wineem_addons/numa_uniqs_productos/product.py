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


class product_fabric(osv.osv):
    _name = 'product.fabric'
    
    _columns = {
        'code': fields.char('Code', size=32),
        'name': fields.char('Name', size=128),
        'manufacturers_code': fields.char("Manufacturer's code", size=32),
        'manufacturers_name': fields.char("Manufacturer's name", size=128),
        'notes': fields.text('Notes'),
    }

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The internal code of the fabric must be unique!')
    ]

product_fabric()

class product_color(osv.osv):
    _name = 'product.color'
    
    _columns = {
        'code': fields.char('Code', size=32),
        'name': fields.char('Name', size=128),
        'notes': fields.text('Notes'),
    }

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The internal code of the color must be unique!')
    ]

product_color()

class product_template(osv.osv):
    _inherit = "product.template"
    
    # def _get_default_account_products(self, cr, uid, val, context=None):
    #     print '=======',val
    #     print '=======',context
    #     account_obj = self.pool.get('account.account')
    #     account_id = account_obj.search(cr, uid, [('code','=','110600')])
    #     if not account_id:
    #         raise osv.except_osv(_('Error!'), _('Por favor defina una cuenta de ingresos'))
    #     return account_id
    #
    # def default_get(self, cr, uid, fields_list, context=None):
    #     print '====....===',fields_list
    #     print '====....===',context
    #     context = context and context or {}
    #     res = super(product_template, self).default_get(cr, uid, fields_list, context)
    #     account = self.pool.get('account.account').search(cr, uid, [('code', '=', '110600')])#410101000
    #     print '=====',account
    #     account_id = account and account[0] or ''
    #     res.update({'property_account_income': account_id,'property_account_expense': account_id })
    #     return res

    _columns = {
        'fabric_type': fields.many2one('product.fabric', 'Fabric type'),
        
        #~ 'property_account_income': fields.many2one('account.account',"Income Account",
            #~ help="This account will be used for invoices instead of the default one to value sales for the current product."),
        #~ 'property_account_expense': fields.many2one('account.account', "Expense Account",
            #~ help="This account will be used for invoices instead of the default one to value expenses for the current product."),
    }
    
    #~ _defaults = {
        #~ 'property_account_income': 1,
        #~ 'property_account_expense': _get_default_account_products
    #~ }

product_template()

class product_product (osv.osv):
    _inherit = "product.product"
    
    _columns = {
        'color': fields.many2one('product.color', 'Color'),
    }
    
    def _check_ean_key(self, cr, uid, ids, context=None):
        return True

    _constraints = [(_check_ean_key, 'You provided an invalid "EAN13 Barcode" reference. You may use the "Internal Reference" field instead.', ['ean13'])]

product_product()
