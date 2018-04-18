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
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta


class hr_contract_funciones_lines(models.Model):
    _name = "hr.contract.funciones.lines"

    _description = 'Funciones del Contrato'

    name = fields.Char('Nombre', required=True)
    hr_contract_funciones_id = fields.Many2one('hr.contract.funciones')
    prioridad = fields.Selection([
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta')
    ], string='Prioridad', default='baja')


class hr_contract_funciones(models.Model):
    _name = "hr.contract.funciones"

    _description = 'Funciones'

    name = fields.Char('Funciones')
    hr_contract_funciones_lines = fields.One2many('hr.contract.funciones.lines', 'hr_contract_funciones_id',
                                                  u'Línea de Funciones')
    hr_contract_id = fields.Many2one('hr.contract', 'Contrato')


class Job(models.Model):
    _inherit = 'hr.job'

    state = fields.Selection([
        ('recruit', 'Recruitment in Progress'),
        ('open', 'No Seleccionado')
    ], string='Status', readonly=True, required=True, track_visibility='always', copy=False, default='recruit',
        help="Set whether the recruitment process is open or closed for this job position.")


class Contract(models.Model):
    _inherit = 'hr.contract'

    @api.one
    def _get_antiguedad(self):
        fecha_inicio = datetime.strptime(self.date_start, '%Y-%m-%d')
        fecha_fin = datetime.strptime(self.date_start, '%Y-%m-%d') + timedelta(days=self.days_for_trial)
        tiempo = (str(fecha_fin - fecha_inicio)).strip(', 0:00:00')
        # MARZ
        days = int("".join([x for x in tiempo if x.isdigit()]))
        self.antiguedad = str(days) + " días"
        if self.fecha_salida:
            self.write({'state_eliterp': 'pasivo'})

    @api.onchange('if_trial')
    def onchange_if_trial(self):
        if self.if_trial == True:
            if self.date_start:
                self.trial_date_start = self.date_start
                self.trial_date_end = (datetime.strptime(self.date_start, '%Y-%m-%d') + relativedelta(days=+ 90))

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.date_start = self.employee_id.fecha_ingreso
        if self.employee_id.sueldo:
            self.wage = self.employee_id.sueldo
        if self.employee_id.payroll_structure_id:
            self.struct_id = self.employee_id.payroll_structure_id.id

    # MARZ
    @api.onchange('working_hours')
    def onchange_working_hours(self):
        if self.working_hours.name == 'Parcial Permanente':
            self.show_days_for_jornada_parcial = True
        else:
            self.show_days_for_jornada_parcial = False

    def action_view_funciones(self):
        funciones_id = self.env['hr.contract.funciones'].search([('hr_contract_id', '=', self.id)])._ids
        res = {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.contract.funciones',
            'view_mode': 'form',
            'view_type': 'form',
        }
        if funciones_id:
            res['res_id'] = funciones_id[0]
            res['context'] = "{}"
        else:
            res['context'] = "{'default_hr_contract_id': " + str(self.id) + "}"

        return res

    def _get_days_for_trial(self):
        result = 0
        for contrato in self:
            if contrato.days_for_trial == 90:
                result = 90
            else:
                days = ((datetime.strptime(fields.Date.today(), '%Y-%m-%d')) - (
                    datetime.strptime(contrato.date_start, '%Y-%m-%d'))).days
                result = days
            contrato.days_for_trial = result

    def _funciones_count(self):
        records = self
        res = {}
        funciones = self.env['hr.contract.funciones'].search([('hr_contract_id', '=', self.id)])._ids
        if not funciones:
            count = 0
        else:
            lines = self.env['hr.contract.funciones.lines'].search([('hr_contract_funciones_id', '=', funciones[0])])
            count = len(lines)

        res[records.id] = count
        return res

    def _funcion_antiguedad(self):
        if self.days_for_trial >= 90:
            self.if_end_trial = True

    # MARZ
    def activar_contrato(self):
        '''Consecutivo personalizado'''
        if self.date_start:
            new_name = self.env['ir.sequence'].next_by_code('hr.contract.customize')
            new_name = new_name.split('-')
            name = new_name[0] + '-' + self.date_start[0:4] + '-' + self.date_start[5:7] + '-' + new_name[3]
            return self.write({
                'name': name,
                'state_eliterp': 'activo'
            })


    name = fields.Char('No. Contrato', required=False)
    if_trial = fields.Boolean('Período de Prueba?')
    funciones_count = fields.Integer(compute='_funciones_count', string="Funciones")
    days_for_trial = fields.Integer(u'Días Período de Prueba', compute='_get_days_for_trial')
    fecha_salida = fields.Date(related='employee_id.fecha_salida', string='Fecha de Salida')
    legal_hours = fields.Float('Horas Legales', default=240.00)
    # MARZ
    show_days_for_jornada_parcial = fields.Boolean(default=False)
    days_for_jornada_parcial = fields.Integer('Días de Jornada Parcial')
    leyenda_finalizado = fields.Char(string='Estado', default=u'Período de Prueba Finalizado')
    if_end_trial = fields.Boolean(compute='_funcion_antiguedad', default=False)
    state_eliterp = fields.Selection([
        ('draft', 'Borrador'),  # Confirmar para crear consecutivo
        ('activo', 'Activo'),
        ('pasivo', 'Pasivo'), ],
        string='Status', track_visibility='onchange', default='draft')
    antiguedad = fields.Char('Antiguedad', compute='_get_antiguedad')
