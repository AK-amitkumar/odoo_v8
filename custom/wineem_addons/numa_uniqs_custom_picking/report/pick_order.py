# -*- coding: utf-8 -*-
##############################################################################
#
#    NUMA
#    Copyright (C) 2014 NUMA Extreme Systems (<http:www.numaes.com>).
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


class pick_order_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(pick_order_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'get_moves': self._get_moves,
            'get_address': self._get_address,
            'get_catalogo_oportunidades': self._get_catalogo_oportunidades,
            'get_wineem_express': self._get_wineem_express,
            'get_whatsapp': self._get_whatsapp,
            'get_normal': self._get_normal,
            'get_club_de_amigas': self._get_club_de_amigas,
            'get_oportunidades': self._get_oportunidades,
            'get_no_comisionables': self._get_no_comisionables,
        })

    def _get_moves(self, po):
        return sorted(po.moves, key=lambda x: x.product_id.code)

    def _get_catalogo_oportunidades(self, po):
        return sorted(filter(lambda m: m.product_id.categ_id.name in ['Catalogo de Oportunidades'], po.move_ids),
                      key=lambda x: x.product_id.code)

    def _get_wineem_express(self, po):
        return sorted(filter(lambda m: m.product_id.categ_id.name in ['Wineem Express'], po.move_ids),
                      key=lambda x: x.product_id.code)

    def _get_whatsapp(self, po):
        return sorted(filter(lambda m: m.product_id.categ_id.name in ['Whatsapp'], po.move_ids),
                      key=lambda x: x.product_id.code)

    def _get_normal(self, po):
        return sorted(filter(lambda m: m.product_id.categ_id.name not in ['Catalogo de Oportunidades', 'Wineem Express',
                                                                          'Whatsapp', 'Club de Amigas', 'Oportunidades',
                                                                          'NO COMISIONABLES'], po.move_ids),
                      key=lambda x: x.product_id.code)

    def _get_club_de_amigas(self, po):
        return sorted(filter(lambda m: m.product_id.categ_id.name in ['Club de Amigas'], po.move_ids),
                      key=lambda x: x.product_id.code)

    def _get_oportunidades(self, po):
        return sorted(filter(lambda m: m.product_id.categ_id.name in ['Oportunidades'], po.move_ids),
                      key=lambda x: x.product_id.code)

    def _get_no_comisionables(self, po):
        return sorted(filter(lambda m: m.product_id.categ_id.name in ['NO COMISIONABLES'], po.move_ids),
                      key=lambda x: x.product_id.code)

    def _get_address(self, partner, atype):
        atype = atype or 'default'

        r = partner  # .address_get(atype) [atype]
        a = "%s%s" % (r.street, r.street2)
        return a


report_sxw.report_sxw(
    'report.pick_order_report',
    'stock.picking.order',
    'addons/numa_uniqs_custom_picking/report/pick_order.rml',
    parser=pick_order_report,
    header="external"
)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: