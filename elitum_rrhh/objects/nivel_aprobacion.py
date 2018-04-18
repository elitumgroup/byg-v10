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

import time
from datetime import datetime, timedelta
from dateutil import relativedelta

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError, except_orm
from odoo.tools.safe_eval import safe_eval


class RrhhNivelAprobacion(models.Model):
    _name = 'rrhh.nivel.aprobacion'

    _description = u'Modelo - Nivel de Aprobación'

    # MARZ
    @api.multi
    def name_get(self):
        res = []
        for data in self:
            res.append((data.id, "Nivel de %s" % (data.nivel_1_nomina.name)))
        return res

    nivel_1_nomina = fields.Many2one('res.users', 'Nivel 1')
    nivel_2_nomina = fields.Many2one('res.users', 'Nivel 2')
    tiempo_nomina = fields.Integer('Tiempo de Espera (Horas)')
