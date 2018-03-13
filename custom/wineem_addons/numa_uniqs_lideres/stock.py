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

from openerp.osv import fields, osv

class stock_picking (osv.osv):
    _inherit = "stock.picking"
    
    _columns = {
        'campaign': fields.many2one('sale.campaign', 'Campaign'),
        'leader_id': fields.related('partner_id', 'leader_id', string="Leader", type="many2one", relation="res.partner", readonly=True),
    }

stock_picking()

class stock_move (osv.osv):
    _inherit = "stock.move"
    
    _columns = {
        'leader_id': fields.related('partner_id', 'leader_id', string="Leader", type="many2one", relation="res.partner", readonly=True),
        'campaign': fields.related('picking_id','campaign', string='Campaign', type='many2one', relation='sale.campaign', readonly=True),
        'client_partner_id': fields.related('partner_id', string="Partner", type="many2one", relation="res.partner",
                                    readonly=True),
    }

stock_move()

#~ class stock_partial_picking_box_create (osv.osv_memory):
    #~ _inherit = "stock.partial.picking.box.create"
    
    #~ _columns = {
        #~ 'rep_id': fields.many2one('res.partner', 'Representant', help="Representant to send the box to", required=True, domain="['|',('group_id.name','=','RESPONSABLES'),('is_leader','=',True)]"), 
    #~ }
    
#~ stock_partial_picking_box_create()

#~ class stock_partial_picking (osv.osv_memory):
    #~ _inherit = "stock.partial.picking"
    
    #~ _columns = {
        #~ 'rep_id': fields.many2one('res.partner', 'Representant', help="Representant to send the box to", domain="['|',('group_id.name','=','RESPONSABLES'),('is_leader','=',True)]"), 
    #~ }
    
    #~ def create (self, cr, uid, vals, context=None):
        #~ context = context or {}
        #~ vals = vals or {}
        
        #~ if 'active_ids' in context:        
            #~ picking_obj = self.pool.get("stock.picking")
            #~ picking = picking_obj.browse(cr, uid, context['active_ids'][0], context=context)
            #~ if picking.partner_id:
                #~ if picking.partner_id.is_leader:
                    #~ vals['rep_id'] = picking.partner_id.id
                #~ elif picking.partner_id.leader_id:
                    #~ vals['rep_id'] = picking.partner_id.leader_id.id
                #~ elif picking.partner_id.group_id.name == "RESPONSABLES":
                    #~ vals['rep_id'] = picking.partner_id.id
                #~ else:
                    #~ vals['rep_id'] = picking.partner_id.parent_id and picking.partner_id.parent_id.id or vals.get('rep_id', False)

        #~ return super(stock_partial_picking, self).create (cr, uid, vals, context=context)

                    
#~ stock_partial_picking()
