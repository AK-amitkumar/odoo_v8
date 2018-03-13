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

from openerp.osv import fields, osv

class season(osv.osv):
    _name = "product.season"
    
    _columns = {
        'name': fields.char ('Name', size=32, required=True, select=1),
        'description': fields.text ('Description'),
        'valid_from': fields.date ('Valid from', help="Initial date for sales order acceptance", required=True),
        'valid_to': fields.date ('Valid up to', help="End date for sales order acceptance", required=True),
        'product_ids': fields.one2many('product.product', 'season', 'Products', required=True), #Campo agregado
    }
    
season()

class product_product(osv.osv):
    _inherit = "product.product"
    
    _columns = {
        'season': fields.many2one ('product.season', 'Season'),
    }

product_product()

#clase agregada
class product_template(osv.osv):
    _inherit = "product.template"
    
    _columns = {
        'season': fields.related('product_variant_ids', 'season', string="Season", type="many2one", relation="product.season"),

    }

product_template()
