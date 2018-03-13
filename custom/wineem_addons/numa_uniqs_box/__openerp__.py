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
        "name" : "Special box handling for UNIQS",
        "version" : "1.0",
        "author" : "NUMA Extreme Systems",
        "website" : "www.numaes.com",
        "category" : "Vertical Modules/Parametrization",
        "description": """UNIQS Box""",
        "depends" : ["base", 
                     "product", 
                     "stock", 
                     "numa_uniqs_base", 
                     #"numa_uniqs_picking", 
                     "magentoerpconnect", 
                     "sale"],
        "init_xml" : [ ],
        "demo_xml" : [ ],
        "data" : [
            "security/box_security.xml",
            "security/ir.model.access.csv",
            "stock_view.xml", 
            "box_view.xml", 
            "box_sequences.xml",
            "box_report.xml", 
            "sale_view.xml",
        ],
        "installable": True,
        "active": False,
} 
