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
from datetime import datetime, timedelta


class FiniquitoVacaciones(models.Model):
    _name = 'finiquito.vacaciones'

    _description = 'Finiquito Vacaciones'

    # MARZ
    mes = fields.Char(u'Días')
    sueldo = fields.Float('Valor')
    finiquito_id = fields.Many2one('finiquito', string=u'Período')


class FiniquitoDecimaCuarta(models.Model):
    _name = 'finiquito.decima.cuarta'

    _description = 'Finiquito Decima Cuarta'

    mes = fields.Char('Mes')
    dias = fields.Integer('Dias')
    finiquito_id = fields.Many2one('finiquito')


class FiniquitoDecimaTercera(models.Model):
    _name = 'finiquito.decima.tercera'

    _description = 'Finiquito Decima Tercera'

    mes = fields.Char('Mes')
    sueldo = fields.Float('Sueldo')
    finiquito_id = fields.Many2one('finiquito')


class Finiquito(models.Model):
    _name = 'finiquito'

    _description = 'Finiquito'

    # MARZ
    @api.multi
    def name_get(self):
        res = []
        for data in self:
            res.append((data.id, "Finiquito No. %s" % data.id))
        return res

    def confirmar(self):
        self.write({'state': 'confirm'})

    def _get_mes(self, mes):
        if mes == 1:
            return "Enero"
        if mes == 2:
            return "Febrero"
        if mes == 3:
            return "Marzo"
        if mes == 4:
            return "Abril"
        if mes == 5:
            return "Mayo"
        if mes == 6:
            return "Junio"
        if mes == 7:
            return "Julio"
        if mes == 8:
            return "Agosto"
        if mes == 9:
            return "Septiembre"
        if mes == 10:
            return "Octubre"
        if mes == 11:
            return "Noviembre"
        if mes == 12:
            return "Diciembre"

    def cargar_valores(self):
        fecha = datetime.strptime(self.fecha_salida, "%Y-%m-%d")
        mes = fecha.month

        # Cálculo de Décimo Tercero
        meses_tercer = []
        if mes < 11:
            for x in range(mes, 0, -1):
                meses_tercer.append({'month': x, 'year': fecha.year})
            for x in range(12, 11, -1):
                meses_tercer.append({'month': x, 'year': fecha.year - 1})
        if mes > 11:
            meses_tercer.append({'month': 12, 'year': fecha.year})
        if mes == 11:
            meses_tercer.append({'month': mes, 'year': fecha.year})

        # MARZ
        roles = self.env['hr.payslip'].search([
            ('employee_id', '=', self.empleado.id),
            ('state', '=', 'done')
        ])

        # Cálculo de Décimo Cuarto
        meses_cuarto = []
        if mes > 3:
            for x in range(mes, 2, -1):
                meses_cuarto.append({'month': x, 'year': fecha.year})
        if mes < 3:
            for y in range(mes, 0, -1):
                meses_cuarto.append({'month': y, 'year': fecha.year})
            for x in range(12, mes, -1):
                meses_cuarto.append({'month': x, 'year': fecha.year - 1})
        if mes == 3:
            meses_cuarto.append({'month': mes, 'year': fecha.year})

        # Vacaciones
        meses_vacaciones = []
        mes_vacaciones = (datetime.strptime(self.fecha_ingreso, "%Y-%m-%d")).month
        if mes > mes_vacaciones:
            for x in range(mes - 1, mes_vacaciones + 1):
                meses_vacaciones.append({'month': x, 'year': fecha.year})
        if mes < mes_vacaciones:
            for x in range(mes, 0, -1):
                meses_vacaciones.append({'month': x, 'year': fecha.year})
            for x in range(12, mes_vacaciones, -1):
                meses_vacaciones.append({'month': x, 'year': fecha.year - 1})

        # Información de Décimo Tercero
        data_tercera = []
        for mes in meses_tercer:
            rol = roles.filtered(lambda rol: (datetime.strptime(rol.date_from, "%Y-%m-%d")).year == mes['year']
                                             and (datetime.strptime(rol.date_from, "%Y-%m-%d")).month == mes['month'])
            if len(rol) != 0:
                data_tercera.append([0, 0, {'mes': self._get_mes(mes['month']) + "-" + str(mes['year']),
                                            'sueldo': rol.input_line_ids.filtered(
                                                lambda rol: rol.name == 'Sueldo').amount}])
        self.update({'line_decima_tercera': data_tercera})

        # Información de Décimo Cuarto
        data_cuarta = []
        for mes in meses_cuarto:
            rol = roles.filtered(lambda rol: (datetime.strptime(rol.date_from, "%Y-%m-%d")).year == mes['year']
                                             and (datetime.strptime(rol.date_from, "%Y-%m-%d")).month == mes['month'])
            if len(rol) != 0:
                data_cuarta.append([0, 0, {'mes': self._get_mes(mes['month']) + "-" + str(mes['year']),
                                           'dias': rol.dias_trabajados}])
        self.update({'line_decima_cuarta': data_cuarta})

        # Información de Vacaciones
        data_vacaciones = []
        for mes in meses_vacaciones:
            rol = roles.filtered(lambda rol: (datetime.strptime(rol.date_from, "%Y-%m-%d")).year == mes['year']
                                             and (datetime.strptime(rol.date_from, "%Y-%m-%d")).month == mes['month'])
            if len(rol) != 0:
                data_vacaciones.append([0, 0, {'mes': self._get_mes(mes['month']) + "-" + str(mes['year']),
                                               'sueldo': rol.input_line_ids.filtered(
                                                   lambda rol: rol.name == 'Sueldo').amount}])

        # Calcular días trabajados el último mes
        fechas_roles = []
        for rol in roles:
            fechas_roles.append((datetime.strptime(rol.date_from, "%Y-%m-%d")).date())

        fechas_roles = sorted(fechas_roles, reverse=True)
        rol = roles.filtered(
            lambda rol: (datetime.strptime(rol.date_from, "%Y-%m-%d")).year == fechas_roles[0].year and (
                                                                                                            datetime.strptime(
                                                                                                                rol.date_from,
                                                                                                                "%Y-%m-%d")).month ==
                                                                                                        fechas_roles[
                                                                                                            0].month)

        # Cálculo de Liquidación
        dias_trabajados = rol.dias_trabajados
        ultimo_sueldo = (float(self.ultimo_sueldo) / float(30)) * float(dias_trabajados)

        # Actualizar Información
        self.update({'line_vacaciones': data_vacaciones})
        self.update(
            {'total_decima_tercera': float(float(sum(line.sueldo for line in self.line_decima_tercera)) / float(12))})
        self.update({'total_decima_cuarta': float((float(375) / float(360))) * float(
            sum(line.dias for line in self.line_decima_cuarta))})
        self.update({'total_vacaciones': float(float(sum(line.sueldo for line in self.line_vacaciones)) / float(24))})
        self.update({'dias_trabajdos_ultimo_mes': dias_trabajados,
                     'decimo_tercer_sueldo': self.total_decima_tercera,
                     'decimo_cuarto_sueldo': self.total_decima_cuarta,
                     'vacaciones_periodo_actual': self.total_vacaciones,
                     'ultimo_sueldo_haberes': ultimo_sueldo, })
        return

    # MARZ
    @api.onchange('decimo_tercer_sueldo', 'decimo_cuarto_sueldo', 'vacaciones_periodo_actual', 'vacaciones_pendientes',
                  'ultimo_sueldo_haberes', 'fondos_reserva', 'indemnizacion_despido', 'horas_extra', 'desahucio',
                  'otros_descuentos', 'line_vacaciones')
    def _compute_liquidacion(self):
        # MARZ
        valor_total_vacaciones = float(float(sum(line.sueldo for line in self.line_vacaciones)) / float(24))
        self.total_vacaciones = valor_total_vacaciones
        self.vacaciones_periodo_actual = valor_total_vacaciones

        self.subtotal = 0.00
        subtotal = self.decimo_tercer_sueldo + self.decimo_cuarto_sueldo + self.vacaciones_periodo_actual + self.vacaciones_pendientes + self.ultimo_sueldo + self.fondos_reserva + self.indemnizacion_despido + self.horas_extra + self.desahucio
        self.subtotal = subtotal

        self.aporte_iess = 0.00
        aporte_iess = ((self.ultimo_sueldo + self.horas_extra) * 9.45) / 100
        self.aporte_iess = aporte_iess

        self.subtotal_deducciones = 0.00
        subtotal_deducciones = self.aporte_iess + self.otros_descuentos
        self.subtotal_deducciones = subtotal_deducciones

        self.a_recibir = 0.00
        a_recibir = self.subtotal  - self.subtotal_deducciones
        self.a_recibir = a_recibir

    empleado = fields.Many2one('hr.employee')
    cargo = fields.Many2one('hr.job')
    motivo_salida = fields.Char('Motivo de Salida')
    fecha_ingreso = fields.Date('Fecha Ingreso')
    fecha_salida = fields.Date('Fecha Salida')
    ultimo_sueldo = fields.Float('Ultimo Sueldo')
    dias_trabajdos_ultimo_mes = fields.Integer('Dias Trabajados Ultimo Mes')
    state = fields.Selection([('draft', 'Borrador'), ('confirm', 'Confirmado')], default='draft')
    line_decima_tercera = fields.One2many('finiquito.decima.tercera', 'finiquito_id')
    total_decima_tercera = fields.Float('TOTAL D.T.R')
    line_decima_cuarta = fields.One2many('finiquito.decima.cuarta', 'finiquito_id')
    total_decima_cuarta = fields.Float('TOTAL D.C.R')
    line_vacaciones = fields.One2many('finiquito.vacaciones', 'finiquito_id')
    total_vacaciones = fields.Float('TOTAL VACACIONES')

    decimo_tercer_sueldo = fields.Float('Decimo Tercer Sueldo')
    decimo_cuarto_sueldo = fields.Float('Decimo Cuarto Sueldo')
    vacaciones_periodo_actual = fields.Float('Vacaciones Periodo Actual')
    vacaciones_pendientes = fields.Float('Vacaciones Pendientes')
    ultimo_sueldo_haberes = fields.Float('Ultimo Sueldo')
    fondos_reserva = fields.Float('Fondo de Reserva')
    indemnizacion_despido = fields.Float('Indemnizacion Despido')
    horas_extra = fields.Float('Horas Extra')
    desahucio = fields.Float('Desahucio')
    subtotal = fields.Float('Subtotal')
    aporte_iess = fields.Float('Aportes IESS')
    otros_descuentos = fields.Float('Otras Descuentos')
    subtotal_deducciones = fields.Float('Subtotal')
    a_recibir = fields.Float('A recibir')
