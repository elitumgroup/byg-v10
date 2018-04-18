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

from collections import defaultdict
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from itertools import ifilter
import math


class LineaReporteFlujoCajaIngresos(models.Model):
    _name = 'linea.reporte.flujo.caja.ingresos'

    _description = "Linea Reporte Flujo de Caja Ingresos"

    rubro = fields.Many2one('account.config.reporte.flujo.caja', 'Rubro')
    enero = fields.Float('Enero')
    febrero = fields.Float('Febrero')
    marzo = fields.Float('Marzo')
    abril = fields.Float('Abril')
    mayo = fields.Float('Mayo')
    junio = fields.Float('Junio')
    julio = fields.Float('Julio')
    agosto = fields.Float('Agosto')
    septiembre = fields.Float('Septiembre')
    octubre = fields.Float('Octubre')
    noviembre = fields.Float('Noviembre')
    diciembre = fields.Float('Diciembre')
    total_elementos = fields.Float('Total')
    reporte_flujo_caja_id = fields.Many2one('account.reporte.flujo.caja')


class TotalFlujoCajaEgresos(models.Model):
    _name = 'total.flujo.caja.egresos'

    _description = "Total Flujo de Caja Egresos"

    name = fields.Char('Totales')
    enero = fields.Float('Enero')
    febrero = fields.Float('Febrero')
    marzo = fields.Float('Marzo')
    abril = fields.Float('Abril')
    mayo = fields.Float('Mayo')
    junio = fields.Float('Junio')
    julio = fields.Float('Julio')
    agosto = fields.Float('Agosto')
    septiembre = fields.Float('Septiembre')
    octubre = fields.Float('Octubre')
    noviembre = fields.Float('Noviembre')
    diciembre = fields.Float('Diciembre')
    total_elementos = fields.Float('Total')
    reporte_flujo_caja_id = fields.Many2one('account.reporte.flujo.caja')


class TotalFlujoCajaIngresos(models.Model):
    _name = 'total.flujo.caja.ingresos'

    _description = "Total Flujo de Caja Ingresos"

    name = fields.Char('Totales')
    enero = fields.Float('Enero')
    febrero = fields.Float('Febrero')
    marzo = fields.Float('Marzo')
    abril = fields.Float('Abril')
    mayo = fields.Float('Mayo')
    junio = fields.Float('Junio')
    julio = fields.Float('Julio')
    agosto = fields.Float('Agosto')
    septiembre = fields.Float('Septiembre')
    octubre = fields.Float('Octubre')
    noviembre = fields.Float('Noviembre')
    diciembre = fields.Float('Diciembre')
    total_elementos = fields.Float('Total')
    reporte_flujo_caja_id = fields.Many2one('account.reporte.flujo.caja')


class LineaReporteFlujoCajaEgresos(models.Model):
    _name = 'linea.reporte.flujo.caja.egresos'

    _description = "Linea Reporte Flujo de Caja Egresos"

    rubro = fields.Many2one('account.config.reporte.flujo.caja', 'Rubro')
    enero = fields.Float('Enero')
    febrero = fields.Float('Febrero')
    marzo = fields.Float('Marzo')
    abril = fields.Float('Abril')
    mayo = fields.Float('Mayo')
    junio = fields.Float('Junio')
    julio = fields.Float('Julio')
    agosto = fields.Float('Agosto')
    septiembre = fields.Float('Septiembre')
    octubre = fields.Float('Octubre')
    noviembre = fields.Float('Noviembre')
    diciembre = fields.Float('Diciembre')
    total_elementos = fields.Float('Total')
    reporte_flujo_caja_id = fields.Many2one('account.reporte.flujo.caja')


class AccountReporteFlujoCaja(models.Model):
    _name = 'account.reporte.flujo.caja'

    _description = "Reporte Flujo de Caja"

    def open_reporte(self):
        return self.write({'state': 'open'})

    name = fields.Char('Periodo')
    linea_ingresos = fields.One2many('linea.reporte.flujo.caja.ingresos', 'reporte_flujo_caja_id', 'Ingresos')
    linea_egresos = fields.One2many('linea.reporte.flujo.caja.egresos', 'reporte_flujo_caja_id', 'Egresos')
    linea_totales_ingresos = fields.One2many('total.flujo.caja.ingresos', 'reporte_flujo_caja_id', 'Total Ingresos')
    linea_totales_egresos = fields.One2many('total.flujo.caja.egresos', 'reporte_flujo_caja_id', 'Total Ingresos')
    state = fields.Selection([('draft', 'Borrador'), ('open', 'Iniciado'), ('closed', 'Cerrado')], default='draft')


class LineasAccountFlujoCaja(models.Model):
    _name = 'lines.account.flujo.caja'

    _description = 'Lineas Cuentas Flujo caja'

    account_id = fields.Many2one('account.account', 'Cuenta', domain=[('tipo_contable', '=', 'movimiento')])
    reporte_flujo_caja_id = fields.Many2one('account.config.reporte.flujo.caja')


