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

from odoo import api, fields, models, _
import time
from datetime import datetime, timedelta


class ReporteRolPago(models.AbstractModel):
    _name = 'report.elitum_rrhh.reporte_rol_pago'

    def get_mes(self, mes):
        if mes == 1:
            return 'Enero'
        if mes == 2:
            return 'Febrero'
        if mes == 3:
            return 'Marzo'
        if mes == 4:
            return 'Abril'
        if mes == 5:
            return 'Mayo'
        if mes == 6:
            return 'Junio'
        if mes == 7:
            return 'Julio'
        if mes == 8:
            return 'Agosto'
        if mes == 9:
            return 'Septiembre'
        if mes == 10:
            return 'Octubre'
        if mes == 11:
            return 'Noviembre'
        if mes == 12:
            return 'Diciembre'

    def get_periodo_pago(self, fecha):
        return self.get_mes(datetime.strptime(fecha, "%Y-%m-%d").month)

    def get_total_egresos(self, object):
        total = sum(line.amount for line in object.input_line_ids_2)
        return format(total, ',.2f')

    def get_total_ingresos(self, object):
        total = sum(line.amount for line in object.input_line_ids)
        return format(total, ',.2f')

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'hr.payslip',
            'docs': self.env['hr.payslip'].browse(docids),
            'data': data,
            'get_periodo_pago': self.get_periodo_pago,
            'get_total_ingresos': self.get_total_ingresos,
            'get_total_egresos': self.get_total_egresos,
        }
        return self.env['report'].render('elitum_rrhh.reporte_rol_pago', docargs)


class ReporteRolConsolidado(models.AbstractModel):
    _name = 'report.elitum_rrhh.reporte_rol_consolidado'

    def get_mes(self, mes):
        if mes == 1:
            return 'Enero'
        if mes == 2:
            return 'Febrero'
        if mes == 3:
            return 'Marzo'
        if mes == 4:
            return 'Abril'
        if mes == 5:
            return 'Mayo'
        if mes == 6:
            return 'Junio'
        if mes == 7:
            return 'Julio'
        if mes == 8:
            return 'Agosto'
        if mes == 9:
            return 'Septiembre'
        if mes == 10:
            return 'Octubre'
        if mes == 11:
            return 'Noviembre'
        if mes == 12:
            return 'Diciembre'

    def get_total(self, object):
        total = sum(line.neto_recibir for line in object.input_line_hr_run)
        return format(total, ',.2f')

    def get_periodo(self, fecha):
        return self.get_mes(datetime.strptime(fecha, "%Y-%m-%d").month)

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'hr.payslip.run',
            'docs': self.env['hr.payslip.run'].browse(docids),
            'data': data,
            'get_total': self.get_total,
            'get_periodo': self.get_periodo,
        }
        return self.env['report'].render('elitum_rrhh.reporte_rol_consolidado', docargs)


# MARZ
class ReporteEmpleados(models.AbstractModel):
    _name = 'report.elitum_rrhh.reporte_empleados_pdf'

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'reporte.empleados',
            'docs': self.env['reporte.empleados'].browse(docids),
            'data': data,
            'fecha_actual': fields.date.today(),
            'get_lines': self.env['reporte.empleados'].get_lines,
        }
        return self.env['report'].render('elitum_rrhh.reporte_empleados_pdf', docargs)


class ReporteAusencias(models.AbstractModel):
    _name = 'report.elitum_rrhh.reporte_ausencias_pdf'

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'reporte.ausencias',
            'docs': self.env['reporte.ausencias'].browse(docids),
            'data': data,
            'get_lines': self.env['reporte.ausencias'].get_lines,
        }
        return self.env['report'].render('elitum_rrhh.reporte_ausencias_pdf', docargs)


class ReporteVacacionesPersonal(models.AbstractModel):
    _name = 'report.elitum_rrhh.reporte_vacaciones_personal_pdf'

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'reporte.vacaciones.personal',
            'docs': self.env['reporte.vacaciones.personal'].browse(docids),
            'data': data,
            'get_lines': self.env['reporte.vacaciones.personal'].get_lines,
        }
        return self.env['report'].render('elitum_rrhh.reporte_vacaciones_personal_pdf', docargs)


class ReporteSolicitudVacaciones(models.AbstractModel):
    _name = 'report.elitum_rrhh.reporte_solicitud_vacaciones'

    def get_period_vacaciones(self, doc):
        data = []
        for line in doc.linea_vacaciones:
            if line.dias_vacaciones != 0 or line.vacaciones_disponibles != 0:
                data.append({
                    'period': line.periodo,
                    'disponibles': int(line.vacaciones_disponibles),
                    'solicitados': int(doc.number_of_days_temp),
                    'saldo': int(line.vacaciones_disponibles - doc.number_of_days_temp)
                })
        return data

    def get_format_date(self, fecha):
        '''Convierte String a Fecha'''
        object_datetime = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S")
        return object_datetime.date().strftime("%d/%m/%Y")

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'hr.holidays',
            'docs': self.env['hr.holidays'].browse(docids),
            'data': data,
            'fecha_actual': fields.date.today().strftime("%d/%m/%Y"),
            'get_format_date': self.get_format_date,
            'get_period_vacaciones': self.get_period_vacaciones,
        }
        return self.env['report'].render('elitum_rrhh.reporte_solicitud_vacaciones', docargs)
