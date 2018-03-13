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
from openerp import netsvc
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class sale_order (osv.osv):
    _inherit = "sale.order"
    
    def action_massive_confirm (self, cr, uid, ids, context=None):
        for so in self.browse(cr, uid, ids, context=context):
            so.action_confirm()
        return True

    def action_ship_create(self, cr, uid, ids, *args):
        #Wineem : Create a different pick per each season
        
        wf_service = netsvc.LocalService("workflow")
        picking_id = False
        move_obj = self.pool.get('stock.move')
        proc_obj = self.pool.get('procurement.order')
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        for order in self.browse(cr, uid, ids, context={}):
            proc_ids = []
            #output_id = order.shop_id.warehouse_id.lot_output_id.id
            output_id = order.warehouse_id.wh_output_stock_loc_id.id
            picking_id = {}
            no_season_picking_id = False
            for line in order.order_line:
                proc_id = False
                date_planned = datetime.now() + relativedelta(days=line.delay or 0.0)
                date_planned = (date_planned - timedelta(days=company.security_lead)).strftime('%Y-%m-%d %H:%M:%S')

                if line.state == 'done':
                    continue
                move_id = False
                if line.product_id and line.product_id.product_tmpl_id.type in ('product', 'consu'):
                    #location_id = order.shop_id.warehouse_id.lot_stock_id.id
                    location_id = order.warehouse_id.lot_stock_id.id
                    if line.product_id.season:
                        if not picking_id.get(line.product_id.season.id, None):
                            pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
                            p_id = self.pool.get('stock.picking').create(cr, uid, {
                                'name': pick_name,
                                'origin': order.name,
                                'type': 'out',
                                'state': 'auto',
                                'move_type': order.picking_policy,
                                'sale_id': order.id,
                                'address_id': order.partner_shipping_id.id,
                                'note': order.note,
                                'invoice_state': (order.order_policy=='picking' and '2binvoiced') or 'none',
                                'season': line.product_id.season.id,
                                'company_id': order.company_id.id,
                            })
                            picking_id[line.product_id.season.id] = p_id
                        else:
                            p_id = picking_id[line.product_id.season.id]
                    else:
                        if not no_season_picking_id:
                            pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
                            p_id = self.pool.get('stock.picking').create(cr, uid, {
                                'name': pick_name,
                                'origin': order.name,
                                'type': 'out',
                                'state': 'auto',
                                'move_type': order.picking_policy,
                                'sale_id': order.id,
                                'address_id': order.partner_shipping_id.id,
                                'note': order.note,
                                'invoice_state': (order.order_policy=='picking' and '2binvoiced') or 'none',
                                'company_id': order.company_id.id,
                            })
                            no_season_picking_id = p_id
                        else:
                            p_id = no_season_picking_id
                        
                    move_id = self.pool.get('stock.move').create(cr, uid, {
                        'name': line.name[:64],
                        'picking_id': p_id,
                        'product_id': line.product_id.id,
                        'date': date_planned,
                        'date_expected': date_planned,
                        'product_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'product_uos_qty': line.product_uos_qty,
                        'product_uos': (line.product_uos and line.product_uos.id)\
                                or line.product_uom.id,
                        'product_packaging': line.product_packaging.id,
                        'address_id': line.address_allotment_id.id or order.partner_shipping_id.id,
                        'location_id': location_id,
                        'location_dest_id': output_id,
                        'sale_line_id': line.id,
                        'tracking_id': False,
                        'state': 'draft',
                        #'state': 'waiting',
                        'note': line.notes,
                        'company_id': order.company_id.id,
                    })

                if line.product_id:
                    proc_id = self.pool.get('procurement.order').create(cr, uid, {
                        'name': line.name,
                        'origin': order.name,
                        'date_planned': date_planned,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'product_uos_qty': (line.product_uos and line.product_uos_qty)\
                                or line.product_uom_qty,
                        'product_uos': (line.product_uos and line.product_uos.id)\
                                or line.product_uom.id,
                        #'location_id': order.shop_id.warehouse_id.lot_stock_id.id,
                        'location_id': order.warehouse_id.lot_stock_id.id,
                        'procure_method': line.type,
                        'move_id': move_id,
                        'property_ids': [(6, 0, [x.id for x in line.property_ids])],
                        'company_id': order.company_id.id,
                    })
                    proc_ids.append(proc_id)
                    self.pool.get('sale.order.line').write(cr, uid, [line.id], {'procurement_id': proc_id})
                    if order.state == 'shipping_except':
                        for pick in order.picking_ids:
                            for move in pick.move_lines:
                                if move.state == 'cancel':
                                    mov_ids = move_obj.search(cr, uid, [('state', '=', 'cancel'),('sale_line_id', '=', line.id),('picking_id', '=', pick.id)])
                                    if mov_ids:
                                        for mov in move_obj.browse(cr, uid, mov_ids):
                                            move_obj.write(cr, uid, [move_id], {'product_qty': mov.product_qty, 'product_uos_qty': mov.product_uos_qty})
                                            proc_obj.write(cr, uid, [proc_id], {'product_qty': mov.product_qty, 'product_uos_qty': mov.product_uos_qty})

            val = {}

            if picking_id:
                for pick_id in picking_id.keys():
                    wf_service.trg_validate(uid, 'stock.picking', picking_id[pick_id], 'button_confirm', cr)

            if no_season_picking_id:
                wf_service.trg_validate(uid, 'stock.picking', no_season_picking_id, 'button_confirm', cr)

            for proc_id in proc_ids:
                wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)

            if order.state == 'shipping_except':
                val['state'] = 'progress'
                val['shipped'] = False

                if (order.order_policy == 'manual'):
                    for line in order.order_line:
                        if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                            val['state'] = 'manual'
                            break
            self.write(cr, uid, [order.id], val)
        return True

sale_order()


class validate_order_confirm (osv.osv_memory):
    _name = "sale.validate_orders_confirm"

    _columns = {
        'campaign': fields.many2one('sale.campaign', 'Campaign', required=True),
    }

    def action_validate_orders (self, cr, uid, ids, context=None):
        context = context or {}
        so_obj = self.pool.get('sale.order')

        if context.get('active_ids', None):
            so_ids = context['active_ids']
            if so_ids:
                assert ids and len(ids) == 1
                msc = self.browse(cr, uid, ids[0], context=context)
                so_obj.write(cr, uid, so_ids, {'campaign': msc.campaign.id}, context=context)
                self.pool.get('sale.order').action_massive_confirm (cr, uid, so_ids, context=context)
            
        return {'type': 'ir.actions.act_window_close'}
    
validate_order_confirm()


class cancel_order_confirm (osv.osv_memory):
    _name = "sale.cancel_orders_confirm"

    def action_cancel_orders (self, cr, uid, ids, context=None):
        context = context or {}
        
        if context.get('active_ids', None):
            so_ids = context['active_ids']
            self.pool.get('sale.order').action_cancel (cr, uid, so_ids, context=context)
            
        return {'type': 'ir.actions.act_window_close'}
    
cancel_order_confirm()