class AccountConfigReporteFlujoCaja(models.Model):
    _name = 'account.config.reporte.flujo.caja'

    _description = "Config. Reporte Flujo de Caja"

    @api.model
    def create(self, vals):
        res = super(AccountConfigReporteFlujoCaja, self).create(vals)
        if res.tipo == 'ingreso':
            self.env['linea.reporte.flujo.caja.ingresos'].create({'reporte_flujo_caja_id': res.flujo_caja_id.id,
                                                                  'rubro': res.id,
                                                                  'enero': res.valor_mensualizado,
                                                                  'febrero': res.valor_mensualizado,
                                                                  'marzo': res.valor_mensualizado,
                                                                  'abril': res.valor_mensualizado,
                                                                  'mayo': res.valor_mensualizado,
                                                                  'junio': res.valor_mensualizado,
                                                                  'julio': res.valor_mensualizado,
                                                                  'agosto': res.valor_mensualizado,
                                                                  'septiembre': res.valor_mensualizado,
                                                                  'octubre': res.valor_mensualizado,
                                                                  'noviembre': res.valor_mensualizado,
                                                                  'diciembre': res.valor_mensualizado,
                                                                  })
        if res.tipo == 'egreso':
            self.env['linea.reporte.flujo.caja.egresos'].create({'reporte_flujo_caja_id': res.flujo_caja_id.id,
                                                                 'rubro': res.id,
                                                                 'enero': res.valor_mensualizado,
                                                                 'febrero': res.valor_mensualizado,
                                                                 'marzo': res.valor_mensualizado,
                                                                 'abril': res.valor_mensualizado,
                                                                 'mayo': res.valor_mensualizado,
                                                                 'junio': res.valor_mensualizado,
                                                                 'julio': res.valor_mensualizado,
                                                                 'agosto': res.valor_mensualizado,
                                                                 'septiembre': res.valor_mensualizado,
                                                                 'octubre': res.valor_mensualizado,
                                                                 'noviembre': res.valor_mensualizado,
                                                                 'diciembre': res.valor_mensualizado,
                                                                 })

        return res

    name = fields.Char('Nombre')
    lines_account_ids = fields.One2many('lines.account.flujo.caja', 'reporte_flujo_caja_id', 'Cuentas')
    valor_mensualizado = fields.Float('Valor Mensualizado')
    flujo_caja_id = fields.Many2one('account.reporte.flujo.caja', 'Flujo de Caja')
    tipo = fields.Selection([('ingreso', 'Ingreso'), ('egreso', 'Egreso')])


class AccountReportesFinancieros(models.TransientModel):
    _name = 'account.reportes.financieros'

    _description = "Reporte Estado de Situacion Financiera"

    def imprimir_reporte_estado_situacion_financiero(self):
        return self.env['report'].get_action(self, 'elitum_contabilidad.reporte_estado_financiero')

    tipo_proyecto = fields.Selection([('all', 'Todos'), ('one', 'Individual')], default='all', string="Tipo de Proyecto")
    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    tipo_centro_costo = fields.Selection([('all', 'Todos'), ('one', 'Individual')], default='all', string="Tipo de Centro de Costo")
    analytic_account_id = fields.Many2one('account.analytic.account', 'Centro de Costos')
    fecha_inicio = fields.Date('Fecha Inicio', required=True)
    fecha_fin = fields.Date('Fecha Fin', required=True)


class AccountReporteLibroMayor(models.TransientModel):
    _name = 'account.reporte.libro.mayor'

    _description = "Reporte Libro Mayor"

    def imprimir_reporte_libro_mayor(self):
        return self.env['report'].get_action(self, 'elitum_contabilidad.reporte_libro_mayor')

    tipo_reporte = fields.Selection([('all', 'Todas'), ('one', 'Individual')], default='all')
    cuenta = fields.Many2one('account.account', 'Cuenta', domain=[('tipo_contable', '=', 'movimiento')])
    fecha_inicio = fields.Date('Fecha Inicio', required=True)
    fecha_fin = fields.Date('Fecha Fin', required=True)


class AccountReporteEstadoResultado(models.TransientModel):
    _name = 'account.reporte.estado.resultado'

    _description = "Reporte Estado Resultado"

    def imprimir_reporte_estado_resultado(self):
        return self.env['report'].get_action(self, 'elitum_contabilidad.reporte_estado_resultado')

    tipo_proyecto = fields.Selection([('all', 'Todos'), ('one', 'Individual')], default='all',
                                     string="Tipo de Proyecto")
    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    tipo_centro_costo = fields.Selection([('all', 'Todos'), ('one', 'Individual')], default='all',
                                         string="Tipo de Centro de Costo")
    analytic_account_id = fields.Many2one('account.analytic.account', 'Centro de Costos')
    fecha_inicio = fields.Date('Fecha Inicio', required=True)
    fecha_fin = fields.Date('Fecha Fin', required=True)
