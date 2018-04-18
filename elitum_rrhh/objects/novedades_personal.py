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

import time
from datetime import datetime, timedelta
from dateutil import relativedelta

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError, except_orm
from odoo.tools.safe_eval import safe_eval


class HolidaysType(models.Model):
    _inherit = 'hr.holidays.status'

    description = fields.Char(u'Descripción')
    color = fields.Char(string="Color")


class LineEmployeeCategory(models.Model):
    _name = 'line.employee.category'

    _description = 'Linea de Empleados'

    employee_id = fields.Many2one('hr.employee', string="Empleado")
    etiqueta_empleado_id = fields.Many2one('hr.employee.category', string='Etiqueta de Empleado')


class EmployeeCategory(models.Model):
    _inherit = 'hr.employee.category'

    description = fields.Char(u'Descripción')
    line_employe_category = fields.One2many('line.employee.category', 'etiqueta_empleado_id', string="Empleados")


class LineaVacaciones(models.Model):
    _name = 'linea.vacaciones'

    _description = 'Linea de Vacaciones'

    tipo = fields.Selection([('empleado', 'Empleado'), ('categoria', 'Categoría')])
    empleado = fields.Many2one('hr.employee', string='Empleado')
    periodo = fields.Char()
    dias_vacaciones = fields.Integer()
    vacaciones_tomadas = fields.Integer()
    vacaciones_disponibles = fields.Integer()
    holiday_id = fields.Many2one('hr.holidays')


