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

class box (osv.osv):

    _inherit = "stock.box"

    _columns = {
        'campaign': fields.many2one('sale.campaign', 'Campaign'),
    }
    
    def action_cancel (self, cr, uid, ids, context=None):
        picking_obj = self.pool.get('res.picking')
    
        assert ids and len(ids)==1
        
        box = self.browse (cr, uid, ids[0], context=context)
        if box.state not in ['opened', 'closed']:
            raise osv.except_osv(_('Error !'),
                _('Only opened and closed boxes could be cancelled!'))
                
        if box.delivered_pickings_ids:
            included_ids = [p.id for p in box.delivered_pickings_ids]
            picking_obj.write (cr, uid, included_ids, {'box_id': False}, context=context)
        
        self.write (cr, uid, ids, {'state': 'cancelled', 'date_cancelled': time.strftime('%Y-%m-%d')}, context=context)
        return True

box()

