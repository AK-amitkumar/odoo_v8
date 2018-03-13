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

import time
from openerp.osv import osv
from openerp.report import report_sxw

class picking_list_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(picking_list_report, self).__init__(cr, uid, name, context=context)
        # self.localcontext.update({
        #     'time': time,
        #     'get_moves': self._get_moves,
        #     'get_address': self._get_address,
        #     'get_saldos': self._get_saldos,
        #     'get_normal': self._get_normal,
        #     'get_oportunidades': self._get_oportunidades,
        # })
        self.localcontext.update({
            'time': time,
            'get_pickings': self._get_pickings,
            'get_total_discount': self._get_total_discount,
            'get_total': self._get_total,
            'get_total_qty': self._get_total_qty,
        })
        self.context = context

    def _get_pickings(self, obj):
        pickings = [x.picking_id for x in obj.move_ids]
        return [pickings[i] for i in range(len(pickings)) if i == pickings.index(pickings[i])]

    def _get_total(self, picking):
        return sum([x.procurement_id.sale_line_id.price_subtotal for x in picking.move_lines])

    def _get_total_qty(self, picking):
        return sum([x.product_uom_qty for x in picking.move_lines])

    def _get_total_discount(self, picking):
        return sum([(x.procurement_id.sale_line_id.price_subtotal*x.procurement_id.sale_line_id.discount/100)\
                        for x in picking.move_lines])


######################


    # def _get_moves(self, po):
    #     return sorted(po.moves, key=lambda x: x.product_id.code)
    #
    # def _get_saldos(self, po):
    #     return sorted(filter(lambda m: m.product_id.categ_id.name in ['Saldos'], po.moves),
    #                   key=lambda x: x.product_id.code)
    #
    # def _get_normal(self, po):
    #     return sorted(
    #         filter(lambda m: m.product_id.categ_id.name not in ['Oportunidades', 'Club de Amigas', 'Saldos'], po.moves),
    #         key=lambda x: x.product_id.code)
    #
    # def _get_oportunidades(self, po):
    #     return sorted(filter(lambda m: m.product_id.categ_id.name in ['Oportunidades', 'Club de Amigas'], po.moves),
    #                   key=lambda x: x.product_id.code)
    #
    # def _get_address(self, partner, atype):
    #     atype = atype or 'default'
    #
    #     r = partner.address_get(atype)[atype]
    #     a = "%s%s" % (r.street, r.street2)
    #     return a



# report_sxw.report_sxw(
#     'report.pick_order_report',
#     'stock.picking.order',
#     'addons/numa_uniqs_custom_picking/report/pick_order.rml',
#     parser=picking_list_report,
#     header="external"

class report_pickinglist(osv.AbstractModel):
    _name = 'report.numa_uniqs_custom_picking.report_picking_list'
    _inherit = 'report.abstract_report'
    _template = 'numa_uniqs_custom_picking.report_picking_list'
    _wrapped_report_class = picking_list_report
