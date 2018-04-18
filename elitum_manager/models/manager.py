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


class AccountMoveLine(models.Model):

    _inherit = "account.move.line"

    @api.multi
    def _update_check(self):
        return True


class ManagerObject (models.Model):

    _name = 'manager.object'

    _description = 'Administrador de Odoo'

    def reparar_facturas(self):
        moves = self.env['account.move'].search([])
        for move in moves:
            for line in move.line_ids:
                line.update({'date':move.date})


