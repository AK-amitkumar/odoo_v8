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


{
        "name" : "Magento extensions for UNIQS",
        "version" : "1.0",
        "author" : "NUMA Extreme Systems",
        "website" : "www.numaes.com",
        "category" : "Vertical Modules/Parametrization",
        "description": """
        UNIQS Magento - Extensiones

        -   Actualización de partners en Magento:
            Se actualiza la cuenta contable del partner en función del grupo de Magento
            Se toman los vouchers de descuento de magento
            Se permite recalcular precios teniendo en cuenta los descuentos otorgados en Magento

        """,
        "depends" : ["base", 
                     "sale", 
                     "magentoerpconnect", 
                     "numa_uniqs_base", 
                     "numa_wineem_temporada"
                     ],
        "data" : [
            "sale_view.xml",
            "res_view.xml",
            #todo Liricus
            #"external.mappinglines.template.csv",
        ],
        "installable": True,
        "active": False,
} 
