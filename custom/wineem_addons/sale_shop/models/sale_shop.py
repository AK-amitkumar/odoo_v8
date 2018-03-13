# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################
from openerp.osv import fields, osv


class sale_shop(osv.osv):
    _name = "sale.shop"
    _description = "Sales Shop"
    _columns = {
        'name': fields.char('Shop Name', size=64, required=True),
        'payment_default_id': fields.many2one('account.payment.term', 'Default Payment Term', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist'),
        'project_id': fields.many2one('account.analytic.account', 'Analytic Account', domain=[('parent_id', '!=', False)]),
        'company_id': fields.many2one('res.company', 'Company', required=False),
        'afip_sales_point_id': fields.many2one('numa_ar_base.afip_sales_point', 'AFIP sales point',
                                               help='AFIP sales point to be used on operations based on this shop'),

    }
    _defaults = {
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'sale.shop', context=c),
    }

sale_shop()


class sale_order(osv.osv):
    _inherit = "sale.order"

    _columns = {
        'shop_id':fields.many2one('sale.shop', 'Shop')
    }

sale_order()
