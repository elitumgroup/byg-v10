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
from pytz import timezone
import base64


class LineaProcesoPanelControl(models.Model):
    _name = 'linea.proceso.panel.control'

    _description = 'Linea Proceso Panel Control'

    @api.one
    def generate_file(self):
        return self.write({'excel_file': base64.encodestring(content),
                           'file_name': 'file.txt'})

    @api.multi
    def export_file(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=linea.proceso.panel.control&field=adjunto&id=%s&download=true&filename_field=adjunto_name' % (
                self.id),
            'target': 'self'}

    def busqueda_estado(self):
        fecha_actual = datetime.datetime.today().date()
        if datetime.datetime.strptime(self.fecha, "%Y-%m-%d").date() < fecha_actual:
            if not self.adjunto:
                self.write({'estado': 'vencido'})
        return

    @api.one
    def _busqueda_estado(self):
        self.busqueda_estado()
        self.flag = False

    flag = fields.Boolean(compute='_busqueda_estado', default=False)
    estado = fields.Selection([('nuevo', 'Nuevo'),
                               ('realizado', 'Realizado'),
                               ('vencido', 'Vencido')], "Estado", default='nuevo')

    novedades = fields.Char('Novedades')
    fecha = fields.Date('')
    fecha_gestion = fields.Date('')
    adjunto = fields.Binary('Adjunto')
    adjunto_name = fields.Char()
    line_panel_control_id = fields.Many2one('line.panel.control.eliterp', ondelete='cascade', string=u'Obligación')
    name_panel = fields.Char(u'Institución', related="line_panel_control_id.name", store=True)
    imagen_panel = fields.Binary(store=True, related="line_panel_control_id.imagen_institucion")
    tipo_panel = fields.Selection([('mensual', 'Mensual'),
                                   ('anual', 'Anual')], 'Frecuencia', default='mensual',
                                  related="line_panel_control_id.tipo", store=True)
    obligacion_panel = fields.Char(u'Obligación', related="line_panel_control_id.obligacion", store=True)
    departamento_panel = fields.Many2one('hr.department', "Departamento", related="line_panel_control_id.departamento",
                                         store=True)


class LinePanelControlEliterp(models.Model):
    _name = 'line.panel.control.eliterp'

    _description = 'Linea Panel de Control'

    @api.one
    def generate_file(self):
        content = ''
        return self.write({'imagen_institucion': base64.encodestring(content),
                           'name_imagen': 'file.txt'})

    def _get_mes(self, mes):
        if mes == 1:
            return "Enero"
        if mes == 2:
            return "Febrero"
        if mes == 3:
            return "Marzo"
        if mes == 4:
            return "Abril"
        if mes == 5:
            return "Mayo"
        if mes == 6:
            return "Junio"
        if mes == 7:
            return "Julio"
        if mes == 8:
            return "Agosto"
        if mes == 9:
            return "Septiembre"
        if mes == 10:
            return "Octubre"
        if mes == 11:
            return "Noviembre"
        if mes == 12:
            return "Diciembre"

    def cargar_meses(self):
        list_lines = []
        if not self.ano_frecuencia:
            raise Warning("Debe ingresar el Año Contable")
        if self.ano_frecuencia < 1990 and self.ano_frecuencia > 3000:
            raise Warning("Ingreso un Año Válido")
        fecha = datetime.date.today()
        if self.tipo == 'mensual':
            fecha = fecha.replace(year=self.ano_frecuencia)
            fecha = fecha.replace(day=self.fecha_gerencia)
            for x in range(1, 13):
                # MARZ
                if x == 12:
                    fecha = fecha.replace(year=self.ano_frecuencia + 1)
                    fecha = fecha.replace(month=1)
                    list_lines.append([0, 0, {'code': x,
                                              'fecha': fecha,
                                              'estado': 'nuevo'}])
                else:
                    fecha = fecha.replace(month=(x + 1))
                    list_lines.append([0, 0, {'code': x,
                                          'fecha': fecha,
                                          'estado': 'nuevo'}])

        else:
            if not self.mes_frecuencia:
                raise Warning("Debe ingresar el Mes de Frecuencia")
            if self.mes_frecuencia < 1 and self.mes_frecuencia > 12:
                raise Warning("Ingreso un Mes Válido del 1 (Enero) al 12 (Diciembre)")
            fecha = fecha.replace(year=self.ano_frecuencia)
            fecha = fecha.replace(month=self.mes_frecuencia)
            fecha = fecha.replace(day=self.fecha_gerencia)
            list_lines.append([0, 0, {'code': self.mes_frecuencia,
                                      'fecha': fecha,
                                      'estado': 'nuevo'}])

        return self.update({'line_proceso': list_lines, 'tipo': self.tipo})

    @api.depends('tipo')
    def _get_months(self):
        result = False
        if self.tipo == 'mensual':
            if len(self.line_proceso) == 12:
                result = True
        else:
            if len(self.line_proceso) == 1:
                result = True
        self.count_month = result

    name = fields.Char(u'Institución', required=True)
    imagen_institucion = fields.Binary(u'Imagen de Institución')
    tipo = fields.Selection([('mensual', 'Mensual'), ('anual', 'Anual')], 'Frecuencia', default='mensual')
    ano_frecuencia = fields.Integer(u'Año Contable', help="Ingrese el Año (Ej. 2017")
    mes_frecuencia = fields.Integer('Mes', help="Ingrese el Mes (Ej. 1 [Enero]")
    mes = fields.Many2one('lines.account.period', 'Mes')
    fecha_gerencia = fields.Integer('Fecha de Gerencia', )
    fecha_institucion = fields.Integer(u'Fecha de Institución')
    obligacion = fields.Char(u'Obligación', required=True)
    documento = fields.Char('Documento')
    responsable = fields.Many2one('hr.employee', 'Responsable', required=True)
    departamento = fields.Many2one('hr.department', "Departamento", related="responsable.department_id", store=True)
    line_proceso = fields.One2many('linea.proceso.panel.control', 'line_panel_control_id', string=u'Líneas de Proceso')
    panel_control_id = fields.Many2one('panel.control.eliterp')
    count_month = fields.Boolean(compute='_get_months', default=False) # MARZ


class PanelControlEliterp(models.Model):
    _name = 'panel.control.eliterp'

    _description = 'Panel de Control'

    @api.onchange('responsable')
    def onchange_responsable(self):
        if len(self.responsable) == 0:
            return ""
        self.name = 'Panel de Control' + '-' + self.responsable.department_id.name

    name = fields.Char()
    responsable = fields.Many2one('hr.employee', 'Responsable')
    line_panel_control_ids = fields.One2many('line.panel.control.eliterp', 'panel_control_id', u'Líneas de Panel')