class Holidays(models.Model):
    _inherit = 'hr.holidays'

    def get_vacaciones_tomadas(self, empleado):
        tipo_ausencia = self.env['hr.holidays.status'].search([('name', '=', 'VAC')])[0]
        vacaciones = self.env['hr.holidays'].search([('holiday_status_id', '=', tipo_ausencia.id),
                                                     ('state', '=', 'validate')])
        dias_tomados = 0
        for vac in vacaciones:
            if vac.holiday_type == 'employee':
                if vac.employee_id == empleado:
                    dias_tomados += vac.number_of_days_temp
            else:
                for line in vac.category_id.line_employe_category:
                    if line.employee_id == empleado:
                        dias_tomados += vac.number_of_days_temp
        return dias_tomados

    @api.model
    def create(self, vals):
        # MARZ
        if len(vals['linea_vacaciones']) != 0: # Valide soló con VAC
            if vals['number_of_days_temp'] > TOTAL:
                raise UserError(_('Duración de Vacaciones mayores a las Por Gozar'))
        res = super(Holidays, self).create(vals)
        if res.holiday_type == 'employee':
            res.write({'nombre': res.employee_id.name})
        else:
            res.write({'nombre': res.category_id.name})
        return res

    @api.one
    def action_refuse(self):
        return self.write({'state': 'refuse'})

    def _check_state_access_right(self, vals):
        return True

    @api.multi
    def action_approve(self):
        return self.write({
            'usuario_aprobacion': self.env.user.id,
            'state': 'validate1'
        })

    @api.one
    def action_validate(self):
        if self.holiday_type == 'employee':
            self.employee_id.write(
                {'numero_ausencias': self.employee_id.numero_ausencias + self.number_of_days_temp})
        if self.holiday_type == 'category':
            for line in self.category_id.line_employe_category:
                line.employee_id.write(
                    {'numero_ausencias': self.employee_id.numero_ausencias + self.number_of_days_temp})

        return self.write({'state': 'validate'})

    @api.constrains('state', 'number+_of_days_temp')
    def _check_holidays(self):
        return True

    @api.onchange('holiday_status_id')
    def _onchange_holiday_status_id(self):
        self.name = self.holiday_status_id.description
        self.color_name = self.holiday_status_id.color_name
        if not self.holiday_status_id:
            self.vacaciones = False
        else:
            if self.holiday_status_id.name == 'VAC':
                self.vacaciones = True
            else:
                self.vacaciones = False

    @api.one
    def action_confirm(self):
        return self.write({
            'state': 'confirm'
        })

    @api.multi
    def name_get(self):
        res = []
        for leave in self:
            if leave.holiday_type == 'employee':
                res.append((leave.id, _("%s - %s") % (leave.employee_id.name, leave.holiday_status_id.name)))
            else:
                res.append((leave.id, _("%s - %s") % (leave.category_id.name, leave.holiday_status_id.name)))
        return res

    # MARZ
    @api.onchange('employee_id', 'holiday_status_id')
    def _onchange_employee_id(self):
        if self.holiday_status_id.name == 'VAC':
            empleado = self.employee_id
            if not empleado.fecha_ingreso:
                return
            linea_vacaciones = self.linea_vacaciones.browse([])
            data = []
            dias = 0
            fecha_actual = datetime.today().date()
            fecha_ingreso = datetime.strptime(empleado.fecha_ingreso, "%Y-%m-%d").date()
            anos = fecha_actual.year - fecha_ingreso.year
            if anos == 0:
                dias = int(float((datetime.combine(fecha_actual, datetime.min.time()) - datetime.combine(fecha_ingreso,
                                                                                                         datetime.min.time())).days) / float(
                    24))
                data = {'empleado': empleado.id,
                        'periodo': str(fecha_ingreso.year) + "-" + str(fecha_actual.year),
                        'dias_vacaciones': dias,
                        'vacaciones_tomadas': 0,
                        'vacaciones_disponibles': 0, }
                linea_vacaciones += linea_vacaciones.new(data)
            if anos >= 1:
                if anos == 1:
                    if fecha_actual < fecha_ingreso.replace(year=fecha_actual.year):
                        dias = int(float((datetime.combine(fecha_actual, datetime.min.time()) - datetime.combine(
                            fecha_ingreso, datetime.min.time())).days) / float(24))
                        data = {'empleado': empleado.id,
                                'periodo': str(fecha_ingreso.year) + "-" + str(fecha_actual.year),
                                'dias_vacaciones': dias,
                                'vacaciones_tomadas': 0,
                                'vacaciones_disponibles': 0, }
                        linea_vacaciones += linea_vacaciones.new(data)
                    else:
                        dias = 15
                        data = {'empleado': empleado.id,
                                'periodo': str(fecha_ingreso.year) + "-" + str(fecha_actual.year),
                                'dias_vacaciones': dias,
                                'vacaciones_tomadas': 0,
                                'vacaciones_disponibles': 0, }
                        linea_vacaciones += linea_vacaciones.new(data)

                        dias = int(float((datetime.combine(fecha_actual, datetime.min.time()) - datetime.combine(
                            fecha_ingreso.replace(year=fecha_actual.year), datetime.min.time())).days) / float(24))
                        data = {'empleado': empleado.id,
                                'periodo': str(fecha_actual.year) + "-" + str(fecha_actual.year + 1),
                                'dias_vacaciones': dias,
                                'vacaciones_tomadas': 0,
                                'vacaciones_disponibles': 0, }
                        linea_vacaciones += linea_vacaciones.new(data)
                if anos > 1:
                    for x in range(1, anos):
                        dias = 15
                        data = {'empleado': empleado.id,
                                'periodo': str(fecha_ingreso.year) + "-" + str(fecha_ingreso.year + x),
                                'dias_vacaciones': dias,
                                'vacaciones_tomadas': 0,
                                'vacaciones_disponibles': 0, }
                        linea_vacaciones += linea_vacaciones.new(data)

                    if fecha_actual < fecha_ingreso.replace(year=fecha_actual.year):
                        # MARZ
                        dias = int(float((datetime.combine(fecha_actual, datetime.min.time()) - datetime.combine(
                            fecha_ingreso.replace(year=fecha_actual.year - 1), datetime.min.time())).days) / float(24))
                        data = {'empleado': empleado.id,
                                'periodo': str(fecha_ingreso.year + 1) + "-" + str(fecha_actual.year),
                                'dias_vacaciones': dias,
                                'vacaciones_tomadas': 0,
                                'vacaciones_disponibles': 0, }
                        linea_vacaciones += linea_vacaciones.new(data)
                    else:
                        dias = 15
                        data = {'empleado': empleado.id,
                                'periodo': str(fecha_ingreso.year + 1) + "-" + str(fecha_actual.year),
                                'dias_vacaciones': dias,
                                'vacaciones_tomadas': 0,
                                'vacaciones_disponibles': 0, }
                        linea_vacaciones += linea_vacaciones.new(data)
                        dias = int(float((datetime.combine(fecha_actual, datetime.min.time()) - datetime.combine(
                            fecha_ingreso.replace(year=fecha_actual.year), datetime.min.time())).days) / float(24))
                        data = {'empleado': empleado.id,
                                'periodo': str(fecha_actual.year) + "-" + str(fecha_actual.year + 1),
                                'dias_vacaciones': dias,
                                'vacaciones_tomadas': 0,
                                'vacaciones_disponibles': 0, }
                        linea_vacaciones += linea_vacaciones.new(data)
            self.linea_vacaciones = linea_vacaciones
            vacaciones_tomadas = self.get_vacaciones_tomadas(empleado)
            for line in self.linea_vacaciones:
                if vacaciones_tomadas != 0:
                    # MARZ
                    if vacaciones_tomadas == line.dias_vacaciones:
                        line.update({'vacaciones_tomadas': vacaciones_tomadas,
                                     'vacaciones_disponibles': 0})
                        vacaciones_tomadas = 0
                        continue
                    if vacaciones_tomadas - line.dias_vacaciones > 0:
                        line.update({'vacaciones_tomadas': line.dias_vacaciones,
                                     'vacaciones_disponibles': 0})
                        vacaciones_tomadas = vacaciones_tomadas - line.dias_vacaciones
                        continue
                    if vacaciones_tomadas - line.dias_vacaciones < 0:
                        line.update({'vacaciones_tomadas': vacaciones_tomadas,
                                     'vacaciones_disponibles': abs(vacaciones_tomadas - line.dias_vacaciones)})
                        vacaciones_tomadas = 0
                        continue
                if vacaciones_tomadas == 0:
                    line.update({'vacaciones_tomadas': 0,
                                 'vacaciones_disponibles': line.dias_vacaciones})
            if vacaciones_tomadas != 0:
                self.linea_vacaciones[-1].update(
                    {'vacaciones_disponibles': self.linea_vacaciones[-1].vacaciones_disponibles - vacaciones_tomadas})

            global TOTAL
            TOTAL = 0.00
            for line in self.linea_vacaciones:
                TOTAL += line.vacaciones_disponibles

        return

    def print_solicitud(self):
        return self.env['report'].get_action(self, 'elitum_rrhh.reporte_solicitud_vacaciones')

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('cancel', 'Anulado'),
        ('confirm', 'Para Aprobación'),
        ('refuse', 'Negada'),
        ('validate1', 'Aprobada'),
        ('validate', 'Validada')
    ], string='Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
        help="The status is set to 'To Submit', when a holiday request is created." +
             "\nThe status is 'To Approve', when holiday request is confirmed by user." +
             "\nThe status is 'Refused', when holiday request is refused by manager." +
             "\nThe status is 'Approved', when holiday request is approved by manager.")

    nombre = fields.Char('Nombre')
    color_name = fields.Selection([
        ('red', 'Red'),
        ('blue', 'Blue'),
        ('lightgreen', 'Light Green'),
        ('lightblue', 'Light Blue'),
        ('lightyellow', 'Light Yellow'),
        ('magenta', 'Magenta'),
        ('lightcyan', 'Light Cyan'),
        ('black', 'Black'),
        ('lightpink', 'Light Pink'),
        ('brown', 'Brown'),
        ('violet', 'Violet'),
        ('lightcoral', 'Light Coral'),
        ('lightsalmon', 'Light Salmon'),
        ('lavender', 'Lavender'),
        ('wheat', 'Wheat'),
        ('ivory', 'Ivory')], default='lightblue')

    type = fields.Selection([
        ('remove', 'Leave Request'),
        ('add', 'Allocation Request')
    ], string='Request Type', required=True, readonly=True, index=True, default='remove',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help="Choose 'Leave Request' if someone wants to take an off-day. "
             "\nChoose 'Allocation Request' if you want to increase the number of leaves available for someone")
    linea_vacaciones = fields.One2many('linea.vacaciones', 'holiday_id', string=u'Líneas de Vacaciones')
    vacaciones = fields.Boolean(default=False)
    # MARZ
    usuario_aprobacion = fields.Many2one('res.users', u'Usuario Aprobación')
    document = fields.Binary('Documento Adjunto', attachment=True)
    document_name = fields.Char()