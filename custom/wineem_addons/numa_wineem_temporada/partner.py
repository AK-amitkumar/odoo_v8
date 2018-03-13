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

from openerp.osv import osv, fields


class closing (osv.osv):
    _name = 'res.partner.closing'

    _columns = {
        'name': fields.char ('Commercial closing', size=64, required=True),
        'description': fields.text ('Description'),
        'id_magento': fields.char('id_magento', size=64, required=True),
    }
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Closing reference must be unique!'),
    ]
    _order = 'name asc'
    
closing()

class partner (osv.osv):
    _inherit = "res.partner"

    def _get_effective_closing (self, cr, uid, ids, field, args, context=None):
        res = {}
        for p in self.read (cr, uid, ids, ['id', 'parent_id','commercial_closing'], context=context):
            if p['commercial_closing']:
                res[p['id']] = p['commercial_closing'][0]
            else:
                res[p['id']] = p['parent_id'] and self.browse(cr, uid, p['parent_id'][0]).effective_closing.id or False
        return res

    def _get_children (self, cr, uid, ids, context=None):
        result = set()
        for parent in self.browse(cr, uid, ids, context=context):
            result.add(parent.id)
            for child in parent.salesmen_ids:
                result.add(child.id)
        return list(result)
    
    _columns = {
        'parent_id': fields.many2one ('res.partner', 'Parent'),
        'salesmen_ids': fields.one2many ('res.partner', 'parent_id', 'Salesmen'),

        'commercial_closing': fields.many2one ('res.partner.closing', 'Commercial closing'),
        'effective_closing': fields.function (_get_effective_closing, method=True, type="many2one", obj='res.partner.closing', string='Effective closing', readonly=True,
                                              store = {
                                                    'res.partner': (_get_children, ['commercial_closing'], 10),
                                              }),
    }
    
    def onchange_commercial_closing (self, cr, uid, ids, commercial_closing, parent_id, context=None):
        values = {}
        
        if commercial_closing:
            values = {'effective_closing': commercial_closing}
        else:
            if parent_id:
                parent = self.browse (cr, uid, parent_id, context=context)
                values = {'effective_closing': parent.effective_closing.id}
            else:
                values = {'effective_closing': False}
                
        return {'value': values}

partner()
