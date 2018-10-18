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

from odoo.exceptions import except_orm, Warning, RedirectWarning
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import datetime
from pytz import timezone
from odoo.tools import amount_to_text_en, float_round, float_is_zero
import math


class QWeb(models.AbstractModel):
    _inherit = 'ir.qweb'


class AccountVoucherSaldoELiterp(models.Model):
    _name = 'account.voucher.saldo.eliterp'

    _description = 'Saldo en Pago'

    def confirm_saldo(self):
        voucher = self.env['account.voucher'].browse(self._context['active_id'])
        voucher.write({'account_saldo': self.account_saldo.id,
                       'valor_saldo': self.saldo,
                       'mostrar_cuenta': True,
                       'flag_saldo': True})
        voucher.validar_voucher_eliterp()
        return True

    saldo = fields.Float('Saldo')
    account_saldo = fields.Many2one('account.account', domain=[('tipo_contable', '=', 'movimiento')])


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.multi
    def post_eliterp(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(
                    _("Only a draft payment can be posted. Trying to post a payment in state %s.") % rec.state)

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            # Use the right sequence to set the name
            if rec.payment_type == 'transfer':
                sequence_code = 'account.payment.transfer'
            else:
                if rec.partner_type == 'customer':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.customer.invoice'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.customer.refund'
                if rec.partner_type == 'supplier':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.supplier.refund'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.supplier.invoice'
            rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(
                sequence_code)

            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            move = rec._create_payment_entry(amount)

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the tran sfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = move.line_ids.filtered(
                    lambda r: r.account_id == rec.company_id.transfer_account_id)
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()

            rec.write({'state': 'posted', 'move_name': move.name})


class PaymentTypeLines(models.Model):
    _name = "payment.type.lines"

    _description = 'Linea De Pagos'

    @api.onchange('name_girador')
    def onchange_name_girador(self):
        self.if_beneficiario = True

    tipo_de_pagos = fields.Selection([('bank', 'Cheque'),
                                      ('cash', 'Efectivo'),
                                      ('transferencia', 'Transferencia')], string='Tipo de Pago')

    name_girador = fields.Char('Nombre')
    numero_cuenta = fields.Char('No. Cuenta')
    numero_cheque = fields.Char('No. Cheque')
    banco = fields.Many2one('res.bank', 'Banco')
    cuenta = fields.Many2one('account.account', 'Cuenta', domain=[('tipo_contable', '=', 'movimiento')])
    amount = fields.Float('Monto')
    voucher_id = fields.Many2one('account.voucher', 'Cobro')
    time_type = fields.Selection([('corriente', 'Corriente'), ('postfechado', 'A Fecha')], string='Tipo Cheque')
    date_created_eliterp = fields.Date('Fecha Emitido')
    date_due = fields.Date('Fecha Vencimiento')
    if_beneficiario = fields.Boolean('Es Beneficiario?', default=False)
    asiento_contable = fields.Many2one('account.move', string=u'Asiento Contable')


class LineRefundCharges(models.Model):
    _name = 'lines.refund.charges'

    _description = u'Linea de Nota de Crédito'

    invoice_id = fields.Many2one('account.invoice', u'Nota de Crédito')
    name = fields.Char(u'Nota de Crédito', related="invoice_id.numero_factura_interno")
    journal_id = fields.Many2one('account.journal', string="Forma de Pago",
                                 domain=[('type', 'in', ('bank', 'cash'))])
    fecha_vencimiento_factura = fields.Date('Fecha Vencimiento')
    valor_nota = fields.Float('Total Nota')
    aplicar_nota = fields.Boolean('Aplicar', default=False)
    facturas_afectar = fields.Many2one('lines.invoice.charges', 'Factura Aplicar')
    voucher_id = fields.Many2one('account.voucher', 'Comprobante de Cobro')


class LineInvoiceCharges(models.Model):
    _name = 'lines.invoice.charges'

    _description = 'Linea de Carga de Facturas'

    invoice_id = fields.Many2one('account.invoice', 'Factura')
    name = fields.Char('Factura', related="invoice_id.numero_factura_interno")
    journal_id = fields.Many2one('account.journal', string="Forma de Pago",
                                 domain=[('type', 'in', ('bank', 'cash'))])
    fecha_vencimiento_factura = fields.Date('Fecha Vencimiento')
    valor_factura = fields.Float('Total Factura')
    monto_pago = fields.Float('Pago')
    monto_adeudado = fields.Float('Valor Adeudado')
    # MARZ
    valor_aprobado_pago = fields.Float('Pago Programado')
    voucher_id = fields.Many2one('account.voucher', 'Comprobante de Cobro')


class LineSupplierCharges(models.Model):
    _name = 'lines.supplier.charges'

    _description = 'Linea de Carga de Proveedor '

    account_id = fields.Many2one('account.account', string="Cuenta", domain=[('tipo_contable', '=', 'movimiento')])
    monto_pago = fields.Float('Valor')
    voucher_id = fields.Many2one('account.voucher', 'Comprobante de Cobro')


class AccountVoucherCancelReason(models.Model):
    _name = 'account.voucher.cancel.reason'

    _description = 'Razon para Cancelar Voucher'

    description = fields.Text(u'Descripción', required=True)

    def confirm_cancel_reason(self):
        voucher = self.env['account.voucher'].browse(self._context['active_id'])
        move_id = voucher.move_id
        for line in move_id.line_ids:
            if line.full_reconcile_id:
                line.remove_move_reconcile()
        move_id.with_context(from_voucher=True, id_voucher=voucher.id).reverse_moves(voucher.date,
                                                                                     voucher.journal_id or False)
        move_id.write({'state': 'cancel', 'ref': self.description})
        voucher.write({'state': 'cancel'})

        return


class AccountVoucher(models.Model):
    _inherit = "account.voucher"

    def action_vocher_cancel_reason(self):
        context = dict(self._context or {})
        return {
            'name': "Explique la Razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.voucher.cancel.reason',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

    def imprimir_comprobante_ingreso(self):
        return self.env['report'].get_action(self, 'elitum_financiero.reporte_comprobante_ingreso')

    def imprimir_comprobante_egreso(self):
        return self.env['report'].get_action(self, 'elitum_financiero.reporte_comprobante_egreso')

    @api.multi
    def _get_total(self):
        for voucher in self:
            total = 0.00
            for line in voucher.lineas_tipos_pagos:
                total += line.amount
            voucher.total = total

    @api.multi
    def _get_total_factura(self):
        for voucher in self:
            total = 0.00
            for line in voucher.lineas_cobros_facturas:
                total += line.monto_adeudado
            voucher.total_factura = total

    @api.multi
    def voucher_move_line_create_eliterp(self, line_total, move_id, company_currency, current_currency):
        for linea_cobro in self.lineas_cobros_facturas:
            amount = linea_cobro.valor_factura
            line = linea_cobro.invoice_id
            self.journal_id.default_credit_account_id.id
            move_line = {
                'journal_id': self.journal_id.id,
                'name': line.name or '/',
                'account_id': self.journal_id.default_credit_account_id.id,
                'move_id': move_id,
                'partner_id': self.partner_id.id,
                'quantity': 1,
                'credit': abs(amount) if self.voucher_type == 'purchase' else 0.0,
                'debit': abs(amount) if self.voucher_type == 'sale' else 0.0,
                'date': self.account_date,
            }
            self.env['account.move.line'].with_context(apply_taxes=True).create(move_line)
        return line_total

    @api.multi
    def first_move_line_get_eliterp(self, move_id, company_currency, current_currency):
        total_cobro = 0
        for forma_cobro in self.lineas_tipos_pagos:
            total_cobro += forma_cobro.amount
        amount = total_cobro
        debit = credit = 0.0
        if self.voucher_type == 'purchase':
            debit = self._convert_amount(amount)
        elif self.voucher_type == 'sale':
            credit = self._convert_amount(amount)
        if debit < 0.0: debit = 0.0
        if credit < 0.0: credit = 0.0
        sign = debit - credit < 0 and -1 or 1
        # set the first line of the voucher
        move_line = {
            'name': self.name or '/',
            'debit': debit,
            'credit': credit,
            'account_id': self.account_id.id,
            'move_id': move_id,
            'journal_id': self.journal_id.id,
            'partner_id': self.partner_id.id,
            'currency_id': company_currency != current_currency and current_currency or False,
            'amount_currency': (sign * abs(amount)  # amount < 0 for refunds
                                if company_currency != current_currency else 0.0),
            'date': self.account_date,
            'date_maturity': self.date_due
        }
        return move_line

    @api.multi
    def account_move_get_eliterp(self):
        if self.number:
            name = self.number
        elif self.journal_id.sequence_id:
            if not self.journal_id.sequence_id.active:
                raise UserError(_('Please activate the sequence of selected journal !'))
            name = self.journal_id.sequence_id.with_context(ir_sequence_date=self.date).next_by_id()
        else:
            raise UserError(_('Please define a sequence on the journal.'))

        move = {
            'name': name,
            'journal_id': self.journal_id.id,
            'narration': self.narration,
            'date': self.account_date,
            'ref': self.reference,
        }
        return move

    @api.multi
    def action_move_line_create_eliterp(self):
        '''
        Confirm the vouchers given in ids and create the journal entries for each of them
        '''
        for voucher in self:
            local_context = dict(self._context, force_company=voucher.journal_id.company_id.id)
            total_cobro = 0
            for forma_cobro in voucher.lineas_tipos_pagos:
                total_cobro += forma_cobro.amount

            total_facturas = 0
            for facturas in voucher.lineas_cobros_facturas:
                total_facturas += facturas.valor_factura

            if total_cobro != total_facturas:
                raise except_orm("Error", "El monto Recaudado es difirente a suma de las Facturas")

            if voucher.move_id:
                continue
            company_currency = voucher.journal_id.company_id.currency_id.id
            current_currency = voucher.currency_id.id or company_currency
            # we select the context to use accordingly if it's a multicurrency case or not
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = local_context.copy()
            ctx['date'] = voucher.account_date
            ctx['check_move_validity'] = False
            # Create the account move record.
            move = self.env['account.move'].create(voucher.account_move_get_eliterp())
            # Get the name of the account_move just created
            # Create the first line of the voucher
            move_line = self.env['account.move.line'].with_context(ctx).create(
                voucher.first_move_line_get_eliterp(move.id, company_currency, current_currency))
            line_total = move_line.debit - move_line.credit
            if voucher.voucher_type == 'sale':
                line_total = line_total - voucher._convert_amount(voucher.tax_amount)
            elif voucher.voucher_type == 'purchase':
                line_total = line_total + voucher._convert_amount(voucher.tax_amount)
            # Create one move line per voucher line where amount is not 0.0
            line_total = voucher.with_context(ctx).voucher_move_line_create_eliterp(line_total, move.id,
                                                                                    company_currency,
                                                                                    current_currency)

            # Add tax correction to move line if any tax correction specified
            if voucher.tax_correction != 0.0:
                tax_move_line = self.env['account.move.line'].search(
                    [('move_id', '=', move.id), ('tax_line_id', '!=', False)], limit=1)
                if len(tax_move_line):
                    tax_move_line.write(
                        {'debit': tax_move_line.debit + voucher.tax_correction if tax_move_line.debit > 0 else 0,
                         'credit': tax_move_line.credit + voucher.tax_correction if tax_move_line.credit > 0 else 0})

            # We post the voucher.
            voucher.write({
                'move_id': move.id,
                'state': 'posted',
                'number': move.name
            })
            move.post()
        return True

    def move_comprobante_eliterp(self, name, comprobante, credit, debit, account_credit, account_debit, saldo):
        '''Comprobante de Ingresos'''
        move_id = self.env['account.move'].create({'journal_id': comprobante.journal_id.id,
                                                   'date': comprobante.date
                                                   })
        if saldo > 0:
            self.env['account.move.line'].with_context(check_move_validity=False).create(
                {'name': name,
                 'journal_id': comprobante.journal_id.id,
                 'partner_id': comprobante.partner_id.id,
                 'account_id': account_debit,
                 'move_id': move_id.id,
                 'credit': saldo,
                 'debit': 0.0,
                 'date': comprobante.date
                 })
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': comprobante.partner_id.name,
             'journal_id': comprobante.journal_id.id,
             'partner_id': comprobante.partner_id.id,
             'account_id': account_credit,
             'move_id': move_id.id,
             'credit': (credit - saldo) if saldo > 0 else credit,
             'debit': 0.0,
             'date': comprobante.date
             })
        self.env['account.move.line'].with_context(check_move_validity=True).create(
            {'name': comprobante.partner_id.name,
             'journal_id': comprobante.journal_id.id,
             'partner_id': comprobante.partner_id.id,
             'account_id': account_debit,
             'move_id': move_id.id,
             'credit': 0.0,
             'debit': debit,
             'date': comprobante.date
             })
        return move_id

    @api.multi
    def validar_voucher_eliterp(self):
        # MARZ
        cuenta = False
        if self.forma_de_pago == 'cash' and self.beneficiario_proveedor == 'supplier':
            cuenta = self.partner_id.property_account_payable_id
        else:
            cuenta = self.account_id
        if self.beneficiario_proveedor == 'solicitud_pago':
            if round(self.cantidad, 2) != round(self.solicitud_id.total, 2):
                raise ValidationError(_("La cantidad a cancelar debe ser el total de la Solicitud de Pago"))
        for line in self.lineas_pagos_facturas:
            if line.monto_pago == 0.00:
                raise ValidationError(_("Debe eliminar las Líneas de Facturas con Monto a Aplicar igual a 0"))
            ''' TODO - MARZ
            if self.beneficiario_proveedor == 'supplier':
                if line.monto_pago != line.valor_aprobado_pago:
                    raise ValidationError(
                        _("El Monto a Aplicar no es igual al Programado en Factura No. %s.") % line.name)'''
        if self.voucher_type == 'purchase':
            if self.beneficiario_proveedor != 'caja_chica' and self.beneficiario_proveedor != 'solicitud_pago' and self.beneficiario_proveedor != 'viaticos':
                if round((sum(line.monto_pago for line in self.lineas_pagos_facturas)), 2) != round(((
                        self.lineas_pagos_proveedores.filtered(
                            lambda
                                    x: x.account_id == cuenta))).monto_pago,
                                                                                                    2):
                    raise ValidationError(_("Revise los valores, de las Líneas de Cuentas"))
            nombre_asiento = ''
            if self.forma_de_pago == 'bank':  # Soló con cheques generamos el consecutivo
                numero_cheque = ""
                for x in range(1, (self.banco.padding - len(str(self.banco.numero_siguiente)))):
                    numero_cheque = numero_cheque + "0"
                new_name = "Cheque No. " + numero_cheque + str(self.banco.numero_siguiente)
                nombre_asiento = 'Egreso Cheque No. ' + numero_cheque + str(self.banco.numero_siguiente)
                self.banco.write({'numero_siguiente': self.banco.numero_siguiente + 1})
                self.env['cheques.eliterp'].create({
                    'partner_id': self.partner_id.id,
                    'name': new_name,
                    'nombre': self.beneficiario,
                    'tipo_cheque': 'emitidos',
                    'fecha_recepcion_emision': self.date,
                    'fecha_del_cheque': self.post_date,
                    'banco': self.banco.id,
                    'cuenta_del_cheque': self.banco.numero_cuenta,
                    'cuenta_id': self.banco.account_id.id,
                    'tipo_cheque_fecha': 'corriente',
                    'state': 'emitido',
                    'monto': self.cantidad,
                    'voucher_id': self.id,
                })
            elif self.forma_de_pago == 'cash':  # Efectivo
                sequence = self.env['ir.sequence'].next_by_code('account.voucher.purchase.cash')
                new_name = 'Efectivo No. ' + sequence
                nombre_asiento = 'Egreso Efectivo No. ' + sequence
            else:
                sequence = self.env['ir.sequence'].next_by_code('account.voucher.purchase.transferencia')
                new_name = 'Transferencia No. ' + sequence
                nombre_asiento = 'Egreso Transferencia No. ' + sequence
            move_id = self.env['account.move'].create({
                'journal_id': self.journal_id.id,
                'date': self.date
            })
            self.env['account.move.line'].with_context(check_move_validity=False).create({
                'name': self.concepto_pago if self.beneficiario_proveedor != 'viaticos' else self.viatico_id.name,
                'journal_id': self.journal_id.id,
                'partner_id': self.partner_id.id,
                'account_id': self.banco.account_id.id if self.forma_de_pago != 'cash' else self.account_id.id,
                'move_id': move_id.id,
                'debit': 0.0,
                'credit': self.cantidad,
                'date': self.date
            })
            count = len(self.lineas_pagos_proveedores)
            count_ = len(self.lineas_pagos_facturas)
            if count_ > 1:
                account_partner = self.partner_id.property_account_payable_id.id
                for line in self.lineas_pagos_proveedores.filtered(lambda x: not x.account_id.id == account_partner):
                    self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'name': self.concepto_pago,
                        'journal_id': self.journal_id.id,
                        'partner_id': False,
                        'account_id': line.account_id.id,
                        'move_id': move_id.id,
                        'credit': 0.0,
                        'debit': line.monto_pago,
                        'date': self.date,
                    })
                for line in self.lineas_pagos_facturas:
                    count_ -= 1
                    if count_ == 0:
                        self.env['account.move.line'].with_context(check_move_validity=True).create({
                            'name': "Pago de factura: " + line.name,
                            'journal_id': self.journal_id.id,
                            'partner_id': self.partner_id.id,
                            'account_id': account_partner,
                            'move_id': move_id.id,
                            'credit': 0.0,
                            'debit': line.monto_pago,
                            'date': self.date,
                            'invoice_id': line.invoice_id.id
                        })
                    else:
                        self.env['account.move.line'].with_context(check_move_validity=False).create({
                            'name': "Pago de factura: " + line.name,
                            'journal_id': self.journal_id.id,
                            'partner_id': self.partner_id.id,
                            'account_id': account_partner,
                            'move_id': move_id.id,
                            'credit': 0.0,
                            'debit': line.monto_pago,
                            'date': self.date,
                            'invoice_id': line.invoice_id.id
                        })
            else:
                for line in self.lineas_pagos_proveedores:
                    count -= 1
                    if count == 0:
                        self.env['account.move.line'].with_context(check_move_validity=True).create(
                            {'name': self.concepto_pago,
                             'journal_id': self.journal_id.id,
                             'partner_id': self.partner_id.id,
                             'account_id': line.account_id.id,
                             'move_id': move_id.id,
                             'credit': 0.0,
                             'debit': line.monto_pago,
                             'date': self.date})
                    else:
                        self.env['account.move.line'].with_context(check_move_validity=False).create(
                            {'name': self.concepto_pago,
                             'journal_id': self.journal_id.id,
                             'partner_id': self.partner_id.id,
                             'account_id': line.account_id.id,
                             'move_id': move_id.id,
                             'credit': 0.0,
                             'debit': line.monto_pago,
                             'date': self.date})
            if self.beneficiario_proveedor == 'supplier':
                for line_nota in self.lineas_notas_credito:
                    line_move_factura = line_nota.facturas_afectar.invoice_id.move_id.line_ids.filtered(
                        lambda x: x.account_id == cuenta)
                    line_move_nota = line_nota.invoice_id.move_id.line_ids.filtered(
                        lambda x: x.account_id == cuenta)
                    (line_move_factura + line_move_nota).reconcile()
                if len(self.lineas_pagos_facturas) > 1:
                    for line_invoice in self.lineas_pagos_facturas:
                        line_move_voucher = move_id.line_ids.filtered(
                            lambda x: x.account_id == cuenta and x.invoice_id.id == line_invoice.invoice_id.id)
                        line_move_invoice = line_invoice.invoice_id.move_id.line_ids.filtered(
                            lambda x: x.account_id == cuenta)
                        (line_move_invoice + line_move_voucher).reconcile()
                else:
                    line_move_pago = move_id.line_ids.filtered(lambda x: x.account_id == cuenta)
                    for line_factura in self.lineas_pagos_facturas:
                        line_move_factura = line_factura.invoice_id.move_id.line_ids.filtered(
                            lambda x: x.account_id == cuenta)
                        (line_move_factura + line_move_pago).reconcile()
            if self.beneficiario_proveedor == 'viaticos':
                self.env['account.move.line'].with_context(check_move_validity=True).create(
                    {'name': self.viatico_id.name,
                     'journal_id': self.journal_id.id,
                     'partner_id': self.partner_id.id,
                     'account_id': self.account_id.id,
                     'move_id': move_id.id,
                     'credit': 0.0,
                     'debit': self.cantidad,
                     'date': self.date})
            move_id.write({'ref': nombre_asiento})
            move_id.with_context(asientos_eliterp=True, name_asiento=new_name).post()
            if self.beneficiario_proveedor == 'caja_chica':
                for line in self.custodian_id.petty_cash_id.lineas_vale_factura:
                    if line.check_reposicion == True:
                        line.update({'state_reposicion': 'pagado'})
                # MARZ
                self.custodian_id.petty_cash_id.update({'date_reposicion': self.post_date})
            # MARZ
            if self.beneficiario_proveedor == 'solicitud_pago':
                self.solicitud_id.update({'state': 'paid'})
            ''' TODO if self.beneficiario_proveedor == 'supplier':
                for pago in pagos_programados_confirm:
                    pp = self.env['account.invoice.payment.scheduled'].search([('id', '=', pago)])
                    pp.update({'pagada': True})'''
            if self.beneficiario_proveedor == 'viaticos':
                self.viatico_id.update({
                    'state': 'managed'
                })
            return self.write({
                'state': 'posted',
                'name': new_name,
                'move_id': move_id.id
            })
        else:
            asientos_comprobante = []
            comprobante = self
            saldo = self.total - self.total_factura
            if saldo > 0:
                if self.flag_saldo == False:
                    return {'name': "Escoja la Cuenta para el Saldo",
                            'view_mode': 'form',
                            'view_type': 'form',
                            'res_model': 'account.voucher.saldo.eliterp',
                            'type': 'ir.actions.act_window',
                            'target': 'new',
                            'context': {'default_saldo': saldo},
                            }
            for metodo_pago in self.lineas_tipos_pagos:
                if metodo_pago.tipo_de_pagos == 'bank':
                    self.env['cheques.eliterp'].create({'partner_id': self.partner_id.id,
                                                        'name': metodo_pago.numero_cheque,
                                                        'nombre': metodo_pago.name_girador,
                                                        'tipo_cheque': 'recibidos',
                                                        'fecha_recepcion_emision': metodo_pago.date_created_eliterp,
                                                        'fecha_del_cheque': metodo_pago.date_due,
                                                        'banco': metodo_pago.banco.id,
                                                        'cuenta_del_cheque': metodo_pago.numero_cuenta,
                                                        'cuenta_id': metodo_pago.cuenta.id,
                                                        'tipo_cheque_fecha': metodo_pago.time_type,
                                                        'state': 'recibido',
                                                        'monto': metodo_pago.amount})
                    move_id = self.move_comprobante_eliterp(self.concepto_pago,
                                                            comprobante,
                                                            metodo_pago.amount,
                                                            metodo_pago.amount,
                                                            self.partner_id.property_account_receivable_id.id,
                                                            metodo_pago.cuenta.id,
                                                            saldo)
                    move_id.with_context(asientos_eliterp=True, comprobante_interno=True).post()
                    metodo_pago.write({'asiento_contable': move_id.id})
                    line_move_transferencia = move_id.line_ids.filtered(
                        lambda x: x.account_id == self.partner_id.property_account_receivable_id)
                    for line_factura in self.lineas_cobros_facturas:
                        line_move_factura = line_factura.invoice_id.move_id.line_ids.filtered(
                            lambda x: x.account_id == self.partner_id.property_account_receivable_id)
                        (line_move_transferencia + line_move_factura).reconcile()
                    asientos_comprobante.append(move_id)

                if metodo_pago.tipo_de_pagos == 'cash':
                    move_id = self.move_comprobante_eliterp(self.concepto_pago,
                                                            comprobante,
                                                            metodo_pago.amount,
                                                            metodo_pago.amount,
                                                            self.partner_id.property_account_receivable_id.id,
                                                            metodo_pago.cuenta.id,
                                                            saldo)
                    metodo_pago.write({'asiento_contable': move_id.id})
                    line_move_efectivo = move_id.line_ids.filtered(
                        lambda x: x.account_id == self.partner_id.property_account_receivable_id)
                    for line_factura in self.lineas_cobros_facturas:
                        line_move_factura = line_factura.invoice_id.move_id.line_ids.filtered(
                            lambda x: x.account_id == self.partner_id.property_account_receivable_id)
                        (line_move_efectivo + line_move_factura).reconcile()
                    asientos_comprobante.append(move_id)
                    move_id.with_context(asientos_eliterp=True, comprobante_interno=True).post()
                    metodo_pago.write({'asiento_contable': move_id.id})

                if metodo_pago.tipo_de_pagos == 'transferencia':
                    move_id = self.move_comprobante_eliterp(self.concepto_pago,
                                                            comprobante,
                                                            metodo_pago.amount,
                                                            metodo_pago.amount,
                                                            self.partner_id.property_account_receivable_id.id,
                                                            metodo_pago.cuenta.id,
                                                            saldo)
                    move_id.with_context(asientos_eliterp=True, comprobante_interno=True).post()
                    metodo_pago.write({'asiento_contable': move_id.id})
                    line_move_transferencia = move_id.line_ids.filtered(
                        lambda x: x.account_id == self.partner_id.property_account_receivable_id)
                    for line_factura in self.lineas_cobros_facturas:
                        line_move_factura = line_factura.invoice_id.move_id.line_ids.filtered(
                            lambda x: x.account_id == self.partner_id.property_account_receivable_id)
                        (line_move_transferencia + line_move_factura).reconcile()
                    asientos_comprobante.append(move_id)
            new_name = self.journal_id.sequence_id.next_by_id()
            for move_comprobante in asientos_comprobante:
                move_comprobante.write({'ref': new_name})
            return self.write({'state': 'posted', 'name': new_name, 'move_id': move_id.id})

    def aplicar_monto(self):
        self.cantidad = sum(line.monto_pago for line in self.lineas_pagos_proveedores)
        return

    def cargar_monto(self):
        journal_id = self.env['account.journal'].search([('name', '=', 'Efectivo')]).id
        if self.voucher_type == 'sale':
            if not self.lineas_cobros_facturas:
                raise except_orm("Error", "Necesita cargar líneas")
            if not self.lineas_tipos_pagos:
                raise except_orm("Error", "No tiene ninguna forma de pago cargada")
            else:
                total = 0.00
                for cobro in self.lineas_tipos_pagos:
                    total += cobro.amount
        else:
            self.cantidad = sum(line.monto_pago for line in self.lineas_pagos_proveedores)
            if self.forma_de_pago == 'cash' and self.beneficiario_proveedor == 'supplier':
                total = self.lineas_pagos_proveedores.filtered(
                    lambda x: x.account_id == self.partner_id.property_account_payable_id).monto_pago
            else:
                total = self.lineas_pagos_proveedores.filtered(lambda x: x.account_id == self.account_id).monto_pago
        for inv in self.lineas_cobros_facturas:
            if total == 0.00:
                continue
            if inv.monto_adeudado <= total:
                inv.update({'monto_pago': inv.monto_adeudado, 'journal_id': journal_id})
                total = total - inv.monto_adeudado
            else:
                inv.update({'monto_pago': total, 'journal_id': journal_id})
                total = 0.00

        '''journal_id = self.env['account.journal'].search([('name', '=', 'Efectivo')]).id # ?
        if self.voucher_type == 'sale':
            if not self.lineas_cobros_facturas:
                raise except_orm("Error", "Necesita cargar líneas")
            if not self.lineas_tipos_pagos:
                raise except_orm("Error", "No tiene ninguna forma de pago cargada")
            else:
                total = 0.00
                # MARZ
                for cobro in self.lineas_tipos_pagos:
                    total += cobro.amount
            for inv in self.lineas_cobros_facturas:
                if total == 0.00:
                    continue
                if inv.monto_adeudado <= total:
                    inv.update({'monto_pago': inv.monto_adeudado, 'journal_id': journal_id})
                    total = total - inv.monto_adeudado
                else:
                    inv.update({'monto_pago': total, 'journal_id': journal_id})
                    total = 0.00
        else:
            self.cantidad = sum(line.monto_pago for line in self.lineas_pagos_proveedores)
            cuentas = self.lineas_pagos_proveedores.filtered(lambda x: x.account_id == self.account_id)
            total = 0.00
            if cuentas:
                total = cuentas[0].monto_pago  # Misma cuenta, pago adelantado
                # MARZ (monto_adeudado <-> valor_aprobado_pago)
            for inv in self.lineas_cobros_facturas:
                if total == 0.00:
                    continue
                TODO if inv.valor_aprobado_pago <= total:
                    inv.update({'monto_pago': inv.valor_aprobado_pago, 'journal_id': journal_id})
                    total = total - inv.valor_aprobado_pago
                else:
                    inv.update({'monto_pago': total, 'journal_id': journal_id})
                    total = 0.00'''
        return

    def aplicar_notas(self):
        for line in self.lineas_notas_credito:
            line_factura = self.lineas_pagos_facturas.filtered(lambda x: x.id == line.facturas_afectar.id)
            line_factura.write({'monto_adeudado': line_factura.monto_adeudado + line.valor_nota})
        return True

    '''TODO MARZ
    def get_suma_pagos(self, invoice):
        global pagos_programados_confirm
        pagos_programados_confirm = []
        pagos_programados = self.env['account.invoice.payment.scheduled'].search(
            [('invoice_id', '=', invoice), ('fecha', '<=', datetime.date.today()), ('pagada', '=', False)])
        for line in pagos_programados:
            pagos_programados_confirm.append(line.id)
        return round(sum(line.value for line in pagos_programados), 2)'''

    def cargar_facturas(self):
        if not self.partner_id:
            if self.voucher_type == 'sale':
                raise except_orm("Error", "Necesita seleccionar al Cliente")
            else:
                raise except_orm("Error", "Necesita seleccionar al Proveedor")
        else:
            if self.voucher_type == 'sale':
                invoices_list = self.env['account.invoice'].search(
                    [('partner_id', '=', self.partner_id.id), ('state', '=', 'open')])
            else:
                invoices_list = self.env['account.invoice'].search([('partner_id', '=', self.partner_id.id),
                                                                    ('state', '=', 'open'),
                                                                    ('line_approval', '=', 'aprobado')])
                ''' TODO ('line_approval', 'in', ('aprobado_parcial', 'aprobado'))])'''
                notas_list = self.env['account.invoice'].search([('partner_id', '=', self.partner_id.id),
                                                                 ('state', '=', 'open'),
                                                                 ('type', '=', 'in_refund')])
            list_lines = []
            total_factura_supplier = 0.00
            # MARZ
            for inv in invoices_list:
                list_lines.append([0, 0, {'invoice_id': inv.id,
                                          'fecha_vencimiento_factura': inv.date_due,
                                          'valor_factura': inv.amount_total,
                                          'monto_adeudado': inv.residual}])
                ''''valor_aprobado_pago': self.get_suma_pagos(inv.id)}])'''
                total_factura_supplier += inv.residual
            list_notas = []
            if self.voucher_type == 'purchase':
                if notas_list:
                    list_notas = []
                    for nota in notas_list:
                        list_notas.append([0, 0, {'invoice_id': nota.id,
                                                  'fecha_vencimiento_factura': nota.date_due,
                                                  'valor_nota': -1 * nota.amount_total}])
                list_supplier = []
                list_supplier.append([0, 0, {'monto_pago': 0.00,
                                             'account_id': self.account_id.id if not self.forma_de_pago == 'cash'
                                                                                 and not self.beneficiario_proveedor == 'supplier'
                                             else self.partner_id.property_account_payable_id.id}])
                return self.update({'lineas_cobros_facturas': list_lines,
                                    'lineas_pagos_proveedores': list_supplier,
                                    'lineas_notas_credito': list_notas})
            return self.update({'lineas_cobros_facturas': list_lines})

    @api.onchange('partner_id', 'pay_now')
    def onchange_partner_id(self):
        if self.pay_now == 'pay_now':
            liq_journal = self.env['account.journal'].search([('type', 'in', ('bank', 'cash'))], limit=1)
            self.account_id = liq_journal.default_debit_account_id \
                if self.voucher_type == 'sale' else liq_journal.default_credit_account_id
        else:
            if self.partner_id:
                if self.voucher_type == 'sale':
                    self.account_id = self.partner_id.property_account_receivable_id
                else:
                    if self.forma_de_pago <> 'cash':
                        self.account_id = self.partner_id.property_account_payable_id
                    else:
                        self.account_id = False
            else:
                self.account_id = self.journal_id.default_debit_account_id \
                    if self.voucher_type == 'sale' else self.journal_id.default_credit_account_id
        self.beneficiario = self.partner_id.name

    @api.model
    def _default_journal(self):
        if self._context['voucher_type'] == 'sale':
            return self.env['account.journal'].search([('name', '=', 'Comprobante de Ingreso')])[0].id
        else:
            return self.env['account.journal'].search([('name', '=', 'Comprobante de Egreso')])[0].id

    @api.onchange('account_saldo')
    def onchange_account_saldo(self):
        if len(self.account_saldo) != 0:
            self.if_saldo = True

    @api.onchange('banco', 'beneficiario_proveedor', 'forma_de_pago')
    def onchange_banco_beneficiario_proveedor_forma_de_pago(self):
        # MARZ
        if self.forma_de_pago <> 'cash':
            if self.beneficiario_proveedor == 'viaticos':
                self.account_id = self.env['account.account'].search([('code', '=', '1.1.2.3.9')])[
                    0].id  # Crear esa cuenta es necesario
            if self.beneficiario_proveedor == 'beneficiario' or self.beneficiario_proveedor == 'solicitud_pago':
                self.account_id = self.banco.account_id.id
        else:
            self.account_id = False
        if self.forma_de_pago == 'bank':
            numero_cheque = ""
            for x in range(1, (self.banco.padding - len(str(self.banco.numero_siguiente)))):
                numero_cheque = numero_cheque + "0"
            self.numero_cheque = numero_cheque + str(self.banco.numero_siguiente)
        else:
            self.numero_cheque = False

    @api.onchange('custodian_id')
    def onchange_custodian_id(self):
        self.beneficiario = self.custodian_id.name
        if self.forma_de_pago != 'cash':
            self.account_id = self.custodian_id.account_id.id
        else:
            self.account_id = False

    # MARZ
    @api.onchange('solicitud_id')
    def onchange_solicitud_id(self):
        if self.solicitud_id:
            self.cantidad = self.solicitud_id.total
            self.beneficiario = self.solicitud_id.beneficiary

    @api.onchange('viatico_id')
    def onchange_viatico_id(self):
        if self.viatico_id:
            self.cantidad = self.viatico_id.total_solicitud
            self.beneficiario = self.viatico_id.beneficiary.name
            self.concepto_pago = self.viatico_id.reason

    def cargar_valores(self):
        if self.beneficiario_proveedor == 'caja_chica':
            if self.custodian_id.petty_cash_id.state == 'closed':
                line = []
                line.append([0, 0, {'monto_pago': self.custodian_id.petty_cash_id.monto_vale_factura,
                                    'account_id': self.custodian_id.account_id.id}])
                self.update({'lineas_pagos_proveedores': line})
            else:
                return True

    def imprimir_cheque(self):
        reporte = []
        reporte.append(self.id)
        amount = self.env['report.elitum_contabilidad.reporte_factura_cliente'].get_amount_to_word(self.cantidad).upper()
        monto1 = int(self.cantidad)
        if self.cantidad - monto1 == 0:
            monto = '{:,}'.format(self.cantidad) + "0"
        else:
            monto = '{:,}'.format(self.cantidad)
        if self.banco.display_name == 'BANCO BOLIVARIANO':
            result = {
                'type': 'ir.actions.report.xml',
                'report_name': 'elitum_financiero.reporte_cheque_bo',
                'datas': {'ids': reporte},
                'context': {
                    'reporte_cheque_i': True,
                    'fecha': 'GUAYAQUIL, ' + self.post_date,
                    'nombre': self.beneficiario,
                    'monto': monto,
                    'monto_letras': amount
                }
            }
        elif self.banco.display_name == 'BANCO INTERNACIONAL':
            result = {
                'type': 'ir.actions.report.xml',
                'report_name': 'elitum_financiero.reporte_cheque_in',
                'datas': {'ids': reporte},
                'context': {
                    'reporte_cheque_i': True,
                    'fecha': 'GUAYAQUIL, ' + self.post_date,
                    'nombre': self.beneficiario,
                    'monto': monto,
                    'monto_letras': amount
                }
            }
        else:
            return
        return result

    lineas_tipos_pagos = fields.One2many('payment.type.lines', 'voucher_id', string=u'Detalle de Cobros')
    lineas_cobros_facturas = fields.One2many('lines.invoice.charges', 'voucher_id', string=u'Detalle de Cobros')
    lineas_pagos_facturas = fields.One2many('lines.invoice.charges', 'voucher_id', string=u'Detalle de Pagos')
    lineas_notas_credito = fields.One2many('lines.refund.charges', 'voucher_id', string=u'Notas de Credito')
    lineas_pagos_proveedores = fields.One2many('lines.supplier.charges', 'voucher_id', string=u'Detalle de Proveedor')
    journal_id = fields.Many2one('account.journal', 'Journal',
                                 required=True, readonly=True, states={'draft': [('readonly', False)]},
                                 default=_default_journal)
    # MARZ
    forma_de_pago = fields.Selection([('bank', 'Cheque'),
                                      ('cash', 'Varios'),
                                      ('transferencia', 'Transferencia')], string='Forma de Pago', default='bank',
                                     required=True)
    beneficiario_proveedor = fields.Selection(
        [('beneficiario', 'Varios'), ('supplier', 'Proveedor'), ('caja_chica', 'Caja Chica'),
         ('solicitud_pago', 'Solicitud de Pago'), ('viaticos', 'Solicitud de Viáticos')],
        string="Tipo", default='beneficiario', required=True)
    solicitud_id = fields.Many2one('eliterp.payment.request', string="Titular", domain=[('state', '=', 'approved')])
    viatico_id = fields.Many2one('eliterp.provision', string="Titular")
    # Fin MARZ
    beneficiario = fields.Char('Beneficiario')
    numero_cheque = fields.Char('No. Cheque')
    post_date = fields.Date('Fecha Entrega')
    banco = fields.Many2one('res.bank', string="Banco")
    custodian_id = fields.Many2one('petty.cash.custodian')
    cantidad = fields.Float('Valor a Cancelar',
                            help="Campo se llenará automáticamente al presionar botón Cargar Valores")
    total = fields.Monetary('Total', compute='_get_total')
    total_factura = fields.Monetary('Total Factura', compute='_get_total_factura')
    account_id = fields.Many2one('account.account', string='Cuenta',
                                 domain=[('deprecated', '=', False), ('tipo_contable', '=', 'movimiento')])
    concepto_pago = fields.Char('Concepto', required=True)
    flag_saldo = fields.Boolean('Ya no hay saldo', default=False)
    mostrar_cuenta = fields.Boolean('Se muestra la Cuenta?', default=False)
    account_saldo = fields.Many2one('account.account', domain=[('tipo_contable', '=', 'movimiento')])
    valor_saldo = fields.Float('saldo')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('cancel', 'Anulado'),
        ('posted', 'Contabilizado'),
        ('proforma', 'Pro-forma')], 'Estado', readonly=True, track_visibility='onchange', copy=False, default='draft')
    transfer_code = fields.Char('Código de transferencia', readonly=True, states={'draft': [('readonly', False)]})
    _sql_constraints = [
        ('transfer_code_uniq', 'unique (bank_id, transfer_code, state)',
         'El Código de transferencia debe ser única por banco.')
    ]
