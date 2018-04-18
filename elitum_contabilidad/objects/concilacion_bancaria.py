# -*- encoding: utf-8 -*-
#########################################################################
# Copyright (C) 2017 Ing. Harry Alvarez, Elitum Group                   #
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


from odoo.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from odoo import api, fields, models, _


class ConcilacionBancariaWizard(models.TransientModel):
    _name = 'concilacion.bancaria.wizard'

    _description = 'Concilacion Bancaria Wizard'

    def generar_conciliacion(self):
        movimientos = self.env['account.move.line'].search([('account_id', '=', self.banco_id.account_id.id),
                                                            ('date', '>=', self.fecha_inicio),
                                                            ('date', '<=', self.fecha_fin)])

        lineas_movimientos = []
        concilaciones = self.env['concilacion.bancaria'].search([('state', '=', 'confirmado'),
                                                                 ('banco_id', '=', self.banco_id.id)])
        saldo_inicial = 0.00
        if len(concilaciones) == 0:
            # MARZ
            """
                Apertura de Conciliaciones Bancarias
            """
            saldo_inicial = self.env['report.elitum_contabilidad.reporte_libro_mayor'].get_saldo_inicial(
                self.banco_id.account_id, self.fecha_inicio, self.fecha_fin)
        else:
            concilacion_anterior = concilaciones[-1]
            saldo_inicial = concilacion_anterior.saldo_cuenta
            for line in concilacion_anterior.lineas_movimientos_bancarios_ids:
                if line.check == False:
                    lineas_movimientos.append([0, 0, {'move_line_id': line.move_line_id.id,
                                                      'valor': line.valor}])
        for line in movimientos:
            if line.move_id.state == 'posted' and line.move_id.reversado == False:
                valor = 0.00
                if line.credit == 0.00:
                    valor = abs(line.debit)
                if line.debit == 0.00:
                    valor = abs(line.credit)
                    valor = -1 * valor
                lineas_movimientos.append([0, 0, {'move_line_id': line.id,
                                                  'valor': valor}])
        concilacion = self.env['concilacion.bancaria'].create({
            'banco_id': self.banco_id.id,
            'fecha_inicio': self.fecha_inicio,
            'fecha_fin': self.fecha_fin,
            'saldo_inicial': saldo_inicial,
            'lineas_movimientos_bancarios_ids': lineas_movimientos
        })

        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('elitum_contabilidad.action_concilacion_bancaria_eliterp')
        form_view_id = imd.xmlid_to_res_id('elitum_contabilidad.eliterp_concilacion_bancaria_view_form')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'res_id': concilacion.id,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        return result

    banco_id = fields.Many2one('res.bank', "Banco", domain=[('type_action', '=', 'payments')], required=True)
    fecha_inicio = fields.Date('Fecha Inicio', required=True)
    fecha_fin = fields.Date('Fecha Fin', required=True)


class LineaMovimientosBancarios(models.Model):
    _name = 'linea.movimientos.bancarios'

    _description = 'Linea Movimientos Bancarios'

    move_line_id = fields.Many2one('account.move.line', 'Movimiento')
    check = fields.Boolean(default=False, string="Seleccionar")
    fecha = fields.Date(related='move_line_id.date', string="Fecha", store=True)
    tipo = fields.Many2one('account.journal', related='move_line_id.journal_id', string="Tipo", store=True)
    concepto = fields.Char(related='move_line_id.name', string="Concepto", store=True)
    referencia = fields.Char(related='move_line_id.ref', string="Referencia", store=True)
    valor = fields.Float('Valor')
    concilacion_bancaria_id = fields.Many2one('concilacion.bancaria', ondelete='cascade', string=u"Conciliación")


class ConcilacionBancaria(models.Model):
    _name = 'concilacion.bancaria'

    _description = 'Concilacion Bancaria'

    @api.one
    @api.depends('lineas_movimientos_bancarios_ids')
    def get_totales(self):
        total = 0.00
        total_cuenta = 0.00
        if len(self.lineas_movimientos_bancarios_ids) == 0:
            concilaciones = self.env['concilacion.bancaria'].search([('state', '=', 'confirmado'),
                                                                     ('banco_id', '=', self.banco_id.id)])[-1]
            if len(concilaciones) != 0:
                self.total = concilaciones.total_concilacion
            else:
                self.total = total
                self.saldo_cuenta = self.saldo_inicial
        else:
            for line in self.lineas_movimientos_bancarios_ids:
                # MARZ
                if line.check:
                    total_cuenta += line.valor
                total += line.valor
            self.total = total + self.saldo_inicial
        print total_cuenta
        self.saldo_cuenta = self.saldo_inicial + total_cuenta

    def imprimir_concilacion_bancaria(self):
        return self.env['report'].get_action(self, 'elitum_contabilidad.reporte_concilacion_bancaria')

    def confirmar_concilacion(self):
        '''Confirmamos la Conciliación Bancaria'''
        new_name = self.journal_id.sequence_id.next_by_id()
        return self.write({
            'state': 'confirmado',
            'name': new_name,
            'fecha_confirmacion': fields.Date.today(),
            'total_concilacion': self.total
        })

    @api.model
    def _default_journal(self):
        return self.env['account.journal'].search([('name', '=', 'Concilacion Bancaria')])[0].id

    banco_id = fields.Many2one('res.bank', "Banco", domain=[('type_action', '=', 'payments')])
    account_id = fields.Many2one('account.account', related='banco_id.account_id', store=True)
    name = fields.Char()
    fecha_confirmacion = fields.Date()
    fecha_inicio = fields.Date('Fecha Inicio')
    fecha_fin = fields.Date('Fecha Fin')
    concepto = fields.Char()
    saldo_inicial = fields.Float('Saldo Inicial')
    total = fields.Float('Saldo Cuenta Contable', compute='get_totales')
    total_concilacion = fields.Float('')
    journal_id = fields.Many2one('account.journal', default=_default_journal)
    saldo_cuenta = fields.Float('Saldo Cuenta Banco')
    lineas_movimientos_bancarios_ids = fields.One2many('linea.movimientos.bancarios', 'concilacion_bancaria_id',
                                                       string=u"Líneas de Movimientos")
    state = fields.Selection([('pendiente', 'Borrador'), ('confirmado', 'Confirmado')], default='pendiente')
    notas = fields.Text()
