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

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp import netsvc

class afip (osv.osv):
    _name = "numa_ar_base.afip"

    _columns = {
        'rs_max_inv_wo_wt_rg': fields.float ('Product sales limit (products)', help='Maximun accumulated revenue for the simplified regimen (products), before witholding taxes', digits=(10,2)),
        'rs_max_inv_wo_wt_ser': fields.float ('Service sales limit (services)', help='Maximun accumulated revenue for the simplified regimen (products), before witholding taxes', digits=(10,2)),
        'rs_wt_iva': fields.float ('SR VAT retention', help='VAT retention to supplier exceeding the yearly revenue limit', digits=(2,2)),
        'rs_wt_gan': fields.float ('SR Rent retention', help='Rent retention to supplier exceeding the yearly revenue limit', digits=(2,2)),
        'b_inv_max_no_name': fields.float ('B invoice, max no name', help='For B type invoices, the maximun amount allowed without name and CUIT information', digits=(2,2)),

        'rg830_min': fields.float ('RG830/00, minimun ammount', help='Régimen general de retención de ganancias RG 830/00, minimun ammount', digits=(10,2)),
        'max_b_no_id': fields.float ('Max. amount no id', help='Maximun invoice amount, type B, without name and ID (CUIT/CUIL/DNI)'),

    }

    _defaults = {
        'rs_max_inv_wo_wt_rg': 200000.0,
        'rs_max_inv_wo_wt_ser': 300000.0,
        'rs_wt_iva': 21.0,
        'rs_wt_gan': 35.0,
        'b_inv_max_no_name': 1000.0,
        'rg830_min': 50.0,
        'max_b_no_id': 1000.0,    
    }

    def get_rs_max_inv_wo_wt_rg (self, cr, uid):
        #Assume there is only one record with valid info
        ids = self.search (cr, uid, [])
        if ids:
            a = self.browse (cr, uid, ids[0])
            return a.rs_max_inv_wo_wt_rg
        else:
            return 200000.0

    def get_rs_max_inv_wo_wt_ser (self, cr, uid):
        #Assume there is only one record with valid info
        ids = self.search (cr, uid, [])
        if ids:
            a = self.browse (cr, uid, ids[0])
            return a.rs_max_inv_wo_wt_ser
        else:
            return 300000.0

    def get_rs_wt_iva (self, cr, uid):
        #Assume there is only one record with valid info
        ids = self.search (cr, uid, [])
        if ids:
            a = self.browse (cr, uid, ids[0])
            return a.rs_wt_iva
        else:
            return 21.0

    def get_rs_wt_gan (self, cr, uid):
        #Assume there is only one record with valid info
        ids = self.search (cr, uid, [])
        if ids:
            a = self.browse (cr, uid, ids[0])
            return a.rs_wt_gan
        else:
            return 35.0

    def get_b_inv_max_no_name (self, cr, uid):
        #Assume there is only one record with valid info
        ids = self.search (cr, uid, [])
        if ids:
            a = self.browse (cr, uid, ids[0])
            return a.b_inv_max_no_name
        else:
            return 1000.0

    def get_rg830_min (self, cr, uid):
        #Assume there is only one record with valid info
        ids = self.search (cr, uid, [])
        if ids:
            a = self.browse (cr, uid, ids[0])
            return a.rg830_min
        else:
            return 50.0

    def get_max_b_no_id (self, cr, uid):
        #Assume there is only one record with valid info
        ids = self.search (cr, uid, [])
        if ids:
            a = self.browse (cr, uid, ids[0])
            return a.max_b_no_id
        else:
            return 1000.0

afip()

