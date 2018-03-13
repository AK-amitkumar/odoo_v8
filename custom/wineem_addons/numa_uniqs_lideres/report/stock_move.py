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
import logging

logger = logging.getLogger(__name__)

import pdb

class report_stock_move_form(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_stock_move_form, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_by_rep': self._get_by_rep,
        })

    def _get_by_rep(self, move_list):
        res = []
        current_leader = None
        current_moves = []
        current_total = 0
        for m in sorted(move_list, key=lambda x: ((((x.picking_id.partner_id.is_leader or not x.picking_id.partner_id.parent_id) and x.picking_id.partner_id or \
                                                   x.picking_id.partner_id.leader_id or \
                                                   x.picking_id.partner_id.parent_id) and ((x.picking_id.partner_id.is_leader or not x.picking_id.partner_id.parent_id) and x.picking_id.partner_id or \
                                                   x.picking_id.partner_id.leader_id or \
                                                   x.picking_id.partner_id.parent_id).name or ''), x.picking_id.partner_id.name, x.picking_id.origin, x.picking_id.product_id.code)):
            this_leader = (m.picking_id.partner_id.is_leader or not m.picking_id.partner_id.parent_id) and m.picking_id.partner_id or m.picking_id.partner_id.leader_id or m.picking_id.partner_id.parent_id
            if (not current_leader) or this_leader != current_leader:
                if current_leader:
                    res.append({
                        'leader': current_leader,
                        'moves': current_moves,
                        'total': current_total,
                    })
                current_leader = this_leader
                current_moves = []
                current_total = 0
            current_moves.append(m)
            current_total += m.product_qty
            
        if current_leader:
            res.append({
                'leader': current_leader,
                'moves': current_moves,
                'total': current_total,
            })
            
        return res

report_sxw.report_sxw(
    'report.stock_move_print_2',
    'stock.move',
    'addons/numa_uniqs_lideres/report/stock_move_form.rml',
    parser=report_stock_move_form,header="external"
)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
