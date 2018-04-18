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

import json
import datetime
from dateutil import relativedelta
from ast import literal_eval
from operator import itemgetter

from babel.dates import format_datetime, format_date

from odoo import models, api, _, fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools.misc import formatLang


class RrhhTablero(models.Model):
    _name = 'rrhh.tablero'

    _description = 'Tablero de RRHH'

    name = fields.Char('Nombre de Tablero')
    kanban_dashboard = fields.Text(compute='_kanban_dashboard')
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')
    show_on_dashboard = fields.Boolean(string='Show journal on dashboard',
                                       help="Whether this journal should be displayed on the dashboard or not",
                                       default=True)
    tipo_tablero = fields.Selection([('total_empleado', 'Total de Empleados'),
                                     ('ausencias', 'Ausencias Mensual'),
                                     ('gastos_nomina', u'Gastos de Nómina')], string="Tipo de Tablero")
    type = fields.Selection([('bar', 'Barra'),
                             ('line', u'Línea'),
                             ('bar_stacked', 'Barra Agrupada'),
                             ('pie', 'Pie')], string="Tipo de Tablero")

    @api.one
    def _kanban_dashboard(self):
        '''Devolver gráficas'''
        self.kanban_dashboard = json.dumps(self.get_journal_dashboard_datas())

    def get_mes(self, mes):
        '''Devolver label del mes y año'''
        if mes == 1:
            month = 'Enero'
        if mes == 2:
            month = 'Febrero'
        if mes == 3:
            month = 'Marzo'
        if mes == 4:
            month = 'Abril'
        if mes == 5:
            month = 'Mayo'
        if mes == 6:
            month = 'Junio'
        if mes == 7:
            month = 'Julio'
        if mes == 8:
            month = 'Agosto'
        if mes == 9:
            month = 'Septiembre'
        if mes == 10:
            month = 'Octubre'
        if mes == 11:
            month = 'Noviembre'
        if mes == 12:
            month = 'Diciembre'
        return month

    def last_day_of_month(self, any_day):
        '''Devolver el último día del mes'''
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
        return next_month - datetime.timedelta(days=next_month.day)

    def get_correct_month(self, mes):
        if mes == 0:
            mes = 12
        if mes < 0:
            mes = mes + 12
        return mes

    def get_correct_month_action(self, mes, month):
        # Otro meses
        if month > 3:
            mes = month + mes
            # Marzo
        if mes == -3 and month == 3:
            mes = 12
        if mes == -2 and month == 3:
            mes = 1
        if mes == -1 and month == 3:
            mes = 2
        # Febrero
        if mes == -3 and month == 2:
            mes = 11
        if mes == -2 and month == 2:
            mes = 12
        if mes == -1 and month == 2:
            mes = 1
        # Enero
        if mes == -3 and month == 1:
            mes = 10
        if mes == -2 and month == 1:
            mes = 11
        if mes == -1 and month == 1:
            mes = 12
        return mes

    @api.multi
    def toggle_favorite(self):
        self.write({'show_on_dashboard': False if self.show_on_dashboard else True})
        return False

    def get_data_total_empleado(self):
        data = []
        fecha = datetime.date.today()
        for x in range(1, 4):
            domain = []
            mes = fecha.month - x
            year = fecha.year
            if mes == 0:
                mes = 12
                year -= 1
            if mes == -1:
                mes = 11
                year -= 1
            fecha_inicio = datetime.date(year, mes, 1)
            fecha_fin = self.last_day_of_month(fecha_inicio)
            domain = [('date_start', '>=', fecha_inicio.strftime('%Y-%m-%d')),
                      ('date_end', '<=', fecha_fin.strftime('%Y-%m-%d')),
                      ('state', '=', 'closed')]
            roles = self.env['hr.payslip.run'].search(domain)
            data.append({
                'mes': self.get_mes(mes),
                'empleados': int(roles.numero_empleados)
            })
        data = data[::-1]
        return data

    def get_data_ausencias(self):
        data = self.get_bar_graph_datas()
        return data[0]['values']

    def get_data_nominas(self):
        '''Data de Gastos de Nóminas'''
        data = []
        fecha = datetime.date.today()
        for x in range(1, 4):
            query = """select cast((sum(total_monto_nomina)) as float) AS total
                                       from hr_payslip_run
                                       where (date_trunc('month', current_date - interval '%s months')::DATE) BETWEEN
                                       date_start AND date_end AND state = 'closed';
                                      """ % x
            self.env.cr.execute(query)
            monto = self.env.cr.dictfetchall()
            mes = self.get_correct_month(fecha.month - x)
            data.append({
                'mes': self.get_mes(mes),
                'valor': "$" + "{:.2f}".format(monto[0]['total']) if monto[0]['total'] else 0.00
            })
        data = data[::-1]
        return data

    @api.multi
    def get_journal_dashboard_datas(self):
        '''Devolvemos data a mostrar en gráficas'''
        return {
            'total_empleado': self.get_data_total_empleado(),
            'ausencias': self.get_data_ausencias(),
            'nominas': self.get_data_nominas()
        }

    @api.one
    def _kanban_dashboard_graph(self):
        '''Depende del tipo de gráfica devolvemos la data'''
        if (self.type in ['bar']):
            self.kanban_dashboard_graph = json.dumps(self.get_bar_graph_datas())
        if (self.type in ['bar']):
            self.kanban_dashboard_graph = json.dumps(self.get_bar_graph_datas())
        if (self.type in ['line']):
            self.kanban_dashboard_graph = json.dumps(self.get_line_graph_datas())
        if (self.type in ['pie']):
            self.kanban_dashboard_graph = json.dumps(self.get_pie_graph_datas())
        if (self.type in ['bar_stacked']):
            self.kanban_dashboard_graph = json.dumps(self.get_bar_stacked_graph_datas())

    @api.multi
    def get_bar_graph_datas(self):
        data = []
        key = ''
        fecha = datetime.date.today()
        if self.tipo_tablero == 'total_empleado':
            key = 'Total de Empleados'
            for x in range(1, 4):
                domain = []
                mes = fecha.month - x
                year = fecha.year
                if mes == 0:
                    mes = 12
                    year -= 1
                if mes == -1:
                    mes = 11
                    year -= 1
                fecha_inicio = datetime.date(year, mes, 1)
                fecha_fin = self.last_day_of_month(fecha_inicio)
                domain = [('date_start', '>=', fecha_inicio.strftime('%Y-%m-%d')),
                          ('date_end', '<=', fecha_fin.strftime('%Y-%m-%d')),
                          ('state', '=', 'closed')]
                roles = self.env['hr.payslip.run'].search(domain)
                data.append({
                    'label': self.get_mes(mes),
                    'value': int(roles.numero_empleados)
                })
            data = data[::-1]
        elif self.tipo_tablero == 'ausencias':
            key = 'Ausencias'
            for x in range(1, 4):
                year = fecha.year
                if (fecha.month - x) <= 0:
                    year = year - 1
                mes = self.get_correct_month(fecha.month - x)
                fecha_inicio = datetime.date(year, mes, 1)
                fecha_fin = self.last_day_of_month(fecha_inicio)
                ausencias = self.env['hr.holidays'].search(
                    [('date_from', '>=', fecha_inicio.strftime('%Y-%m-%d')),
                     ('date_from', '<', fecha_fin.strftime('%Y-%m-%d')),
                     ('state', '=', 'validate')])
                dias = 0.00
                for ausencia in ausencias:
                    dias = dias + ausencia.number_of_days_temp
                data.append({
                    'label': self.get_mes(mes),
                    'value': dias
                })
            data = data[::-1]
        else:
            key = 'Gastos de Nómina'
            for x in range(1, 4):
                query = """select cast((sum(total_monto_nomina)) as float) AS total
                           from hr_payslip_run
                           where (date_trunc('month', current_date - interval '%s months')::DATE) BETWEEN
                           date_start AND date_end AND state = 'closed';
                          """ % x
                self.env.cr.execute(query)
                monto = self.env.cr.dictfetchall()
                mes = self.get_correct_month(fecha.month - x)
                data.append({
                    'label': self.get_mes(mes),
                    'value': "{:.2f}".format(monto[0]['total']) if monto[0]['total'] else 0.00
                })
            data = data[::-1]
        return [{
            'values': data,
            'key': key
        }]

    @api.multi
    def get_line_graph_datas(self):
        data = []
        fecha = datetime.date.today()
        for x in range(1, 4):
            query = """select cast((sum(total_monto_nomina)) as float) AS total
                       from hr_payslip_run
                       where (date_trunc('month', current_date - interval '%s months')::DATE) BETWEEN
                       date_start AND date_end AND state = 'closed';
                      """ % x
            self.env.cr.execute(query)
            monto = self.env.cr.dictfetchall()
            mes = self.get_correct_month(fecha.month - x)
            data.append({
                'label': self.get_mes(mes),
                'value': "{:.2f}".format(monto[0]['total']) if monto[0]['total'] else 0.00
            })
        data = data[::-1]
        return [{'values': data, 'key': 'Gastos de Nómina', 'color': "#F02F29"}]

    @api.multi
    def open_action(self):
        # Acciones
        tipo = self._context.get('tipo', False)
        mes = self._context.get('mes', False)
        ctx = self._context.copy()
        ctx.pop('group_by', None)
        fecha = datetime.date.today()
        year = fecha.year
        month = fecha.month
        if month == 3 and mes == -3:  # Marzo
            year = year - 1
        if month == 2 and (mes == -3 or mes == -2): # Febrero
            year = year - 1
        if month == 1: # Enero
            year = year - 1
        mes = self.get_correct_month_action(mes, month)
        fecha_inicio = datetime.date(year, mes, 1)
        fecha_fin = self.last_day_of_month(fecha_inicio)
        domain = []
        if tipo == 'total_empleado' or tipo == 'nominas':
            domain = [('date_start', '>=', fecha_inicio.strftime('%Y-%m-%d')),
                      ('date_end', '<=', fecha_fin.strftime('%Y-%m-%d')),
                      ('state', '=', 'closed')]
            [action] = self.env.ref('elitum_rrhh.eliterp_open_action_nomina').read()
        if tipo == 'ausencias':
            domain = [('date_from', '>=', fecha_inicio.strftime('%Y-%m-%d')),
                      ('date_from', '<', fecha_fin.strftime('%Y-%m-%d')),
                      ('state', '=', 'validate')]
            [action] = self.env.ref('elitum_rrhh.eliterp_action_ausencias').read()
        action['domain'] = domain
        action['context'] = ctx
        return action
