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

from openerp.osv import fields,osv


class picking (osv.osv):
    _inherit = "stock.picking"

    _columns = {
        'season': fields.many2one ('product.season', 'Season', select=1),
        'wclosing': fields.related ('partner_id', 'effective_closing', string="Closing", type="many2one",
                                    obj="res.partner.closing", readonly=True, store=True),
        'document_number': fields.related ('partner_id', 'document_number', string="DNI", type="char", readonly=True),
        # 'document_number': fields.char(related='partner_id.document_number', string="DNI"),
    }


picking()


class stock_move (osv.osv):
    _inherit = "stock.move"
    
    _columns = {
        'season': fields.related ('product_id', 'season', string="Season", type="many2one", obj="product.season", readonly=True),
    }
    
    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False,
                            loc_dest_id=False, address_id=False):
        res = super (stock_move, self).onchange_product_id (cr, uid, ids, prod_id, loc_id, loc_dest_id, address_id)
        if prod_id:
            product_obj = self.pool.get('product.product')
            product = product_obj.browse(cr, uid, prod_id)
            values = res.get('value', {})
            values.update({'season': product.season.id})
            if res.get('value', None):
                res['value'].update(values)
            else:
                res = res or {'value': values}
        return res
    
stock_move()