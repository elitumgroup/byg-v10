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


class partner_purchase_type(models.Model):
    _name = 'partner.purchase.type'

    _description = 'Tipo Proveedor'

    def create(self, vals):
        if 'name' in vals:
            code = (vals['name'][:3]).upper()
            vals.update({'code': code})
        return super(partner_purchase_type, self).create(vals)

    name = fields.Char('Nombre')
    code = fields.Char(u'Código')


class res_partner(models.Model):
    _inherit = "res.partner"

    @api.multi
    def _purchase_invoice_count(self):
        PurchaseOrder = self.env['purchase.order']
        Invoice = self.env['account.invoice']
        for partner in self:
            partner.purchase_order_count = PurchaseOrder.search_count([('partner_id', 'child_of', partner.id)])
            facturas = Invoice.search([('partner_id', '=', partner.id), ('state', '!=', 'cancel')])
            partner.supplier_invoice_count = round(float(sum(factura.amount_total for factura in facturas)), 2)
            partner.saldo_pendiente = round(float(sum(factura.residual for factura in facturas)), 2)

    @api.onchange('property_account_payable_id')
    def onchange_cuenta_payable(self):
        if self.property_account_payable_id:
            self.property_account_receivable_id = self.property_account_payable_id.id

    # MARZ
    @api.onchange('rise_category', 'rise_activity')
    def onchange_max_amount(self):
        category_acivity = self.env['rise.category.activity'].search([
            ('category_id', '=', self.rise_category.id),
            ('activity_id', '=', self.rise_activity.id),
            ('status', '=', True)
        ])
        self.max_amount = category_acivity.max_amount

    supplier_invoice_count = fields.Float(compute='_purchase_invoice_count', string='Facturado')
    saldo_pendiente = fields.Float(compute='_purchase_invoice_count', string='Saldo')
    rise_category = fields.Many2one('rise.category', u'Categoría')
    rise_activity = fields.Many2one('rise.activity', 'Actividad')
    max_amount = fields.Float(u'Monto Máximo')
    purchase_type = fields.Many2many('partner.purchase.type',
                                     'rel_partner_purchase_type',
                                     'purchase_id',
                                     'res_partner_id',
                                     'Tipo de Compra')
    payment_conditions = fields.Selection([('cash', 'Contado'), ('credit', u'Crédito')], u'Condiciones de Pago')
    way_to_pay = fields.Selection([('transfer', 'Transferencia'), ('check', 'Cheque'), ('cash', 'Efectivo')],
                                  u'Formas de Pago')
    bank_id = fields.Many2one('res.bank', 'Banco')
    type_bank_account = fields.Selection([('saving', 'Ahorro'), ('current', 'Corriente')], u'Condiciones de Pago')
    number_bank = fields.Char(u'No. Cuenta')
    property_account_payable_id = fields.Many2one('account.account',
                                                  string='Cuenta a Cobrar',
                                                  domain=[('tipo_contable', '=', 'movimiento')])
