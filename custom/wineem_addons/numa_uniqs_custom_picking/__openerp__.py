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


{
        "name" : "Custom Logistic for UNIQS",
        "version" : "1.0",
        "author" : "NUMA Extreme Systems, Alexander Rodriguez <adrt271988@gmail.com>",
        "website" : "www.numaes.com",
        "category" : "Stock",
        "description": """UNIQS Picking""",
        "depends" : ["numa_uniqs_lideres"],
        'application': True,
        'data':[
                'data/sequence.xml',
                'report/report_picking_order.xml',
                'report/report_picking_list.xml',
                'report/stock_report.xml',
                'wizard/stock_picking_order_confirm_wizard.xml',
                'views/stock_picking_order_view.xml',
                'views/resources.xml',
        ],
        "installable": True,
        "active": True,
} 
