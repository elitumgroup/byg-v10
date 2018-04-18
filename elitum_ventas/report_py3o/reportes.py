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


class ParserReVentas(models.TransientModel):
    _inherit = 'py3o.report'

    @api.multi
    def _extend_parser_context(self, context_instance, report_xml):
        if 'reporte_ventas' in self._context:
            reporte = self.env['reporte.ventas'].browse(self._context['active_id'])
            lines = reporte.get_lines(context_instance.localcontext)
            context_instance.localcontext.update({
                'get_lines': lines,
                'cliente': "Todos" if self._context['cliente'] == False else self.env['res.partner'].browse(
                    self._context['cliente']).name,
                'asesor': "Todos" if self._context['asesor'] == False else self.env['hr.employee'].browse(
                    self._context['asesor']).name,
                'fecha_actual': fields.date.today(),
                'total': format(sum(line['total'] for line in lines), ',.2f')
            })
        res = super(ParserReVentas, self)._extend_parser_context(context_instance, report_xml)
        return res


class ReporteVentas(models.TransientModel):
    _name = 'reporte.ventas'
    _description = 'Reporte Ventas'

    def get_estado(self, estado):
        if estado == 'invoice':
            return "Facturado"
        if estado == 'order':
            return "Emitido"
        if estado == 'invoice_parcial':
            return "Facturado Parcial"

    def get_lines(self, context):
        data = []
        arg = []
        if context['tipo_cliente'] != 'todos':
            if isinstance(context['cliente'], int):
                arg.append(('partner_id', '=', context['cliente']))
            else:
                arg.append(('partner_id', '=', context['cliente'].id))
        if context['tipo_asesor'] != 'todos':
            if isinstance(context['cliente'], int):
                arg.append(('partner_id', '=', context['asesor']))
            else:
                arg.append(('consultant_sale_id', '=', context['asesor'].id))
        arg.append(('date_created', '>=', context['fecha_inicio']))
        arg.append(('date_created', '<=', context['fecha_fin']))
        arg.append(('type_eliterp', '=', 'pedido_venta'))
        pedidos = self.env['sale.order'].search(arg)
        total = 0.00
        for pedido in pedidos:
            data.append({'fecha': pedido.date_created,
                         'cliente': pedido.partner_id.name,
                         'valor': format(pedido.amount_total, ',.2f'),
                         'total': pedido.amount_total,
                         'asesor': pedido.consultant_sale_id.name if pedido.consultant_sale_id.name else "",
                         'estado': self.get_estado(pedido.state_pedido_eliterp),
                         'documento': pedido.name})
        return data

    def imprimir_reporte_ventas(self):
        reporte = []
        reporte.append(self.id)
        result = {'type': 'ir.actions.report.xml',
                  'report_name': 'elitum_ventas.reporte_ventas',
                  'datas': {'ids': reporte},
                  'context': {'reporte_ventas': True,
                              'fecha_inicio': self.fecha_inicio,
                              'fecha_fin': self.fecha_fin,
                              'tipo_cliente': self.tipo_cliente,
                              'cliente': self.cliente.id if len(self.cliente) != 0 else False,
                              'tipo_asesor': self.tipo_asesor,
                              'asesor': self.asesor.id if len(self.asesor) != 0 else False,
                              }
                  }
        return result

    def imprimir_reporte_ventas_pdf(self):
        return self.env['report'].get_action(self, 'elitum_ventas.reporte_ventas_pdf')

    fecha_inicio = fields.Date('Fecha Inicio', required=True)
    fecha_fin = fields.Date('Fecha Fin', required=True)
    tipo_cliente = fields.Selection([
        ('todos', 'Todos'),
        ('cliente', 'Individual')], 'Tipo de Cliente', default='todos')
    cliente = fields.Many2one('res.partner', 'Cliente')
    tipo_asesor = fields.Selection([
        ('todos', 'Todos'),
        ('asesor', 'Individual')], 'Tipo de Asesor', default='todos')
    asesor = fields.Many2one('hr.employee', 'Asesor')
