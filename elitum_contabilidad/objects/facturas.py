# -*- coding: utf-8 -*-
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
from odoo.tools import float_is_zero, float_compare
from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, except_orm, RedirectWarning, ValidationError
from lxml import etree

# (Sobreescrito) tipo de Diario (Compra/Venta)
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'in_sale_note': 'purchase_sale_note',  # MARZ
    'out_refund': 'sale',
    'in_refund': 'purchase',
}


class AccountInvoiceCancelReason(models.Model):
    _name = 'account.invoice.cancel.reason'

    _description = u'Modelo - Razón para Anular Documento'

    description = fields.Text(u'Descripción', required=True)

    def confirm_cancel_reason(self):
        '''Confirmar la Anulación del Documento'''
        invoice = self.env['account.invoice'].browse(self._context['active_id'])
        invoice.action_cancel()
        self.env['account.invoice']
        invoice.move_id.write({'ref': self.description})
        for line in invoice.withhold_id.line_tax_withhold:
            invoice_tax = self.env['account.invoice.tax'].search([('invoice_id', '=', invoice.id),
                                                                  ('name', '=', line.retencion.name),
                                                                  ('tax_id', '=', line.retencion.id),
                                                                  ('account_id', '=', line.retencion.account_id.id)])
            invoice_tax.unlink()
        invoice.withhold_id.write({'state': 'cancel'})
        invoice.write({'withhold_id': False,
                       'have_withhold': False,
                       'comment': 'Factura Anulada: ' + invoice.numero_factura_interno, })
        if invoice.type == 'in_invoice':
            invoice.write({'numero_factura_interno': False})
        invoice._compute_amount()
        invoice._compute_residual()
        return True


