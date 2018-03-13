# -*- coding: utf-8 -*-
##############################################################################
#
#    NUMA
#    Copyright (C) 2015 NUMA Extreme Systems (<http:www.numaes.com>).
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
import traceback

import pdb

class res_partner(osv.osv):
    _inherit = "res.partner"

    _columns = {
        'perception_iibb_cordoba': fields.boolean(u'Percepción IIBB Cordoba?'),    
    }

    def create(self, cr, uid, vals, context=None):
        vals = vals or {}
        if 'parent_id' in vals:
            parent = self.browse(cr, uid, vals['parent_id'], context=context)
            vals['perception_iibb_cordoba'] = vals.get('perception_iibb_cordoba', 
                                                       parent.perception_iibb_cordoba)
        return super(res_partner, self).create(cr, uid, vals, context=context)
        
    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]

        if 'perception_iibb_cordoba' in vals:
            for p in self.browse(cr, uid, ids, context=context):
                children_ids = self.search(cr, uid, [('parent_id','=',p.id)], context=context)
                if children_ids:
                    self.write(cr, uid, children_ids, {'perception_iibb_cordoba': vals['perception_iibb_cordoba']}, context=context)

        return super(res_partner, self).write(cr, uid, ids, vals, context=context)
            
res_partner()



