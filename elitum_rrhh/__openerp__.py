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
    "name": "Módulo RRHH - Elitum",
    "version": "1.0",
    "author": "Ing. Harry Alvarez",
    "category": "Personalization",
    "depends": [
        'base',
        'board',
        'hr',
        'hr_contract',
        'sale_timesheet',
        'hr_holidays',
        'hr_payroll',
        'hr_payroll_account',
        'hr_attendance',
        'hr_timesheet',
        'resource',
        'web_kanban',
        'report_py3o',
    ],
    "website": "www.elitumerp.com",
    "description": """Módulo que contiene la configuración y personalización de RRHH""",
    "data": [
        'security/rrhh_security.xml',
        'data/secuencias.xml',
        'data/dashboard_data.xml',
        'views/rrhh_view.xml',
        'views/nivel_aprobacion_view.xml',
        'views/empleado_view.xml',
        'views/contrato_view.xml',
        'views/contrato_view.xml',
        'views/nomina_roles_view.xml',
        'views/novedades_view.xml',
        'views/finiquito_view.xml',
        'report/reporte_anticipo_quincena.xml',
        'report/reporte_rol_consolidado.xml',
        'report/reporte_rol_pago.xml',
        'report/reporte_empleados.xml',
        'report/reporte_ausencias.xml',
        'report/reporte_vacaciones_personal.xml',
        'report/reporte_solicitud_vacaciones.xml',
        'report_py3o/reportes.xml',
        'report_py3o/reportes_data.xml',
        'views/rrhh_tablero.xml',
        'views/assets.xml',
        'views/delete.xml',
        'data/configuration_data.xml'
    ],
    "init_xml": [],
    "update_xml": [],
    "installable": True,
    "active": False,
}
