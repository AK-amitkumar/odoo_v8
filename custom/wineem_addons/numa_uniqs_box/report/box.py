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

import time
from openerp.report import report_sxw
from openerp.tools import amount_to_text
from openerp.tools.translate import _
import pdb

to_29 = ( 'cero',  'un',   'dos',  'tres', 'cuatro',   'cinco',   'seis',
          'siete', 'ocho', 'nueve', 'diez',   'once', 'doce', 'trece',
          'catorce', 'quince', 'dieciseis', 'diecisiete', 'dieciocho', 'diecinueve',
          'veintiuno', 'veintidos', 'veintitres', 'veinticuatro', 'veinticinco',
          'veintiseis', 'veintisiete', 'veintiocho', 'veintinueve' )

tens  = ( 'veinte', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa')
hundreds = ( 'cien', 'doscientos', 'trescientos', 'cuatrocientos', 'quinientos', 'seiscientos', 'setecientos', 'ochocientos', 'novecientos')
denom = ( '', 'mil', 'millón', 'mil millones', 'billón', 'mil de billones',)
denom2 = ( '', 'miles','millones', 'miles de millones', 'billones', 'miles de billones',)
# convert a value < 100 to Spanish.
def _convert_nn(val):
    if val == 20:
        return tens[0]
    if val < 20:
        return to_29[val]

    if val % 10 == 0:
        return tens[(val//10)-2]

    return tens[(val // 10)-2] + ' y ' + to_29[val % 10]

# convert a value < 1000 to spanish, special cased because it is the level that kicks 
# off the < 100 special case.  The rest are more general.  This also allows you to
# get strings in the form of 'forty-five hundred' if called directly.
def _convert_nnn(val):
    if val < 100:
        return _convert_nn(val)
    if val < 200:
        return 'ciento '+_convert_nn(val-100)
    if val % 100 == 0:
        return hundreds[val // 100 - 1]

    return hundreds[val // 100 - 1]+' '+_convert_nn(val % 100)

def spanish_number(val):
    if val < 100:
        return _convert_nn(val)
    if val < 1000:
         return _convert_nnn(val)
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom))):
        if dval > val:
            mod = 1000 ** didx
            l = val // mod
            r = val - (l * mod)
            if l < 200:
                ret = _convert_nnn(l) + ' ' + denom[didx]
            else:
                ret = _convert_nnn(l) + ' ' + denom2[didx]
            if r > 0:
                ret = ret + ' ' + spanish_number(r)
            return ret

def amount_to_text(number, currency):
    number = '%.2f' % number
    units_name = currency
    list = str(number).split('.')
    start_word = spanish_number(int(list[0]))
    end_word = spanish_number(int(list[1]))
    cents_number = int(list[1])
    cents_name = (cents_number > 1) and 'centavos' or 'centavo'
    final_result = start_word +' '+units_name+' con ' + end_word +' '+cents_name
    return final_result


class report_box(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_box, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'convert':self.convert,
        })

    def convert(self, amount, cur):
        amt_words = amount_to_text(amount, cur or '')
        return amt_words.capitalize()
        
        
class ddata ():
    pass


class report_detailed_box(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_detailed_box, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'convert':self.convert,
            'get_data':self.get_data,
        })

    def convert(self, amount, cur):
        amt_words = amount_to_text(amount, cur or '')
        return amt_words.capitalize()
    
    def get_data (self, boxes):
        #It receives a list of boxes
        #It will make a selection from db of all included boxes.
        #It returns a list of rep (filled with res.partner browse record on data), 
        # linked with salesmen (filled with res.partner broswe record on data),
        # linked with lines containing so_number, picking_number, product_code, product_name, box_id, ordered_qty, delivered_qty, list_unit_price, unit_price, discount (%), subtotal
        #Rep and salesman have also totals on ordered_qty, delivered_qty and subtotal
        partner_obj = self.pool.get('res.partner')
        so_obj = self.pool.get('sale.order')
        
        self.cr.execute("""
            select 
                   p2.id as rep_id,
                   p2.name as rep_name,
                   p1.id as salesman_id, 
                   p1.name as salesman, 
                   sp.name as picking_number,
                   s.name as so_number,
                   s.id as so_id,
                   pr.id as product_id,
                   sl.product_uom as uom_id,
                   b.name as box_number, 
                   pr.default_code as product_code, 
                   pt.name as product_name, 
                   sl.product_uom_qty as ordered_qty, 
                   m.product_qty as delivered_qty, 
                   sl.price_unit as list_price, 
                   sl.price_unit, 
                   sl.discount
                from sale_order_line as sl
                inner join sale_order as s on sl.order_id = s.id 
                inner join stock_move as m on sl.id = m.sale_line_id
                inner join product_product as pr on sl.product_id = pr.id 
                inner join product_template as pt on pr.product_tmpl_id = pt.id 
                inner join res_partner as p1 on s.partner_id = p1.id
                inner join stock_picking as sp on m.picking_id = sp.id 
                inner join stock_box as b on sp.box_id = b.id 
                inner join res_partner as p2 on b.rep_id = p2.id 
                where b.id in %s
                order by p2.name, p1.name, b.name, pr.default_code
            """, (tuple([b.id for b in boxes]), ))
        
        res = self.cr.dictfetchall()
        current_rep = None
        current_salesman = None
        tsoq = 0.0
        tsdq = 0.0
        tss = 0.0
        troq = 0.0
        trdq = 0.0
        trs = 0.0
        result = []
        
        pl_data = {}
        so_data = {}
        
        for row in res:
            if (not current_rep) or current_rep.data.id != row['rep_id'] or current_salesman.data.id != row['salesman_id']:
                if current_salesman:
                    current_salesman.ordered_qty = tsoq
                    current_salesman.delivered_qty = tsdq
                    current_salesman.subtotal = tss
                    troq += tsoq
                    trdq += tsdq
                    trs += tss
                  
                tsoq = 0.0
                tsdq = 0.0
                tss = 0.0

                current_salesman = ddata()
                current_salesman.data = partner_obj.browse (self.cr, self.uid, row['salesman_id'])
                current_salesman.lines = []
                if current_rep and current_rep.data.id == row['rep_id']:
                    current_rep.salesmen.append(current_salesman)

            if (not current_rep) or current_rep.data.id != row['rep_id']:
                if current_rep:                    
                    current_rep.ordered_qty = troq
                    current_rep.delivered_qty = trdq
                    current_rep.subtotal = trs

                troq = 0.0
                trdq = 0.0
                trs = 0.0
                
                current_rep = ddata()
                current_rep.data = partner_obj.browse (self.cr, self.uid, row['rep_id'])
                current_rep.salesmen = []
                current_rep.salesmen.append(current_salesman)
                result.append(current_rep)

            if row['so_id'] not in so_data:
                so_data[row['so_id']] = so_obj.browse(self.cr, self.uid, row['so_id'])
            so = so_data[row['so_id']]
            if so.pricelist_id not in pl_data:
                pricelist = so.pricelist_id
                base_pricelist = pricelist
                for pv in pricelist.version_id:
                    for pvi in pv.items_id:
                        if pvi.base == -1:
                            base_pricelist = pvi.base_pricelist_id
                pl_data[so.pricelist_id] = base_pricelist

            base_price = pl_data[so.pricelist_id].price_get(
                            row['product_id'], row['delivered_qty'], partner=None, context={
                                'uom': row['uom_id'],
                                'date': so.date_order,
                            })[pl_data[so.pricelist_id].id]
            price_unit = base_price 
            discount = row['list_price'] and (row ['list_price'] - base_price) / row['list_price'] * 100.0 or 0.0
            price_subtotal = base_price * row ['delivered_qty']
                
            new_line = ddata()
            new_line.so_number = row ['so_number']
            new_line.picking_number = row ['picking_number']
            new_line.box_code = row ['box_number']
            new_line.product_code = row ['product_code']
            new_line.product_name = row ['product_name']
            new_line.ordered_qty = row ['ordered_qty']
            new_line.delivered_qty = row ['delivered_qty']
            new_line.list_unit_price = row ['list_price']
            new_line.unit_price = price_unit
            new_line.discount = discount
            new_line.subtotal = price_subtotal
            current_salesman.lines.append(new_line)

            tsoq += new_line.ordered_qty
            tsdq += new_line.delivered_qty
            tss += new_line.subtotal

        if current_salesman:
            current_salesman.ordered_qty = tsoq
            current_salesman.delivered_qty = tsdq
            current_salesman.subtotal = tss
            troq += tsoq
            trdq += tsdq
            trs += tss

        if current_rep:                    
            current_rep.ordered_qty = troq
            current_rep.delivered_qty = trdq
            current_rep.subtotal = trs

        return result

report_sxw.report_sxw(
    'report.uniqs_box_label.print',
    'stock.box',
    'addons/numa_uniqs_box/report/box_label.rml',
    parser=report_box,header="external"
)

report_sxw.report_sxw(
    'report.uniqs_box_form.print',
    'stock.box',
    'addons/numa_uniqs_box/report/box_form.rml',
    parser=report_box,header="external"
)

report_sxw.report_sxw(
    'report.uniqs_box_detailed.print',
    'stock.box',
    'addons/numa_uniqs_box/report/box_detailed.rml',
    parser=report_detailed_box,header="external"
)

if __name__=='__main__':
    from sys import argv
    
    lang = 'es'
    if len(argv) < 2:
        for i in range(1,200):
            print i, ">>", amount_to_text(i, lang)
        for i in range(200,999999,139):
            print i, ">>", amount_to_text(i, lang)
    else:
        print amount_to_text(int(argv[1]), lang)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
