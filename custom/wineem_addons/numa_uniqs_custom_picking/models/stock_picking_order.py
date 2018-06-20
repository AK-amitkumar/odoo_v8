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
from datetime import date, datetime
import time

STOCK_MOVE_STATES = [('draft', 'New'),
                        ('cancel', 'Cancelled'),
                        ('waiting', 'Waiting Another Move'),
                        ('confirmed', 'Waiting Availability'),
                        ('assigned', 'Available'),
                        ('done', 'Done')]

class StockPickingOrder(osv.osv):
    _name = 'stock.picking.order'
    _order = 'name desc'
    _rec_name = 'name'

    def _get_rep(self, cr, uid, ids, fields, args, context=None):
        res = {}
        for po in self.browse(cr, uid, ids, context=context):
            res[po.id] = po.partner_id.parent_id and po.partner_id.parent_id.id or po.partner_id.id
        return res

    _columns = {
        'name': fields.char('Reference', size=32, required=True, readonly=True),
        'partner_id': fields.many2one('res.partner', 'Customer', ondelete='cascade', required=True),
        'rep': fields.function(_get_rep, method=True, string="Rep", type="many2one", relation="res.partner", store=True),
        # 'p_rep': fields.related('partner_id', 'parent_id', string="Rep", type="many2one", relation="res.partner", readonly=True, store=True),
        'leader': fields.related('partner_id', 'leader_id', string="Leader", type="many2one", relation="res.partner", readonly=True, store=True),
        'box_id': fields.many2one('stock.box', 'Box', ondelete='set null', domain=[('state','=','opened')]),
        'state': fields.selection([
                    ('draft', 'Draft'),
                    ('planned', 'Planned'),
                    ('done', 'Done'),
                    ('canceled', 'Cancelled')], 'State', required=True, readonly=True),
        'planned_on': fields.datetime('Planned on', readonly=True),
        'confirmed_on': fields.datetime('Confirmed on', readonly=True),
        'canceled_on': fields.datetime('Canceled on', readonly=True),
        'move_ids': fields.one2many('stock.move', 'pick_order_id', 'Moves'),
    }
    
    _defaults = {
        'name': '/',
        'state': 'draft',
    }

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Pick Order Reference must be unique !'),
    ]

    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.order')
        return super(StockPickingOrder, self).create(cr, uid, vals, context=context)

    def get_moves(self, cr, uid, ids, context=None):
        po = self.browse(cr, uid, ids[0], context = context)
        move_obj = self.pool.get('stock.move')
        move_ids = move_obj.search(cr, uid,
                                   [('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned']),
                                    ('pick_order_id', '=', False),
                                    ('picking_id.picking_type_id.code', '=', 'outgoing'),
                                    ('picking_id.partner_id', '=', po.partner_id.id)], context=context)
        # self.write(cr, uid, ids, {'state': 'planned',
        #                             'planned_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        #                             'move_ids': [(6,0,move_ids)]})
        self.write(cr, uid, ids, {'state': 'draft',
                                    'move_ids': [(6,0,move_ids)]})

        move_obj.write(cr, uid, move_ids, {'pick_order_id': po.id,
                                           'state': 'confirmed',
                                           'client_partner_id': po.partner_id.id})
        return True

    def action_plan(self, cr, uid, ids, context=None):
        po = self.browse(cr, uid, ids[0], context = context)
        move_obj = self.pool.get('stock.move')
        move_ids = move_obj.search(cr, uid,
                                   [('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned']),
                                    ('pick_order_id', '=', False),
                                    ('picking_id.picking_type_id.code', '=', 'outgoing'),
                                    ('picking_id.partner_id', '=', po.partner_id.id)], context=context)
        self.write(cr, uid, ids, {'state': 'planned',
                                    'planned_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        # self.write(cr, uid, ids, {'state': 'draft',
        #                             'move_ids': [(6,0,move_ids)]})
        #
        move_obj.write(cr, uid, move_ids, {'client_partner_id': po.partner_id.id})
        return True

    def action_confirm(self, cr, uid, ids, context=None):
        assert ids and len(ids)==1, 'One at the time'
        po = self.browse(cr, uid, ids[0], context=context)
        for move in po.move_ids:
            if move.state not in ['draft','confirmed', 'assigned']:
                raise osv.except_osv(_('Processing Error'),\
                       _('Move (product [%s]) from picking [%s] in not valid state to be confirmed. Please check!') % (move.product_id.name, po.name))
        return {
            'name':_("Confirm Picking Order %s") % po.name,
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'stock.picking.order.confirm',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            # 'target': 'new',
            'domain': '[]',
            'context': dict(context, active_ids=ids, box_id = po.box_id.id, pick_order_id = po.id)
        }

    def action_cancel(self, cr, uid, ids, context=None):
        for po in self.browse(cr, uid, ids, context=context):
            po.write({'state': 'canceled',
                        'canceled_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'move_ids': False})
        return True

    def action_back_to_draft(self, cr, uid, ids, context=None):
        for po in self.browse(cr, uid, ids, context=context):
            po.write({'state': 'draft',
                        'planned_on': False,
                        'confirmed_on':False,
                        'canceled_on': False,
                        })
        return True

    def action_print(self, cr, uid, ids, context=None):
        assert ids and len(ids)==1, 'One at the time'
        return {
                'type': 'ir.actions.report.xml', 
                'report_name': 'numa_uniqs_custom_picking.report_picking_order', 
                'datas': {'model': 'stock.picking.order','ids': ids}, 
                'nodestroy': True
            }

    def action_print_picking_list(self, cr, uid, ids, context=None):

        assert ids and len(ids) == 1, 'One at the time'
        pick_order = self.browse(cr, uid, ids[0], context=context)

        datas = {
            'model': 'stock.picking.order',
            'ids': list(set([m.picking_id.id for m in pick_order.move_ids])),
        }

        return {'type': 'ir.actions.report.xml',
                'report_name': 'picking_packing_list_print',
                'datas': datas,
                'nodestroy': True}


class stock_move(osv.osv):
    _inherit = 'stock.move'

    _columns = {
        'pick_order_id': fields.many2one('stock.picking.order', 'Pick Order', readonly=True, ondelete='set null'),
    }

#~ class stock_picking_order_line(osv.osv):
    #~ _name = 'stock.picking.order.line'
#~
    #~ _columns = {
        #~ 'pick_order_id': fields.many2one('stock.picking.order', 'Pick Order', readonly=True, ondelete='set null'),
        #~ 'move_id': fields.many2one('stock.move', 'Move', readonly=True),
        #~ 'picking_id': fields.related('move_id', 'picking_id', type='many2one', relation="stock.picking", string='Reference', store=True),
        #~ 'product_id': fields.related('move_id', 'product_id', type='many2one', relation="product.product", string='Product', store=True),
        #~ 'group_id': fields.related('move_id', 'group_id', type='many2one', relation="procurement.group", string='Procurement Group', store=True),
        #~ 'product_uom': fields.related('move_id', 'product_uom', type='many2one', relation="product.uom", string='Procurement Group', store=True),
        #~ 'product_uom_qty': fields.related('move_id', 'product_uom_qty', type='float', string='Quantity'),
        #~ 'state': fields.related('move_id', 'state', type='selection', selection=STOCK_MOVE_STATES, string='State', store=False),
    #~ }


class stock_picking(osv.osv):
    _inherit = "stock.picking"

    # _columns = {
    #     'leader_id': fields.related('partner_id', 'leader_id', string="Leader", type="many2one", relation="res.partner",
    #                                 readonly=True, store=True),
    #     'rep_id': fields.related('partner_id', 'parent_id', string="Rep", type="many2one", relation="res.partner",
    #                              readonly=True, store=True),
    # }

    def _invoice_line_hook(self, cr, uid, move_line, invoice_line_id):
        invoice_line_obj = self.pool.get('account.invoice.line')

        if (move_line.product_uos_qty or move_line.product_qty) <= 0:
            invoice_line_obj.unlink(cr, uid, [invoice_line_id])

    def action_generate_picking_order(self, cr, uid, ids, context=None):
        active_ids = context.get('active_ids', [])

        if active_ids:
            pick_order_obj = self.pool.get('stock.picking.order')
            move_obj = self.pool.get('stock.move')

            pick_by_partner = {}
            moves_to_add = []

            for picking in self.browse(cr, uid, active_ids, context=context):
                for mov in picking.move_lines:
                    if not mov.pick_order_id and mov.state in ['waiting', 'draft', 'confirmed', 'assigned']:
                        moves_to_add.append(mov)

            if moves_to_add:
                for mov in moves_to_add:
                    if mov.picking_id.partner_id in pick_by_partner:
                        pick_by_partner[mov.picking_id.partner_id].append(mov)
                    else:
                        pick_by_partner[mov.picking_id.partner_id] = [mov]
            if pick_by_partner:
                picking_orders_ids = []
                for partner in pick_by_partner.keys():
                    po_id = pick_order_obj.create(cr, uid,
                                                  {'partner_id': partner.id},
                                                  context=context)
                    # po = pick_order_obj.browse(cr, uid, po_id, context=context)
                    move_ids = []
                    for mov in pick_by_partner[partner]:
                        move_ids.append(mov.id)
                    #     move_obj.write(cr, uid,
                    #                    [mov.id],
                    #                    {'pick_order_id': po_id, 'state': 'confirmed'},
                    #                    context=context)
                    pick_order_obj.write(cr, uid, [po_id], {'state': 'draft', 'move_ids': [(6, 0, move_ids)]})
                    move_obj.write(cr, uid, move_ids, {'pick_order_id': po_id, 'state': 'confirmed',
                                                       'client_partner_id': partner.id})
                    picking_orders_ids.append(po_id)

                return picking_orders_ids

        # self.write(cr, uid, ids, {'state': 'draft', 'move_ids': [(6,0,move_ids)]})
        # move_obj.write(cr, uid, move_ids, {'pick_order_id': po.id, 'state': 'confirmed'})


        return True


class stock_picking_to_picking_order(osv.osv_memory):
    _name = "stock.picking_to_picking_order"

    def action_create(self, cr, uid, ids, context=None):
        picking_obj = self.pool.get('stock.picking')

        active_ids = context.get('active_ids', [])

        if active_ids:
            po_ids = picking_obj.action_generate_picking_order(cr, uid, active_ids, context=context)
            if isinstance(po_ids, list):
                return {
                    'name': _("Picking to Picking Orders"),
                    'view_mode': 'tree,form',
                    'view_id': False,
                    'view_type': 'form',
                    'res_model': 'stock.picking.order',
                    'res_id': False,
                    'type': 'ir.actions.act_window',
                    'nodestroy': False,
                    'domain': [('id', 'in', po_ids)],
                    'context': context
                }

        raise osv.except_osv(_('Error'), \
                             _('No picking to process'))


stock_picking_to_picking_order()