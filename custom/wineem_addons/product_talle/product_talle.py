# -*- encoding: utf-8 -*-
 
#importamos la clase osv del modulo osv y fields
from openerp.osv import osv, fields
 
#Creamos una clase llamada product_product que hereda de la clase product_product padre que esta en /opt/openerp/server/openerp/addons/product
#En openobject hay varios tipos de herencia averiguar mas del tema
#Aqui las clases tienen un atributo _name que es el nombre de la tabla que existe o se creara cuando instalamos el modulo en postgresql
 
class product_product(osv.osv):
    _name = 'product.template' # Aqui va el mismo nombre de la clase que se hereda
    _inherit = 'product.template' # Permite la herencia propiamente dicho del modulo product 
 
    #Agregamos el campo talle al formulario producto o a la tabla product_product
    _columns = {
                'talle': fields.char('Talle',size=40),
        }
product_product()
