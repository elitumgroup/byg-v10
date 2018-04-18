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

from odoo.exceptions import except_orm, UserError
from odoo import api, fields, models, _


class MoveCancelReason(models.Model):
    _name = 'move.cancel.reason'

    _description = 'Razon para Cancelar Asiento Contables'

    description = fields.Text(u'Descripción', required=True)

    def cancel_reason_move(self):
        move = self.env['account.move'].browse(self._context['active_id'])
        move.with_context(from_move=True, id_nota=move.id).reverse_moves(move.date, move.journal_id or False)
        move.write({'state': 'cancel'})
        return


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def create(self, vals):
        '''Sobreescribimos método (CREATE) del modelo account.move'''
        self.env['eliterp.funciones'].validar_periodo(vals['date'])
        res = super(AccountMove, self).create(vals)
        return res

    def anular_move(self):
        '''Anulamos Asientos Contables'''
        for line in self.line_ids:
            if line.full_reconcile_id:
                raise except_orm("Error", "Hay Asientos Conciliados, consulte con su Administrador")
        return {
            'name': "Explique la Razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'move.cancel.reason',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def imprimir_asiento_contable(self):
        '''Imprimir Comprobante de Asiento Contbale'''
        return self.env['report'].get_action(self, 'elitum_contabilidad.reporte_comprobante_diario')

    @api.multi
    def post(self):
        '''Sobreescribimos método (post) del modelo'''
        invoice = self._context.get('invoice', False)
        self._post_validate()
        for move in self:
            move.line_ids.create_analytic_lines()
            if move.name == '/':
                new_name = False
                journal = move.journal_id
                if invoice and invoice.move_name and invoice.move_name != '/':
                    new_name = invoice.move_name
                else:
                    if 'asientos_eliterp' in self._context:
                        if 'comprobante_interno' in self._context:
                            new_name = self.env['ir.sequence'].next_by_code('procesos.internos')
                        if 'name_asiento' in self._context:
                            new_name = self._context['name_asiento']
                    else:
                        if journal.sequence_id:
                            # If invoice is actually refund and journal has a refund_sequence then use that one or use the regular one
                            sequence = journal.sequence_id
                            if invoice and invoice.type in ['out_refund', 'in_refund'] and journal.refund_sequence:
                                sequence = journal.refund_sequence_id
                            new_name = sequence.with_context(ir_sequence_date=move.date).next_by_id()
                        else:
                            raise UserError(_('Please define a sequence on the journal.'))
                if new_name:
                    move.name = new_name
        # ABEL (Si es factura/nc llenar centro de costos y proyecto del movimiento)
        if invoice:
            return self.write({
                'state': 'posted',
                'analytic_account_id': invoice.analytic_account_id.id,
                'project_id': invoice.project_id.id
            })
        else:
            return self.write({
                'state': 'posted'
            })

    @api.multi
    def reverse_moves(self, date=None, journal_id=None):
        '''Sobreescribimos método (reverse_moves) del modelo'''
        date = date or fields.Date.today()
        reversed_moves = self.env['account.move']
        for ac_move in self:
            datos = {'date': date,
                     'reversado': True,
                     'journal_id': journal_id.id if journal_id else ac_move.journal_id.id,
                     'ref': _('reversal of: ') + ac_move.name}
            if 'from_invoice' in self._context:
                datos.update(
                    {'name': str(self.env['account.invoice'].browse(self._context['active_id']).number) + "- Reverso"})
            if 'from_retencion' in self._context:
                datos.update(
                    {'name': str(self.env['tax.withhold'].browse(self._context['active_id']).name) + "- Reverso"})
            if 'from_payment' in self._context:
                datos.update(
                    {'name': str(self.env['account.payment'].browse(self._context['id_payment']).name) + "- Reverso"})
            if 'from_nota' in self._context:
                datos.update({'name': str(
                    self.env['account.credit.debit.notes'].browse(self._context['id_nota']).name) + "- Reverso"})
            if 'from_move' in self._context:
                datos.update(
                    {'name': str(self.env['account.move'].browse(self._context['id_nota']).name) + "- Reverso"})
            if 'from_voucher' in self._context:
                datos.update(
                    {'name': str(self.env['account.voucher'].browse(self._context['id_voucher']).name) + "- Reverso"})
            reversed_move = ac_move.copy(default=datos)
            for acm_line in reversed_move.line_ids:
                acm_line.with_context(check_move_validity=False).write({
                    'debit': acm_line.credit,
                    'credit': acm_line.debit,
                    'amount_currency': -acm_line.amount_currency
                })
            reversed_moves |= reversed_move
        if reversed_moves:
            reversed_moves._post_validate()
            reversed_moves.post()
            return [x.id for x in reversed_moves]
        return []

    date = fields.Date(required=True, states={}, index=True,
                       default=fields.Date.context_today)
    state = fields.Selection([('draft', 'Sin Validar'),
                              ('posted', 'Validado'),
                              ('cancel', 'Anulado')],
                             string='Estado', required=True, readonly=True, copy=False, default='draft')
    reversado = fields.Boolean(default=False)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Centro de Costos')
    project_id = fields.Many2one('eliterp.project', 'Proyecto')

# ABEL
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    analytic_account_id = fields.Many2one('account.analytic.account', 'Centro de Costos', related="move_id.analytic_account_id", store=True)
    project_id = fields.Many2one('eliterp.project', 'Proyecto', related="move_id.project_id", store=True)

