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
import datetime


class PaymentCancelReason(models.Model):
    _name = 'payment.cancel.reason'

    _description = 'Razon para Cancelar Payment'

    description = fields.Text(u'Descripción', required=True)

    def cancel_reason_payment(self):
        payment = self.env['account.payment'].browse(self._context['active_id'])
        move_id = payment.move_id
        move_id.with_context(from_payment=True, id_payment=payment.id).reverse_moves(fields.Date.today(),
                                                                                     payment.journal_id or False)
        move_id.write({'state': 'cancel', 'ref': self.description})
        payment.write({'state': 'cancel'})
        if payment:
            if payment.tipo_deposito == 'cheque':
                for cheque in payment.line_deposits_check_ids:
                    cheque.cheque_id.write({'state': 'recibido'})
        return


class LinePaymentMethod(models.Model):
    _name = 'line.patment.method'

    _description = 'Linea de Metodo de Pago'

    account_id = fields.Many2one('account.account', string='Cuenta', domain=[('tipo_contable', '=', 'movimiento')])
    payment_method = fields.Selection([('cash', 'Caja'), ('bank', 'Banco')])
    amount = fields.Float('Monto')
    payment_id = fields.Many2one('account.payment')
    glosa_referencia = fields.Char(string="Glosa")


class LineDepositsBank(models.Model):
    _name = 'line.deposits.bank'

    _description = 'Linea de Depositos Bancarios'

    account_id = fields.Many2one('account.account', string='Cuenta', domain=[('tipo_contable', '=', 'movimiento')])
    amount = fields.Float('Monto')
    payment_id = fields.Many2one('account.payment')


class LineDepositsEfectivo(models.Model):
    _name = 'line.deposits.efectivo'

    _description = 'Linea Depositos Efectivo'

    account_id = fields.Many2one('account.account', 'Cuenta Contable', domain=[('tipo_contable', '=', 'movimiento')])
    referencia = fields.Char('Referencia')
    monto = fields.Float('Monto')
    payment_id = fields.Many2one('account.payment')


class LineDepositsChecksExtern(models.Model):
    _name = 'line.deposits.checks.extern'

    _description = 'Linea Depositos Cheques Externos'

    banco = fields.Many2one('res.bank', 'Banco')
    numero_cuenta = fields.Char('No. Cuenta')
    numero_cheque = fields.Char('No. Cheque')
    nombre_girador = fields.Char('Nombre del Girador')
    account_id = fields.Many2one('account.account', 'Cuenta Contable', domain=[('tipo_contable', '=', 'movimiento')])
    monto = fields.Float('Monto')
    payment_id = fields.Many2one('account.payment')


