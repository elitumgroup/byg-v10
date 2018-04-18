# -*- encoding: utf-8 -*-
#########################################################################
# Copyright (C) 2016 Ing. Harry Alvarez, Elitum Group                   #
#                                                                       #
#This program is free software: you can redistribute it and/or modify   #
#it under the terms of the GNU General Public License as published by   #
#the Free Software Foundation, either version 3 of the License, or      #
#(at your option) any later version.                                    #
#                                                                       #
#This program is distributed in the hope that it will be useful,        #
#but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
#GNU General Public License for more details.                           #
#                                                                       #
#You should have received a copy of the GNU General Public License      #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################

from odoo import api, fields, models, _


class ResPartner (models.Model):

    _inherit = "res.partner"

    def _account_receivable(self):
        return 10

    def _account_payable(self):
        return 10

    property_account_receivable_id = fields.Many2one('account.account', 'Cuenta a Pagar', default=None, domain=[('tipo_contable','=','movimiento')])
    property_account_payable_id = fields.Many2one('account.account', 'Cuenta a Cobrar', default=None, domain=[('tipo_contable','=','movimiento')])
