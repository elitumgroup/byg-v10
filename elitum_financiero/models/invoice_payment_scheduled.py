# -*- encoding: utf-8 -*-
#########################################################################
# Copyright (C) 2017 Ing. Mario Rangel, Elitum Group                    #
#                                                                       #
# This program is free software: you can redistribute it and/or modify  #
# it under the terms of the GNU General Public License as published by  #
# the Free Software Foundation, either version 3 of the License, or     #
# (at your option) any later version.                                   #
#                                                                       #
# This program is distributed in the hope that it will be useful,       #
# but WITHOUT ANY WARRANTY; without even the implied warranty of        #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
# GNU General Public License for more details.                          #
#                                                                       #
# You should have received a copy of the GNU General Public License     #
# along with this program.  If not, see <http://www.gnu.org/licenses/>. #
#########################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def add_payment_scheduled(self):
        '''
        :return: TODO
        view = self.env.ref('elitum_financiero.elitum_invoice_payment_scheduled_form_wizard')
        context = {
            'default_invoice_id': self.id,
            'default_saldo_pendiente': self.residual
        }
        return {
            'name': "Pago Programado",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.invoice.payment.scheduled',
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }
        '''
        return self.write({'line_approval': 'aprobado'})

    scheduled_payment_id = fields.Many2one('account.invoice.payment.scheduled', string='Pago Programado')


class ScheduledPaymentsPurchases(models.Model):
    # Métodos
    @api.model
    def create(self, values):
        if values['value'] > values['saldo_pendiente']:
            raise UserError(_("Valor a pagar mayor al saldo pendiente"))
        if values['value'] == 0:
            raise UserError(_("Valor de pago debe ser mayor a 0"))
        if values['payment_type'] == 'total':
            type_approval = 'aprobado'
        else:
            type_approval = 'aprobado_parcial'
        invoice = self.env['account.invoice'].browse(values['invoice_id'])
        pay = super(ScheduledPaymentsPurchases, self).create(values)
        invoice.write({
            'line_approval': type_approval,
            'scheduled_payment_id': pay.id,
            'have_scheduled_payment': True
        })
        return pay

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if self.payment_type == 'total':
            self.value = self.saldo_pendiente
        else:
            self.value = 0

    # Tabla y su descripción (UI)
    _name = 'account.invoice.payment.scheduled'
    _description = 'Modelo - Pagos Factura Proveedor'

    # Columnas
    name = fields.Char(u'Título', default='Pago Programado')
    invoice_id = fields.Many2one('account.invoice')
    saldo_pendiente = fields.Float(store=False)
    payment_type = fields.Selection([('total', 'Total'), ('parcial', 'Parcial')], required=True, default='total')
    value = fields.Float('Valor', required=True)
    fecha = fields.Date('Fecha de Pago', default=fields.Date.context_today, required=True)
    way_to_pay = fields.Selection([('efectivo', 'Efectivo'), ('cheque', 'Cheque')], required=True)
    bank_id = fields.Many2one('res.bank')
    pagada = fields.Boolean(default=False)