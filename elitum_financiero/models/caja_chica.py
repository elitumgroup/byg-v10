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
import json
from io import StringIO
import ast
import datetime


class PettyCashSupplier(models.Model):
    _name = 'petty.cash.supplier'

    _description = 'Proveedor de Caja Chica'

    name = fields.Char(string="Nombre")
    ruc = fields.Char('RUC')
    direccion = fields.Char('Dirección')


class PettyCashVoucherLine(models.Model):
    _name = 'petty.cash.voucher.line'

    _description = u'Líneas de Vale/Factura Caja Chica'

    account_id = fields.Many2one('account.account', string="Cuenta Contable",
                                 domain=[('tipo_contable', '=', 'movimiento')])
    amount = fields.Float(string="Cantidad")
    petty_cash_voucher_id = fields.Many2one('petty.cash.voucher')


class PettyCashVoucher(models.Model):
    _name = 'petty.cash.voucher'

    _description = 'Comprobante de Caja Chica'

    def imprimir_vale_caja(self):
        return self.env['report'].get_action(self, 'elitum_financiero.reporte_vale_caja_chica')

    @api.one
    def confirm_voucher(self):
        if self.type_voucher == 'invoice':
            factura = self.env['account.invoice'].search([('voucher_caja_chica_id', '=', self.id)])[0]
            if factura.state == 'draft':
                raise ValidationError(_("Debe validar la Factura"))
        else:
            if len(self.line_petty_cash_voucher) == 0:
                raise ValidationError(_("Debe ingresar Líneas de Cuentas"))
            for line in self.line_petty_cash_voucher:
                if line.amount == 0.00:
                    raise ValidationError(_("Debe eliminar las Líneas de Cuentas con Monto igual a 0"))
        return self.write({
            'state': 'open',
            'name': self.journal_id.sequence_id.next_by_id(),
            'petty_cash_replacement_id': self.custodian_id.petty_cash_id.id
        })
    @api.model
    def _default_journal(self):
        return self.env['account.journal'].search([('name', '=', 'Vale Caja')])[0].id

    def revisar_factura(self):
        factura = self.env['account.invoice'].search([('voucher_caja_chica_id', '=', self.id)])
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account.action_invoice_tree2')
        form_view_id = imd.xmlid_to_res_id('account.invoice_supplier_form')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
            'res_id': factura[0].id
        }
        return result

    def invoice_caja_chica(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account.action_invoice_tree2')
        form_view_id = imd.xmlid_to_res_id('account.invoice_supplier_form')
        context = json.loads(str(action.context).replace("'", '"'))
        context.update({'default_pago_caja_chica': True})
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'context': context,
            'res_model': action.res_model,
        }
        return result

    @api.one
    def _get_total(self):
        if self.type_voucher == 'vale':
            self.amount_total = sum(line.amount for line in self.line_petty_cash_voucher)
        else:
            factura = self.env['account.invoice'].search([('voucher_caja_chica_id', '=', self.id)])
            if len(factura) == 0:
                self.amount_total = 0.00
            else:
                self.amount_total = factura[0].residual

    @api.model
    def create(self, vals):
        if len(self.env['petty.cash.replacement'].search([('custodian_id', '=', vals['custodian_id'])])) == 0:
            raise ValidationError(_("Debe aperturar una caja para el Custodio"))
        res = super(PettyCashVoucher, self).create(vals)
        return res

    name = fields.Char(string="Nombre")
    type_voucher = fields.Selection([('vale', 'Vale'), ('invoice', 'Factura')], string="Tipo de Vale", default='vale')
    journal_id = fields.Many2one('account.journal', default=_default_journal)
    beneficiario = fields.Char(string="Beneficiario")
    date = fields.Date('Fecha Registro', default=fields.Date.context_today)
    amount_total = fields.Float(string="Cantidad Comprobante", compute='_get_total')
    detalle = fields.Char(string="Concepto")
    have_factura = fields.Boolean(default=False)
    line_petty_cash_voucher = fields.One2many('petty.cash.voucher.line', 'petty_cash_voucher_id',
                                              string="Detalle de Cuenta")
    custodian_id = fields.Many2one('petty.cash.custodian')
    state = fields.Selection([('draft', 'Borrador'), ('open', 'Confirmado')], string="Tipo de Vale", default='draft')
    petty_cash_replacement_id = fields.Many2one('petty.cash.replacement')
    check_reposicion = fields.Boolean('Reponer', default=False)
    state_reposicion = fields.Selection([('pendiente', 'Pendiente'), ('pagado', 'Pagado')], string="Estado",
                                        default='pendiente')


class PettyCashCustodian(models.Model):
    _name = 'petty.cash.custodian'

    _description = 'Custodio de Caja Chica'

    name = fields.Char('Nombre')
    account_id = fields.Many2one('account.account', domain=[('tipo_contable', '=', 'movimiento')])
    amount = fields.Float('Monto Asignado')
    petty_cash_id = fields.Many2one('petty.cash.replacement')