class rg830_rate (osv.osv):
    _name = "numa_ar_base.rg830_rate"
    _rec_name = 'codigo_de_regimen'

    _columns = {
        'codigo_de_regimen': fields.char('Codigo de regimen', size=10),
        'descripcion': fields.text('Descripcion', help="Conceptos sujetos a retención"),
        'use_tabla': fields.boolean('Usa tabla de escala?'),
        'inscriptos': fields.float ('Inscriptos', help="Porcentaje de retención a sujetos inscriptos", digits=(2,2)),
        'no_inscriptos': fields.float ('No inscriptos', help="Porcentaje de retención a sujetos no inscriptos", digits=(2,2)),
        'monto_no_sujeto': fields.float ('Monto no sujeto a retencion', digits=(10,2)),
    }

    def get_tax (self, cr, uid, code, base, inscripto=True):
        rg830_table_obj = self.pool.get("numa_ar_base.rg830_table")
        rates_ids = self.search (cr, uid, [('codigo_de_regimen','=',code)])
        if rates_ids:
            rates = self.browse (cr, uid, rates_ids[0])
            if rates.use_tabla:
                table_ids = rg830_table_obj.search (cr, uid, [('desde','>=',base)])
                if table_ids:
                    if len(table_ids) > 1:
                        for table_t in rg830_table_obj.browse (cr, uid, table_ids):
                            table = table_t
                            if table_t.hasta == 0 or table_t.hasta <= base:
                                break
                    else:
                        table = rg830_table_obj.browse (cr, uid, table_ids[0])
                return table.monto + ((base - table.no_imponible) * table_tasa / 100.0)                                                      
            else:
                return (base - rates.monto_no_sujeto) * (inscripto and rates.inscriptos or rates.no_inscriptos) / 100.0
        return 0.0
        
rg830_rate()

class rg830_table (osv.osv):
    _name = "numa_ar_base.rg830_table"

    _columns = {
        'desde' : fields.float ('Desde', digits=(10,2)),
        'hasta' : fields.float ('Hasta', digits=(10,2)),
        'monto' : fields.float ('Monto fijo', digits=(10,2)),
        'tasa' : fields.float ('Alicuota', digits=(10,2)),
        'no_imponible' : fields.float ('Monto no imponible', digits=(10,2)),
    }

rg830_table()

