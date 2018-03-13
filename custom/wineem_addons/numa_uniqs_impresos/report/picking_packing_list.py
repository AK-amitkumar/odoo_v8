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

import time
from openerp.report import report_sxw
from openerp.tools import amount_to_text
from openerp.tools.translate import _
import pdb

class report_picking_packing_list(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_picking_packing_list, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_qtytotal':self._get_qtytotal,
            'get_unittotal':self._get_unittotal,
            'lineInfo':self._lineInfo,
        })

    def _get_qtytotal(self,move_lines):
        total = 0.0
        uom = move_lines[0].product_uom.name
        for move in move_lines:
            total+=move.product_qty
        return {'quantity':total,'uom':uom}

    def _get_unittotal(self,move_lines):
        total = 0.0
        discount = 0.0
        for move in move_lines:
            data = self._lineInfo(move)
            total += data['price_subtotal']
            discount += data['price_unit'] * data['discount'] / 100.0 * move.product_qty
        return {'price_subtotal': total, 'discount': discount}
        
    def _lineInfo(self, move):
        if move:
            sale_obj = self.pool.get('sale.order')
            sale_id = sale_obj.search(self.cr, self.uid, [('name', '=', move.picking_id.origin)], None)
            sale = sale_obj.browse(self.cr, self.uid, sale_id, None)
            product_id = move.product_id.id
            order_line = sale.order_line.filtered(lambda r: r.product_id.id == product_id)
            # sol = move.sale_line_id
            sol = order_line
            if sol:
                pricelist = sol.order_id.pricelist_id
                base_pricelist = pricelist
                for pv in pricelist.version_id:
                    for pvi in pv.items_id:
                        if pvi.base == -1:
                            base_pricelist = pvi.base_pricelist_id

                list_price = pricelist.price_get(
                                sol.product_id.id, move.product_qty, {
                                    'uom': sol.product_uom.id,
                                    'date': sol.order_id.date_order,
                                })[pricelist.id]

                base_price = base_pricelist.price_get(
                                sol.product_id.id, move.product_qty, {
                                    'uom': sol.product_uom.id,
                                    'date': sol.order_id.date_order,
                                })[base_pricelist.id]

                price_unit = sol.product_id.list_price and sol.product_id.list_price * sol.price_unit / sol.product_id.list_price or sol.price_unit

                return {
                    'price_unit': price_unit,
                    'discount': sol.product_id.list_price and (sol.product_id.list_price - base_price) / sol.product_id.list_price * 100.0 or 0.0,
                    'price_subtotal': base_price * sol.price_unit / sol.product_id.list_price * move.product_qty,
                }

                # return {
                #     'price_unit': sol.price_unit,
                #     'discount': sol.discount,
                #     'price_subtotal': sol.price_subtotal
                # }

        return {
            'price_unit': 0.0, 
            'discount': 0.0,
            'price_subtotal': 0.0,                                    
        }

report_sxw.report_sxw(
    'report.picking_packing_list_print',
    'stock.picking',
    'addons/numa_uniqs_impresos/report/picking_packing_list.rml',
    parser=report_picking_packing_list,header="external"
)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
