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
    "name": "Módulo Inventario - Elitum",
    "version": "1.0",
    "author": "Ing. Harry Alvarez",
    "category": "Personalization",
    "depends": ['product', 'stock', 'hr_expense', 'board', 'purchase', 'account'],
    "website": "www.elitumerp.com",
    "description": """Módulo que contiene la configuración y personalización de Inventario""",
    "data": [
        'report/reporte_ingreso_bodega.xml',
        'report/reporte_egreso_bodega.xml',
        'report/reporte_transferencia_bodega.xml',
        'views/productos_view.xml',
        'views/inventario_tablero.xml',
        'views/stock_picking_view.xml',
        'views/stock_warehouse_view.xml',
        'views/delete.xml',
    ],
    "init_xml": [],
    "update_xml": [],
    "installable": True,
    "active": False,
}
