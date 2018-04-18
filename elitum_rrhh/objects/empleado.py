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

from odoo import api, fields, models, _
from datetime import datetime


class hr_employee_documentos_line(models.Model):
    _name = 'hr.employee.documentos.line'

    _description = 'Linea de Documento'

    name = fields.Char('Documento')
    adjunto = fields.Binary('Adjunto')
    hr_employee_documentos_id = fields.Many2one('hr.employee.documentos')


class hr_employee_documentos(models.Model):
    _name = 'hr.employee.documentos'

    _description = 'Documentos'

    def _get_lines_documentos(self, tipo):
        res = []
        if tipo == 1:
            lista_documentos = ['Acuerdo de Confidencialidad',
                                'Aviso de Entrada IESS',
                                'Contrato de Trabajo',
                                'Hoja de Vida',
                                ]
        if tipo == 2:
            lista_documentos = ['Copia de certificados de cursos, seminarios, talleres',
                                'Copia de título o acta de grado',
                                'Copia de título o prefesional registrado en Senescyt',
                                ]
        if tipo == 3:
            lista_documentos = ['Copia a color Cédula de identidad',
                                'Copia a color Certificado de Votación',
                                'Fotografía tamaño carnet a color',
                                ]
        if tipo == 4:
            lista_documentos = ['Copia acta de matrimonio ò declaración juramentada unión libre',
                                'Copia de cédula de cargas familiares',
                                ]
        if tipo == 5:
            lista_documentos = ['Certificado de salud del MSP',
                                'Certificado de trabajo con números de contacto',
                                'Copia de planilla de servicios básicos',
                                'Referencias personales con números de contacto',
                                ]

        if tipo == 6:
            lista_documentos = ['Aviso de Salida IESS',
                                'Acta de Finiquito',
                                ]

        list_lines = []
        for line in lista_documentos:
            list_lines.append([0, 0, {'name': line, }])
        return list_lines

    def _get_lines_ingreso(self):
        res = self._get_lines_documentos(1)
        return res

    def _get_lines_academica(self):
        res = self._get_lines_documentos(2)
        return res

    def _get_lines_personales(self):
        res = self._get_lines_documentos(3)
        return res

    def _get_lines_familiares(self):
        res = self._get_lines_documentos(4)
        return res

    def _get_lines_otros(self):
        res = self._get_lines_documentos(5)
        return res

    def _get_lines_salida(self):
        res = self._get_lines_documentos(6)
        return res

    name = fields.Char('Documentos')
    line_documentos_ingreso = fields.One2many('hr.employee.documentos.line', 'hr_employee_documentos_id', 'Ingreso',
                                              default=_get_lines_ingreso)
    line_documentos_formacion_academica = fields.One2many('hr.employee.documentos.line', 'hr_employee_documentos_id',
                                                          u'Formación Académica', default=_get_lines_academica)
    line_documentos_documentos_personales = fields.One2many('hr.employee.documentos.line', 'hr_employee_documentos_id',
                                                            'Documentos Personales', default=_get_lines_personales)
    line_documentos_cargas_familiares = fields.One2many('hr.employee.documentos.line', 'hr_employee_documentos_id',
                                                        'Cargas Familiares', default=_get_lines_familiares)
    line_documentos_otros = fields.One2many('hr.employee.documentos.line', 'hr_employee_documentos_id', 'Otros',
                                            default=_get_lines_otros)
    line_documentos_salida = fields.One2many('hr.employee.documentos.line', 'hr_employee_documentos_id', 'Salida',
                                             default=_get_lines_salida)
    hr_employee_id = fields.Many2one('hr.employee', 'Empleado')


class hr_employee_codigo_sectorial(models.Model):
    _name = 'hr.employee.codigo.sectorial'

    _description = 'Codigo Sectorial'

    name = fields.Char('Codigo')


class hr_employee_discapacidad_grado(models.Model):
    _name = 'hr.employee.discapacidad.grado'

    _description = 'Grado de Discapacidad'

    name = fields.Char('Grado')
    discapacidad_id = fields.Many2one('hr.employee.discapacidad')


