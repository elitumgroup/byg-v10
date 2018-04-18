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
    "name": "Módulo Compras - Elitum",
    "version": "1.0",
    "author": "Ing. Harry Alvarez",
    "category": "Personalization",
    "depends": [
        'purchase_requisition',
        'purchase', 'mrp',
        'stock',
        'product',
        'board',
        'contacts',
        'stock_account',
        'elitum_ventas',
        'account',
        'report_py3o',
        'elitum_inicio'
    ],
    "website": "www.elitumerp.com",
    "description": """Módulo que contiene la configuración y personalización de las Compras""",
    "data": [
        'security/compras_security.xml',
        # 'security/ir.model.access.csv',
        'report/reporte_solicitud_compra.xml',
        'report/reporte_orden_compra.xml',
        'report/reporte_comparativo_cotizaciones_compras.xml',
        'report/report_solicitud_pago.xml',
        'report/reporte_solicitud_provision.xml',
        'report/reporte_provision_liquidate.xml',
        'report/reporte_compras.xml',
        'report/reporte_tipo_compra.xml',
        'report_py3o/reportes_data.xml',
        'report_py3o/reportes.xml',
        'data/secuencias.xml',
        'data/email_data.xml',
        'data/dashboard_data.xml',
        'views/proveedor_view.xml',
        'views/provision_view.xml',
        'views/requerimientos_view.xml',
        'views/requerimientos_secuencia.xml',
        'views/solicitud_compra_view.xml',
        'views/compras_tablero.xml',
        'views/delete_view.xml',
        'views/assets.xml',
    ],
    "init_xml": [],
    "update_xml": [],
    "installable": True,
    "active": False,
}
