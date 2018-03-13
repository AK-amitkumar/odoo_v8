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

class ref_delivery(osv.osv):

    _name = "stock.delivery"
    
ref_delivery()

class box(osv.osv):

    _name = "stock.box"
    
    _columns = {
        'name': fields.char ('Box ID', size=32, readonly=True),
        'rep_id': fields.many2one('res.partner', 'Dest. Representant/Leader', help='Representant, responsible for final delivery to sales reps. Destination of box delivery', readonly=True, required=True, states={'opened': [('readonly', False)]}),
        # 'rep_id': fields.many2one('res.partner', 'Representant', help="Representant to send the box to",                                                                                     required=True, domain="['|',('group_id.name','=','RESPONSABLES'),('is_leader','=',True)]"),
        'rep_rep_id': fields.related ('rep_id', 'parent_id', type="many2one", relation='res.partner', string='Representant', store=True, readonly=True),
        'rep_shipping_id': fields.many2one('res.partner', 'Shipping Address', readonly=True, states={'opened': [('readonly', False)]}, help="Shipping address for this box."),        
        'date_opened': fields.date ('Date opened', readonly=True, required=True, states={'opened': [('readonly', False)]}), 
        'date_closed': fields.date ('Date closed', readonly=True, states={'opened': [('readonly', False)]}), 
        'date_canceled': fields.date ('Date canceled', readonly=True, states={'opened': [('readonly', False)]}), 
        'date_delivered': fields.date ('Date delivered', readonly=True, states={'opened': [('readonly', False)]}), 
        'state': fields.selection([
            ('opened', 'Opened'),
            ('closed', 'Closed, not delivered'),
            ('delivered', 'Already delivered'),
            ('canceled', 'Canceled'),
            ], 'Box State', readonly=True, help="Gives the state of the box. \nThe box is created on the opened state. In this state you can add pickings to the box, till the box is closed. \nAfter the delivery confirmation, the box goes to the 'delivered' state.\nWhile opened a box could be canceled, meaning nothing was delivered or stored (just to document the use of the box ID).", select=True),
        'notes': fields.text('Notes'),
        'pickings_ids': fields.one2many ('stock.picking', 'box_id', 'Included pickings'), 
        'company_id': fields.many2one('res.company', 'Company',select=1, readonly=True, states={'opened': [('readonly', False)]}),
        'delivery_id': fields.many2one('stock.delivery', 'Delivery', select=1, readonly=True, states={'closed': [('readonly', False)]}),
    }
    
    _defaults = {
        'state': 'opened',
        'name': '/',
        'date_opened': lambda *a: time.strftime('%Y-%m-%d'),
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'res.partner', context=c),
    }

    def default_get(self, cr, uid, fields_list, context=None):
        res = super(box, self).default_get(cr, uid, fields_list, context=context)
        if 'rep_id' in context:
            res['rep_id'] = context['rep_id']
        return res

    def create(self, cr, user, vals, context=None):
        if ('name' not in vals) or (vals.get('name')=='/'):
            seq_obj_name =  'stock.box'
            vals['name'] = self.pool.get('ir.sequence').get(cr, user, seq_obj_name)

            partner_obj = self.pool.get('res.partner')
            context = context or {}
            rep_id = vals['rep_id']
            rep = partner_obj.browse(cr, user, rep_id, context=context)
            rep_shipping_id = partner_obj.address_get(cr, user, [rep_id], ['delivery'])['delivery']
            rep_rep_id = rep.parent_id and rep.parent_id.id or False

            if not rep_shipping_id:
                raise osv.except_osv(_('Error !'),
                                     _('NO delivery address for the rep was found. Please check!'))

            vals["rep_shipping_id"] = rep_shipping_id
            vals["rep_rep_id"] = rep_rep_id

        new_id = super(box, self).create(cr, user, vals, context)

        return new_id

    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        res = []
        for b in self.browse (cr, uid, ids, context=context):
            res.append ((b.id, "%s [%s]" % (b.name or "/", b.rep_id and b.rep_id.name or '')))
        return res

    def onchange_rep_id (self, cr, uid, ids, rep_id, context=None):
        partner_obj = self.pool.get('res.partner')
        
        context = context or {}
        
        if not rep_id:
            return False
            
        res = {}
        rep = partner_obj.browse(cr, uid, rep_id, context=context)
        res['rep_shipping_id'] = partner_obj.address_get(cr, uid, [rep_id], ['delivery'])['delivery']
        res['rep_rep_id'] = rep.parent_id and rep.parent_id.id or False

        if not res['rep_shipping_id']:
            raise osv.except_osv(_('Error !'),
                _('NO delivery address for the rep was found. Please check!'))

        self.write(cr, uid, ids, {'rep_shipping_id': res['rep_shipping_id'], 'rep_rep_id': res['rep_rep_id']},
                   context=context)
        return {'value': res}

    def action_close (self, cr, uid, ids, context=None):
    
        assert ids and len(ids)==1
        
        box = self.browse (cr, uid, ids[0], context=context)
        if box.state != 'opened':
            raise osv.except_osv(_('Error !'),
                _('Only opened boxes could be closed!'))
        
        self.write (cr, uid, ids, {'state': 'closed', 'date_closed': time.strftime('%Y-%m-%d')}, context=context)
        return True
    
    def action_cancel (self, cr, uid, ids, context=None):
        picking_obj = self.pool.get('res.picking')
    
        assert ids and len(ids)==1
        
        box = self.browse (cr, uid, ids[0], context=context)
        if box.state != 'opened':
            raise osv.except_osv(_('Error !'),
                _('Only opened boxes could be cancelled!'))
                
        if box.delivered_pickings_ids:
            included_ids = [p.id for p in box.delivered_pickings_ids]
            picking_obj.write (cr, uid, included_ids, {'box_id': False}, context=context)
        
        self.write (cr, uid, ids, {'state': 'cancelled', 'date_cancelled': time.strftime('%Y-%m-%d')}, context=context)
        return True
        
    def set_delivered (self, cr, uid, ids, delivery_id, context=None):
    
        for box in self.browse (cr, uid, ids, context=context):
            if box.state != 'closed':
                raise osv.except_osv(_('Error !'),
                    _('Only closed boxes could be delivered!'))
        
        self.write (cr, uid, ids, {'state': 'delivered', 'date_delivered': time.strftime('%Y-%m-%d'), 'delivery_id': delivery_id}, context=context)
        return True
    
