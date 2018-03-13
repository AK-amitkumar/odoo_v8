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
from openerp.tools.translate import _
import time

import pdb
import re

class stock_picking (osv.osv):
    _inherit = "stock.picking"
    
    _columns = {
        'box_id': fields.many2one ('stock.box', 'Included in box', ondelete='set null', domain=[('state','=','opened')]),
        'box_state': fields.related('box_id', 'state', string="Box state", type="selection", selection=[
            ('opened', 'Opened'),
            ('closed', 'Closed, not delivered'),
            ('delivered', 'Already delivered'),
            ('canceled', 'Canceled'),
            ], readonly=True),
        'box_closed_date': fields.related('box_id', 'date_closed', string='Box closed on', type="date", readonly=True),
        'rep_mg_group': fields.related ('partner_id', 'group_id', string="Magento Group", type='many2one', relation="res.partner.category", readonly=True, store=True),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        context = context or {}
        
        new_vals = default.copy()
        new_vals['box_id'] = False
        
        return super(stock_picking, self).copy (cr, uid, id, new_vals, context=context)
        
    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        assert ids and len(ids)==1
        
        picking = self.browse (cr, uid, ids[0], context=context)
        box = picking.box_id
        if not box:
            raise osv.except_osv(_('Error !'),
                _('It is not posible to confirm a picking without a box!. Please check it'))

        res = super(stock_picking, self).do_partial(cr, uid, ids, partial_datas, context=context)
        if res:
            for pick_id in res.keys():
                delivered_pack = self.browse (cr, uid, res[pick_id]['delivered_picking'], context=context)
                if delivered_pack.id != picking.id:
                    self.write (cr, uid, [delivered_pack.id], {'box_id': picking.box_id.id}, context=context)
                    self.write (cr, uid, [picking.id], {'box_id': False}, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        for picking in self.browse(cr, uid, ids, context=context):
            if picking.box_id:
                raise osv.except_osv(_('Error !'),
                    _('NO picking could be deleted if it is assigned to a box (picking %s). Please check!') % picking.name)

        return super.unlink(cr, uid, ids, context=context)
    
stock_picking()

class stock_move (osv.osv):
    _inherit = "stock.move"

    _columns = {
        'rep_mg_group': fields.related ('picking_id', 'rep_mg_group', string="Magento Group", type='many2one', relation="res.partner.category", readonly=True, store=True),
    }

stock_move()

#~ class stock_partial_picking(osv.osv_memory):
    #~ _inherit = "stock.partial.picking"


    #~ def _get_rep_id (self, cr, uid, ids, fields, args, context=None):
        #~ partner_obj = self.pool.get('res.partner')

        #~ res = {}
        #~ for spp in self.browse (cr, uid, ids, context=context):
            #~ rep = False
            #~ if spp.picking_id and spp.picking_id.partner_id and spp.picking_id.partner_id.parent_id:
                #~ rep = spp.picking_id.partner_id.parent_id
            #~ elif spp.picking_id and spp.picking_id.partner_id and spp.picking_id.partner_id.group_id:
                #~ reps_ids = partner_obj.search (cr, uid, ['|', 
                                                         #~ '&',
                                                         #~ ('name','=',spp.picking_id.partner_id.group_id.name.replace('_',' ')),
                                                         #~ ('group_id.name','=',"RESPONSABLES"),
                                                         #~ ('group_id.nmae','=',"RESPONSABLES")], context=context)
                #~ if reps_ids:
                    #~ rep = partner_obj.browse (cr, uid, reps_ids[0], context=context)
            #~ res[spp.id] = rep and rep.id or False

        #~ return res
        
    #~ _columns = {
        #~ 'box_id': fields.many2one('stock.box', 'Included in box'),
        #~ 'rep_id': fields.function (_get_rep_id, method=True, type='many2one', relation="res.partner", string="Rep", readonly=True),
    #~ }
    
    #~ def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
    
        #~ r = super (stock_partial_picking, self).fields_view_get (cr, uid, view_id, view_type, context=context, toolbar=toolbar, submenu=submenu)
        
        #~ sv = re.split ('(<field name="picking_id" invisible="1"/>)', r['arch'])
        #~ assert len(sv)==3
        
        #~ picking_ids = context.get('active_ids')
        #~ assert picking_ids and len(picking_ids)==1
        #~ picking_obj = self.pool.get('stock.picking')
        #~ picking = picking_obj.browse(cr, uid, picking_ids[0], context=context)
        
        #~ r['arch'] = sv[0]+sv[1]+ \
                    #~ ("<field name=\"box_id\" domain=\"[('state','=','opened'),('rep_id','=',rep_id)]\" invisible=\"%(invisible)s\" />"+ \
                     #~ '<button name="action_create_box" string="' + _("_Create a new box") + '" type="object" invisible=\"%(invisible)s\"/>'+ \
                     #~ sv[2]) % {'invisible': picking.type=='out' and '0' or '1'}
        #~ return r

    #~ def action_create_box (self, cr, uid, ids, context=None):
        #~ if context is None: context = {}

        #~ picking_obj = self.pool.get('stock.picking')
        #~ partner_obj = self.pool.get('res.partner')
                
        #~ assert ids and len(ids)==1
        
        #~ spp = self.browse (cr, uid, ids[0], context=context)

        #~ if not spp.rep_id:
            #~ raise osv.except_osv(_('Error !'),
                #~ _('NO rep was found for this delivery order. Please check!'))

        #~ sppbc_id = self.pool.get("stock.partial.picking.box.create").create(
            #~ cr, uid, {'spp_id': ids[0], 
                      #~ 'rep_id': spp.rep_id.id}, context=dict(context, active_ids=ids))
            
        #~ return {
            #~ 'name':_("Create a new box"),
            #~ 'view_mode': 'form',
            #~ 'view_id': False,
            #~ 'view_type': 'form',
            #~ 'res_model': 'stock.partial.picking.box.create',
            #~ 'res_id': sppbc_id,
            #~ 'type': 'ir.actions.act_window',
            #~ 'nodestroy': True,
            #~ 'target': 'new',
            #~ 'domain': '[]',
            #~ 'context': dict(context, active_ids=ids)
        #~ }

    #~ def do_partial(self, cr, uid, ids, context=None):
        #~ assert ids and len(ids)==1, 'One at the time!'

        #~ if not context: context={}
        #~ picking_obj = self.pool.get ('stock.picking')

        #~ spp = self.browse (cr, uid, ids[0], context=context)
        
        #~ if spp.picking_id.type == 'out' and not spp.box_id:
            #~ raise osv.except_osv(_('Error !'),
                #~ _('No se puede procesar una orden de entrega sin caja!. Por favor revisar!'))

        #~ picking_obj.write (cr, uid, [spp.picking_id.id], {'box_id': spp.box_id.id}, context=context)
        
        #~ return super(stock_partial_picking, self).do_partial(cr, uid, ids, context=context)

#~ stock_partial_picking()

#~ class stock_partial_picking_box_create (osv.osv_memory):
    #~ _name = "stock.partial.picking.box.create"
    
    #~ _columns = {
        #~ 'spp_id': fields.many2one('stock.partial.picking', 'Partial picking wizard'), 
        #~ 'rep_id': fields.many2one('res.partner', 'Representant', help="Representant to send the box to", required=True, domain="[('group_id.name','=','RESPONSABLES')]"), 
    #~ }
    
    #~ def action_create_box (self, cr, uid, ids, context=None):
        #~ context = context or {}
        
        #~ assert ids and len(ids)==1
        
        #~ sppbc = self.browse (cr, uid, ids[0], context=context)
        
        #~ spp_obj = self.pool.get('stock.partial.picking')

        #~ sa_id = self.pool.get('res.partner').address_get(cr, uid, [sppbc.rep_id.id], ['delivery'])['delivery']

        #~ if not sa_id:
            #~ raise osv.except_osv(_('Error !'),
                #~ _('NO delivery address for the rep was found. Please check!'))

        #~ new_box_id = self.pool.get('stock.box').create (cr, uid, {
                            #~ 'rep_id': sppbc.rep_id.id,
                            #~ 'rep_shipping_id': sa_id,
                            #~ }, context=context)
        #~ spp_obj.write (cr, uid, [sppbc.spp_id.id], {'box_id': new_box_id}, context=context)

        #~ return {'type': 'ir.actions.act_window_close'}

#~ stock_partial_picking_box_create ()
