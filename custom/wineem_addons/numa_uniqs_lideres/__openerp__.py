# -*- coding: utf-8 -*-
##############################################################################
#
#    NUMA
#    Copyright (C) 2013 NUMA Extreme Systems (<http:www.numaes.com>).
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
        "name" : "WINEEM - Lideres for UNIQS",
        "version" : "1.0",
        "author" : "NUMA Extreme Systems",
        "website" : "www.numaes.com",
        "category" : "Vertical Modules/Parametrization",
        "description": """Wineem - Lideres""",
        "depends" : ["base", 
                     "product", 
                     "stock",
                     "sale",
                     "account_voucher",
                     "numa_uniqs_box",
                     "magentoerpconnect", 
                     #todo liricus
                     #"numa_uniqs_picking",
                     #"numa_uniqs_impresos",

                     ],
        "data" : [
            #todo Liricus
            #"security/security.xml", --> archivo vacio
            #"box_view.xml",          --> archivo vacio
            #"external.mappinglines.template.csv",
            "security/ir.model.access.csv",
            "stock_view.xml",
            "sale_view.xml",
            "partner_view.xml",
            "report.xml",
        ],
        "installable": True,
        "active": False,
} 
