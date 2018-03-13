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


class report_invoice_form(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_invoice_form, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'convert':self.convert,
            'descespecial': self.desc_especial,
            'percepcionIIBB': self.percepcionIIBB,
            'pltotal': self.pl_total,
        })

    def convert(self, amount, cur):
        amt_words = amount_to_text(amount, cur or '')
        return amt_words.capitalize()

    def pl_total (self, invoice):
        tp = 0.0

        for line in invoice.invoice_line:
            tp += line.price_unit*0.75*line.quantity
        return tp
        
    def desc_especial(self, invoice):
        sp = 0.0
        
        for line in invoice.invoice_line:
            sp += line.price_unit*0.75*line.quantity
        return sp-invoice.amount_total+self.percepcionIIBB(invoice)

    def percepcionIIBB(self, invoice):
        iibb = 0.0
        
        for tax in invoice.tax_line:
            if tax.name.endswith('CBAPERIIBB'):
                iibb += tax.amount
        return iibb


report_sxw.report_sxw(
    'report.wineem_invoice_print',
    'account.invoice',
    'addons/numa_uniqs_impresos/report/invoice_form.rml',
    parser=report_invoice_form,header="external"
)

if __name__=='__main__':
    from sys import argv
    
    lang = 'nl'
    if len(argv) < 2:
        for i in range(1,200):
            print i, ">>", amount_to_text(i, lang)
        for i in range(200,999999,139):
            print i, ">>", amount_to_text(i, lang)
    else:
        print amount_to_text(int(argv[1]), lang)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
