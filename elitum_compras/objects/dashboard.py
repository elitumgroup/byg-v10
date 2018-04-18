# -*- encoding: utf-8 -*-
#########################################################################
# Copyright (C) 2018 Ing. Mario Rangel, Elitum Group                   #
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
from odoo import models, api, _, fields
import datetime


class PurchasesDashboard(models.Model):
    _name = 'elitumgroup.purchases.dashboard'

    _description = 'Tablero de Compras'

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
        if mes == 12 or mes == 0:
            return 'Diciembre'

    name = fields.Char('Nombre')
    kanban_dashboard = fields.Text(compute='_kanban_dashboard')
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')
    show_on_dashboard = fields.Boolean(string='Mostrar en Tablero', default=True)
    type_dashboard = fields.Selection([
        ('proveedores', 'Proveedores'),
        ('meses', 'Meses')
    ], string='Tipo de Tablero')
    type = fields.Selection([('bar', 'Barra'),
                             ('line', u'Línea'),
                             ('bar_stacked', 'Barra Agrupada'),
                             ('pie', 'Pie')], string=u"Tipo de Gráfica")

    @api.one
    def _kanban_dashboard(self):
        self.kanban_dashboard = json.dumps(self.get_journal_dashboard_datas())

    @api.one
    def _kanban_dashboard_graph(self):
        if (self.type in ['bar']):
            self.kanban_dashboard_graph = json.dumps(self.get_bar_graph_datas())
        if (self.type in ['bar_stacked']):
            self.kanban_dashboard_graph = json.dumps(self.get_bar_stacked_graph_datas())

    @api.multi
    def toggle_favorite(self):
        self.write({'show_on_dashboard': False if self.show_on_dashboard else True})
        return False

    @api.multi
    def get_bar_stacked_graph_datas(self):
        '''Gráfica de barras dobles'''
        data = []
        # Líneas del mes anterior
        facturas_mes_anterior = []
        account_object = self.env['account.invoice']
        fecha = datetime.date.today()
        mes = fecha.month - 1
        year = fecha.year
        if mes == 0:
            mes = 12
            year = year - 1
        fecha_inicio = datetime.date(year, mes, 1)
        fecha_fin = self.last_day_of_month(fecha_inicio)
        facturas_mes_anterior = account_object.search([
            ('state', 'in', ('open', 'paid')),
            ('type', '=', 'in_invoice'),
            ('date_invoice', '>=', fecha_inicio.strftime('%Y-%m-%d')),
            ('date_invoice', '<=', fecha_fin.strftime('%Y-%m-%d'))
        ])
        lines_invoice_anterior = []
        temporal = {}
        for factura in facturas_mes_anterior:
            lines_factura = factura.invoice_line_ids
            for line in lines_factura:
                if not temporal.get(line.account_id.code):
                    temporal[line.account_id.code] = {
                        'code': '',
                        'x': '',
                        'y': 0.00
                    }
                temporal[line.account_id.code]['code'] = line.account_id.code
                temporal[line.account_id.code]['x'] = line.account_id.name
                temporal[line.account_id.code]['y'] += round(line.price_subtotal, 2)
        for k, v in temporal.items():
            lines_invoice_anterior.append(v)
        lines_invoice_anterior = sorted(lines_invoice_anterior, key=lambda x: (x['y']), reverse=True)  # Ordenamos por valor mayor
        lines_invoice_anterior = lines_invoice_anterior[:5]  # Seleccionamos los 5 primeros

        # Líneas del mes
        facturas_mes = []
        fecha = datetime.date.today()
        fecha_inicio = datetime.date(fecha.year, fecha.month, 1)
        fecha_fin = self.last_day_of_month(fecha_inicio)
        facturas_mes = account_object.search([
            ('state', 'in', ('open', 'paid')),
            ('type', '=', 'in_invoice'),
            ('date_invoice', '>=', fecha_inicio.strftime('%Y-%m-%d')),
            ('date_invoice', '<=', fecha_fin.strftime('%Y-%m-%d'))
        ])
        lines_invoice = []
        temporal_mes = {}
        for factura in facturas_mes:
            lines_factura = factura.invoice_line_ids
            for line in lines_factura:
                if not temporal_mes.get(line.account_id.code):
                    temporal_mes[line.account_id.code] = {
                        'code': '',
                        'x': '',
                        'y': 0.00
                    }
                temporal_mes[line.account_id.code]['code'] = line.account_id.code
                temporal_mes[line.account_id.code]['x'] = line.account_id.name
                temporal_mes[line.account_id.code]['y'] += round(line.price_subtotal, 2)
        for k, v in temporal_mes.items():
            lines_invoice.append(v)

        lines_invoice_final = []
        for line in lines_invoice_anterior:
            for line_mes in lines_invoice:
                if line['code'] == line_mes['code']:
                    lines_invoice_final.append({
                        'x': line_mes['x'],
                        'y': line_mes['y']
                    })

        data.append({
            'key': 'Mes Anterior',
            'color': "#9B9CA2",
            'values': lines_invoice_anterior
        })

        data.append({
            'key': 'Mes Actual',
            'color': "#0E20A8",
            'values': lines_invoice_final
        })
        return data

    @api.multi
    def get_bar_graph_datas(self):
        '''Gráfica de barras'''
        data = []
        # Histórico de Facturación
        if self.type_dashboard == 'meses':
            query = """select cast((sum(inv.amount_untaxed)) as float)
                                      from account_invoice as inv
                                      where extract(MONTH FROM inv.date_invoice) = EXTRACT(month FROM current_date - '2 month'::interval)
                                      and extract(YEAR FROM inv.date_invoice) = EXTRACT(YEAR FROM current_date - '2 month'::interval)
                                      and inv.type='in_invoice'
                                      and inv.state in ('open', 'paid')"""
            self.env.cr.execute(query)
            facturas_2_meses = self.env.cr.dictfetchall()  # Dos meses anteriores
            query = """select cast((sum(inv.amount_untaxed)) as float)
                                      from account_invoice as inv
                                      where extract(MONTH FROM inv.date_invoice) = EXTRACT(month FROM current_date - '1 month'::interval)
                                      and extract(YEAR FROM inv.date_invoice) = EXTRACT(YEAR FROM current_date - '1 month'::interval)
                                      and inv.type='in_invoice'
                                      and inv.state in ('open', 'paid')"""
            self.env.cr.execute(query)
            facturas_1_mes = self.env.cr.dictfetchall()  # Mes anterior
            query = """select cast((sum(inv.amount_untaxed)) as float)
                                      from account_invoice as inv
                                      where extract(MONTH FROM inv.date_invoice) = EXTRACT(month FROM current_date)
                                      and extract(YEAR FROM inv.date_invoice) = EXTRACT(YEAR FROM current_date)
                                      and inv.type='in_invoice'
                                      and inv.state in ('open', 'paid')"""
            self.env.cr.execute(query)
            facturas_mes = self.env.cr.dictfetchall()  # Mes actual
            fecha = datetime.date.today()
            mes = fecha.month
            data.append({
                'label': self.get_mes(mes - 2),
                'value': "{:.2f}".format(float(facturas_2_meses[0]['sum'])) if facturas_2_meses[0]['sum'] else 0.00
            })
            data.append({
                'label': self.get_mes(mes - 1),
                'value': "{:.2f}".format(float(facturas_1_mes[0]['sum'])) if facturas_1_mes[0]['sum'] else 0.00
            })
            data.append({
                'label': self.get_mes(mes),
                'value': "{:.2f}".format(float(facturas_mes[0]['sum'])) if facturas_mes[0]['sum'] else 0.00
            })
            return [{
                'key': 'Histórico de Facturación',
                'values': data,
                'flag': True
            }]
        # Facturas por Proveedor
        else:
            query = """SELECT b.name AS empresa, cast((sum(a.amount_untaxed)) as float) AS total
                       FROM account_invoice AS a
                       INNER JOIN res_partner AS b ON b.id = a.partner_id
                       WHERE a.type = 'in_invoice' AND a.state IN ('open', 'paid')
                       GROUP BY b.name
                       ORDER BY total DESC
                       LIMIT 5"""
            self.env.cr.execute(query)
            facturado = self.env.cr.dictfetchall()
            for factura in facturado:
                data.append({
                    'label': factura['empresa'],
                    'value': "{:.2f}".format(float(factura['total'])) if factura['total'] else 0.00
                })
            return [{
                'key': 'Facturas por Proveedores',
                'values': data,
                'flag': True
            }]

    def last_day_of_month(self, any_day):
        '''Último día del mes'''
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
        return next_month - datetime.timedelta(days=next_month.day)

    def get_dashboard_1(self):
        '''Data de Histórico de Facturación'''
        data = []
        fecha = fields.date.today()
        for x in range(-2, 1):
            query = """select cast((sum(inv.amount_untaxed)) as float)
                                      from account_invoice as inv
                                      where extract(MONTH FROM inv.date_invoice) = EXTRACT(month FROM current_date + '%s  month'::interval)
                                      and extract(YEAR FROM inv.date_invoice) = EXTRACT(YEAR FROM current_date + '%s month'::interval)
                                      and inv.type='in_invoice'
                                      and inv.state in ('open', 'paid')""" % (x, x)
            self.env.cr.execute(query)
            facturas = self.env.cr.dictfetchall()
            mes = fecha.month + x
            data.append({
                'mes': self.get_mes(mes),
                'valor': "{:.2f}".format(float(facturas[0]['sum'])) if facturas[0]['sum'] else 0.00
            })
        return data

    def get_dashboard_3(self):
        query = """SELECT b.name AS empresa, cast((sum(a.amount_untaxed)) as float) AS total
                               FROM account_invoice AS a
                               INNER JOIN res_partner AS b ON b.id = a.partner_id
                               WHERE a.type = 'in_invoice' AND a.state IN ('open', 'paid')
                               GROUP BY b.name
                               ORDER BY total DESC
                               LIMIT 5"""
        self.env.cr.execute(query)
        data = self.env.cr.dictfetchall()
        return data

    @api.multi
    def get_journal_dashboard_datas(self):
        '''Información en botones Más'''
        return {
            'dashboard_1': self.get_dashboard_1(),
            'dashboard_3': self.get_dashboard_3()
        }

    @api.multi
    def open_action(self):
        '''Acciones dentro de botones Más'''
        action_name = self._context.get('action_name', False)
        type = self._context.get('tipo', False)
        mes = self._context.get('mes', False)
        ctx = self._context.copy()
        ctx.pop('group_by', None)
        [action] = self.env.ref('account.%s' % action_name).read()
        fecha = fields.date.today()
        if type == 'facturas':
            '''Acción de Histórico de Facturación'''
            mes = fecha.month + mes
            year = fecha.year
            if mes == -1:
                mes = 11
                year = year - 1
            if mes == 0:
                mes = 12
                year = year - 1
            fecha_inicio = datetime.date(year, mes, 1)
            fecha_fin = self.last_day_of_month(fecha_inicio)
            domain = [
                ('type', '=', 'in_invoice'),
                ('state', 'in', ('open', 'paid')),
                ('date_invoice', '<=', fecha_fin.strftime('%Y-%m-%d')),
                ('date_invoice', '>=', fecha_inicio.strftime('%Y-%m-%d'))
            ]
            ctx.update({'group_by': 'date_invoice:month'})
            action['domain'] = domain
        if type == 'factura_proveedor':
            '''Acción de Factura por Proveedor'''
            ctx.update({'group_by': 'partner_id'})
        action['context'] = ctx
        return action