class hr_employee_discapacidad_tipo(models.Model):
    _name = 'hr.employee.discapacidad.tipo'

    _description = 'Tipo de Discapacidad'

    name = fields.Char('Tipo')
    discapacidad_id = fields.Many2one('hr.employee.discapacidad')


class hr_employee_discapacidad(models.Model):
    _name = 'hr.employee.discapacidad'

    _description = 'Discapacidad'

    Discapacidad = fields.Char('Discapacidad')
    discapacidad_grado = fields.One2many('hr.employee.discapacidad.tipo', 'discapacidad_id')
    discapacidad_tipo = fields.One2many('hr.employee.discapacidad.grado', 'discapacidad_id')


class hr_employee_hijos(models.Model):
    _name = 'hr.employee.hijos'

    _description = 'Hijos de Empleados'

    def get_edad_hijos(self):
        res = {}
        for hijo in self:
            if (hijo.fecha_nacimiento):
                edad = (datetime.now().date() - datetime.strptime(hijo.fecha_nacimiento, '%Y-%m-%d').date()).days / 365
            else:
                edad = 0
            hijo.update({'edad': edad})

    name = fields.Char('Nombres')
    identificacion = fields.Char('Identificacion')
    fecha_nacimiento = fields.Date('Fecha de Nacimiento')
    edad = fields.Integer('Edad', readonly=True, compute='get_edad_hijos')
    employee_id = fields.Many2one('hr.employee')


class hr_employee_uniformes(models.Model):
    _name = 'hr.employee.uniformes'

    _description = 'Uniformes de Empleados'

    name = fields.Char('Articulo')
    talla = fields.Char('Talla')
    cantidad = fields.Integer('Cantidad')
    employee_id = fields.Many2one('hr.employee')


class HrEmployeeTipoNotas(models.Model):
    _name = 'hr.employee.tipo.notas'

    _description = 'Tipo de Notas'

    name = fields.Char('Tipo de Notas')


class HrEmployeeHistorialNotas(models.Model):
    _name = 'hr.employee.historial.notas'

    _description = 'Historial de Notas'

    name = fields.Many2one('hr.employee.tipo.notas', 'Tipo de Notas')
    fecha = fields.Date('Fecha Registro')
    comentarios = fields.Text('Comentario')
    fecha_vigencia = fields.Date('Fecha Vigencia')
    employee_id = fields.Many2one('hr.employee', 'Empleado')


class FiniquitoReasonWizard(models.TransientModel):
    _name = 'finiquito.reason.wizard'

    _description = 'Wizard Finiquito'

    def create_finiquito(self):
        empleado = self.env['hr.employee'].browse(self._context['active_id'])
        empleado.write({'state_laboral': 'pasivo', 'fecha_salida': self.fecha_salida})
        contrato = self.env['hr.contract'].search([('employee_id', '=', empleado.id)])[0]
        contrato.write({'state_eliterp': 'pasivo', 'fecha_salida': self.fecha_salida})
        finiquito = self.env['finiquito'].create({'empleado': empleado.id,
                                                  'cargo': empleado.job_id.id,
                                                  'motivo_salida': self.motivo,
                                                  'fecha_ingreso': empleado.fecha_ingreso,
                                                  'fecha_salida': self.fecha_salida,
                                                  'ultimo_sueldo': empleado.sueldo})

        finiquito.cargar_valores()
        finiquito._compute_liquidacion()
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('elitum_rrhh.eliterp_action_finiquito')
        form_view_id = imd.xmlid_to_res_id('elitum_rrhh.eliterp_finiquito_form_view')
        empleado.write({'finiquito_id': finiquito.id, 'have_finiquito': True})
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'res_id': finiquito.id,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        return result

    motivo = fields.Char('Motivo')
    fecha_salida = fields.Date('Fecha Salida')

class ResourceResource(models.Model):
    _inherit = 'resource.resource'

