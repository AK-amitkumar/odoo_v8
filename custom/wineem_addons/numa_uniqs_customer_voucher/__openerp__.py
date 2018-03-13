# -*- encoding: utf-8 -*-
#################################################################################
#
#    Copyright (C) 2011  NUMA Extreme Systems
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################

{
    'name': 'Argentina: Basic country data and adaptations by NUMA',
    'description': '''
Argentinean Localization
Simplified customer receipt and reconcile

''',
    'category': 'Localization',
    'author': 'NUMA Extreme System',
    'website': 'http://www.numaes.com',
    'version': '6.0.4',
    'depends': ['base', 'account', 'numa_uniqs_base', 'numa_uniqs_account_extension'],
    'init_xml': [],
    'update_xml': [
        'security/ar_base_security.xml',
        'security/ir.model.access.csv',
        'document_receipt_view.xml',
        'report/document_receipt.xml',
        'customer_reconcile_view.xml',
        'quick_move_view.xml',
    ],
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