class afip_sales_point (osv.osv):
    _name = "numa_ar_base.afip_sales_point"

    def _get_afip_invoicing_type (self, cr, uid, context=None):
        return self.get_afip_invoicing_type(cr, uid, context=context)

    _columns = {
        'name': fields.char('Description', size=50, select=True, required=True, help='Sales point description'),
        'afip_id': fields.integer('AFIP sales point id', required=True),
        'afip_invoicing_type': fields.selection(_get_afip_invoicing_type, "Invoicing type", required=True),
        'company_id': fields.many2one('res.company', 'Company'),

        # Next number for all 'tipo_comprobante'
        'separate_sequences': fields.boolean('Use separate sequences?'),

        'a_next_number': fields.float('Next A invoice/debit note/credit note', required=True, digits=(8,0)),
        'a_i_next_number': fields.float('Next A invoice note', required=True, digits=(8,0)),
        'a_dn_next_number': fields.float('Next A debit note', required=True, digits=(8,0)),
        'a_cn_next_number': fields.float('Next A credit note', required=True, digits=(8,0)),
        'b_next_number': fields.float('Next B invoice/debit note/credit note', required=True, digits=(8,0)),
        'b_i_next_number': fields.float('Next B invoice note', required=True, digits=(8,0)),
        'b_dn_next_number': fields.float('Next B debit note', required=True, digits=(8,0)),
        'b_cn_next_number': fields.float('Next B credit note', required=True, digits=(8,0)),
        'c_next_number': fields.float('Next C invoice/debit note/credit note', required=True, digits=(8,0)),
        'c_i_next_number': fields.float('Next C invoice note', required=True, digits=(8,0)),
        'c_dn_next_number': fields.float('Next C debit note', required=True, digits=(8,0)),
        'c_cn_next_number': fields.float('Next C credit note', required=True, digits=(8,0)),
        'e_next_number': fields.float('Next E invoice/debit note/credit note', required=True, digits=(8,0)),
        'e_i_next_number': fields.float('Next E invoice note', required=True, digits=(8,0)),
        'e_dn_next_number': fields.float('Next E debit note', required=True, digits=(8,0)),
        'e_cn_next_number': fields.float('Next E credit note', required=True, digits=(8,0)),

        'a_dup': fields.boolean('A docs duplicates?'),
        'b_dup': fields.boolean('B docs duplicates?'),
        'c_dup': fields.boolean('C docs duplicates?'),
        'e_dup': fields.boolean('E docs duplicates?'),

        'a_i_printer': fields.many2one('printing.printer', 'Printer for A invoices'),
        'a_dn_printer': fields.many2one('printing.printer', 'Printer for A debit notes'),
        'a_cn_printer': fields.many2one('printing.printer', 'Printer for A credit notes'),
        'b_i_printer': fields.many2one('printing.printer', 'Printer for B invoices'),
        'b_dn_printer': fields.many2one('printing.printer', 'Printer for B debit notes'),
        'b_cn_printer': fields.many2one('printing.printer', 'Printer for B credit notes'),
        'c_i_printer': fields.many2one('printing.printer', 'Printer for C invoices'),
        'c_dn_printer': fields.many2one('printing.printer', 'Printer for C debit notes'),
        'c_cn_printer': fields.many2one('printing.printer', 'Printer for C credit notes'),
        'e_i_printer': fields.many2one('printing.printer', 'Printer for E invoices'),
        'e_dn_printer': fields.many2one('printing.printer', 'Printer for E debit notes'),
        'e_cn_printer': fields.many2one('printing.printer', 'Printer for E credit notes'),
   }

    _defaults= {
        'afip_id': 1,
        'afip_invoicing_type': 'pf',
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.account', context=c),

        'separate_sequences': False,
        'a_next_number': 1,
        'a_i_next_number': 1,
        'a_dn_next_number': 1,
        'a_cn_next_number': 1,
        'b_next_number': 1,
        'b_i_next_number': 1,
        'b_dn_next_number': 1,
        'b_cn_next_number': 1,
        'c_next_number': 1,
        'c_i_next_number': 1,
        'c_dn_next_number': 1,
        'c_cn_next_number': 1,
        'e_next_number': 1,
        'e_i_next_number': 1,
        'e_dn_next_number': 1,
        'e_cn_next_number': 1,
    }
    
    def get_afip_invoicing_type (self, cr, uid, context=None):
        if not context: context = {}
        return [('pf', 'Preprinted forms')]

    def next_number(self, cr, uid, ids, afip_invoice_type, context=None):
        assert ids and len(ids), 'One at the time'
        
        sp = self.browse(cr, uid, ids[0], context=context)
        selector = {
            '001': ('a_i_next_number', 'a_next_number'),
            '002': ('a_dn_next_number', 'a_next_number'),
            '003': ('a_cn_next_number', 'a_next_number'),
            '006': ('b_i_next_number', 'b_next_number'),
            '007': ('b_dn_next_number', 'b_next_number'),
            '008': ('b_cn_next_number', 'b_next_number'),
            '011': ('c_i_next_number', 'c_next_number'),
            '012': ('c_dn_next_number', 'c_next_number'),
            '013': ('c_cn_next_number', 'c_next_number'),
            '019': ('e_i_next_number', 'e_next_number'),
            '020': ('e_dn_next_number', 'e_next_number'),
            '021': ('e_cn_next_number', 'e_next_number'),
            '090': ('c_i_next_number', 'c_next_number'),
            '091': ('c_cn_next_number', 'c_next_number'),
        }
        separate_counter, unique_counter = selector.get(afip_invoice_type, ('c_i_next_number', 'c_next_number'))        
        if sp.separate_sequences:
            ret = sp[separate_counter]
            sp.write({separate_counter: ret+1})
        else:
            ret = sp[unique_counter]
            sp.write({unique_counter: ret+1})

        return ret
        
    def get_printer(self, cr, uid, ids, afip_invoice_type, context=None):
        assert ids and len(ids)==1, 'One at the time'
        
        selector = {
            '001': 'a_i_printer',
            '002': 'a_dn_printer',
            '003': 'a_cn_printer',
            '006': 'b_i_printer',
            '007': 'b_dn_printer',
            '008': 'b_cn_printer',
            '011': 'c_i_printer',
            '012': 'c_dn_printer',
            '013': 'c_cn_printer',
            '019': 'e_i_printer',
            '020': 'e_dn_printer',
            '021': 'e_cn_printer',
            '090': 'c_i_printer',
            '091': 'c_cn_printer',
        }

        sp = self.browse(cr, uid, ids[0], context=context)
        printer = selector.get(afip_invoice_type, 'c_i_printer')
        return sp[printer]

    def is_dup(self, cr, uid, ids, afip_invoice_type, context=None):
        assert ids and len(ids)==1, 'One at the time'
        
        selector = {
            '001': 'a_dup',
            '002': 'a_dup',
            '003': 'a_dup',
            '006': 'b_dup',
            '007': 'b_dup',
            '008': 'b_dup',
            '011': 'c_dup',
            '012': 'c_dup',
            '013': 'c_dup',
            '019': 'e_dup',
            '020': 'e_dup',
            '021': 'e_dup',
            '090': 'c_dup',
            '091': 'c_dup',
        }

        sp = self.browse(cr, uid, ids[0], context=context)
        dup_field = selector.get(afip_invoice_type, 'c_dup')
        return sp[dup_field]
        
