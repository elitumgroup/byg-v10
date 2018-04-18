# -*- encoding: utf-8 -*-
#########################################################################
# Copyright (C) 2016 Ing. Harry Alvarez, Elitum Group                   #
#                                                                       #
#This program is free software: you can redistribute it and/or modify   #
#it under the terms of the GNU General Public License as published by   #
#the Free Software Foundation, either version 3 of the License, or      #
#(at your option) any later version.                                    #
#                                                                       #
#This program is distributed in the hope that it will be useful,        #
#but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
#GNU General Public License for more details.                           #
#                                                                       #
#You should have received a copy of the GNU General Public License      #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################

{
    "name": "Elitum Manager Eliterp",
    "version": "1.0",
    "author": "Ing. Harry Alvarez",
    "category": "Personalization",
    "depends": [
                'account',
                'base',
                'mail',
                'board'],
    "website": "www.elitumerp.com",
    "description": """Modulo que permite la configuracion General del Sistema Eliterp""",
    "data": [
        'views/tablero_manager.xml',
        'views/manager_view.xml',
        'data/secuencias.xml',
        'views/delete.xml',
    ],
    "init_xml": [],
    "update_xml": [],
    "installable": True,
    "active": False,
}