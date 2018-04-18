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

import json
from datetime import datetime, timedelta
import datetime
from babel.dates import format_datetime, format_date

from odoo import models, api, _, fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools.misc import formatLang

class VentasTablero(models.Model):

    _name = 'ventas.tablero'

    _description = 'Tablero de Ventas'

    def last_day_of_month(self, any_day):
        '''Último día del mes'''
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
        return next_month - datetime.timedelta(days=next_month.day)

    def get_mes(self, mes):
        if mes==1:
            return 'Enero'
        if mes==2:
            return 'Febrero'
        if mes==3:
            return 'Marzo'
        if mes==4:
            return 'Abril'
        if mes==5:
            return 'Mayo'
        if mes==6:
            return 'Junio'
        if mes==7:
            return 'Julio'
        if mes==8:
            return 'Agosto'
        if mes==9:
            return 'Septiembre'
        if mes==10:
            return 'Octubre'
        if mes==11:
            return 'Noviembre'
        if mes==12 or mes == 0:
            return 'Diciembre'


    name = fields.Char('Nombre')
    kanban_dashboard = fields.Text(compute='_kanban_dashboard')
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')
    show_on_dashboard = fields.Boolean(string='Show journal on dashboard', default=True)
    type_barra_doble = fields.Selection([('asesor','Asesor'),('producto','Producto'),('meses','Meses')])
    type = fields.Selection([('bar','Barra'),
                             ('line',u'Línea'),
                             ('bar_stacked','Barra Agrupada'),
                             ('pie', 'Pie')], string="Tipo de Tablero")

    @api.one
    def _kanban_dashboard(self):
        self.kanban_dashboard = json.dumps(self.get_journal_dashboard_datas())

    @api.one
    def _kanban_dashboard_graph(self):
        if (self.type in ['bar']):
            self.kanban_dashboard_graph = json.dumps(self.get_bar_graph_datas())
        if(self.type in ['line']):
            self.kanban_dashboard_graph = json.dumps(self.get_line_graph_datas())
        if (self.type in ['bar_stacked']):
            self.kanban_dashboard_graph = json.dumps(self.get_bar_stacked_graph_datas())

    @api.multi
    def toggle_favorite(self):
        self.write({'show_on_dashboard': False if self.show_on_dashboard else True})
        return False

    @api.multi
    def get_line_graph_datas(self):
        if self.type_barra_doble == 'meses':
            data = []
            query = """select sum(inv.residual)
                          from account_invoice as inv
                          where extract(MONTH FROM inv.date_invoice) = EXTRACT(month FROM inv.date_invoice - '2 month'::interval)"""
            self.env.cr.execute(query)
            datos_facturas = self.env.cr.dictfetchall()

        data[00].update({'y':400})
        data[01].update({'y':400})
        data[02].update({'y':200})
        data[03].update({'y':200})
        data[04].update({'y':920})
        data[04].update({'y':920})
        data[06].update({'y':800})
        data[07].update({'y':800})
        data[10].update({'y':200})
        data[12].update({'y':700})
        data[14].update({'y':600})
        data[20].update({'y':100})
        data[25].update({'y':200})
        data[28].update({'y':3})
        data[29].update({'y':2})
        data[30].update({'y':1})

        return [{'values': data, 'area': True}]

    @api.multi
    def get_bar_stacked_graph_datas(self):
        data=[]
        value_cotizacion=[]
        value_pedido_venta = []
        if self.type_barra_doble=='asesor':
            query ="""select count(sale.id), asesor.name_related
                      from sale_order as sale, res_partner as cli, hr_employee as asesor
                      where cli.id = sale.partner_id
                            and cli.consultant_sale_id = asesor.id
                            and sale.type_eliterp='draft'
                            and sale.state_cotizacion_eliterp not in ('draft','denied','cancel')
                            and sale.have_pedidos_ventas = False
                            and extract(MONTH FROM sale.date_created) = extract(MONTH FROM current_date)
                      group by asesor.name_related"""
            self.env.cr.execute(query)
            cotizaciones= self.env.cr.dictfetchall()

            query = """select count(sale.id), asesor.name_related
                              from sale_order as sale, res_partner as cli, hr_employee as asesor
                              where cli.id = sale.partner_id
                                    and cli.consultant_sale_id = asesor.id
                                    and type_eliterp='pedido_venta'
                                    and sale.state_pedido_eliterp != 'cancel'
                                    and extract(MONTH FROM sale.date_created) = extract(MONTH FROM current_date)
                              group by asesor.name_related"""
            self.env.cr.execute(query)
            pedidos = self.env.cr.dictfetchall()
            for cotizacion in cotizaciones:
                value_cotizacion.append({'x': cotizacion['name_related'],
                                         'y': cotizacion['count']
                                         })
            for pedido in pedidos:
                value_pedido_venta.append({'x': pedido['name_related'],
                                           'y': pedido['count']
                                           })

        if self.type_barra_doble == 'producto':
            query = """select count(sale.id), product.default_code
                              from sale_order as sale, product_template as product, sale_order_line as line
                              where line.order_id = sale.id and product.id = line.product_id
                                    and sale.type_eliterp='draft'
                                    and sale.state_cotizacion_eliterp not in ('draft','denied','cancel')
                                    and sale.have_pedidos_ventas = False
                                    and extract(MONTH FROM sale.date_created) = extract(MONTH FROM current_date)
                              group by product.default_code"""
            self.env.cr.execute(query)
            cotizaciones = self.env.cr.dictfetchall()

            query = """select count(sale.id), product.default_code
                              from sale_order as sale, product_template as product, sale_order_line as line
                              where line.order_id = sale.id and product.id = line.product_id
                                    and type_eliterp='pedido_venta'
                                    and sale.state_pedido_eliterp != 'cancel'
                                    and extract(MONTH FROM sale.date_created) = extract(MONTH FROM current_date)
                                    group by product.default_code"""
            self.env.cr.execute(query)
            pedidos = self.env.cr.dictfetchall()
            for cotizacion in cotizaciones:
                value_cotizacion.append({'x': cotizacion['default_code'],
                                         'y': cotizacion['count']
                                         })
            for pedido in pedidos:
                value_pedido_venta.append({'x': pedido['default_code'],
                                           'y': pedido['count']
                                           })

        data.append({'key':'Cotizaciones',
                     'color':"#9B9CA2",
                     'values': value_cotizacion})

        data.append({'key':'Pedidos de Venta',
                     'color':"#0E20A8",
                     'values': value_pedido_venta})

        return data

    @api.multi
    def get_bar_graph_datas(self):
        if self.type_barra_doble == 'meses':
            data = []
            query = """select cast((sum(inv.amount_untaxed)) as float)
                                      from account_invoice as inv
                                      where extract(MONTH FROM inv.date_invoice) = EXTRACT(month FROM current_date - '2 month'::interval)
                                      and extract(YEAR FROM inv.date_invoice) = EXTRACT(YEAR FROM current_date - '2 month'::interval)
                                      and inv.type='out_invoice'
                                      and inv.state!='draft'"""
            self.env.cr.execute(query)
            facturas_3_mes = self.env.cr.dictfetchall()
            query = """select cast((sum(inv.amount_untaxed)) as float)
                                      from account_invoice as inv
                                      where extract(MONTH FROM inv.date_invoice) = EXTRACT(month FROM current_date - '1 month'::interval)
                                      and extract(YEAR FROM inv.date_invoice) = EXTRACT(YEAR FROM current_date - '1 month'::interval)
                                      and inv.type='out_invoice'
                                      and inv.state!='draft'"""
            self.env.cr.execute(query)
            facturas_2_mes = self.env.cr.dictfetchall()
            query = """select cast((sum(inv.amount_untaxed)) as float)
                                      from account_invoice as inv
                                      where extract(MONTH FROM inv.date_invoice) = EXTRACT(month FROM current_date)
                                      and extract(YEAR FROM inv.date_invoice) = EXTRACT(YEAR FROM current_date)
                                      and inv.type='out_invoice'
                                      and inv.state!='draft'"""
            self.env.cr.execute(query)
            facturas_mes = self.env.cr.dictfetchall()
            fecha = datetime.date.today()
            mes = fecha.month
            data.append({'label': self.get_mes(mes-2),
                         'value': "{:.2f}".format(float(facturas_3_mes[0]['sum'])) if facturas_3_mes[0]['sum'] else 0.00})
            data.append({'label': self.get_mes(mes-1),
                         'value': "{:.2f}".format(float(facturas_2_mes[0]['sum'])) if facturas_2_mes[0]['sum'] else 0.00})
            data.append({'label': self.get_mes(mes),
                         'value': "{:.2f}".format(float(facturas_mes[0]['sum'])) if facturas_mes[0]['sum'] else 0.00})
            return [{'key': 'Historico 3 Meses', 'values': data, 'flag':True}]
        else:
            data = []
            query = """select count(sale.id), cli.name
                                from sale_order as sale, res_partner as cli
                                where cli.id = sale.partner_id
                                      and type_eliterp='pedido_venta'
                                      and sale.state_pedido_eliterp != 'cancel'
                                      group by cli.name"""
            self.env.cr.execute(query)
            datos_clientes = self.env.cr.dictfetchall()
            for cli in datos_clientes:
                data.append({'label': cli['name'],'value':cli['count']})
            return [{'key':'Acumulado', 'values':data, 'flag':False}]

    def get_tablero_1(self):
        data=[]
        query = """select t1.sum as "Total Pedidos", t2.sum as "Total de Cotizaciones", t1.asesor as "Asesor" from
                          (select sum(sale.amount_untaxed), asesor.name_related as asesor
                                      from sale_order as sale, res_partner as cli, hr_employee as asesor
                                      where cli.id = sale.partner_id
                                            and cli.consultant_sale_id = asesor.id
                                            and type_eliterp='pedido_venta'
                                            and sale.state_pedido_eliterp != 'cancel'
                                            and extract(MONTH FROM sale.date_created) = extract(MONTH FROM current_date)
                                      group by asesor.name_related) t1 left join
                          (select sum(sale.amount_untaxed), asesor.name_related as asesor
                                      from sale_order as sale, res_partner as cli, hr_employee as asesor
                                      where cli.id = sale.partner_id
                                            and cli.consultant_sale_id = asesor.id
                                            and sale.type_eliterp='draft'
                                            and sale.state_cotizacion_eliterp not in ('draft','denied','cancel')
                                            and sale.have_pedidos_ventas = False
                                            and extract(MONTH FROM sale.date_created) = extract(MONTH FROM current_date)
                                      group by asesor.name_related) t2
                    on t1.asesor = t2.asesor"""
        self.env.cr.execute(query)
        datas = self.env.cr.dictfetchall()
        for x in range(0, len(datas)):
            datas[x].update({'Total Pedidos': 0.00 if datas[x]['Total Pedidos']==None else datas[x]['Total Pedidos'],
                             'Total de Cotizaciones': 0.00 if datas[x]['Total de Cotizaciones']==None else datas[x]['Total de Cotizaciones']})
        for x in range(0,len(datas)):
            datas[x].update({'Total Pedidos':"$"+"{:.2f}".format(float(datas[x]['Total Pedidos'])),
                             'Total de Cotizaciones':"$"+"{:.2f}".format(float(datas[x]['Total de Cotizaciones']))})
        return datas

    def get_tablero_2(self):
        data = []
        query = """select sum(sale.amount_untaxed), cli.name
                                        from sale_order as sale, res_partner as cli
                                        where cli.id = sale.partner_id
                                              and type_eliterp='pedido_venta'
                                              and sale.state_pedido_eliterp != 'cancel'
                                              group by cli.name"""
        self.env.cr.execute(query)
        datos_clientes = self.env.cr.dictfetchall()
        for cli in datos_clientes:
            data.append({'cliente': cli['name'], 'monto':"$""{:.2f}".format(cli['sum'])})
        return data

    def get_tablero_3(self):
        '''Data de Histórico de Facturación'''
        data = []
        fecha = fields.date.today()
        for x in range(-2, 1):
            query = """select cast((sum(inv.amount_untaxed)) as float)
                                           from account_invoice as inv
                                           where extract(MONTH FROM inv.date_invoice) = EXTRACT(month FROM current_date + '%s  month'::interval)
                                           and extract(YEAR FROM inv.date_invoice) = EXTRACT(YEAR FROM current_date + '%s month'::interval)
                                           and inv.type='out_invoice'
                                           and inv.state in ('open', 'paid')""" % (x, x)
            self.env.cr.execute(query)
            facturas = self.env.cr.dictfetchall()
            mes = fecha.month + x
            data.append({
                'mes': self.get_mes(mes),
                'valor': "{:.2f}".format(float(facturas[0]['sum'])) if facturas[0]['sum'] else 0.00
            })
        return data

    @api.multi
    def get_journal_dashboard_datas(self):
        return {
            'mas_tablero_1':self.get_tablero_1(),
            'mas_tablero_2':self.get_tablero_2(),
            'mas_tablero_3': self.get_tablero_3()
        }

    @api.multi
    def action_create_new(self):
        ctx = self._context.copy()
        model = 'account.invoice'
        if self.type == 'sale':
            ctx.update({'journal_type': self.type, 'default_type': 'out_invoice', 'type': 'out_invoice', 'default_journal_id': self.id})
            if ctx.get('refund'):
                ctx.update({'default_type':'out_refund', 'type':'out_refund'})
            view_id = self.env.ref('account.invoice_form').id
        elif self.type == 'purchase':
            ctx.update({'journal_type': self.type, 'default_type': 'in_invoice', 'type': 'in_invoice', 'default_journal_id': self.id})
            if ctx.get('refund'):
                ctx.update({'default_type': 'in_refund', 'type': 'in_refund'})
            view_id = self.env.ref('account.invoice_supplier_form').id
        else:
            ctx.update({'default_journal_id': self.id})
            view_id = self.env.ref('account.view_move_form').id
            model = 'account.move'
        return {
            'name': _('Create invoice/bill'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': model,
            'view_id': view_id,
            'context': ctx,
        }

    @api.multi
    def create_cash_statement(self):
        ctx = self._context.copy()
        ctx.update({'journal_id': self.id, 'default_journal_id': self.id, 'default_journal_type': 'cash'})
        return {
            'name': _('Create cash statement'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.bank.statement',
            'context': ctx,
        }

    @api.multi
    def open_action(self):
        action_name = self._context.get('action_name', False)
        tipo = self._context.get('tipo', False)
        mes = self._context.get('mes', False)
        ctx = self._context.copy()
        ctx.pop('group_by', None)
        [action] = self.env.ref(action_name).read()
        fecha = fields.date.today()
        if tipo == 'facturas':
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
                ('type', '=', 'out_invoice'),
                ('state', 'in', ('open', 'paid')),
                ('date_invoice', '<=', fecha_fin.strftime('%Y-%m-%d')),
                ('date_invoice', '>=', fecha_inicio.strftime('%Y-%m-%d'))
            ]
            ctx.update({'group_by': 'date_invoice:month'})
            action['domain'] = domain
        if tipo=='clientes':
            ctx.update({'group_by': 'partner_id'})
        if tipo=='asesor':
            ctx.update({'group_by': 'consultant_sale_id'})
        action['context'] = ctx
        return action

    @api.multi
    def open_spend_money(self):
        return self.open_payments_action('outbound')

    @api.multi
    def open_collect_money(self):
        return self.open_payments_action('inbound')

    @api.multi
    def open_transfer_money(self):
        return self.open_payments_action('transfer')

    @api.multi
    def open_payments_action(self, payment_type):
        ctx = self._context.copy()
        ctx.update({
            'default_payment_type': payment_type,
            'default_journal_id': self.id
        })
        ctx.pop('group_by', None)
        action_rec = self.env['ir.model.data'].xmlid_to_object('account.action_account_payments')
        if action_rec:
            action = action_rec.read([])[0]
            action['context'] = ctx
            action['domain'] = [('journal_id','=',self.id),('payment_type','=',payment_type)]
            return action

    @api.multi
    def open_action_with_context(self):
        action_name = self.env.context.get('action_name', False)
        if not action_name:
            return False
        ctx = dict(self.env.context, default_journal_id=self.id)
        if ctx.get('search_default_journal', False):
            ctx.update(search_default_journal_id=self.id)
        ctx.pop('group_by', None)
        ir_model_obj = self.env['ir.model.data']
        model, action_id = ir_model_obj.get_object_reference('account', action_name)
        [action] = self.env[model].browse(action_id).read()
        action['context'] = ctx
        if ctx.get('use_domain', False):
            action['domain'] = ['|', ('journal_id', '=', self.id), ('journal_id', '=', False)]
            action['name'] += ' for journal ' + self.name
        return action

    @api.multi
    def create_bank_statement(self):
        """return action to create a bank statements. This button should be called only on journals with type =='bank'"""
        self.bank_statements_source = 'manual'
        action = self.env.ref('account.action_bank_statement_tree').read()[0]
        action.update({
            'views': [[False, 'form']],
            'context': "{'default_journal_id': " + str(self.id) + "}",
        })
        return action



