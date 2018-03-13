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

class StockPickingOrderConfirm(osv.osv_memory):
    _name = 'stock.picking.order.confirm'

    def default_get(self, cr, uid, fields_list, context=None):
        res = super(StockPickingOrderConfirm, self).default_get(cr, uid, fields_list, context=context)
        if 'pick_order_id' in fields_list:
            active_ids = context.get('active_ids')
            if not active_ids:
                raise osv.except_osv(_('Processing Error'),\
                       _('Invalid operation. Internal error. Contact system administrator'))
            pick_order_id = active_ids[0]
            res['pick_order_id'] = pick_order_id
            po = self.pool.get('stock.picking.order').browse(cr, uid, pick_order_id, context=context)
            res['rep'] = po.rep.id
            if 'lines' in fields_list:
                res['lines'] = [(0,0,{'move_id': m.id, 
                               'requested_qty': m.product_uom_qty,
                               'actual_qty': 0.0,
                               'product': m.product_id.id,
                               'uom': m.product_id.uom_id.id,
                               'picking': m.picking_id.id,
                               }) for m in po.move_ids]
        return res
    
    _columns = {
        'pick_order_id': fields.many2one('stock.picking.order', 'Picking Order', readonly=True),
        'rep': fields.many2one('res.partner','Representant',readonly=True),
        'scanned_item': fields.char('Scanned EAN13', size=64),
        'box_id': fields.many2one('stock.box', 'Box'),
        'lines': fields.one2many('stock.picking.order.confirm.line', 'wizard_id', 'Lines'),
    }

    def do_reset_scan(self, cr, uid, ids, context=None):
        """
        Start the count again. All counters to 0
        """
        assert ids and len(ids)==1, 'One at the time'
        for poc_line in self.browse(cr, uid, ids[0], context=context).lines:
            self.write(cr, uid, ids[0], {'actual_qty': 0.0})
        return True

    def do_set_scan_to_requested(self, cr, uid, ids, context=None):
        """
        Start the count again. All counters to 0
        """
        assert ids and len(ids)==1, 'One at the time'
        for poc_line in self.browse(cr, uid, ids[0], context=context).lines:
            poc_line.write({'actual_qty': poc_line.requested_qty})
        return True

    def resolve_2many_commands(self, cr, uid, field_name, commands, fields=None, context=None):
        """ Serializes one2many and many2many commands into record dictionaries
            (as if all the records came from the database via a read()).  This
            method is aimed at onchange methods on one2many and many2many fields.

            Because commands might be creation commands, not all record dicts
            will contain an ``id`` field.  Commands matching an existing record
            will have an ``id``.

            :param field_name: name of the one2many or many2many field matching the commands
            :type field_name: str
            :param commands: one2many or many2many commands to execute on ``field_name``
            :type commands: list((int|False, int|False, dict|False))
            :param fields: list of fields to read from the database, when applicable
            :type fields: list(str)
            :returns: records in a shape similar to that returned by ``read()``
                (except records may be missing the ``id`` field if they don't exist in db)
            :rtype: list(dict)
        """
        result = []             # result (list of dict)
        record_ids = []         # ids of records to read
        updates = {}            # {id: dict} of updates on particular records
        for command in commands:
            if not isinstance(command, (list, tuple)):
                record_ids.append(command)
            elif command[0] == 0:
                result.append(command[2])
            elif command[0] == 1:
                record_ids.append(command[1])
                updates.setdefault(command[1], {}).update(command[2])
            elif command[0] in (2, 3):
                record_ids = [id for id in record_ids if id != command[1]]
            elif command[0] == 4:
                record_ids.append(command[1])
            elif command[0] == 5:
                result, record_ids = [], []
            elif command[0] == 6:
                result, record_ids = [], list(command[2])
        # read the records and apply the updates
        for record in self.read(cr, uid, record_ids, fields, context=context):
            record.update(updates.get(record['id'], {}))
            result.append(record)
        return result

    def onchange_scanned_item(self, cr, uid, ids, scanned_item, lines, context=None):
        context = context or {}
        product_obj = self.pool.get('product.product')
        move_obj = self.pool.get('stock.move')
        if not scanned_item:
            return False
        rlines = self.resolve_2many_commands(cr, uid, 'lines', lines, fields=['move_id','actual_qty','requested_qty'], context=context)
        found = False
        incremented = False
        new_lines = []
        if rlines:
            for line in rlines:
                move = move_obj.browse(cr, uid, line['move_id'], context=context)
                if not move or not move.product_id:
                    raise osv.except_osv(_('Processing Error'),\
                           _('Invalid operation. Internal error. Contact system administrator'))
                product = move.product_id
                if (not incremented) and product and product.ean13 == scanned_item:
                    found = True
                    if 'actual_qty' not in line:
                        raise osv.except_osv(_('Processing Error'),\
                           _('Invalid operation. Please set the actual quantity to compare'))
                    if line['actual_qty'] < line['requested_qty']:
                        line['actual_qty'] += 1.0
                        incremented = True
                if 'id' in line:
                    del line['id']
                new_lines.append(line)
        if found and incremented:
            return {'value': {'lines': new_lines, 'scanned_item': False}}
        elif found and not incremented:
            raise osv.except_osv(_('Processing Error'),\
                   _('Invalid operation. Expected product count already reached. It is not allowed to move more units of [%s]') % product.name)
        product_ids = product_obj.search(cr, uid, [('ean13','=',scanned_item)])
        if not product_ids:
            raise osv.except_osv(_('Processing Error'),\
                _('Invalid code scanned. It is not found on any product of the database'))
        product = product_obj.browse(cr, uid, product_ids[0], context=context)
        raise osv.except_osv(_('Processing Error'),\
               _('Product scanned is not part of the picking. The scanned code corresponds to a [%s]') % product.name)

    def action_confirm_po(self, cr, uid, ids, context=None):
        picking_obj= self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        porder_obj = self.pool.get('stock.picking.order')

        for poc in self.browse(cr, uid, ids, context=context):
            pick_order = poc.pick_order_id
            cancel_moves = []
            moves = []
            new_moves = []
            pickings = []
            picks_to_bo = []
            qtities_to_write = {}
            from collections import defaultdict
            dict = defaultdict(list)
            for line in poc.lines:
                if line.requested_qty < line.actual_qty:
                    raise osv.except_osv(_('Error'),\
                               _('The actual qty is bigger than the requested qty, please check!'))
                actual_qty = line.actual_qty and line.actual_qty or 0
                if not line.move_id:
                    raise osv.except_osv(_('Processing Error'),\
                           _('It is not foreseen you to add lines to picking on processing. Please check!'))
                if actual_qty > 0.0:
                    moves.append(line.move_id.id)
                    qtities_to_write[line.move_id.id] = actual_qty
                if line.move_id.picking_id.id not in pickings:
                    pickings.append(line.move_id.picking_id.id)
                if line.requested_qty > actual_qty:
                    diff = line.requested_qty - actual_qty
                    new_move_id = move_obj.split(cr, uid, line.move_id, diff, context = context)
                    dict[line.move_id.picking_id.id].append(new_move_id)
                    new_moves.append(new_move_id)
                    if line.move_id.picking_id not in picks_to_bo:
                        picks_to_bo.append(line.move_id.picking_id)
            for p in picks_to_bo:
                picking_obj._create_backorder(cr, uid, p, backorder_moves=move_obj.browse(cr, uid, dict[p.id]), context = context)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            porder_obj.write(cr, uid, [poc.pick_order_id.id], {'state': 'done',
                                                                'box_id': poc.box_id.id,
                                                                'confirmed_on': now})


            move_obj.action_assign(cr, uid, moves, context = context)
            #~ move_obj.action_cancel(cr, uid, cancel_moves, context = context)
            picking_obj.do_transfer(cr, uid, pickings, context = context)
            # todo liricus agregue 'invoice_state': '2binvoiced'
            picking_obj.write(cr, uid, pickings, {'box_id': poc.box_id.id,'invoice_state': '2binvoiced'})
            move_obj.write(cr, uid, new_moves, {'pick_order_id': False})
            for m in moves:
                move_obj.write(cr, uid, [m], {'product_uom_qty': qtities_to_write[m]})
        return {'type': 'ir.actions.act_window_close'}


class StockPickingOrderConfirmLine(osv.osv_memory):
    _name = 'stock.picking.order.confirm.line'
    
    _columns = {
        'wizard_id': fields.many2one('stock.picking.order.confirm', 'Parent Wizard'),
        'move_id': fields.many2one('stock.move', 'Move'),
        'picking': fields.related('move_id', 'picking_id', 
                                  string='Picking', 
                                  type='many2one', relation='stock.picking', 
                                  readonly=True),
        'product': fields.related('move_id', 'product_id', 
                                  string='Product', 
                                  type='many2one', relation='product.product', 
                                  readonly=True),
        'uom': fields.related('move_id','product_id', 'uom_id', 
                                  string='UOM', 
                                  type='many2one', relation='product.uom',
                                  readonly=True),
        'requested_qty': fields.related('move_id', 'product_qty',
                                  string='Requested Qty', 
                                  type='float', digits=(5,0),
                                  readonly=True),
        'ean13': fields.related('move_id', 'product_id', 'ean13',
                                  string='EAN13', 
                                  type="char", size=16,
                                  readonly=True),
        'actual_qty': fields.float('Actual Qty', digits=(5,0)),
    }
