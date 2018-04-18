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

from odoo import api, fields, models, _
import pytz
import datetime

class ReporteCotizacion(models.AbstractModel):
    _name = 'report.elitum_ventas.reporte_cotizacion'

    def sorted_name(self, linea):
        split = linea.name.split(']')
        return split[1]

    def convert_integer(self, cantidad):
        return int(cantidad)

    def get_total_line(self, precio, cantidad):
        numero = round((precio * cantidad), 2)
        return format(numero,',.2f')

    def two_decimal(self, cantidad):
        numero = round(float(cantidad),2)
        return format(numero,',.2f')

    def get_fecha_actual(self):
        return datetime.now(pytz.timezone("America/Guayaquil")).strftime("%Y-%m-%d %H:%M:%S")

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': self.env['sale.order'].browse(docids),
            'data': data,
            'get_total_line': self.get_total_line,
            'two_decimal': self.two_decimal,
            'sorted_name': self.sorted_name,
            'convert_integer': self.convert_integer,
            'get_fecha_actual': self.get_fecha_actual,
        }
        return self.env['report'].render('elitum_ventas.reporte_cotizacion', docargs)

# MARZ
class ReporteVentas(models.AbstractModel):
    _name = 'report.elitum_ventas.reporte_ventas_pdf'

    def get_mensaje(self, tipo):
        if not tipo:
            return 'Todos'
        else:
            return tipo.name

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'reporte.ventas',
            'docs': self.env['reporte.ventas'].browse(docids),
            'data': data,
            'fecha_actual': fields.date.today(),
            'get_mensaje': self.get_mensaje,
            'get_lines': self.env['reporte.ventas'].get_lines,
        }
        return self.env['report'].render('elitum_ventas.reporte_ventas_pdf', docargs)
