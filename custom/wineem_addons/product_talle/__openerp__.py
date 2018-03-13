# -*- encoding: utf-8 -*-
 
{
    "name": "Talle del producto",
    "version": "1.0",
    "description": """
        Permite agregar al formulario producto el campo talle
    """,
    "author": "Pablo Calvo",
    "website": "http://uniqs.com.ar",
    "category": "Tools",
    "depends": [
            "product",
            "base",#Este modulo para instalarse debe tener el modulo base y product instalado
                ],
    "data":[
            "product_talle_view.xml", #todos los archivos xml que posea nuestro modulo se debe de agregarse aqui
                ],
    "demo_xml": [
                        ],
    "update_xml": [
                        ],
    "active": False,
    "installable": True,
    "certificate" : "",
}
