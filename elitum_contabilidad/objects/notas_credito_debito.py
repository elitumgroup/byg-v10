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

from odoo import api, fields, models


class NotesCancelReason(models.Model):
    _name = 'notes.cancel.reason'

    _description = u'Razón para Cancelar Notas de Crédito/Débito'

    description = fields.Text(u'Descripción', required=True)

    def cancel_reason_notes(self):
        '''Cancelación de Nota'''
        notas = self.env['account.credit.debit.notes'].browse(self._context['active_id'])
        move_id = notas.move_id
        move_id.with_context(from_nota=True, id_nota=notas.id).reverse_moves(fields.Date.today(),
                                                                             notas.journal_id or False)
        move_id.write({
            'state': 'cancel',
            'ref': self.description
        })
        notas.write({'state': 'cancel'})
        return


class AccountCreditDebitNotes(models.Model):
    _name = 'account.credit.debit.notes'

    _description = u'Notas de Crédito/Débito'

    @api.model
    def create(self, vals):
        self.env['eliterp.funciones'].validar_periodo(vals['fecha'])
        res = super(AccountCreditDebitNotes, self).create(vals)
        return res

    def linea_asiento_eliterp(self, name, debe, haber, cuenta, flag, diario, move, fecha):
        self.env['account.move.line'].with_context(check_move_validity=flag).create(
            {'name': name,
             'journal_id': diario,
             'account_id': cuenta.id,
             'move_id': move,
             'debit': debe,
             'credit': haber,
             'date': fecha
             })

    @api.model
    def _default_journal(self):
        '''Colocamos el Diario por defecto en la Nota'''
        if 'default_type' in self._context:
            if self._context['default_type'] == 'credit':
                return self.env['account.journal'].search([('name', '=', 'Credito Bancaria')])[0].id
            if self._context['default_type'] == 'debit':
                return self.env['account.journal'].search([('name', '=', 'Debito Bancaria')])[0].id

    def imprimir_nota(self):
        '''Imprimimos Nota de Crédito/Débito (PDF)'''
        if self.type == 'credit':
            return self.env['report'].get_action(self, 'elitum_contabilidad.reporte_nota_credito_bancaria')
        if self.type == 'debit':
            return self.env['report'].get_action(self, 'elitum_contabilidad.reporte_nota_debito_bancaria')

    @api.one
    def confirmar_nota(self):
        '''Confirmar Nota de Crédito/Débito'''
        diario = self.journal_id.id
        move_id = self.env['account.move'].create({'journal_id': self.journal_id.id,
                                                   'date': self.fecha,
                                                   })
        if self.type == "debit":
            self.linea_asiento_eliterp(self.concepto, 0.00, self.amount, self.banco.account_id, False, diario,
                                       move_id.id, self.fecha)
            self.linea_asiento_eliterp(self.concepto, self.amount, 0.00, self.account_id, True, diario, move_id.id,
                                       self.fecha)
        if self.type == "credit":
            self.linea_asiento_eliterp(self.concepto, 0.00, self.amount, self.account_id, False, diario, move_id.id,
                                       self.fecha)
            self.linea_asiento_eliterp(self.concepto, self.amount, 0.00, self.banco.account_id, True, diario,
                                       move_id.id, self.fecha)
        move_id.post()
        move_id.write({'ref': self.glosa_debe})
        return self.write({
            'state': 'posted',
            'name': move_id.name,
            'move_id': move_id.id
        })

    def anular_nota(self):
        return {
            'name': "Explique la Razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'notes.cancel.reason',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    name = fields.Char('No. Documento')
    concepto = fields.Char('Concepto', required=True)
    banco = fields.Many2one('res.bank', 'Banco', domain="[('type_action', '=', 'payments')]", required=True)
    fecha = fields.Date('Fecha', default=fields.Date.context_today, required=True)
    glosa_debe = fields.Char('Glosa')
    amount = fields.Float('Monto', required=True)
    account_id = fields.Many2one('account.account', 'Cuenta Contable', domain=[('tipo_contable', '=', 'movimiento')],
                                 required=True)
    glosa_haber = fields.Char('Glosa')
    journal_id = fields.Many2one('account.journal', 'Journal', default=_default_journal)
    move_id = fields.Many2one('account.move')
    type = fields.Selection([('credit', 'Crédito'), ('debit', 'Débito')], string='Tipo de Nota')
    state = fields.Selection(
        [('draft', 'Borrador'), ('posted', 'Confirmado'), ('cancel', 'Anulado')],
        readonly=True, default='draft', copy=False, string="Estado")
    # ABEL
    analytic_account_id = fields.Many2one('account.analytic.account', 'Centro de Costos')
    project_id = fields.Many2one('eliterp.project', 'Proyecto')