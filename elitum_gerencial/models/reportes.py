# -*- encoding: utf-8 -*-
#########################################################################
# Copyright (C) 2017 Ing. Harry Alvarez, Elitum Group                   #
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

from collections import defaultdict
import pytz
from datetime import datetime, timedelta
from odoo import api, fields, models, _

class GerencialReportePanelControlGerencial(models.TransientModel):

    _name = 'gerencial.reporte.panel.control.gerencial'

    _description = "Reporte Gerencial"

    def imprimir_reporte_panel_control(self):
        return self.env['report'].get_action(self, 'elitum_gerencial.reporte_panel_control_gerencial')

    fecha_inicio = fields.Date('Fecha Inicio')
    fecha_fin = fields.Date('Fecha Fin')
    estado = fields.Selection([('todos', 'Todos'),
                               ('nuevo', 'Nuevo'),
                               ('en_proceso', 'En Proceso'),
                               ('realizado', 'Realizado'),
                               ('vencido', 'Vencido'),
                               ('anulado', 'Anulado')], "Estado", default='todos')