class hr_employee(models.Model):
    _inherit = 'hr.employee'

    def action_view_finiquito(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('elitum_rrhh.eliterp_action_finiquito')
        form_view_id = imd.xmlid_to_res_id('elitum_rrhh.eliterp_finiquito_form_view')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'res_id': self.finiquito_id.id,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        return result

    @api.onchange('birthday')
    def _onchange_birthday(self):
        if self.birthday:
            edad = (datetime.now().date() - datetime.strptime(self.birthday, '%Y-%m-%d').date()).days / 365
            self.edad = edad

    @api.onchange('user_id')
    def _onchange_user(self):
        dump = False

    def get_edad_empleado(self):
        res = {}
        for empleado in self:
            if (empleado.birthday):
                edad = (datetime.now().date() - datetime.strptime(empleado.birthday, '%Y-%m-%d').date()).days / 365
            else:
                edad = 0
            empleado.edad = edad

    @api.one
    def _get_tiempo_laboral(self):
        if not self.fecha_ingreso:
            self.tiempo_laboral = False
        else:
            # MARZ (Estaba con años, forma incorrecta)
            fecha_inicio = datetime.strptime(self.fecha_ingreso, '%Y-%m-%d').date()
            fecha_fin = datetime.today().date()
            tiempo = abs(fecha_fin - fecha_inicio).days
            if tiempo > 365:
                self.tiempo_laboral = True

    def action_finiquito(self):
        context = dict(self._context or {})
        return {
            'name': "Explique la Razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'finiquito.reason.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

    def action_view_documentos(self):
        documentos_id = self.env['hr.employee.documentos'].search([('hr_employee_id', '=', self[0].id)])
        res = {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.documentos',
            'view_mode': 'form',
            'view_type': 'form',
        }
        if documentos_id:
            res['res_id'] = documentos_id[0]
            res['context'] = "{}"
        else:
            res['context'] = "{'default_hr_employee_id': " + str(self[0].id) + "}"

        return res

    @api.onchange('nombres', 'apellidos')
    def _onchange_apellidos(self):
        value = {}
        if self.nombres and self.apellidos:
            value['name'] = self.apellidos + ' ' + self.nombres
            return {'value': value}

    # MARZ
    @api.depends('state_laboral')
    @api.onchange('fecha_salida')
    def onchange_fecha_salida(self):
        if self.fecha_salida:
            return self.update({'state_laboral': 'pasivo'})
        else:
            return self.update({'state_laboral': 'activo'})

    historial_notas = fields.One2many('hr.employee.historial.notas', 'employee_id', 'Tipo de Notas')
    nombres = fields.Char('Nombres', required=True)
    apellidos = fields.Char('Apellidos', required=True)
    tiene_dispacidad = fields.Boolean('Tiene Discapacidad?')
    discapacidad_id = fields.Many2one('hr.employee.discapacidad', 'Discapacidad')
    discapacidad_grado = fields.Integer('Grado', size=3)
    discapacidad_tipo = fields.Char('Tipo')
    nivel_educacion = fields.Selection([('basico', u'Educación Basica'),
                                        ('bachiller', 'Bachiller'),
                                        ('tercer', 'Tercer Nivel'),
                                        ('postgrado', 'Postgrado')], u'Nivel de Educación')
    tipo_sangre = fields.Selection([('a_mas', 'A+'),
                                    ('a_menos', 'A-'),
                                    ('b_mas', 'B+'),
                                    ('b_menos', 'B-'),
                                    ('ab_mas', 'AB+'),
                                    ('ab_menos', 'AB-'),
                                    ('o_mas', 'O+'),
                                    ('o_menos', 'O-')], u'Tipo de Sangre')
    state_laboral = fields.Selection([('activo', 'Activo'),
                                      ('pasivo', 'Pasivo')], 'Estado', default='activo')
    fecha_ingreso = fields.Date('Fecha de Ingreso', required=True)
    sueldo = fields.Float('Sueldo', required=True)
    codigo_sectorial_id = fields.Many2one('hr.employee.codigo.sectorial', u'Código Sectorial')
    correo = fields.Char('Correo')
    extension = fields.Char('Extension')
    edad = fields.Integer('Edad', compute='get_edad_empleado')
    direccion = fields.Char(u'Dirección de Domicilio')
    telefono_personal = fields.Char(u'Teléfono Personal')
    conyugue = fields.Char(u'Cónyugue')
    identificacion_conyugue = fields.Char(u'Identificación')
    if_hijos = fields.Boolean('Tiene Hijos?')
    line_hijos = fields.One2many('hr.employee.hijos', 'employee_id', 'Hijos')
    nombre_contacto1 = fields.Char('Contacto')
    parentesco_contacto1 = fields.Char('Parentesco')
    telefono_contacto1 = fields.Char('Telefono')
    nombre_contacto2 = fields.Char('Contacto')
    parentesco_contacto2 = fields.Char('Parentesco')
    telefono_contacto2 = fields.Char('Telefono')
    type_bank_account = fields.Selection([('saving', 'Ahorro'), ('current', 'Corriente')], u'Tipo de Cuenta')
    number_bank = fields.Char('No. Cuenta')
    bank_id = fields.Many2one('res.bank', 'Banco')
    if_uniforme = fields.Boolean('Uniforme?')
    line_uniformes = fields.One2many('hr.employee.uniformes', 'employee_id', 'Uniformes')
    if_tarjeta_comisariato = fields.Boolean('Tarjeta Comisariato?')
    tarjeta_comisariato_cupo = fields.Float('Cupo')
    if_movil = fields.Boolean('Movil?')
    movil_operadora = fields.Selection(
        [('cnt', 'CNT'), ('movistar', 'MOVISTAR'), ('claro', 'CLARO'), ('tuenti', 'TUENTI')], 'Operadora')
    movil_plan = fields.Float('Plan')
    movil_monto_subsidio = fields.Float('Monto Subsidio')
    payroll_structure_id = fields.Many2one('hr.payroll.structure', 'Estructura Salarial', required=True)
    journal_id = fields.Many2one('account.journal', 'Diario Contable')
    no_carnet = fields.Char('No. Carnet')
    account_employee = fields.Many2one('account.account', string="Cuenta Nómina",
                                       domain=[('tipo_contable', '=', 'movimiento')])
    account_advance_payment = fields.Many2one('account.account', string="Cuenta Anticipo",
                                              domain=[('tipo_contable', '=', 'movimiento')])
    analytic_account_id = fields.Many2one('account.analytic.account', 'Centro de Costos')
    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    numero_ausencias = fields.Integer('Ausencias', default=0)
    fecha_salida = fields.Date('Fecha de Salida')
    sexo = fields.Selection([('hombre', 'Hombre'), ('mujer', 'Mujer')], required=True)
    acumula_beneficios = fields.Selection(
        [('si', 'Si'), ('no', 'No'), ('ninguna', 'Ninguna')], required=True, help="Para casos especiales seleccionar 'Ninguna'"
    )
    have_finiquito = fields.Boolean('Tiene Finiquito?', default=False)
    finiquito_id = fields.Many2one('finiquito')
    tiempo_laboral = fields.Boolean(compute='_get_tiempo_laboral')
    regla_fondo_reserva = fields.Boolean('Regla de Fondos de Reserva',
                                         default=False, help='Habilitar cuando el empleado tiene varios contratos') # MARZ (Casos especiales antiguos contratos)


class Holidays(models.Model):
    _inherit = 'hr.holidays'

    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
    ], string='Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
        help="The status is set to 'To Submit', when a holiday request is created." +
             "\nThe status is 'To Approve', when holiday request is confirmed by user." +
             "\nThe status is 'Refused', when holiday request is refused by manager." +
             "\nThe status is 'Approved', when holiday request is approved by manager.")


# MARZ
class GastosDeduciblesEmpleado(models.Model):
    _name = 'eliterp.tabla.gastos.deducibles'

    _description = 'Tabla Gastos Deducibles Empleado'

    name = fields.Char('Nombre', required=True)
    valor = fields.Float('Valor', required=True)
    status = fields.Boolean('Activo?', default=True)
