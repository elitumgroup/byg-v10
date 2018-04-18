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

DATA_PORCENTAJE = [
    ('total', 'Total del Pedido'),
    ('diez', '10 %'),
    ('treinta', '30 %'),
    ('cincuenta', '50 %')
]


class PedidosVentasFacturas(models.Model):
    # HACER ?
    def _load_pedido_ventas(self):
        return

    _name = 'pedidos.ventas.facturas'

    _description = 'Pedido de Ventas para Facturas'

    name = fields.Char()
    pedidos_ventas_ids = fields.One2many('sale.order', 'account_invoice_id', 'Pedidos de Venta')


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        res = super(AccountInvoice, self)._onchange_partner_id()
        pedidos_ventas = self.env['sale.order'].search(
            [('partner_id', '=', self.partner_id.id), ('type_eliterp', '=', 'pedido_venta')])
        if self.partner_id:
            if self.partner_id.consultant_sale_id:
                self.consultant_sale_id = self.partner_id.consultant_sale_id
        return res

    @api.depends('invoice_line_ids.price_subtotal')
    def _get_total_discount(self):
        if not self.invoice_line_ids:
            return 0.00
        else:
            total_descuento = 0.00
            for line in self.invoice_line_ids:
                sub_total = round(line.price_unit * line.quantity * (line.discount / 100), 2)
                total_descuento += sub_total
            self.update({'total_discount': total_descuento})

    pedidos_ventas_ids = fields.One2many('sale.order', 'account_invoice_id', 'Pedidos de Venta')  # ?
    descuento_global = fields.Boolean(string=u'Descuento Global', default=False)
    descuento_global_amount = fields.Float(string=u'Descuento')
    base_cero_iva = fields.Float(string=u'Subtotal Cero', store=True, readonly=True, compute='_compute_amount')
    base_gravada = fields.Float(string=u'Subtotal Iva', store=True, readonly=True, compute='_compute_amount')
    total_discount = fields.Float(string=u'Descuento', compute='_get_total_discount', readonly=True, store=True)
    payment_metod_ec = fields.Many2one('account.journal.payment.method', string='Forma de Pago')
    date_invoice = fields.Date(string=u'Fecha Emisión',
                               readonly=True, states={'draft': [('readonly', False)]}, index=True,
                               help="Keep empty to use the current date", copy=False, default=fields.Date.context_today,
                               required=True)
    # MARZ - Anticipo de pedido
    is_anticipo = fields.Boolean(string='Anticipo de Pedido?', default=False)
    pedido_relacionado = fields.Many2one('sale.order', 'Pedido Relacionado')  # Pedido de Venta
    operaciones_pedido = fields.Float(compute='_get_saldo_pedido')
    saldo_pendiente_pedido = fields.Float('Saldo Pendiente en Pedido')
    porcentaje_anticipo = fields.Selection(DATA_PORCENTAJE, string='Porcentaje de Anticipo', default='diez')

    def aplicar_descuento_global(self):
        if not self.invoice_line_ids:
            raise Warning("No hay líneas para Aplicar Descuento")
        else:
            for line in self.invoice_line_ids:
                line.update({'discount': self.descuento_global_amount})
        return

    @api.multi
    def _get_anticipos(self, pedido):
        '''Buscar facturas (anticipos) del mismo pedido'''
        arg = []
        arg.append(('pedido_relacionado', '=', pedido.id))
        anteriores = self.env['account.invoice'].search(arg)
        value_anteriores = 0.00
        value_anteriores = sum(line.amount_untaxed for line in anteriores)
        return round(value_anteriores, 2)

    @api.depends('amount_untaxed', 'pedido_relacionado')
    def _get_saldo_pedido(self):
        '''Calcular saldo pendiente en pedido'''
        if self.pedido_relacionado:
            value = 0.00
            lines_pedido = sum(line.price_unit for line in self.pedido_relacionado.order_line.filtered(lambda x: x.facturado))
            value = self.pedido_relacionado.amount_untaxed - self.amount_untaxed - lines_pedido # Sin iva
            self.saldo_pendiente_pedido = round(value - self._get_anticipos(self.pedido_relacionado), 2)

    def _get_amount_anticipo(self, pedido):
        value = 0.00
        lines_pedido = 0.00
        porcentaje = self.porcentaje_anticipo
        # Calculamos porcentaje de anticipo
        lines_pedido = sum(line.price_unit for line in self.pedido_relacionado.order_line.filtered(lambda x: x.facturado))
        if porcentaje == 'diez':
            value = (pedido.amount_untaxed - lines_pedido) * 0.10
        elif porcentaje == 'treinta':
            value = (pedido.amount_untaxed - lines_pedido) * 0.30
        else:
            value = (pedido.amount_untaxed - lines_pedido) * 0.50
        return round(value, 2)

    @api.onchange('pedido_relacionado', 'porcentaje_anticipo')
    def _onchange_pedido_relacionado(self):
        # Creamos una línea de factura al cambiar de pedido del cliente
        data = []
        if self.pedido_relacionado:
            value_anteriores = 0.00
            mensaje = 'Anticipo de pedido No. ' + self.pedido_relacionado.name
            if self.porcentaje_anticipo == 'total':
                lines_pedido = sum(line.price_unit for line in self.pedido_relacionado.order_line.filtered(lambda x: x.facturado))
                value_anteriores = self._get_anticipos(self.pedido_relacionado) + lines_pedido
                mensaje = 'Pago final de pedido No. ' + self.pedido_relacionado.name
            impuesto_venta = self.env['account.tax'].browse(113).id # Predefinido, id = 113 (IVA 12% COBRADO)
            cuenta_anticipo = self.env['account.account'].browse(1292).id # Predefinido, id = 1292 (ANTICIPOS DE CLIENTES)
            data.append([
                0,
                0,
                {
                    'name': mensaje,
                    'account_id': cuenta_anticipo,
                    'price_unit': round(self.pedido_relacionado.amount_untaxed - value_anteriores, 2) if self.porcentaje_anticipo == 'total' else self._get_amount_anticipo(self.pedido_relacionado),
                    'quantity': 1.0,
                    'discount': 0.0,
                    'invoice_line_tax_ids': [(6, 0, [impuesto_venta])],
                    'account_analytic_id': self.pedido_relacionado.project_id.id or False,
                }
            ])
        self.update({'invoice_line_ids': data})
