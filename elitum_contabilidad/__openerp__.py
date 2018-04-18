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
    "name": "Módulo Contable - Elitum",
    "version": "1.0",
    "author": "Ing. Harry Alvarez",
    "category": "Personalization",
    "depends": [
        'base',
        'sale',
        'account',
        'stock',
        'payment',
        'purchase',
        'report',
        'base_setup',
        'l10n_ec',
        'report_py3o',
    ],
    "website": "www.elitumerp.com",
    "description": """Módulo que contiene la configuración y personalización de la Contabilidad""",
    "data": [
        'report/reporte_estado_financiero.xml',
        'report/reporte_estado_resultado.xml',
        'report/reporte_libro_mayor.xml',
        'report/reporte_provision_factura.xml',
        'report/reporte_factura_cliente.xml',
        'report/reporte_nota_debito_bancaria.xml',
        'report/reporte_nota_credito_bancaria.xml',
        'report/reporte_transferencia.xml',
        'report/reporte_deposito.xml',
        'report/reporte_comprobante_diario.xml',
        'report/concilacion_bancaria.xml',
        'report/reporte_cheque_matricial.xml',
        'report_py3o/reportes.xml',
        'report_py3o/reportes_data.xml',
        'views/reportes_financieros.xml',
        'views/reportes_wizard.xml',
        'views/assets.xml',
        'views/contabilidad_view.xml',
        'views/concilacion_bancaria_view.xml',
        'views/centro_costo_proyecto_view.xml',
        'views/impuestos_view.xml',
        'views/facturas_view.xml',
        'views/pagos_depositos_transferencias_view.xml',
        'views/cheques_view.xml',
        'views/notas_credito_debito_view.xml',
        'views/notas_facturas_view.xml',
        'views/sri_view.xml',
        'data/secuencias.xml',
        'views/contabilidad_tablero.xml',
        'views/delete.xml',
        'data/configuration_data.xml',
    ],
    "init_xml": [],
    "update_xml": [],
    "installable": True,
    "active": False,
}