class AccountInvoiceTax(models.Model):
    _inherit = 'account.invoice.tax'

    @api.model
    def create(self, values):
        '''Sobreescribimos método (CREATE) del modelo'''
        if 'nota_credito' in self._context:
            values.update({'manual': False})
        return super(AccountInvoiceTax, self).create(values)


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.model
    def create(self, values):
        return super(AccountInvoiceLine, self).create(values)

    project = fields.Many2one('analytic.account')
    account_id = fields.Many2one('account.account', string='Account',
                                 default=None,
                                 required=True, help="The income or expense account related to the selected product.")
    type = fields.Selection(related='invoice_id.type')  # MARZ


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _default_journal(self):
        '''(Sobreescrito) Diario por defecto'''
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', filter(None, map(TYPE2JOURNAL.get, inv_types))),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)

    @api.multi
    def invoice_validate(self):
        '''(Sobreescrito) Validamos no exista referencia de Documento'''
        for invoice in self:
            if invoice.type in ('in_invoice') and invoice.reference:
                if self.search([('type', '=', invoice.type), ('reference', '=', invoice.reference),
                                ('company_id', '=', invoice.company_id.id),
                                ('commercial_partner_id', '=', invoice.commercial_partner_id.id),
                                ('id', '!=', invoice.id)]):
                    raise UserError(_(
                        "Duplicated vendor reference detected. You probably encoded twice the same vendor bill/refund."))
        return self.write({'state': 'open'})

    def nota_credito_create(self):
        '''Generar Nota de Crédito'''
        inv_obj = self.env['account.invoice']
        date = self.date_invoice
        description = ""
        nota_credito = self.with_context(nota_credito=True).refund(
            date,
            date,
            description,
            self.env['account.journal'].search([('name', '=', 'Credito Contable')])[0].id
        )
        nota_credito.with_context(nota_credito=True).compute_taxes()
        for line in self.withhold_id.line_tax_withhold:
            self.env['account.invoice.tax'].search(
                [('invoice_id', '=', nota_credito.id), ('account_id', '=', line.retencion.account_id.id)]).unlink()
        self.write({'have_nota_credito': True})
        nota_credito.write({
            'invoice_id_ref': self.id,
            'origin': self.numero_factura_interno
        })
        imd = self.env['ir.model.data']
        if self.type == 'out_invoice':
            autorizacion = self.env['autorizacion.sri'].search([('tipo_comprobante', '=', 5), ('state', '=', 'activo')])
            if len(autorizacion) == 0:
                raise UserError(_(
                    'Debe ingresar la autorización de Nota de Crédito'))
            action = imd.xmlid_to_object('elitum_contabilidad.action_eliterp_nota_credito_factura_ventas_conta')
            list_view_id = imd.xmlid_to_res_id('account.invoice_tree')
            form_view_id = imd.xmlid_to_res_id('account.invoice_form')
        else:
            action = imd.xmlid_to_object('elitum_contabilidad.action_eliterp_nota_credito_factura')
            list_view_id = imd.xmlid_to_res_id('account.invoice_supplier_tree')
            form_view_id = imd.xmlid_to_res_id('account.invoice_supplier_form')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(nota_credito) > 1:
            result['domain'] = "[('id','in',%s)]" % nota_credito.ids
        elif len(nota_credito) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = nota_credito.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    def imprimir_factura_provision(self):
        '''Imprimir Factura/Nota de Venta Proveedor'''
        return self.env['report'].get_action(self, 'elitum_contabilidad.reporte_provision_factura')

    def imprimir_factura_cliente(self):
        '''Imprimir Factura Cliente'''
        return self.env['report'].get_action(self, 'elitum_contabilidad.reporte_factura_cliente')

    @api.onchange('property_supplier_payment_term_id')
    def _onchange_property_supplier_payment_term_id(self):
        '''Evento al cambiar Plaza de Pago (Compras)'''
        if not self.property_supplier_payment_term_id:
            return
        if self.payment_conditions == 'credit':
            self.date_due = datetime.strptime(self.date_due, '%Y-%m-%d') + timedelta(
                days=self.property_supplier_payment_term_id.line_ids[0].days)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        '''Evento al cambiar el Proveedor/Cliente'''
        res = super(AccountInvoice, self)._onchange_partner_id()
        # Condiciones de Pago configuradas en el Partner
        self.payment_conditions = self.partner_id.payment_conditions
        if self.partner_id.payment_conditions == 'credit':
            self.property_supplier_payment_term_id = self.partner_id.property_supplier_payment_term_id.id
        return res

    @api.one
    @api.depends('payment_move_line_ids.amount_residual')
    def _get_payment_info_JSON(self):
        '''(Sobreescrito) Traeen formato JSON Pagos/Retenciones (Widgets)'''
        self.payments_widget = json.dumps(False)
        if self.payment_move_line_ids:
            info = {'title': _('Información de Pago'), 'outstanding': False, 'content': []}
            currency_id = self.currency_id
            for payment in self.payment_move_line_ids:
                payment_currency_id = False
                if self.type in ('out_invoice', 'in_refund'):
                    amount = sum(
                        [p.amount for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                    amount_currency = sum([p.amount_currency for p in payment.matched_debit_ids if
                                           p.debit_move_id in self.move_id.line_ids])
                    if payment.matched_debit_ids:
                        payment_currency_id = all([p.currency_id == payment.matched_debit_ids[0].currency_id for p in
                                                   payment.matched_debit_ids]) and payment.matched_debit_ids[
                                                  0].currency_id or False
                elif self.type in ('in_invoice', 'out_refund', 'in_sale_note'):  # MARZ
                    amount = sum(
                        [p.amount for p in payment.matched_credit_ids if p.credit_move_id in self.move_id.line_ids])
                    amount_currency = sum([p.amount_currency for p in payment.matched_credit_ids if
                                           p.credit_move_id in self.move_id.line_ids])
                    if payment.matched_credit_ids:
                        payment_currency_id = all([p.currency_id == payment.matched_credit_ids[0].currency_id for p in
                                                   payment.matched_credit_ids]) and payment.matched_credit_ids[
                                                  0].currency_id or False
                if payment_currency_id and payment_currency_id == self.currency_id:
                    amount_to_show = amount_currency
                else:
                    amount_to_show = payment.company_id.currency_id.with_context(date=payment.date).compute(amount,
                                                                                                            self.currency_id)
                if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                    continue
                payment_ref = payment.move_id.name
                if payment.move_id.ref:
                    payment_ref += ' (' + payment.move_id.ref + ')'
                info['content'].append({
                    'name': payment.name,
                    'journal_name': payment.journal_id.name,
                    'amount': amount_to_show,
                    'currency': currency_id.symbol,
                    'digits': [69, currency_id.decimal_places],
                    'position': currency_id.position,
                    'date': payment.date,
                    'payment_id': payment.id,
                    'move_id': payment.move_id.id,
                    'ref': payment_ref,
                })
            self.payments_widget = json.dumps(info)

    def action_invoice_cancel_reason(self):
        '''Abrimos Díalogo de Anulación'''
        context = dict(self._context or {})
        return {
            'name': "Explique la Razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.invoice.cancel.reason',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

    @api.multi
    def action_cancel(self):
        '''(Sobreescrito) Anulamos Asiento Contable del Documento'''
        moves = self.env['account.move']
        for inv in self:
            if inv.move_id:
                moves += inv.move_id
            # Si existen pagos no se podrá anular Documento
            if inv.payment_move_line_ids:
                raise UserError(_(
                    'You cannot cancel an invoice which is partially paid. You need to unreconcile related payment entries first.'))
        if moves:
            moves.with_context(from_invoice=True).reverse_moves(self.date_invoice, self.journal_id or False)
            moves.write({'state': 'cancel'})
        referencia_fact = self.reference if self.reference else ""
        self.write({
            'state': 'cancel',
            'reference': str(referencia_fact) + " - Anulado"
        })
        return True

    @api.one
    @api.depends(
        'state', 'currency_id', 'invoice_line_ids.price_subtotal',
        'move_id.line_ids.amount_residual',
        'move_id.line_ids.currency_id')
    def _compute_residual(self):
        '''(Sobreescrito) Calculamos Monto por Pagar/Cobrar del Documento'''
        residual = 0.0
        residual_company_signed = 0.0
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        for line in self.sudo().move_id.line_ids:
            if line.account_id.internal_type in ('receivable', 'payable'):
                residual_company_signed += line.amount_residual
                if line.currency_id == self.currency_id:
                    residual += line.amount_residual_currency if line.currency_id else line.amount_residual
                else:
                    from_currency = (line.currency_id and line.currency_id.with_context(
                        date=line.date)) or line.company_id.currency_id.with_context(date=line.date)
                    residual += from_currency.compute(line.amount_residual, self.currency_id)
        self.residual_company_signed = abs(residual_company_signed) * sign
        self.residual_signed = abs(residual) * sign
        self.residual = abs(residual)
        digits_rounding_precision = self.currency_id.rounding
        if float_is_zero(self.residual, precision_rounding=digits_rounding_precision):
            self.reconciled = True
        else:
            self.reconciled = False
        # Cargar Base Cero, Base Iva
        total_base_gravada = 0.00
        total_base_cero = 0.00
        for line in self.invoice_line_ids:
            for tax in line.invoice_line_tax_ids:
                if tax.amount > 0:
                    total_base_gravada += line.price_subtotal
                else:
                    total_base_cero += line.price_subtotal
        self.base_cero_iva = total_base_cero
        self.base_gravada = total_base_gravada

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 'company_id', 'date_invoice')
    def _compute_amount(self):
        '''Calculamos el Total del Documento'''
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        total_impuesto = 0.00
        total_retencion = 0.00
        for line in self.tax_line_ids:
            if line.amount >= 0:
                total_impuesto += line.amount
            else:
                total_retencion += line.amount
        self.amount_tax = total_impuesto
        self.total_retener = -1 * (total_retencion)
        self.amount_total = self.amount_untaxed + self.amount_tax
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id.with_context(date=self.date_invoice)
            amount_total_company_signed = currency_id.compute(self.amount_total, self.company_id.currency_id)
            amount_untaxed_signed = currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign
        # Cargar Base Cero, Base Iva
        total_base_gravada = 0.00
        total_base_cero = 0.00
        for line in self.invoice_line_ids:
            for tax in line.invoice_line_tax_ids:
                if tax.amount > 0:
                    total_base_gravada += line.price_subtotal
                else:
                    total_base_cero += line.price_subtotal
        self.base_cero_iva = total_base_cero
        self.base_gravada = total_base_gravada

    @api.model
    def line_get_convert(self, line, part):
        return {
            'date_maturity': line.get('date_maturity', False),
            'partner_id': part,
            'name': self.concepto_factura if self.type == 'in_invoice' else line['name'][:64],
            'debit': line['price'] > 0 and line['price'],
            'credit': line['price'] < 0 and -line['price'],
            'account_id': line['account_id'],
            'analytic_line_ids': line.get('analytic_line_ids', []),
            'amount_currency': line['price'] > 0 and abs(line.get('amount_currency', False)) or -abs(
                line.get('amount_currency', False)),
            'currency_id': line.get('currency_id', False),
            'quantity': line.get('quantity', 1.00),
            'product_id': line.get('product_id', False),
            'product_uom_id': line.get('uom_id', False),
            'analytic_account_id': line.get('account_analytic_id', False),
            'invoice_id': line.get('invoice_id', False),
            'tax_ids': line.get('tax_ids', False),
            'tax_line_id': line.get('tax_line_id', False),
            'analytic_tag_ids': line.get('analytic_tag_ids', False),
        }

    @api.multi
    def action_invoice_open(self):
        '''Validar Documento'''
        # Notas de Crédito (Reembolsos)
        if self.type in ('in_refund', 'out_refund'):
            notas_credito = self.env['account.invoice'].search(
                [('invoice_id_ref', '=', self.invoice_id_ref.id), ('state', '=', 'open')])
            valor_para_nota = self.invoice_id_ref.amount_total - sum(nota.amount_total for nota in notas_credito)
            if self.amount_untaxed > valor_para_nota:
                raise except_orm("Error", "Excede el total de Notas de Crédito que puede crear")
            res = super(AccountInvoice, self).action_invoice_open()
            if self.type == 'out_refund':
                self.write({
                    'state_notas': 'confirm',
                    'numero_factura_interno': self.numero_factura
                })
            else:
                self.write({
                    'state_notas': 'confirm',
                    'numero_factura_interno': self.punto_emision + "-" + self.numero_establecimiento + "-" + self.numero_factura
                })
            return res
        # Factura de Compra
        if self.type == 'in_invoice':
            if self.con_sin_withhold:
                if not self.have_withhold:
                    raise except_orm("Error", "Debe ingresar la Retención")
                res = super(AccountInvoice, self).action_invoice_open()
                self.withhold_id.write({
                    'state': 'confirm',
                    'name': self.withhold_id.journal_id.sequence_id.next_by_id()
                })
            else:
                # Validamos Cuentas (Concepto/Factura)
                if self.pago_provision:
                    if len(self.invoice_line_ids) > 1:
                        raise ValidationError(_("Soló debe crear una línea de detalle (Factura de Viáticos)"))
                    else:
                        for line in self.invoice_line_ids:
                            if line.account_id != self.voucher_provision_id.table_provision_id.account_id:
                                raise ValidationError(_("Cuentas contables diferentes (Factura y Concepto)"))
                res = super(AccountInvoice, self).action_invoice_open()
        # Nota de Venta de Compra
        if self.type == 'in_sale_note':
            # Función de validación de RISE de Proveedor
            self.validar_rise(self.partner_id)
            # Asignamos nuevo número a Nota de Vetnta
            new_number = self.env['ir.sequence'].next_by_code('account.invoice.purchase.sale.note')
            self.number = new_number
            res = super(AccountInvoice, self).action_invoice_open()
        # Factura de Venta
        return super(AccountInvoice, self).action_invoice_open()

    @api.multi
    def withhold_button_invoice(self):
        '''Acción de Botón (Box) Retenciones'''
        retencion = self.env['tax.withhold'].search([('invoice_id', '=', self.id)])
        imd = self.env['ir.model.data']
        if self.type == 'out_invoice':
            action = imd.xmlid_to_object('elitum_financiero.eliterp_action_retencion_ventas')
            list_view_id = imd.xmlid_to_res_id('elitum_financiero.eliterp_retenciones_view_tree_ventas')
            form_view_id = imd.xmlid_to_res_id('elitum_financiero.eliterp_retenciones_view_form_ventas')
        else:
            action = imd.xmlid_to_object('elitum_financiero.eliterp_action_retencion_compras')
            list_view_id = imd.xmlid_to_res_id('elitum_financiero.eliterp_retenciones_view_tree_compras')
            form_view_id = imd.xmlid_to_res_id('elitum_financiero.eliterp_retenciones_view_form_compras')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(retencion) > 1:
            result['domain'] = "[('id','in',%s)]" % retencion.ids
        elif len(retencion) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = retencion.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    @api.multi
    def nota_credito_button_invoice(self):
        '''Acción de Botón (Box) Notas de Crédito'''
        nota_credito = self.env['account.invoice'].search([('invoice_id_ref', '=', self.id)])
        imd = self.env['ir.model.data']
        if self.type == 'in_invoice':
            action = imd.xmlid_to_object('elitum_contabilidad.action_eliterp_nota_credito_factura')
            list_view_id = imd.xmlid_to_res_id('account.invoice_supplier_tree')
            form_view_id = imd.xmlid_to_res_id('account.invoice_supplier_form')
        else:
            action = imd.xmlid_to_object('elitum_contabilidad.action_eliterp_nota_credito_factura_ventas_conta')
            list_view_id = imd.xmlid_to_res_id('account.invoice_tree')
            form_view_id = imd.xmlid_to_res_id('account.invoice_form')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(nota_credito) > 1:
            result['domain'] = "[('id','in',%s)]" % nota_credito.ids
        elif len(nota_credito) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = nota_credito.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    # MARZ
    @api.multi
    def payment_button_invoice(self):
        '''Acción de Botón (Box) Pagos Programados'''
        pago_programado = self.env['account.invoice.payment.scheduled'].search([('invoice_id', '=', self.id)])
        imd = self.env['ir.model.data']
        list_view_id = imd.xmlid_to_res_id('elitum_financiero.eliterp_pago_programado_view_tree')
        action = imd.xmlid_to_object('elitum_financiero.eliterp_action_pago_programado')
        form_view_id = imd.xmlid_to_res_id('elitum_financiero.eliterp_pago_programado_view_form')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(pago_programado) > 1:
            result['domain'] = "[('id','in',%s)]" % pago_programado.ids
        elif len(pago_programado) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = pago_programado.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    def validar_rise(self, partner):
        '''Validamos RISE de proveedor'''
        if not partner.max_amount:
            raise except_orm("Error", "Proveedor no tiene configurado el RISE")
        notas = self.env['account.invoice'].search([
            ('partner_id', '=', partner.id),
            ('type', '=', 'in_sale_note'),
            ('state', 'not in', ('draft', 'cancel'))
        ])
        notas_total = notas.filtered(
            lambda nota: (datetime.strptime(nota.date_invoice, "%Y-%m-%d")).year == datetime.today().date().year)
        total_notas = round(sum(nota.amount_total for nota in notas_total), 2)
        if (self.amount_total + total_notas) > (partner.max_amount * 12):
            raise except_orm("Error", "Ha sobrepasado el monto máximo anual (RISE)")

    @api.model
    def create(self, values):
        '''Sobreescribimos método (CREATE) del modelo account.invoice'''
        # Función de validación de Período Contable
        self.env['eliterp.funciones'].validar_periodo(values['date_invoice'])
        flag_venta = False
        if 'active_model' in self._context:
            if self._context['active_model'] == u'sale.order':
                if values['type'] == 'out_invoice':
                    flag_venta = True
        if 'type' in self._context:
            if self._context['type'] == 'out_invoice':
                flag_venta = True
        # Sí es Factura de Venta generamos nuestra Autorización
        if flag_venta == True:
            mensaje = ""
            autorizacion = self.env['autorizacion.sri'].search([('tipo_comprobante', '=', 4), ('state', '=', 'activo')])
            mensaje = "No hay Autorización del SRI para Factura de Venta"
            if 'type' in values:
                if values['type'] == 'out_refund':
                    autorizacion = self.env['autorizacion.sri'].search(
                        [('tipo_comprobante', '=', 5), ('state', '=', 'activo')])
                    mensaje = "No hay Autorización del SRI para Nota de Crédito de Venta"
            if not autorizacion:
                raise except_orm("Error", mensaje)
            if len(str(autorizacion.secuencia)) == 13:
                numero_factura = autorizacion.secuencia
            else:
                faltante = 13 - len(str(autorizacion.secuencia))
                numero_factura = ""
                for x in range(0, faltante):
                    numero_factura = numero_factura + "0"
                numero_factura = numero_factura + str(autorizacion.secuencia)
            values.update({
                'numero_factura': autorizacion.numero_establecimiento + "-" + autorizacion.punto_emision + "-" + numero_factura,
                'autorizacion_sri': autorizacion.id,
                'reference': u'Factura ' + autorizacion.numero_establecimiento + "-" + autorizacion.punto_emision + "-" + numero_factura,
                'numero_factura_interno': autorizacion.numero_establecimiento + "-" + autorizacion.punto_emision + "-" + numero_factura
            })
            autorizacion.write({'secuencia': autorizacion.secuencia + 1})
            if 'pedido_relacionado' in values:  # Anticipos de pedido de ventas
                factura = 'invoice_parcial'
                if values['porcentaje_anticipo'] == 'total':
                    factura = 'invoice'
                pedido = self.env['sale.order'].search([('id', '=', values['pedido_relacionado'])])
                if values['porcentaje_anticipo'] == 'total':
                    # Cambiamos los estados de las líneas
                    for line in pedido.order_line.filtered(lambda x: x.line_approval == 'accepted'):
                        line.write({
                            'line_approval': 'facturado',
                            'facturado': True
                        })
                pedido.write({
                    'have_anticipo': True,
                    'state_pedido_eliterp': factura
                })
        else:
            if 'type' in values:
                if values['type'] == 'in_refund':
                    return super(AccountInvoice, self).create(values)
            numero_previo = values['numero_factura']
            if len(numero_previo) < 9:
                faltante = 9 - len(numero_previo)
                numero_factura = ""
                for x in range(0, faltante):
                    numero_factura = numero_factura + "0"
                numero_factura = numero_factura + str(numero_previo)
            else:
                numero_factura = values['numero_factura']
            values.update({
                'numero_factura': numero_factura,
                'reference': u'Factura ' + numero_factura,
                'numero_factura_interno': values['punto_emision'] + "-" + values[
                    'numero_establecimiento'] + "-" + numero_factura
            })
        # Verificamos modelo activo
        if 'active_model' in self._context:
            # Comprobantes (Factura) de Caja Chica
            if self._context['active_model'] == 'petty.cash.voucher':
                values.update({'pago_caja_chica': True,
                               'voucher_caja_chica_id': self._context['active_id']})
                beneficiario = self.env['res.partner'].browse(values['partner_id'])[0].name
                self.env['petty.cash.voucher'].browse(self._context['active_id']).write({'have_factura': True,
                                                                                         'beneficiario': beneficiario})
            # Comprobantes (Factura) de Viáticos
            if self._context['active_model'] == 'eliterp.provision.voucher':
                # Comprobamos qué no estemos creando dos Facturas en documento de Viáticos
                factura_provision = self.env['account.invoice'].search(
                    [('voucher_provision_id', '=', self._context['active_id'])])
                if factura_provision:
                    raise except_orm("Error", "No se puede crear dos Facturas por registro de Viáticos")
                values.update({'pago_provision': True,
                               'voucher_provision_id': self._context['active_id']})
                self.env['eliterp.provision.voucher'].browse(self._context['active_id']).write({
                    'have_factura': True
                })
        return super(AccountInvoice, self).create(values)

    @api.multi
    def write(self, vals):
        '''Sobreescribimos Método (PUT) del modelo'''
        res = super(AccountInvoice, self).write(vals)
        # Si tiene Líneas de Impuestos procesamos Retención
        if 'tax_line_ids' in vals:
            if self.have_withhold == True:
                self.withhold_id.write({
                    'factura_modificada': True,
                    'base_imponible': self.amount_untaxed,
                    'base_iva': self.amount_tax
                })
        return res

    def get_moneda(self):
        ''''Obtenemos la Moneda'''
        return self.env['res.currency'].search([('name', '=', 'USD')])[0].id

    @api.depends('date_invoice')
    def get_periodo_contable(self):
        '''Obtenemos el Período Contable con la fecha de Emisión'''
        if not self.date_invoice:
            self.periodo = False
        else:
            fecha = datetime.strptime(self.date_invoice, "%Y-%m-%d")
            periodo = self.env['account.period'].search([('name', '=', fecha.year)])
            if len(periodo) == 0:
                raise except_orm("Error", "Debe crear primero el Período Contable")
            periodo_contable = periodo.lineas_periodo.filtered(lambda x: x.code == fecha.month)
            self.periodo = periodo_contable.id

    @api.one
    def compute_total_nota_credito(self):
        '''Calculamos total de la Nota de Cŕedito'''
        total = 0.00
        if self.have_nota_credito == True:
            notas_credito = self.env['account.invoice'].search([('invoice_id_ref', '=', self.id)])
            for nota in notas_credito:
                total = total + nota.amount_total
        self.total_nota_credito = total

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('proforma', 'Pro-forma'),
        ('proforma2', 'Pro-forma'),
        ('abonada', 'Abonada'),
        ('open', 'Ingresada'),
        ('paid', 'Pagada'),
        ('cancel', 'Anulada'),
    ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used when the invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")
    state_notas = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Contabilizada'),
        ('cancel', 'Anulada')], string="Estado", default='draft')
    invoice_id_ref = fields.Many2one('account.invoice', 'Referencia de Factura')
    numero_autorizacion = fields.Char(string='No. Autorización')
    numero_factura = fields.Char(string='No. Factura')
    punto_emision = fields.Char(string='Punto Emisión', size=3)
    numero_factura_interno = fields.Char(string=u'Número de Factura Interno')
    numero_establecimiento = fields.Char(string=u'Número de Establecimiento', size=3)
    sustento_tributario = fields.Many2one('sustento.tributario', string=u'Sustento Tributario')
    autorizacion_sri = fields.Many2one('autorizacion.sri', string='Autorización')
    have_withhold = fields.Boolean('Tiene Retención?', default=False)
    total_retener = fields.Monetary(string='Total a Retener', store=True, readonly=True,
                                    compute='_compute_amount')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Centro de Costos')
    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    payment_conditions = fields.Selection([('cash', 'Contado'), ('credit', u'Crédito')], 'Condiciones de Pago')
    property_supplier_payment_term_id = fields.Many2one('account.payment.term', string="Plazo de Pago")
    fecha_provision = fields.Date('Fecha Provisión', default=fields.Date.context_today)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True, readonly=True, states={'draft': [('readonly', False)]},
                                  default=get_moneda, track_visibility='always')
    consultant_sale_id = fields.Many2one('hr.employee', 'Asesor')
    concepto_factura = fields.Char('Concepto')
    total_nota_credito = fields.Monetary(string="Nota de Crédito", compute='compute_total_nota_credito')
    have_nota_credito = fields.Boolean(defatul=False)
    factura_proveedor = fields.Binary('Factura', attachment=True)
    factura_provision_name = fields.Char()
    periodo = fields.Many2one('lines.account.period', compute='get_periodo_contable')
    pago_caja_chica = fields.Boolean(default=False)
    voucher_caja_chica_id = fields.Many2one('petty.cash.voucher')
    # MARZ
    have_scheduled_payment = fields.Boolean(defatul=False)
    pago_provision = fields.Boolean(default=False)
    voucher_provision_id = fields.Many2one('eliterp.provision.voucher')
    con_sin_withhold = fields.Boolean(u'Con Retención?', default=True)
    line_approval = fields.Selection(
        [('pendiente', 'Pendiente'), ('aprobado_parcial', 'Aprobado Parcial'), ('aprobado', 'Aprobado')],
        default='pendiente')
    type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('in_sale_note', 'Nota de Venta'),
        ('out_refund', 'Customer Refund'),
        ('in_refund', 'Vendor Refund'),
    ], readonly=True, index=True, change_default=True,
        default=lambda self: self._context.get('type', 'out_invoice'),
        track_visibility='always')
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 required=True, readonly=True, states={'draft': [('readonly', False)]},
                                 default=_default_journal,
                                 domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]")

    _sql_constraints = [('numero_factura_interno_uniq', 'CHECK(1=1)', "El Número de Documento ya está registrado")]


# MARZ
class AccountJournal(models.Model):
    _inherit = "account.journal"

    type = fields.Selection([
        ('sale', 'Sale'),
        ('purchase', 'Purchase'),
        ('purchase_sale_note', 'Compra (RISE)'),
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('general', 'Miscellaneous'),
    ], required=True,
        help="Select 'Sale' for customer invoices journals.\n" \
             "Select 'Purchase' for vendor bills journals.\n" \
             "Select 'Cash' or 'Bank' for journals that are used in customer or vendor payments.\n" \
             "Select 'General' for miscellaneous operations journals.")