box()

class stock_invoice_boxes(osv.osv_memory):
    _name = "stock.invoice_boxes"
    _inherit = "stock.invoice.onshipping"

    def _get_journal_id(self, cr, uid, context=None):
        box_obj = self.pool.get('stock.box')
        picking_obj = self.pool.get('stock.picking')
        user_obj = self.pool.get('res.users')
        journal_obj = self.pool.get('account.journal')

        if context is None:
            context = {}

        picking_ids = []
        active_ids = context.get('active_ids',[])
        for box in box_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            if box.state in ['closed', 'delivered']:
                for picking in box.pickings_ids:
                    if picking.invoice_state == '2binvoiced':
                        picking_ids.append(picking.id)

        vals = []
        browse_picking = picking_obj.browse(cr, uid, picking_ids, context=context)
        #todo Liricus
        user = user_obj.browse(cr, 1, uid, context=context)
        
        for pick in browse_picking:
            #~ if pick.shop_id:
                #~ company_id = pick.shop_id.company_id.id
            #~ else:
                #~ company_id = pick.company_id.id
            if pick:
                company_id = pick.company_id.id

            src_usage = pick.move_lines[0].location_id.usage
            dest_usage = pick.move_lines[0].location_dest_id.usage

            type = pick.picking_type_code
            if type == "outgoing":
                type = "out"
            if type == "incoming":
                type = "in"
            if type == 'out' and dest_usage == 'supplier':
                journal_type = 'purchase_refund'
            elif type == 'out' and dest_usage == 'customer':
                journal_type = 'sale'
            elif type == 'in' and src_usage == 'supplier':
                journal_type = 'purchase'
            elif type == 'in' and src_usage == 'customer':
                journal_type = 'sale_refund'
            else:
                journal_type = 'sale'

            #value = journal_obj.search(cr, uid, [('type', '=',journal_type ), ('company_id', '=', company_id)])
            journal_ids = journal_obj.search(cr, uid, [('type', '=',journal_type )])

            for journal in journal_obj.browse(cr, uid, journal_ids, context=context):
                #if pick.shop_id:
                if pick:
                    t1 = (journal.id, "%s [%s]" % (journal.name, journal.company_id.name))
                else:
                    t1 = (journal.id, "%s [%s]" % (journal.name, journal.company_id.name))

                if t1 not in vals:
                    vals.append(t1)

        return vals

    _columns = {
        'journal_id': fields.selection(_get_journal_id, 'Destination Journal',required=True),
    }
        
    _defaults = {
        'journal_id': lambda s, c, u, ctx: s._get_default_journal_id( c, u, context=ctx),     
    }
    
    def view_init(self, cr, uid, fields_list, context=None):
        context = context or {}
        box_obj = self.pool.get('stock.box')

        res = osv.osv_memory.view_init(self, cr, uid, fields_list, context=context)
        pick_obj = self.pool.get('stock.picking')
        count = 0
        picking_count = 0
        box_count = 0
        active_ids = context.get('active_ids',[])
        for box in box_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            if box.state in ['closed', 'delivered']:
                box_count += 1
                for picking in box.pickings_ids:
                    picking_count += 1
                    if picking.invoice_state == '2binvoiced':
                        count += 1

        if box_count == 0:
            raise osv.except_osv(_('Warning !'), _('No box in closed or delivered state selected! Please check it.'))
        if picking_count and count == 0:
            raise osv.except_osv(_('Warning !'), _('This picking list does not require invoicing.'))
        if not picking_count:
            raise osv.except_osv(_('Warning !'), _('No picking to process! Please check it.'))
        return res

    def create_invoice(self, cr, uid, ids, context=None):
        context = context or {}
        box_obj = self.pool.get('stock.box')
        picking_ids = []
        for box in box_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            if box.state in ['closed', 'delivered']:
                for picking in box.pickings_ids:
                    if picking.invoice_state == '2binvoiced':
                        picking_ids.append(picking.id)
        if picking_ids:
            context['active_ids'] = picking_ids
            return super(stock_invoice_boxes, self).create_invoice(cr, uid, ids, context=context)
        else:
            return {'type':'ir.actions.act_window_close' }
    
    def action_invoice_boxes (self, cr, uid, ids, context=None):
        return box_obj.action_invoice_boxes(cr, uid, ids, context=context)
        
