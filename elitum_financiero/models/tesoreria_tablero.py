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
from ast import literal_eval

from babel.dates import format_datetime, format_date

from odoo import models, api, _, fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools.misc import formatLang


class TesoreriaTablero(models.Model):
    _name = 'tesoreria.tablero'

    _description = 'Tablero de Tesoreria'

    name = fields.Char('Nombre')
    kanban_dashboard = fields.Text(compute='_kanban_dashboard', string=u'Información')
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph', string=u'Gráfica')
    show_on_dashboard = fields.Boolean(string='Mostrar en Tablero',
                                       help="Whether this journal should be displayed on the dashboard or not",
                                       default=True)
    type_modulo = fields.Selection([('meses_facturas_emitidas', 'Meses Facturas Emitidas'),
                                    ('meses_facturas_pagadas', 'Meses Facturas Pagadas')], string=u"Tipo de Módulo")
    type = fields.Selection([('bar', 'Barra'),
                             ('line', u'Línea'),
                             ('bar_stacked', 'Barra Agrupada'),
                             ('pie', 'Pie')], string="Tipo de Tablero")
    facturas_ids = fields.Char()

    @api.one
    def _kanban_dashboard(self):
        self.kanban_dashboard = json.dumps(self.get_journal_dashboard_datas())

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
        if mes == 10 or mes == -2:
            return 'Octubre'
        if mes == 11 or mes == -1:
            return 'Noviembre'
        if mes == 12 or mes == 0:
            return 'Diciembre'

    def get_data_bar_stacked(self):
        fecha = datetime.date.today()
        datas = json.loads(self.kanban_dashboard_graph)
        pagar_p_mes = 0.00
        pagadas_p_mes = 0.00
        pagar_s_mes = 0.00
        pagadas_s_mes = 0.00
        pagar_t_mes = 0.00
        pagadas_t_mes = 0.00
        # Botón Más
        for data in datas:
            if data['key'] == u'Por Pagar':
                lines = data['values']
                for line in lines:
                    if line['x'] == self.get_mes(fecha.month - 1):
                        pagar_p_mes = line['y']
                    if line['x'] == self.get_mes(fecha.month):
                        pagar_s_mes = line['y']
                    if line['x'] == self.get_mes(fecha.month + 1):
                        pagar_t_mes = line['y']
            if data['key'] == u'Pagadas' and self.type == 'bar_stacked':
                lines = data['values']
                for line in lines:
                    if line['x'] == self.get_mes(fecha.month - 1):
                        pagadas_p_mes = line['y']
                    if line['x'] == self.get_mes(fecha.month):
                        pagadas_s_mes = line['y']
                    if line['x'] == self.get_mes(fecha.month + 1):
                        pagadas_t_mes = line['y']

        return {
            'pagar_p_mes_title': self.get_mes(fecha.month - 1),
            'pagar_p_mes': "$" + "{:.2f}".format(pagar_p_mes),
            'pagadas_p_mes': "$" + "{:.2f}".format(pagadas_p_mes),
            'saldo_p_mes': "$" + "{:.2f}".format(pagar_p_mes - pagadas_p_mes),
            'pagar_s_mes_title': self.get_mes(fecha.month),
            'pagar_s_mes': "$" + "{:.2f}".format(pagar_s_mes),
            'pagadas_s_mes': "$" + "{:.2f}".format(pagadas_s_mes),
            'saldo_s_mes': "$" + "{:.2f}".format(pagar_s_mes - pagadas_s_mes),
            'pagar_t_mes_title': self.get_mes(fecha.month + 1),
            'pagar_t_mes': "$" + "{:.2f}".format(pagar_t_mes),
            'pagadas_t_mes': "$" + "{:.2f}".format(pagadas_t_mes),
            'saldo_t_mes': "$" + "{:.2f}".format(pagar_t_mes - pagadas_t_mes),
        }

    def get_data_line(self):
        fecha = datetime.date.today()
        datas = json.loads(self.kanban_dashboard_graph)
        ventas_emitido_p_mes = 0.00
        ventas_pagado_p_mes = 0.00
        ventas_emitido_s_mes = 0.00
        ventas_pagado_s_mes = 0.00
        ventas_emitido_t_mes = 0.00
        ventas_pagado_t_mes = 0.00
        for data in datas:
            if data['key'] == u'Por Cobrar':
                lines = sorted(data['values'], reverse=True)
                # MARZ
                if len(lines) == 2:
                    ventas_emitido_s_mes = lines[1]['y']
                    ventas_emitido_t_mes = lines[0]['y']
            if data['key'] == u'Cobradas':
                lines = sorted(data['values'], reverse=True)
                if len(lines) == 2:
                    ventas_pagado_s_mes = lines[1]['y']
                    ventas_pagado_t_mes = lines[0]['y']
        return {
            'ventas_p_mes_title': self.get_mes(fecha.month - 2),
            'ventas_emitido_p_mes': "$" + "{:.2f}".format(ventas_emitido_p_mes),
            'ventas_pagado_p_mes': "$" + "{:.2f}".format(ventas_pagado_p_mes),
            'ventas_saldo_p_mes': "$" + "{:.2f}".format(ventas_emitido_p_mes - ventas_pagado_p_mes),
            'ventas_s_mes_title': self.get_mes(fecha.month - 1),
            'ventas_emitido_s_mes': "$" + "{:.2f}".format(ventas_emitido_s_mes),
            'ventas_pagado_s_mes': "$" + "{:.2f}".format(ventas_pagado_s_mes),
            'ventas_saldo_s_mes': "$" + "{:.2f}".format(ventas_emitido_s_mes - ventas_pagado_s_mes),
            'ventas_t_mes_title': self.get_mes(fecha.month - 0),
            'ventas_emitido_t_mes': "$" + "{:.2f}".format(ventas_emitido_t_mes),
            'ventas_pagado_t_mes': "$" + "{:.2f}".format(ventas_pagado_t_mes),
            'ventas_saldo_t_mes': "$" + "{:.2f}".format(ventas_emitido_t_mes - ventas_pagado_t_mes),
        }

    @api.multi
    def get_journal_dashboard_datas(self):
        res = {}
        if self.type == 'bar_stacked' and self.name == 'Facturas de Compras':
            res = self.get_data_bar_stacked()
        if self.type == 'bar_stacked' and self.name == 'Facturas de Ventas':
            res = self.get_data_line()
        if self.type == 'line':
            res = self.get_data_line()
        return res

    @api.one
    def _kanban_dashboard_graph(self):
        if (self.type in ['bar']):
            self.kanban_dashboard_graph = json.dumps(self.get_bar_graph_datas())
        if (self.type in ['line']):
            self.kanban_dashboard_graph = json.dumps(self.get_line_graph_datas())
        if (self.type in ['pie']):
            self.kanban_dashboard_graph = json.dumps(self.get_pie_graph_datas())
        if (self.type in ['bar_stacked']):
            self.kanban_dashboard_graph = json.dumps(self.get_bar_stacked_graph_datas())

    @api.multi
    def toggle_favorite(self):
        self.write({'show_on_dashboard': False if self.show_on_dashboard else True})
        return False

    @api.multi
    def get_line_graph_datas(self):
        data = []
        emitido = []
        for x in range(-6, 1):
            query = """select sum(inv.amount_total)
                                    from account_invoice as inv
                                    where extract(MONTH FROM inv.date_due) = EXTRACT(month FROM current_date + '%s month'::interval)
                                    and inv.type='out_invoice'
                                    and inv.state in ('open','paid')""" % (x)
            self.env.cr.execute(query)
            facturas = self.env.cr.dictfetchall()
            fecha = datetime.date.today()
            mes = fecha.month
            emitido.append({'x': x,
                            'y': facturas[0]['sum'] if facturas[0]['sum'] else 0.00
                            })

        pagado = []
        facturas = self.env['account.invoice'].search([('state', '!=', 'cancel'), ('type', '=', 'out_invoice')])
        fecha = datetime.date.today()
        meses = {'-6': 0.00,
                 '-5': 0.00,
                 '-4': 0.00,
                 '-3': 0.00,
                 '-2': 0.00,
                 '-1': 0.00,
                 '0': 0.00, }
        for factura in facturas:
            for payment in factura.payment_move_line_ids:
                amount = sum(
                    [p.amount for p in payment.matched_debit_ids if p.debit_move_id in factura.move_id.line_ids])
                amount_currency = sum([p.amount_currency for p in payment.matched_debit_ids if
                                       p.debit_move_id in factura.move_id.line_ids])
                if payment.matched_debit_ids:
                    payment_currency_id = all([p.currency_id == payment.matched_debit_ids[0].currency_id for p in
                                               payment.matched_debit_ids]) and payment.matched_debit_ids[
                                              0].currency_id or False

                if payment_currency_id and payment_currency_id == factura.currency_id:
                    amount_to_show = amount_currency
                else:
                    amount_to_show = payment.company_id.currency_id.with_context(date=payment.date).compute(amount,
                                                                                                            factura.currency_id)
                fecha_payment = datetime.datetime.strptime(payment.date, "%Y-%m-%d")

                for x in range(-6, 1):

                    if (fecha_payment.month == (fecha.month + x)) and (fecha_payment.year == fecha.year):
                        meses[str(x)] = meses[str(x)] + amount_to_show

        for key, value in meses.items():
            if fecha.month + int(key) >= 1:
                pagado.append({'x': fecha.month + int(key),
                               'y': value})

        pagado = sorted(pagado, key=lambda x: (x['x']))

        emitido_ordenado = []
        for emi in emitido:
            if fecha.month + emi['x'] >= 1:
                emitido_ordenado.append({'x': fecha.month + emi['x'],
                                         'y': emi['y']})
        emitido_ordenado = sorted(emitido_ordenado, key=lambda x: (x['x']))
        return [{'values': emitido_ordenado, 'key': 'Por Cobrar', 'color': "#123181"},
                {'values': pagado, 'key': 'Cobradas', 'color': "#3DCE15"}]

    @api.multi
    def get_pie_graph_datas(self):
        data = []
        if self.type_modulo == 'meses_facturas_emitidas':
            tipo = 'open'
        if self.type_modulo == 'meses_facturas_pagadas':
            tipo = 'paid'
        data = []
        query = """select sum(inv.amount_total)
                                        from account_invoice as inv
                                        where extract(MONTH FROM inv.date_invoice) = EXTRACT(month FROM current_date - '2 month'::interval)
                                        and inv.type='in_invoice'
                                        and inv.state=%s""" % (tipo)
        self.env.cr.execute(query)
        facturas_3_mes = self.env.cr.dictfetchall()
        query = """select sum(inv.amount_total)
                                        from account_invoice as inv
                                        where extract(MONTH FROM inv.date_invoice) = EXTRACT(month FROM current_date - '1 month'::interval)
                                        and inv.type='in_invoice'
                                        and inv.state=%s""" % (tipo)
        self.env.cr.execute(query)
        facturas_2_mes = self.env.cr.dictfetchall()
        query = """select sum(inv.amount_total)
                                        from account_invoice as inv
                                        where extract(MONTH FROM inv.date_invoice) = EXTRACT(month FROM current_date)
                                        and inv.type='in_invoice'
                                        and inv.state=%s""" % (tipo)
        self.env.cr.execute(query)
        facturas_mes = self.env.cr.dictfetchall()
        fecha = datetime.date.today()
        mes = fecha.month
        data.append({'label': self.get_mes(mes - 2),
                     'value': "{:.2f}".format(float(facturas_3_mes[0]['sum'])) if facturas_3_mes[0]['sum'] else 0.00})
        data.append({'label': self.get_mes(mes - 1),
                     'value': "{:.2f}".format(float(facturas_2_mes[0]['sum'])) if facturas_2_mes[0]['sum'] else 0.00})
        data.append({'label': self.get_mes(mes),
                     'value': "{:.2f}".format(float(facturas_mes[0]['sum'])) if facturas_mes[0]['sum'] else 0.00})
        return [{'key': 'Historico 3 Meses', 'values': data}]

    @api.multi
    def get_bar_stacked_graph_datas(self):
        data = []
        emitido = []
        pagado = []
        fecha = datetime.date.today()
        # Compras
        if self.name == 'Facturas de Compras':
            for x in range(-1, 2):
                query = """select sum(inv.amount_total)
                                from account_invoice as inv
                                where extract(MONTH FROM inv.date_due) = EXTRACT(month FROM current_date + '%s month'::interval)
                                and extract(YEAR FROM inv.date_invoice) = EXTRACT(year FROM current_date)
                                and inv.type='in_invoice'
                                and inv.state in ('open','paid')""" % (x)
                self.env.cr.execute(query)
                facturas = self.env.cr.dictfetchall()
                fecha = datetime.date.today()
                mes = fecha.month
                emitido.append({
                    'x': self.get_mes(mes + x),
                    'y': facturas[0]['sum'] if facturas[0]['sum'] else 0.00
                })
            facturas = self.env['account.invoice'].search([('state', '!=', 'cancel'),
                                                           ('type', '=', 'in_invoice'), ])
            mes_anterior_total = 0.00
            mes_total = 0.00
            mes_posterior_total = 0.00
            facturas_ids = []
            for factura in facturas:
                if factura.date_due:
                    fecha_factura = datetime.datetime.strptime(factura.date_due, "%Y-%m-%d")
                else:
                    fecha_factura = datetime.datetime.strptime(factura.date_invoice, "%Y-%m-%d")
                flag = False
                if fecha_factura.month in (
                            fecha.month - 1, fecha.month, fecha.month + 1) and fecha_factura.year == fecha.year:
                    for payment in factura.payment_move_line_ids:
                        amount = sum(
                            [p.amount for p in payment.matched_credit_ids if
                             p.credit_move_id in factura.move_id.line_ids])
                        amount_currency = sum(
                            [p.amount_currency for p in payment.matched_credit_ids if
                             p.credit_move_id in factura.move_id.line_ids])
                        if payment.matched_credit_ids:
                            payment_currency_id = all(
                                [p.currency_id == payment.matched_credit_ids[0].currency_id for p in
                                 payment.matched_credit_ids]) and payment.matched_credit_ids[
                                                      0].currency_id or False
                        if payment_currency_id and payment_currency_id == factura.currency_id:
                            amount_to_show = amount_currency
                        else:
                            amount_to_show = payment.company_id.currency_id.with_context(date=payment.date).compute(
                                amount,
                                factura.currency_id)
                        fecha_payment = datetime.datetime.strptime(payment.date, "%Y-%m-%d")
                        if fecha_payment.month == fecha.month - 1 and fecha_payment.year == fecha.year:
                            mes_anterior_total += amount_to_show
                        if fecha_payment.month == fecha.month and fecha_payment.year == fecha.year:
                            mes_total += amount_to_show
                        if fecha_payment.month == fecha.month + 1 and fecha_payment.year == fecha.year:
                            mes_posterior_total += amount_to_show
                        flag = True
                    if flag == True:
                        facturas_ids.append(factura.id)
            pagado.append({'x': self.get_mes(fecha.month - 1),
                           'y': mes_anterior_total})
            pagado.append({'x': self.get_mes(fecha.month),
                           'y': mes_total})
            pagado.append({'x': self.get_mes(fecha.month + 1),
                           'y': mes_posterior_total})
            data.append({'key': 'Por Pagar',
                         'color': "#9B9CA2",
                         'values': emitido})
            data.append({'key': 'Pagadas',
                         'color': "#0E20A8",
                         'values': pagado})
            self.write({'facturas_ids': json.dumps(facturas_ids)})
        # Ventas
        else:
            cobrado = []
            for x in range(-2, 1):
                query = """select sum(inv.amount_total)
                                           from account_invoice as inv
                                           where extract(MONTH FROM inv.date_due) = EXTRACT(month FROM current_date + '%s month'::interval)
                                           and inv.type='out_invoice'
                                           and inv.state in ('open','paid')""" % (x)
                self.env.cr.execute(query)
                facturas = self.env.cr.dictfetchall()
                fecha = datetime.date.today()
                mes = fecha.month
                emitido.append({
                    'x': self.get_mes(mes + x),
                    'y': facturas[0]['sum'] if facturas[0]['sum'] else 0.00
                })
            facturas = self.env['account.invoice'].search([('state', '!=', 'cancel'), ('type', '=', 'out_invoice')])
            fecha = datetime.date.today()
            for factura in facturas:
                for payment in factura.payment_move_line_ids:
                    amount = sum(
                        [p.amount for p in payment.matched_debit_ids if p.debit_move_id in factura.move_id.line_ids])
                    amount_currency = sum([p.amount_currency for p in payment.matched_debit_ids if
                                           p.debit_move_id in factura.move_id.line_ids])
                    if payment.matched_debit_ids:
                        payment_currency_id = all([p.currency_id == payment.matched_debit_ids[0].currency_id for p in
                                                   payment.matched_debit_ids]) and payment.matched_debit_ids[
                                                  0].currency_id or False
                    if payment_currency_id and payment_currency_id == factura.currency_id:
                        amount_to_show = amount_currency
                    else:
                        amount_to_show = payment.company_id.currency_id.with_context(date=payment.date).compute(amount,
                                                                                                                factura.currency_id)
                    fecha_payment = datetime.datetime.strptime(payment.date, "%Y-%m-%d")
                    for x in range(-2, 1):
                        total = 0.00
                        if (fecha_payment.month == (fecha.month + x)) and (fecha_payment.year == fecha.year):
                            total = amount_to_show
                        cobrado.append({
                            'x': self.get_mes(fecha.month + x),
                            'y': total
                        })
            data.append({
                'values': emitido,
                'key': 'Por Cobrar',
                'color': "#123181"
            })
            data.append({
                'values': cobrado,
                'key': 'Cobradas',
                'color': "#3DCE15"
            })
        return data

    @api.multi
    def get_bar_graph_datas(self):
        if self.type_modulo == 'meses_facturas_emitidas':
            tipo = 'open'
        if self.type_modulo == 'meses_facturas_pagadas':
            tipo = 'paid'
        data = []
        query = """select sum(inv.amount_total)
                                        from account_invoice as inv
                                        where extract(MONTH FROM inv.date_invoice) = EXTRACT(month FROM current_date - '2 month'::interval)
                                        and inv.type='in_invoice'
                                        and inv.state='%s'""" % (tipo)
        self.env.cr.execute(query)
        facturas_3_mes = self.env.cr.dictfetchall()
        query = """select sum(inv.amount_total)
                                        from account_invoice as inv
                                        where extract(MONTH FROM inv.date_invoice) = EXTRACT(month FROM current_date - '1 month'::interval)
                                        and inv.type='in_invoice'
                                        and inv.state='%s'""" % (tipo)
        self.env.cr.execute(query)
        facturas_2_mes = self.env.cr.dictfetchall()
        query = """select sum(inv.amount_total)
                                        from account_invoice as inv
                                        where extract(MONTH FROM inv.date_invoice) = EXTRACT(month FROM current_date)
                                        and inv.type='in_invoice'
                                        and inv.state='%s'""" % (tipo)
        self.env.cr.execute(query)
        facturas_mes = self.env.cr.dictfetchall()
        fecha = datetime.date.today()
        mes = fecha.month
        data.append({'label': self.get_mes(mes - 2),
                     'value': "{:.2f}".format(float(facturas_3_mes[0]['sum'])) if facturas_3_mes[0]['sum'] else 0.00})
        data.append({'label': self.get_mes(mes - 1),
                     'value': "{:.2f}".format(float(facturas_2_mes[0]['sum'])) if facturas_2_mes[0]['sum'] else 0.00})
        data.append({'label': self.get_mes(mes),
                     'value': "{:.2f}".format(float(facturas_mes[0]['sum'])) if facturas_mes[0]['sum'] else 0.00})
        return [{'key': 'Historico 3 Meses', 'values': data}]

    def last_day_of_month(self, any_day):
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
        return next_month - datetime.timedelta(days=next_month.day)

    @api.multi
    def open_action(self):
        action_name = self._context.get('action_name', False)
        type = self._context.get('type_tablero', False)
        tipo_factura = self._context.get('tipo_factura', False)
        ctx = self._context.copy()
        ctx.pop('group_by', None)
        ctx.update({'group_by': 'date_due:month'})
        [action] = self.env.ref('account.%s' % action_name).read()
        fecha = datetime.date.today()
        if tipo_factura == 'compras':
            mes_antes = fecha.month - 1
            mes_next = fecha.month + 1
            fecha_inicio = datetime.date(fecha.year, mes_antes, 1)  # Mes anterior
            fecha_fin_ = datetime.date(fecha.year, mes_next, 1)
            fecha_fin = self.last_day_of_month(fecha_fin_)  # Mes final
            domain = [('type', '=', 'in_invoice'),
                      ('date_due', '<=', fecha_fin.strftime('%Y-%m-%d')),
                      ('date_due', '>=', fecha_inicio.strftime('%Y-%m-%d'))]
            if type == 'a_pagar':
                estado = ('open', 'paid')
            if type == 'pagadas':
                estado = 'paid'
                domain.append(('id', 'in', tuple(json.loads(self.facturas_ids))))
            domain.append(('state', '=', estado))
            action['domain'] = domain
            action['context'] = ctx
        if tipo_factura == 'ventas':
            mes_antes = fecha.month - 3
            year_antes = fecha.year
            if mes_antes == -1:
                mes_antes = 12
                year_antes = year_antes -1
            fecha_inicio = datetime.date(year_antes , mes_antes, 1)
            fecha_fin_ = datetime.date(year_antes , fecha.month, 1)
            fecha_fin = self.last_day_of_month(fecha_fin_)
            domain = [('type', '=', 'out_invoice'),
                      ('date_due', '<=', fecha_fin.strftime('%Y-%m-%d')),
                      ('date_due', '>=', fecha_inicio.strftime('%Y-%m-%d'))]
            if type == 'emitidas':
                estado = ('open', 'paid')
            if type == 'pagadas':
                estado = 'paid'
            domain.append(('state', '=', estado))
            action['domain'] = domain
            action['context'] = ctx
        return action
