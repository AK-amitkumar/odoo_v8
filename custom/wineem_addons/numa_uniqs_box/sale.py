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
from openerp.tools.translate import _
import time

import pdb

class sale_order (osv.osv):

    _inherit = "sale.order"
    
    ##### En comentario codigo traido de modulo "attractor_uniqs_group_representante"########
    
    def _get_ids_so_para_partner_modificados(self, cr, uid, ids, context=None):
        partner_ids = self.pool.get("sale.order").search(cr, uid, [('partner_id', 'in', ids)], context=context)
        return partner_ids
        
    _columns = {
        #'rep_mg_group': fields.related ('partner_id', 'group_id', string="Magento Group", type='many2one', relation="res.partner.category", readonly=True),
        'rep_mg_group': fields.related('partner_id', 'group_id', string="Representante", type='many2one', relation="res.partner.category",  readonly=True,
                         store={'res.partner' : ( _get_ids_so_para_partner_modificados, ['group_id'], 10 ),
                                'sale.order': ( lambda self, cr, uid, ids, c={}: ids, ['partner_id'], 10 ), }, ),
        'wclosing': fields.related('partner_id', 'effective_closing', string="Cierre", type="many2one",
                                   obj="res.partner.closing", readonly=True, store=True),

    }

sale_order()