class PettyCashReplacement(models.Model):
    _name = 'petty.cash.replacement'

    _description = u'Reposición de Caja Chica'

    def imprimir_reposicion_caja_chica(self):
        return self.env['report'].get_action(self, 'elitum_financiero.reporte_reposicion_caja_chica')

    @api.model
    def _default_journal(self):
        return self.env['account.journal'].search([('name', '=', 'Caja Chica')])[0].id

    @api.one
    def para_aprobar(self):
        self.write({'state': 'para_aprobrar'})

    @api.one
    def aprobado(self):
        self.write({
            'state': 'aprobado',
            'approval_user': self.env.uid
        })

    def aperturar_caja(self):
        voucher_ids = self.env['petty.cash.voucher'].search([('check_reposicion', '=', False),
                                                             ('state_reposicion', '=', 'pendiente'),
                                                             ('custodian_id', '=', self.custodian_id.id)])
        for voucher in voucher_ids:
            voucher.update({'petty_cash_replacement_id': False})
            voucher.write({'petty_cash_replacement_id': self[0].id})
        # MARZ
        self.write({'state': 'open',
                    'name': self.journal_id.sequence_id.next_by_id(),
                    'date_apertura': self.date})

    def liquidar_caja(self):
        move_id = self.env['account.move'].create({'journal_id': self.journal_id.id,
                                                   'date': self.date,
                                                   'ref': self.name})
        self.env['account.move.line'].with_context(check_move_validity=False).create({'name': self.custodian_id.name,
                                                                                      'journal_id': self.journal_id.id,
                                                                                      'account_id': self.custodian_id.account_id.id,
                                                                                      'move_id': move_id.id,
                                                                                      'debit': 0.00,
                                                                                      'credit': self.monto_vale_factura,
                                                                                      'date': self.date})

        count = len(self.lineas_vale_factura)
        for line_vale_factura in self.lineas_vale_factura:
            # MARZ
            if line_vale_factura.type_voucher == 'invoice':
                factura = self.env['account.invoice'].search([('voucher_caja_chica_id', '=', line_vale_factura.id)])
                self.env['account.move.line'].with_context(check_move_validity=False).create(
                    {'name': factura.account_id.name,
                     'journal_id': self.journal_id.id,
                     'account_id': factura.account_id.id,
                     'move_id': move_id.id,
                     'debit': line_vale_factura.amount_total,
                     'credit': 0.00,
                     'date': self.date})
            count -= 1
            if line_vale_factura.check_reposicion == True and line_vale_factura.state_reposicion == 'pendiente':
                count_line = len(line_vale_factura.line_petty_cash_voucher)
                for line in line_vale_factura.line_petty_cash_voucher:
                    count_line -= 1
                    if count == 0 and count_line == 0:
                        self.env['account.move.line'].with_context(check_move_validity=True).create(
                            {'name': line.account_id.name,
                             'journal_id': self.journal_id.id,
                             'account_id': line.account_id.id,
                             'move_id': move_id.id,
                             'debit': line.amount,
                             'credit': 0.00,
                             'date': self.date})
                    else:
                        self.env['account.move.line'].with_context(check_move_validity=False).create(
                            {'name': line.account_id.name,
                             'journal_id': self.journal_id.id,
                             'account_id': line.account_id.id,
                             'move_id': move_id.id,
                             'debit': line.amount,
                             'credit': 0.00,
                             'date': self.date})
                    line.write({'petty_cash_replacement_id': self.id})
        move_id.with_context(asientos_eliterp=True, name_asiento=self.name).post()
        move_id.write({'ref': self.name})
        # MARZ
        return self.write(
            {'state': 'closed', 'move_id': move_id.id})

    @api.model
    def create(self, vals):
        # ABEL
        if len(self.lineas_vale_factura) == 0:
            raise ValidationError(_("No hay líneas de Vale/Factura"))
        res = super(PettyCashReplacement, self).create(vals)
        res.custodian_id.petty_cash_id = res.id
        res.monto_asignado = res.custodian_id.amount
        res.saldo = res.custodian_id.amount
        return res

    @api.one
    def cargar_valor(self):
        total = 0.00
        for line in self.lineas_vale_factura:
            if line.check_reposicion == True:
                total += line.amount_total
        if total > (self.saldo):
            raise ValidationError(_("El Valor a Reponer es mayor que el Monto Asignado"))
        self.write({'monto_vale_factura': total, 'saldo': self.monto_asignado - total})

    @api.onchange('custodian_id')
    def onchange_custodian_id(self):
        self.monto_asignado = self.custodian_id.amount
        self.saldo = self.custodian_id.amount

    name = fields.Char('Nombre')
    monto_asignado = fields.Float('Monto Asignado')
    monto_vale_factura = fields.Float('Monto Vale/Factura')
    saldo = fields.Float('Saldo')
    move_id = fields.Many2one('account.move', 'Asiento Contable')
    journal_id = fields.Many2one('account.journal', default=_default_journal)
    date = fields.Date('Fecha', default=fields.Date.context_today)
    custodian_id = fields.Many2one('petty.cash.custodian')
    state = fields.Selection([('draft', 'Borrador'), ('open', 'Abierta'),
                              ('para_aprobrar', 'Solicitar Aprobación'), ('aprobado', 'Aprobado'),
                              ('closed', 'Liquidada')], string="Estado", default='draft')
    lineas_vale_factura = fields.One2many('petty.cash.voucher', 'petty_cash_replacement_id', string="Lineas de Caja")
    date_apertura = fields.Date('Fecha Apertura')
    date_reposicion = fields.Date('Fecha Reposición')
    approval_user = fields.Many2one('res.users')  # MARZ