afip_sales_point()

class afip_store_point (osv.osv):
    _name = "numa_ar_base.afip_store_point"
    _columns = {
        'name': fields.char('Description', size=50, select=True, required=True, help='Store point description'),
        'afip_id': fields.integer('AFIP store id', required=True),
        'company_id': fields.many2one('res.company', 'Company'),

        # Next number for all 'tipo_comprobante'
        'r_next_number': fields.float('Next move document number', required=True, digits=(8,0)),

        'r_printer': fields.many2one('printing.printer', 'Printer for Out Pickings'),

        'r_copies': fields.integer('Number of copies'),
    }

    _defaults= {
        'afip_id': 1,
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.account', context=c),

        'r_next_number': 1,
        'r_copies': 3,
        
    }

    def next_number(self, cr, uid, ids, context=None):
        assert ids and len(ids), 'One at the time'
        
        sp = self.browse(cr, uid, ids[0], context=context)
        ret = sp.r_next_number
        sp.write({'r_next_number': ret+1})
        return ret
        
    def get_printer(self, cr, uid, ids, context=None):
        assert ids and len(ids)==1, 'One at the time'
        
        sp = self.browse(cr, uid, ids[0], context=context)
        return sp.r_printer

    def get_copies(self, cr, uid, ids, context=None):
        assert ids and len(ids)==1, 'One at the time'

        sp = self.browse(cr, uid, ids[0], context=context)
        return sp.r_copies

afip_store_point()

class afip_document_type(osv.osv):
    _name = 'afip.document_type'
    _description = 'AFIP document types'
    _columns = {
        'name': fields.char('Name', size=120, required=True),
        'code': fields.char('Code', size=16, required=True),
        'afip_code': fields.integer('AFIP Code', required=True),
        'active': fields.boolean('Active'),
    }
afip_document_type()

class afip_tax_code(osv.osv):
    _inherit = 'account.tax.code'

    def _get_parent_afip_code(self, cr, uid, ids,
                              field_name, args, context=None):
        r = {}

        for tc in self.read(cr, uid, ids, ['afip_code', 'parent_id'],
                            context=context):
            _id = tc['id']
            if tc['afip_code']:
                r[_id] = tc['afip_code']
            elif tc['parent_id']:
                p_id = tc['parent_id'][0]
                r[_id] = self._get_parent_afip_code(cr, uid, [p_id],
                                                    None, None)[p_id]
            else:
                r[_id] = 0

        return r

    _columns = {
        'afip_code': fields.integer('AFIP Code'),
        'parent_afip_code': fields.function(_get_parent_afip_code,
                                            type='integer', method=True,
                                            string='Parent AFIP Code',
                                            readonly=1),
    }

    def get_afip_name(self, cr, uid, ids, context=None):
        r = {}

        for tc in self.browse(cr, uid, ids, context=context):
            if tc.afip_code:
                r[tc.id] = tc.name
            elif tc.parent_id:
                r[tc.id] = tc.parent_id.get_afip_name()[tc.parent_id.id]
            else:
                r[tc.id] = False

        return r

afip_tax_code()


class afip_optional_type(osv.osv):
    _name = 'afip.optional_type'
    _description = 'AFIP optional types'
    _columns = {
        'name': fields.char('Name', size=120, required=True),
        'afip_code': fields.integer('AFIP Code', required=True),
        'apply_rule': fields.char('Apply rule', size=64),
        'value_computation': fields.char('Value computation', size=64),
        'active': fields.boolean('Active'),
    }
afip_optional_type()

class res_currency(osv.osv):
    _inherit = "res.currency"
    _description = "Currency"

    _columns = {
        'afip_code': fields.char('AFIP Code', size=4, readonly=True),
        'afip_desc': fields.char('AFIP Description', size=250, readonly=True),
        'afip_dt_from': fields.date('AFIP Valid from', readonly=True),
    }

res_currency()

class afip_country(osv.osv):
    _inherit = 'res.country'

    _name = 'res.country'

    _columns = {
        'cuit_fisica': fields.char('CUIT persona fisica', size=11),
        'cuit_juridica': fields.char('CUIT persona juridica', size=11),
        'cuit_otro': fields.char('CUIT otro', size=11),
    }
afip_country()

