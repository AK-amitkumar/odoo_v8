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


class report_line ():
    def __init__ (self, number=None, customer=None, customer_vat_condition=None, customer_cuit=None, date=None, vat=None, untaxed=None, taxed=None):
        self.number = number or ''
        self.date = date or ''
        self.vat = vat or 0.0
        self.untaxed = untaxed or 0.0
        self.taxed = taxed or 0.0
        self.customer = customer or ''
        self.customer_cuit = customer_cuit or ''
        self.customer_vat_condition = customer_vat_condition

def convert_date (date):
    # todo Liricus esta mal el formato
    # year = date[6:10]
    # month = date[3:5]
    # day = date[0:2]
    year = date[0:4]
    month = date[5:7]
    day = date[8:10]
    return "%s-%s-%s" % (year, month, day)


class report_vat_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_vat_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'convert':self.convert,
            'get_lines': self.get_lines,
            'get_totals': self.get_totals,
        })
        self.totals = None

    def convert(self, amount, cur):
        amt_words = amount_to_text(amount, cur or '')
        return amt_words.capitalize()
        
    def get_lines (self, r):
        initial_date = convert_date(unicode(r.initial_date))
        final_date = convert_date(unicode(r.final_date))
        user_obj = self.pool.get('res.users')
        user = user_obj.browse(self.cr, self.uid, self.uid)
        self.cr.execute(
                "SELECT i.number as number, i.date_invoice as date, p.name, p.name, p.vat_condition, p.cuit_dni as cuit, "
                    "sum(il.price_unit*il.quantity*(1-il.discount/100)) as amount, i.type " \
                    "FROM account_invoice as i " \
                    "LEFT JOIN res_partner AS p ON i.partner_id = p.id " \
                    "INNER JOIN account_invoice_line AS il ON i.id = il.invoice_id "\
                    "WHERE i.date_invoice >= '%s' AND i.date_invoice <= '%s' AND "\
                    "      i.state in ('open','paid') AND "\
                    "      i.type in ('out_invoice','out_refund') AND "\
                    "      i.company_id = %s "\
                    "GROUP BY i.number, i.date_invoice, p.name, p.vat_condition, p.cuit_dni, i.type " \
                    "ORDER BY i.date_invoice" % (initial_date, final_date, user.company_id.id))

        res = []
        t_vat = 0.0
        t_untaxed = 0.0
        t_taxed = 0.0

        tr = {
            '01': 'IVA Resp.Inscripto',
            '02': 'IVA Resp. no Inscripto',
            '03': 'IVA no responsable',
            '05': 'Consumidor final',
            '06': 'Responsabe monotributo',
        }
        for r in self.cr.dictfetchall():    
            amount = r['type']=='out_invoice' and r['amount'] or -r['amount']
            line = report_line(
                        number=r['number'],
                        date=r['date'],
                        customer=r['name'],
                        customer_vat_condition= tr.get(r['vat_condition'], 'desconocido'),
                        customer_cuit=r['cuit'],
                        vat=amount/1.21 * 0.21,
                        untaxed=amount/1.21,
                        taxed=amount)
            res.append(line)
            t_vat += line.vat
            t_untaxed += line.untaxed
            t_taxed += line.vat + line.untaxed

        #pdb.set_trace()            
        grouped_res = []
        current_month = None
        current_year = None
        current_lines = []
        m_vat = 0.0
        m_untaxed = 0.0
        m_taxed = 0.0
        month_names = {
            '01': 'Enero',
            '02': 'Febrero',
            '03': 'Marzo',
            '04': 'Abril',
            '05': 'Mayo',
            '06': 'Junio',
            '07': 'Julio',
            '08': 'Agosto',
            '09': 'Septiembre',
            '10': 'Octubre',
            '11': 'Noviembre',
            '12': 'Diciembre'
        }
        for l in res:
            if current_month and \
               (current_year != l.date[0:4] or \
                current_month != l.date[5:7]):
                grouped_res.append({
                    'year': current_year,
                    'month': current_month,
                    'month_name': month_names[current_month],
                    'lines': current_lines,
                    'vat': m_vat,
                    'untaxed': m_untaxed,
                    'taxed': m_taxed,
                })
                current_month = None
            if not current_month:
                current_month = l.date[5:7]
                current_year = l.date[0:4]
                current_lines = []
                m_vat = 0.0
                m_untaxed = 0.0
                m_taxed = 0.0
            current_lines.append(l)
            m_vat += l.vat
            m_untaxed += l.untaxed
            m_taxed += l.vat + l.untaxed
        if current_month:
            grouped_res.append({
                'year': current_year,
                'month': current_month,
                'month_name': month_names[current_month],
                'lines': current_lines,
                'vat': m_vat,
                'untaxed': m_untaxed,
                'taxed': m_taxed,
            })

        self.totals = {
            'vat': t_vat,
            'untaxed': t_untaxed,
            'taxed': t_taxed,
        }
        
        return grouped_res
        
    def get_totals (self, r):
        res = {}
        
        if not self.totals:
            self.get_lines()
        
        return self.totals

report_sxw.report_sxw(
    'report.vat_report_print',
    'uniqs.iva_report_old',
    'addons/numa_uniqs_iva_temp/report/vat_report.rml',
    parser=report_vat_report,header="external"
)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
