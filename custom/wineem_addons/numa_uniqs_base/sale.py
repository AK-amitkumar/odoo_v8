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

from openerp.osv import osv
from openerp import netsvc


class sale_order(osv.osv):
    _inherit = "sale.order"

    #~ def _make_invoice(self, cr, uid, order, lines, context=None):
        #~ inv_id = super(sale_order, self)._make_invoice(cr, uid, order, lines, context=context)
        #~ self.pool.get('account.invoice').write (cr, uid, [inv_id], {'shop_id': order.shop_id.id})
        #~ return inv_id

    #~ def action_ship_create(self, cr, uid, ids, context=None):
        #~ result = super(sale_order, self).action_ship_create (cr, uid, ids)

        #~ for so in self.browse(cr, uid, ids):
            #~ for picking in so.picking_ids:
                #~ self.pool.get('stock.picking').write(cr, uid, [picking.id], {'shop_id': so.shop_id.id})

        #~ return result

    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        res = super(sale_order, self).onchange_partner_id(cr, uid, ids, part)

        if part and res.get('value', None) and not res['value'].get('pricelist_id',None):
            partner = self.pool.get('res.partner').browse (cr, uid, part)
            pricelist = partner.get_pricelist()
            res['value'].update(pricelist_id=pricelist and pricelist.id)

        return res

    def action_confirm(self, cr, uid, ids, context=None):
        assert ids and len(ids)==1, 'One at the time'
        
        so = self.browse(cr, uid, ids[0], context=context)
        for sol in so.order_line:
           # price = so.pricelist_id.price_get(
           #         sol.product_id.id, sol.product_uom_qty or 1.0, so.partner_id.id, {
           #             'uom': sol.product_uom.id,
           #             'date': so.date_order,
           #             })[so.pricelist_id.id]
           # todo Liricus: cambie la funcion porque no andaba
           price = self.pool.get('product.pricelist').price_get(cr, uid, [so.pricelist_id.id], sol.product_id.id,sol.product_uom_qty or 1.0, so.partner_id.id, context)[so.pricelist_id.id]
           sol.write({'price_unit': sol.product_id.list_price,
                      'discount': sol.product_id.list_price and (sol.product_id.list_price - price) / sol.product_id.list_price * 100.0 or 0.0})
            
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'sale.order', so.id, 'order_confirm', cr)
        val = {'state': 'progress'}
        so.write(val)
        return True


sale_order()