stock_invoice_boxes()

class delivery (osv.osv):

    _inherit = "stock.delivery"

    def _get_reps(self, cr, uid, ids, fields, args, context=None):
        res = {}
        for d in self.browse(cr, uid, ids, context=context):
            res[d.id] = ', '.join(list(set([b.rep_id and b.rep_id.name or '' for b in d.boxes_ids])))
        
        return res
        
    _columns = {
        'name': fields.char ('Delivery ID', size=32, select=1),
        'forwarder_id': fields.many2one ('res.partner', 'Forwarder', select=True),
        'delivered_on': fields.date ('Delivered on', select=1),
        'notes': fields.text('Notes'),
        'boxes_ids': fields.one2many ('stock.box', 'delivery_id', 'Included boxes'),
        'reps': fields.function(_get_reps, method=True, string="Reps", type="char", size=256, readonly=True, store=True),
    }
    
delivery()
 
class delivery_confirmation (osv.osv_memory):

    _name = "stock.delivery_confirmation"
    
    _columns = {
        'name': fields.char ('Delivery ID', size=32, required=True),
        'forwarder_id': fields.many2one ('res.partner', 'Forwarder'),
        'delivered_on': fields.date ('Delivered on'),
        'notes': fields.text('Notes'),
    }
    
    _defaults = {
        'delivered_on': lambda *a: time.strftime('%Y-%m-%d'),
    } 

    def action_send (self, cr, uid, ids, context=None):
        context = context or {}
        delivery_obj = self.pool.get('stock.delivery')
        box_obj = self.pool.get('stock.box')
        
        boxes_ids = context.get ('active_ids',[])

        if not boxes_ids:
            raise osv.except_osv(_('Error !'),
                _('No boxes to deliver!'))
                
        dc = self.browse (cr, uid, ids[0], context=None)
        delivery_id = delivery_obj.create (cr, uid, {'name': dc.name,
                                                     'forwarder_id': dc.forwarder_id.id,
                                                     'delivered_on': dc.delivered_on,
                                                     'notes': dc.notes}, context=context)
 
        box_obj = self.pool.get('stock.box')
        box_obj.set_delivered (cr, uid, boxes_ids, delivery_id, context=context)

        return {'type':'ir.actions.act_window_close' }
            
delivery_confirmation ()