class LineDepositsCheck(models.Model):
    _name = 'line.deposits.check'

    _description = 'Linea Depositos Cheques'

    amount = fields.Float('Monto')
    numero_cheque = fields.Char('No. Cheque')
    banco = fields.Many2one('res.bank', 'Banco')
    payment_id = fields.Many2one('account.payment')
    cheque_id = fields.Many2one('cheques.eliterp')
    fecha_vencimiento = fields.Date() # MARZ
    account_id = fields.Many2one('account.account', string='Cuenta', domain=[('tipo_contable', '=', 'movimiento')])


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def imprimir_deposito(self):
        return self.env['report'].get_action(self, 'elitum_contabilidad.reporte_deposito')

    def imprimir_transferencia(self):
        return self.env['report'].get_action(self, 'elitum_contabilidad.reporte_transferencia')

    def anular_payment(self):
        return {
            'name': "Explique la Razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'payment.cancel.reason',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.model
    def create(self, vals):
        self.env['eliterp.funciones'].validar_periodo(vals['payment_date'])
        res = super(AccountPayment, self).create(vals)
        res.name = ""
        return res

    @api.one
    def confirmar_transferencia(self):
        move_id = self.env['account.move'].create({'journal_id': self.journal_id.id,
                                                   'date': self.payment_date
                                                   })
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': self.concepto,
             'journal_id': self.journal_id.id,
             'account_id': self.account_credit_id.id,
             'move_id': move_id.id,
             'debit': 0.0,
             'credit': self.monto_transferencia_bancaria,
             'date': self.payment_date
             })
        self.env['account.move.line'].with_context(check_move_validity=True).create(
            {'name': self.concepto,
             'journal_id': self.journal_id.id,
             'account_id': self.cuenta_debit_id.account_id.id,
             'move_id': move_id.id,
             'debit': self.monto_transferencia_bancaria,
             'credit': 0.0,
             'date': self.payment_date
             })
        new_name = self.journal_id.sequence_id.next_by_id()
        move_id.with_context(asientos_eliterp=True, name_asiento=new_name).post()
        move_id.write({'ref': new_name + " - " + self.concepto})
        return self.write({'state': 'posted', 'name': new_name, 'move_id': move_id.id})

    @api.one
    def confirm_payment(self):
        if self.payment_type_eliterp == 'deposit':
            if self.tipo_deposito == 'cheque':
                move_id = self.env['account.move'].create({'journal_id': self.journal_id.id,
                                                           'date': self.payment_date
                                                           })
                for line in self.line_deposits_check_ids:
                    self.env['account.move.line'].with_context(check_move_validity=False).create(
                        {'name': self.concepto,
                         'journal_id': self.journal_id.id,
                         'account_id': line.account_id.id,
                         'move_id': move_id.id,
                         'debit': 0.0,
                         'credit': line.amount,
                         'date': self.payment_date
                         })
                    line.cheque_id.write({'state': 'depositado'})
                self.env['account.move.line'].with_context(check_move_validity=True).create(
                    {'name': self.concepto,
                     'journal_id': self.journal_id.id,
                     'account_id': self.banco_efectivo.account_id.id,
                     'move_id': move_id.id,
                     'debit': self.amount,
                     'credit': 0.0,
                     'date': self.payment_date
                     })
                new_name = self.journal_id.sequence_id.next_by_id()
                move_id.with_context(asientos_eliterp=True, name_asiento=new_name).post()
                move_id.write({'ref': new_name + " - " + self.concepto})
                return self.write({'state': 'posted', 'name': new_name, 'move_id': move_id.id})
            if self.tipo_deposito == 'efectivo':
                move_id = self.env['account.move'].create({'journal_id': self.journal_id.id,
                                                           'date': self.payment_date
                                                           })
                for line in self.linea_depositos_efectivo:
                    self.env['account.move.line'].with_context(check_move_validity=False).create(
                        {'name': self.concepto,
                         'journal_id': self.journal_id.id,
                         'account_id': line.account_id.id,
                         'move_id': move_id.id,
                         'debit': 0.0,
                         'credit': line.monto,
                         'date': self.payment_date
                         })
                self.env['account.move.line'].with_context(check_move_validity=True).create(
                    {'name': self.concepto,
                     'journal_id': self.journal_id.id,
                     'account_id': self.banco_efectivo.account_id.id,
                     'move_id': move_id.id,
                     'debit': self.amount,
                     'credit': 0.0,
                     'date': self.payment_date
                     })
                new_name = self.journal_id.sequence_id.next_by_id()
                move_id.with_context(asientos_eliterp=True, name_asiento=new_name).post()
                move_id.write({'ref': new_name + " - " + self.concepto})
                return self.write({'state': 'posted', 'name': new_name, 'move_id': move_id.id})
            if self.tipo_deposito == 'cheque_externo':
                move_id = self.env['account.move'].create({'journal_id': self.journal_id.id,
                                                           'date': self.payment_date
                                                           })
                for line in self.linea_depositos_cheques_externos:
                    self.env['account.move.line'].with_context(check_move_validity=False).create(
                        {'name': self.concepto,
                         'journal_id': self.journal_id.id,
                         'account_id': line.account_id.id,
                         'move_id': move_id.id,
                         'debit': 0.0,
                         'credit': line.monto,
                         'date': self.payment_date
                         })
                self.env['account.move.line'].with_context(check_move_validity=True).create(
                    {'name': self.concepto,
                     'journal_id': self.journal_id.id,
                     'account_id': self.banco_efectivo.account_id.id,
                     'move_id': move_id.id,
                     'debit': self.amount,
                     'credit': 0.0,
                     'date': self.payment_date
                     })
                new_name = self.journal_id.sequence_id.next_by_id()
                move_id.with_context(asientos_eliterp=True, name_asiento=new_name).post()
                move_id.write({'ref': new_name + " - " + self.concepto})
                return self.write({'state': 'posted', 'name': new_name, 'move_id': move_id.id})

    @api.model
    def _default_journal(self):
        if self._context['default_payment_type_eliterp'] == 'deposit':
            return self.env['account.journal'].search([('name', '=', 'Depositos')])[0].id
        if self._context['default_payment_type_eliterp'] == 'transfer':
            return self.env['account.journal'].search([('name', '=', 'Transferencias')])[0].id

    def cargar_monto(self):
        sum = 0.00
        if self.tipo_deposito == 'cheque':
            for line in self.line_deposits_check_ids:
                sum += line.amount
        if self.tipo_deposito == 'cheque_externo':
            for line in self.linea_depositos_cheques_externos:
                sum += line.monto
        if self.tipo_deposito == 'efectivo':
            for line in self.linea_depositos_efectivo:
                sum += line.monto
        return self.update({'amount': sum})

    def cargar_cheques(self):
        # MARZ
        hoy = datetime.date.today().strftime('%Y-%m-%d')
        cheques_list = self.env['cheques.eliterp'].search([
            ('fecha_recepcion_emision', '<=', hoy),
            ('fecha_del_cheque', '>=', hoy),
            ('tipo_cheque', '=', 'recibidos'),
            ('state', '=', 'recibido')
        ])
        list_lines = []
        for cheque in cheques_list:
            list_lines.append([0, 0, {'cheque_id': cheque.id,
                                      'numero_cheque': cheque.name,
                                      'account_id': cheque.cuenta_id.id,
                                      'banco': cheque.banco.id,
                                      'amount': cheque.monto,
                                      'fecha_vencimiento': cheque.fecha_del_cheque}])
        return self.update({'line_deposits_check_ids': list_lines})

    line_method_pagos = fields.One2many('line.patment.method', 'payment_id', string=u'Linea de Pagos')
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Confirmado'),
                              ('sent', 'Sent'), ('reconciled', 'Reconciled'), ('cancel', 'Anulado')],
                             readonly=True, default='draft', copy=False, string="Status")
    cuenta_debit_id = fields.Many2one('res.bank', string='Cuenta Debe', domain=[('type_action', '=', 'payments')])
    account_credit_id = fields.Many2one('account.account', string='Cuenta Haber',
                                        domain=[('tipo_contable', '=', 'movimiento')])
    monto_transferencia_bancaria = fields.Float('Monto')
    line_deposits_bank_ids = fields.One2many('line.deposits.bank', 'payment_id', string=u'Valores a Depositar')
    line_deposits_check_ids = fields.One2many('line.deposits.check', 'payment_id', string=u'Cheques Recaudados')
    payment_type_eliterp = fields.Selection([('deposit', u'Depósito'),
                                             ('payment', 'Pago'),
                                             ('transfer', 'Transferencia')])
    journal_id = fields.Many2one('account.journal', 'Journal',
                                 required=True, readonly=True, states={'draft': [('readonly', False)]},
                                 default=_default_journal, domain=None)
    amount = fields.Monetary(default=1.00)
    tipo_deposito = fields.Selection(
        [('cheque', 'Cheque Recaudados'), ('cheque_externo', 'Cheques'), ('efectivo', 'Efectivo')],
        string=u"Tipo de Depósito", default='cheque')
    banco_efectivo = fields.Many2one('res.bank')
    concepto = fields.Char('Concepto', required=True)
    linea_depositos_efectivo = fields.One2many('line.deposits.efectivo', 'payment_id', 'Linea de Cuentas')
    linea_depositos_cheques_externos = fields.One2many('line.deposits.checks.extern', 'payment_id', 'Linea de Cheques')
    move_id = fields.Many2one('account.move', "Asiento Contable")
    # ABEL
    analytic_account_id = fields.Many2one('account.analytic.account', 'Centro de Costos')
    project_id = fields.Many2one('eliterp.project', 'Proyecto')