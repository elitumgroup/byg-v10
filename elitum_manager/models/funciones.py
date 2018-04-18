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
from datetime import datetime, timedelta
from odoo.exceptions import UserError,except_orm, RedirectWarning, ValidationError



class EliterpFunciones(models.TransientModel):

    _name = 'eliterp.funciones'

    def validar_periodo(self,fecha):
        '''Función para validar Fecha de Documento'''
        fecha = datetime.strptime(fecha, "%Y-%m-%d")
        periodo = self.env['account.period'].search([('name','=',fecha.year)])
        if len(periodo)==0:
            raise except_orm("Error", "No hay ningún Período Contable")
        periodo_contable = periodo.lineas_periodo.filtered(lambda x: x.code == fecha.month)
        if len(periodo_contable)==0:
            raise except_orm("Error", "No hay ningún Período Contable")
        fecha_actual= fields.Date.today()
        if datetime.strptime(fecha_actual, "%Y-%m-%d")<datetime.strptime(periodo_contable.fecha_inicio, "%Y-%m-%d"):
            raise except_orm("Error", "La Fecha del registro está fuera del rango del Período")
        if datetime.strptime(fecha_actual, "%Y-%m-%d")>datetime.strptime(periodo_contable.fecha_cierre, "%Y-%m-%d"):
            raise except_orm("Error", "El Período Contable está Cerrado")