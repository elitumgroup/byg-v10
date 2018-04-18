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
import logging

_logger = logging.getLogger(__name__)

MESSAGES = {
    'todos': 'Todos',
    'proveedor': 'Proveedor',
    'cuenta': 'Cuenta'
}

STATES = {
    'draft': 'Borrador',
    'open': 'Ingresada',
    'paid': 'Pagada'
}

class ParserReportCompras(models.TransientModel):
    _inherit = 'py3o.report'

    @api.multi
    def _extend_parser_context(self, context_instance, report_xml):
        if 'reporte_compras' in self._context:
            reporte = self.env['elitumgroup.report.purchases'].browse(self._context['active_id'])
            lines = reporte.get_lines(context_instance.localcontext)
            context_instance.localcontext.update({
                'tipo': MESSAGES.get(self._context['tipo_reporte'], ''),
                'get_lines': lines,
                'fecha_actual': fields.date.today(),
            })
        if 'reporte_tipo_compra' in self._context:
            reporte = self.env['elitumgroup.report.purchase.type'].browse(self._context['active_id'])
            lines = reporte.get_lines(context_instance.localcontext)
            context_instance.localcontext.update({
                'tipo': MESSAGES.get(self._context['tipo_reporte'], ''),
                'get_lines': lines,
                'fecha_actual': fields.date.today(),
            })
        res = super(ParserReportCompras, self)._extend_parser_context(context_instance, report_xml)
        return res


class ReporteCompras(models.TransientModel):
    _name = 'elitumgroup.report.purchases'
    _description = 'Reporte de Compras'

    def get_lines(self, context):
        data = []
        object_invoice = self.env['account.invoice']
        arg = []
        if context['tipo_reporte'] != 'todos':
            if isinstance(context['proveedor'], int):
                partner = context['proveedor']
            else:
                partner = context['proveedor'].id
            arg.append(('partner_id', '=', partner))
        arg.append(('date_invoice', '>=', context['fecha_inicio']))
        arg.append(('date_invoice', '<=', context['fecha_fin']))
        arg.append(('state', '!=', 'cancel'))
        arg.append(('type', '=', 'in_invoice'))
        facturas = object_invoice.search(arg)
        for line in facturas:
            data.append({
                'proveedor': line.partner_id.name,
                'factura': line.numero_factura_interno,
                'fecha': line.date_invoice,
                'subtotal': format(line.amount_untaxed, ',.2f'),
                'iva': format(line.amount_tax, ',.2f'),
                'total': format(line.amount_total, ',.2f'),
                'estado': STATES.get(line.state)
            })
        data = sorted(data, key=lambda k: k['proveedor']) # Ordenar por proveedor
        return data

    def imprimir_reporte_compras_xls(self):
        reporte = []
        reporte.append(self.id)
        result = {
            'type': 'ir.actions.report.xml',
            'report_name': 'elitum_compras.reporte_compras',
            'datas': {'ids': reporte},
            'context': {
                'reporte_compras': True,
                'fecha_inicio': self.fecha_inicio,
                'fecha_fin': self.fecha_fin,
                'tipo_reporte': self.tipo_reporte,
                'proveedor': self.proveedor.id if len(self.proveedor) != 0 else False,
            }
        }
        return result

    def imprimir_reporte_compras_pdf(self):
        return self.env['report'].get_action(self, 'elitum_compras.reporte_compras_pdf')

    fecha_inicio = fields.Date('Fecha Inicio', required=True)
    fecha_fin = fields.Date('Fecha Fin', required=True)
    tipo_reporte = fields.Selection([
        ('todos', 'Todos'),
        ('proveedor', 'Proveedor')], 'Tipo de Reporte', default='todos')
    proveedor = fields.Many2one('res.partner', 'Proveedor')


class ReporteTipoCompra(models.TransientModel):
    _name = 'elitumgroup.report.purchase.type'
    _description = 'Reporte de Tipo de Compra (Gasto)'

    def get_lines(self, context):
        data = []
        object_invoice = self.env['account.invoice']
        arg = []
        arg.append(('date_invoice', '>=', context['fecha_inicio']))
        arg.append(('date_invoice', '<=', context['fecha_fin']))
        arg.append(('state', '!=', 'cancel'))
        arg.append(('type', '=', 'in_invoice'))
        facturas = object_invoice.search(arg)
        for line in facturas:
            line_invoice = line.invoice_line_ids
            for x in line_invoice:
                data.append({
                    'id': x.account_id.id,
                    'cuenta': x.account_id.name,
                    'proveedor': line.partner_id.name,
                    'factura': line.numero_factura_interno,
                    'fecha': line.date_invoice,
                    'total': format(x.price_subtotal, ',.2f')
                })
        if context['tipo_reporte'] != 'todos':
            if isinstance(context['cuenta'], int):
                cuenta = context['cuenta']
            else:
                cuenta = context['cuenta'].id
            data = filter(lambda x: x['id'] == cuenta, data) # Filtramos por cuenta
        data = sorted(data, key=lambda k: k['cuenta'])  # Ordenar por cuenta
        return data

    def imprimir_reporte_tipo_compra_xls(self):
        reporte = []
        reporte.append(self.id)
        result = {
            'type': 'ir.actions.report.xml',
            'report_name': 'elitum_compras.reporte_tipo_compra',
            'datas': {'ids': reporte},
            'context': {
                'reporte_tipo_compra': True,
                'fecha_inicio': self.fecha_inicio,
                'fecha_fin': self.fecha_fin,
                'tipo_reporte': self.tipo_reporte,
                'cuenta': self.cuenta.id if len(self.cuenta) != 0 else False,
            }
        }
        return result

    def imprimir_reporte_tipo_compra_pdf(self):
        return self.env['report'].get_action(self, 'elitum_compras.reporte_tipo_compra_pdf')

    fecha_inicio = fields.Date('Fecha Inicio', required=True)
    fecha_fin = fields.Date('Fecha Fin', required=True)
    tipo_reporte = fields.Selection([
        ('todos', 'Todos'),
        ('cuenta', 'Cuenta')], 'Tipo de Reporte', default='todos')
    cuenta = fields.Many2one('account.account', string='Cuenta', domain=[('tipo_contable', '=', 'movimiento')])
