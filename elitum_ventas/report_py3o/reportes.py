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

STATES = {
    'draft': 'Borrador',
    'open': 'Ingresado',
    'paid': 'Pagado'
}


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

                'fecha_actual': fields.date.today(),
                'total': format(sum(line['total'] for line in lines), ',.2f')
            })
        res = super(ParserReVentas, self)._extend_parser_context(context_instance, report_xml)
        return res


class ReporteVentas(models.TransientModel):
    _name = 'reporte.ventas'
    _description = 'Reporte Ventas'

    def get_lines(self, context):
        data = []
        object_sales = self.env['account.invoice']
        arg = []
        if context['tipo_cliente'] != 'todos':
            if isinstance(context['cliente'], int):
                partner = context['cliente']
            else:
                partner = context['cliente'].id
            arg.append(('partner_id', '=', partner))
        arg.append(('date_invoice', '>=', context['fecha_inicio']))
        arg.append(('date_invoice', '<=', context['fecha_fin']))
        arg.append(('type', '=', 'out_invoice'))
        arg.append(('state', 'in', ('open', 'paid')))
        pedidos = object_sales.search(arg)
        total = 0.00
        for line in pedidos:
            data.append({'fecha': line.date_invoice,
                         'cliente': line.partner_id.name,
                         'factura': line.numero_factura_interno,
                         'valor': format(line.amount_total, ',.2f'),
                         'subtotal': format(line.amount_untaxed, ',.2f'),
                         'iva': format(line.amount_tax, ',.2f'),
                         'estado': STATES.get(line.state),
                         'total': line.amount_total})
        data = sorted(data, key=lambda k: k['cliente']) # Ordenar por cliente
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
