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

class report_product_label_form(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_product_label_form, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
        })


report_sxw.report_sxw(
    'report.wineem_product_label',
    'product.product',
    'addons/numa_uniqs_impresos/report/product_label_form.rml',
    parser=report_product_label_form,header=False
)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
