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



from odoo.exceptions import except_orm, Warning, RedirectWarning, UserError
from odoo import api, fields, models, _
from datetime import datetime


class PresupuestoComision(models.Model):

    _name = 'presupuesto.comision'

    _description = 'Presupuesto Comision'


    def get_mes(self, mes):
        if mes==1:
            return 'Enero'
        if mes==2:
            return 'Febrero'
        if mes==3:
            return 'Marzo'
        if mes==4:
            return 'Abril'
        if mes==5:
            return 'Mayo'
        if mes==6:
            return 'Junio'
        if mes==7:
            return 'Julio'
        if mes==8:
            return 'Agosto'
        if mes==9:
            return 'Septiembre'
        if mes==10:
            return 'Octubre'
        if mes==11:
            return 'Noviembre'
        if mes==12:
            return 'Diciembre'


    @api.model
    def create(self, vals):
        res = super(PresupuestoComision, self).create(vals)
        fecha = datetime.strptime(res.fecha_desde, "%Y-%m-%d")
        res.name = self.get_mes(fecha.month)+"-"+str(fecha.year)
        return res

    name = fields.Char()
    fecha_desde = fields.Date('Fecha Desde')
    fecha_hasta = fields.Date('Fecha Hasta')
    name = fields.Char('Nombre')
    monto = fields.Float('Monto')




class LineaComisiones(models.Model):

    _name = 'linea.comisiones'

    _description = 'Linea de Comisiones'

    variable_id = fields.Many2one('variables.comisiones', 'Variable')
    monto = fields.Float('Monto')
    nota = fields.Char('Nota')
    porcentaje_comision= fields.Float('Comision')
    comision_id = fields.Many2one('comisiones')


class Comisiones(models.Model):
    _name = 'comisiones'

    _description = 'Comisiones'


    def calcular_comision(self):
        pedidos = self.env['sale.order'].search([('type_eliterp','=','pedido_venta'),
                                                 ('consultant_sale_id','=',self.asesor_id.id)])
        total_pedidos=0.00
        for pedido in pedidos:
            if (datetime.strptime(pedido.date_created, "%Y-%m-%d")).month==(datetime.strptime(self.presupuesto.fecha_desde, "%Y-%m-%d")).month:
                total_pedidos+= pedido.amount_untaxed
        porcentaje = (total_pedidos*100)/self.presupuesto.monto
        if porcentaje>100:
            porcentaje=100
        for variable in self.lineas_variables:
            for parametro in variable.variable_id.linea_parametros:
                if porcentaje>= parametro.rango_inicial and porcentaje <= parametro.rango_final:
                    variable.write({'monto':(total_pedidos*(parametro.porcentaje/100))*(parametro.cumplimiento/100),
                                    'porcentaje_comision':parametro.porcentaje,
                                    'nota':parametro.name})

        self.total=sum(line.monto for line in self.lineas_variables)
        self.ventas_monto=total_pedidos

    @api.onchange('asesor_id','presupuesto')
    def _get_name_comision(self):
        presupuesto=""
        asesor=""
        if self.presupuesto:
            presupuesto=self.presupuesto.name
        if self.asesor_id:
            asesor=self.asesor_id.name
        self.name=asesor+"-"+presupuesto

    name = fields.Char('Nombre')
    presupuesto = fields.Many2one('presupuesto.comision', 'Periodo')
    presupuesto_monto = fields.Float('Presupuesto', related='presupuesto.monto')
    ventas_monto = fields.Float('Ventas')
    asesor_id = fields.Many2one('hr.employee', 'Asesor')
    tipo_base = fields.Selection([('facturado','Facturado'),('pagado','Pagado')], default='facturado')
    lineas_variables = fields.One2many('linea.comisiones', 'comision_id')
    total = fields.Float('Total')


class ParametrosComisiones(models.Model):

    _name='parametros.comisiones'

    _description = 'Parametros Comisiones'

    name = fields.Char('Nombre')
    porcentaje = fields.Float('Comision')
    cumplimiento = fields.Float('Cumplimiento')
    rango_inicial = fields.Float('Rango Inicial')
    rango_final = fields.Float('Rango Final')
    variable_id = fields.Many2one('variables.comisiones')



class VariablesComisiones(models.Model):

    _name = 'variables.comisiones'

    _description = 'Variables Comisiones'

    name = fields.Char('Nombre')
    linea_parametros = fields.One2many('parametros.comisiones', 'variable_id')
