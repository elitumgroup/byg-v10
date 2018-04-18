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

class ReportePanelControlGerencial(models.AbstractModel):

    _name = 'report.elitum_gerencial.reporte_panel_control_gerencial'

    def get_reporte(self, doc):
        data=[]
        arg=[]
        arg.append(('fecha','>=',doc.fecha_inicio))
        arg.append(('fecha', '<=', doc.fecha_fin))
        if doc.estado!='todos':
            arg.append(('estado', '=', doc.estado))
        lines_panel_control = self.env['linea.proceso.panel.control'].search(arg)
        for line in lines_panel_control:
            data.append({'institucion': line.name_panel,
                         'imagen': line.imagen_panel,
                         'frecuencia': line.tipo_panel,
                         'obligacion': line.obligacion_panel,
                         'fecha': line.fecha,
                         'novedades': line.novedades,
                         'estado': line.estado,
                         })
        return data

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'gerencial.reporte.panel.control.gerencial',
            'docs': self.env['gerencial.reporte.panel.control.gerencial'].browse(docids),
            'data': data,
            'get_reporte':self.get_reporte,
        }
        return self.env['report'].render('elitum_gerencial.reporte_panel_control_gerencial', docargs)