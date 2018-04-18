# -*- encoding: utf-8 -*-
#########################################################################
# Copyright (C) 2016 Ing. Harry Alvarez, Elitum Group                   #
#                                                                       #
# This program is free software: you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by   #
# the Free Software Foundation, either version 3 of the License, or      #
# (at your option) any later version.                                    #
#                                                                       #
# This program is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of         #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
# GNU General Public License for more details.                           #
#                                                                       #
# You should have received a copy of the GNU General Public License      #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################

{
    "name": "Módulo Ventas - Elitum",
    "version": "1.0",
    "author": "Ing. Harry Alvarez",
    "category": "Personalization",
    "depends": [
        'base',
        'sale',
        'account',
        'payment',
        'hr',
        'mail',
        'mrp',
        'sale_stock',
        'project',
        'crm',
        'purchase',
        'web_kanban',
        'base_setup',
        'report',
        'board'],
    "website": "www.elitumerp.com",
    "description": """Módulo que contiene la configuración y personalización de las Ventas""",
    "data": [
        'security/ventas_security.xml',
        # 'security/ir.model.access.csv',
        'views/gestion_view.xml',
        'views/cotizacion_view.xml',
        'views/clientes_view.xml',
        'views/equipo_ventas_view.xml',
        'views/secuencias_sale_order.xml',
        'views/facturas_view.xml',
        'views/comisiones_view.xml',
        'report/reporte_cotizacion.xml',
        'report/reporte_ventas.xml',
        'report_py3o/reportes_data.xml',
        'report_py3o/reportes.xml',
        'views/ventas_tablero.xml',
        'data/tablero.xml',
        'data/email_data.xml',
        'views/assets.xml',
        'views/delete_view.xml',
    ],
    "init_xml": [],
    "update_xml": [],
    "installable": True,
    "active": False,
}
