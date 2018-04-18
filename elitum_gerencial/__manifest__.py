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
    "name": "Módulo Gerencial - Elitum",
    "version": "1.0",
    "author": "Ing. Harry Alvarez",
    "category": "Personalization",
    "depends": ['base',
                'report',
                'hr_payroll',
                'elitum_financiero',
                'elitum_rrhh',
                'elitum_compras',
                'elitum_inicio',
                'report_py3o', ],
    "website": "www.elitumerp.com",
    "description": """Módulo que contiene la configuración y personalización de la Gerencia""",
    "data": [
        'report/panel_control_gerencial.xml',
        'views/reportes.xml',
        'views/panel_control_view.xml',
        'views/gerencial_tablero.xml',
    ],
    "init_xml": [],
    "update_xml": [],
    "installable": True,
    "active": False,
}
