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


class ChequesEliterp(models.Model):
    _name = 'cheques.eliterp'

    _description = 'Cheques'

    # MARZ
    def imprimir_reporte_cheque(self):
        return self.env['report'].get_action(self, 'elitum_contabilidad.reporte_cheque_matricial')


    @api.one
    def check_protestado(self):
        self
        return

    name = fields.Char('Numero de Cheque')
    partner_id = fields.Many2one('res.partner', 'Cliente/Proveedor')

    proveedor_id = fields.Many2one('res.partner', 'Proveedor')
    cliente_id = fields.Many2one('res.partner', 'Cliente')

    nombre = fields.Char('Nombre')
    cuenta_del_cheque = fields.Char('Cuenta Bancaria')
    banco = fields.Many2one('res.bank', 'Banco')

    cuenta_id = fields.Many2one('account.account', domain=[('tipo_contable', '=', 'movimiento')],
                                string=u'Cuenta Contable')
    monto = fields.Float('monto')
    cheque_en_letras = fields.Char('Cheque en Letras')
    fecha_recepcion_emision = fields.Date('Fecha Recepcion/Emision')
    fecha_del_cheque = fields.Date('Fecha del Cheque')
    tipo_cheque = fields.Selection([('emitidos', 'Emitidos'), ('recibidos', 'Recibidos')], string=u'Tipo de Cheque')
    tipo_cheque_fecha = fields.Selection([('corriente', 'Corriente'), ('postfechado', 'A Fecha')],
                                         string=u'Tipo de Cheque Fecha', default='corriente')
    state = fields.Selection([('recibido', 'Recibido'), ('depositado', 'Depositado'),
                              ('emitido', 'Emitido'), ('cobrado', 'Cobrado'), ('protestado', 'Protestado')],
                             string=u'Estado')

    asiento_contable = fields.Many2one('account.move')
