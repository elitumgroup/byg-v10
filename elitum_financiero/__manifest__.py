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
    "name": "Módulo de Finanzas - Elitum",
    "version": "1.0",
    "author": "Ing. Harry Alvarez",
    "category": "Personalization",
    "depends": ['account',
                'base',
                'elitum_contabilidad',
                'report',
                'report_py3o',
                'account_voucher'],
    "website": "www.elitumerp.com",
    "description": """Módulo que contiene la configuración y personalización de las Finanzas""",
    "data": [
        'data/secuencias.xml',
        'views/account_voucher_view.xml',
        'views/tax_withhold_view.xml',
        'views/facturas_view.xml',
        'views/caja_chica_view.xml',
        'report/reporte_retencion_venta.xml',
        'report/comprobante_ingreso.xml',
        'report/comprobante_egreso.xml',
        'report/reporte_vale_caja_chica.xml',
        'report/reporte_reposicion_caja_chica.xml',
        'report/reporte_pago_programado.xml',
        'report/reporte_cuentas_cobrar_completo.xml',
        'report/reporte_cuentas_pagar_completo.xml',
        'report/reporte_cheques_recibidos.xml',
        'report/reporte_cheques_emitidos.xml',
        'report_py3o/reportes_data.xml',
        'report_py3o/reportes.xml',
        'data/tablero.xml',
        'views/assets.xml',
        'views/finanzas_tablero.xml',
    ],
    "init_xml": [],
    "update_xml": [],
    "installable": True,
    "active": False,
}
