    # -*- encoding: utf-8 -*-
#########################################################################
#                                                                       #
#########################################################################
#                                                                       #
# Copyright (C) 2009  Raphaël Valyi                                     #
#                                                                       #
#This program is free software: you can redistribute it and/or modify   #
#it under the terms of the GNU General Public License as published by   #
#the Free Software Foundation, either version 3 of the License, or      #
#(at your option) any later version.                                    #
#                                                                       #
#This program is distributed in the hope that it will be useful,        #
#but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
#GNU General Public License for more details.                           #
#                                                                       #
#You should have received a copy of the GNU General Public License      #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################

from openerp.osv import osv, fields
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class sale_order(osv.osv):
    _inherit = "sale.order"

    _columns = {
        'view_pricelist': fields.related('pricelist_id', string="Price list",
                                         type="many2one", relation="product.pricelist",
                                         readonly=True),
        'magento_discount_amount': fields.float('Magento discount', digits=(10,2),
                                                readonly=True),
        'magento_coupon_code': fields.char('Magento disc.coupon', size=32,
                                           readonly=True),
    }

    def oe_create(self, cr, uid, vals, data, external_referential_id, defaults, context):
        sol_obj = self.pool.get('sale.order.line')
        prod_obj = self.pool.get('product.product')

        vals = vals.copy() or {}

        # todo liricus
        partner_news = self.onchange_partner_id(cr, uid, [], vals.get('partner_id', False), context=context)
        if partner_news:
           vals.update(partner_news.get('value', {}))

        discount_amount = abs(float(data.get('discount_amount', '0.0')))
        coupon_code = data.get('coupon_code','') or ''
        disc_product_code = coupon_code.split('-')[0].upper()
        vals['magento_discount_amount'] = discount_amount
        vals['magento_coupon_code'] = coupon_code

        new_lines = []
        for line in vals.get('order_line', []):
            line_vals = line[2]
            product_id = line_vals.get('product_id')
            if not product_id:
                new_lines.append((0, 0, line_vals))
                continue
            product = prod_obj.browse(cr, uid, product_id, context=context)
            if product.type not in ['product']:
                new_lines.append((0, 0, line_vals))
                continue
            magento_price = line_vals.get('price_unit', 0.0)
            product_uom_qty = float(line_vals.get('product_uom_qty'))
            product_news = sol_obj.product_id_change(
                cr, uid, [],
                vals.get('pricelist_id', False),
                line_vals['product_id'],
                qty=product_uom_qty,
                uom=line_vals.get('product_uom_id'),
                partner_id=int(vals.get('partner_id')),
                lang='es_AR',
                date_order=vals.get('date_order'),
                fiscal_position=vals.get('fiscal_position'),
            )

            if product_news:
                new_vals = product_news.get('value', {})
                line_vals.update(new_vals)
                discount = new_vals.get('discount', 0.0)

                product = prod_obj.browse(cr, uid, line_vals['product_id'], context=context)
                subtotal_wo_discount = magento_price * product_uom_qty
                if disc_product_code and product.default_code.startswith(disc_product_code):
                    line_vals['price_unit'] = magento_price * (1 - (subtotal_wo_discount and discount_amount/subtotal_wo_discount or 0.0))
                    disc_product_code = None
                line_vals['price_subtotal'] = line_vals['price_unit'] * product_uom_qty * (1.0 - discount/100.0)

            new_lines.append((0, 0, line_vals))

        if disc_product_code and discount_amount:
            msg = u"El código de descuento de Magento [%s] NO pudo ser asociado con ningún producto del pedido. El descuento de %8.2f ARS NO FUE TOMADO EN CUENTA" % \
                   (coupon_code, discount_amount)
            _logger.warning(msg)
        elif discount_amount:
            msg = u"Se ha aplicado un cupón de descuento de Magento (%s, %8.2f ARS)\n" % \
                   (coupon_code, discount_amount)
        else:
            msg = u''
        vals['note'] = msg

        if 'order_line' in vals:
            vals['order_line'] = new_lines

        vals['order_policy'] = 'picking'

        return super(sale_order, self).oe_create(cr, uid, vals, data, external_referential_id, defaults, context)
    # todo liricus

    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        res = super(sale_order, self).onchange_partner_id(cr, uid, ids, part, context)

        if res and 'value' in res and 'pricelist_id' in res['value']:
            res['value']['view_pricelist'] = res['value']['pricelist_id']

        return res

    def action_change_pricelist(self, cr, uid, ids, context=None):
        assert ids and len(ids)==1, 'One at the time'

        so = self.browse(cr, uid, ids[0], context=context)

        return {
            'name':_("Change Pricelist"),
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'sale.change_pricelist',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': dict(context,
                            active_ids=ids,
                            default_new_pricelist=so.pricelist_id and so.pricelist_id.id or False)
        }

    # def action_recompute_pricelist(self, cr, uid, ids, context=None):
    #     for so in self.browse(cr, uid, ids, context=context):
    #         discount_amount = so.magento_discount_amount
    #         coupon_code = so.magento_coupon_code
    #         disc_product_code = (coupon_code or '').split('-')[0].upper()
    #
    #         for line in so.order_line:
    #             if line.product_id.type not in ['product']:
    #                 continue
    #             product_news = line.product_id_change(
    #                 so.pricelist_id.id,
    #                 line.product_id.id,
    #                 qty=line.product_uom_qty,
    #                 uom=line.product_uom.id,
    #                 partner_id=so.partner_id.id,
    #                 lang='es_AR',
    #                 date_order=so.date_order,
    #                 fiscal_position=so.fiscal_position and so.fiscal_position.id or False,
    #             )
    #
    #             if product_news:
    #                 new_vals = product_news.get('value', {})
    #                 discount = new_vals.get('discount', 0.0)
    #
    #                 subtotal_wo_discount = line.price_unit * line.product_uom_qty
    #                 new_vals['discount'] = (line.price_unit - new_vals['price_unit'])/line.price_unit * 100
    #                 if disc_product_code and line.product_id.default_code.startswith(disc_product_code):
    #                     new_vals['price_unit'] = line.price_unit * (1 - (subtotal_wo_discount and discount_amount/subtotal_wo_discount or 0.0))
    #                     disc_product_code = None
    #                 else:
    #                     new_vals['price_unit'] = line.price_unit
    #                 new_vals['price_subtotal'] = new_vals.get('price_unit', line.price_unit) * \
    #                                              line.product_uom_qty * (1.0 - discount/100.0)
    #                 line.write(new_vals)
    #
    #         msg = so.note or u''
    #         if disc_product_code and discount_amount:
    #             msg += u"El código de descuento de Magento [%s] NO pudo ser asociado con ningún producto del pedido. El descuento de %8.2f ARS NO FUE TOMADO EN CUENTA\n" % \
    #                    (coupon_code, discount_amount)
    #             _logger.warning(msg)
    #         elif discount_amount:
    #             msg += u"Se ha aplicado un cupón de descuento de Magento (%s, %8.2f ARS)\n" % \
    #                    (coupon_code, discount_amount)
    #         so.write({'note': msg})
    #
    #     return True
    def action_recompute_pricelist(self, cr, uid, ids, context=None):
        for so in self.browse(cr, uid, ids, context=context):
            discount_amount = so.magento_discount_amount
            coupon_code = so.magento_coupon_code
            disc_product_code = (coupon_code or '').split('-')[0].upper()

            for line in so.order_line:
                if line.product_id.type not in ['product']:
                    continue
                product_news = line.product_id_change(
                    so.pricelist_id.id,
                    line.product_id.id,
                    qty=line.product_uom_qty,
                    uom=line.product_uom.id,
                    partner_id=so.partner_id.id,
                    lang='es_AR',
                    date_order=so.date_order,
                    fiscal_position=so.fiscal_position and so.fiscal_position.id or False,
                )

                if product_news:
                    new_vals = product_news.get('value', {})
                    discount = new_vals.get('discount', 0.0)

                    subtotal_wo_discount = line.price_unit * line.product_uom_qty
                    if disc_product_code and line.product_id.default_code.startswith(disc_product_code):
                        new_vals['price_unit'] = line.price_unit * (
                        1 - (subtotal_wo_discount and discount_amount / subtotal_wo_discount or 0.0))
                        disc_product_code = None
                    new_vals['price_subtotal'] = new_vals.get('price_unit', line.price_unit) * \
                                                 line.product_uom_qty * (1.0 - discount / 100.0)

                    line.write(new_vals)

            msg = so.note or u''
            if disc_product_code and discount_amount:
                msg += u"El código de descuento de Magento [%s] NO pudo ser asociado con ningún producto del pedido. El descuento de %8.2f ARS NO FUE TOMADO EN CUENTA\n" % \
                       (coupon_code, discount_amount)
                _logger.warning(msg)
            elif discount_amount:
                msg += u"Se ha aplicado un cupón de descuento de Magento (%s, %8.2f ARS)\n" % \
                       (coupon_code, discount_amount)
            so.write({'note': msg})

        return True

    def action_confirm(self, cr, uid, ids, context=None):
        self.action_recompute_pricelist(cr, uid, ids, context=context)

        return super(sale_order, self).action_confirm(cr, uid, ids, context=context)

sale_order()

class sale_change_pricelist(osv.osv_memory):
    _name = 'sale.change_pricelist'

    _columns = {
        'new_pricelist': fields.many2one('product.pricelist', 'New pricelist',
                                         required=True),
    }

    def action_change_pricelist(self, cr, uid, ids, context=None):
        assert ids and len(ids)==1, 'One at the time'

        context = context or {}
        so_id = context.get('active_ids')[0]

        scp = self.browse(cr, uid, ids[0], context=context)

        so_obj = self.pool.get('sale.order')
        so = so_obj.browse(cr, uid, so_id, context=context)

        so.write({'pricelist_id': scp.new_pricelist.id})

        so.action_recompute_pricelist()

        return {'type': 'ir.actions.act_window_close'}

sale_change_pricelist()
