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

class report_stock_move_form(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_stock_move_form, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_total_qty': self._get_total_qty,
            'get_rep_list': self._get_rep_list,
            'get_ordered': self._get_ordered,
        })

    def _get_total_qty (self, move_list):
        total = 0.0
        for m in move_list:
            total += m.product_qty
        return total
    
    def _get_rep_list (self, move_list):
        return ', '.join(list(set([o.partner_id and o.partner_id.group_id and o.partner_id.group_id.name or '<sin grupo>' for o in move_list])))

    def _get_ordered (self, moves):
        return sorted(moves, key=lambda x: (x.origin or '', x.partner_id and x.partner_id.name or '', x.product_id and x.product_id.name or ''))

report_sxw.report_sxw(
    'report.stock_move_print',
    'stock.move',
    'addons/numa_uniqs_impresos/report/stock_move_form.rml',
    parser=report_stock_move_form,header="external"
)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
