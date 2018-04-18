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
from datetime import datetime, timedelta
from odoo.report import report_sxw
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ParserReportesRRHH(models.TransientModel):
    _inherit = "py3o.report"

    @api.multi
    def _extend_parser_context(self, context_instance, report_xml):
        if 'reporte_empleados' in self._context:
            reporte = self.env['reporte.empleados'].browse(self._context['active_id'])
            lines = reporte.get_lines(context_instance.localcontext)
            context_instance.localcontext.update({
                'get_lines': lines,
                'fecha_actual': fields.date.today(),
            })
        # MARZ
        if 'reporte_107' in self._context:
            reporte = self.env['reporte.107'].browse(self._context['active_id'])
            valores = reporte.get_valores(context_instance.localcontext)
            ruc = valores['data_105']
            ejercicio = str(self._context['ejercicio_fiscal'])
            fecha_actual = fields.date.today()
            fecha_filtrada = filter(lambda x: x != '-', str(fecha_actual))
            context_instance.localcontext.update({
                'data2': valores['data_201'],
                'data3': valores['data_202'],
                'data4': valores['data_301'],
                'data5': valores['data_311'],
                'data6': valores['data_313'],
                'data7': valores['data_315'],
                'data8': valores['data_351'],
                'data9': valores['data_361'],
                'data10': valores['data_363'],
                'data11': valores['data_365'],
                'data12': valores['data_367'],
                'data13': valores['data_369'],
                'data14': valores['data_399'],
                'data15': valores['data_401'],
                'data16': valores['data_405'],
                'data17': valores['data_407'],
                'data18': valores['data_349'],
                # Agente de Retención, Arreglo
                'ruc_0': ruc[0],
                'ruc_1': ruc[1],
                'ruc_2': ruc[2],
                'ruc_3': ruc[3],
                'ruc_4': ruc[4],
                'ruc_5': ruc[5],
                'ruc_6': ruc[6],
                'ruc_7': ruc[7],
                'ruc_8': ruc[8],
                'ruc_9': ruc[9],
                # Ejercicio Fiscal, Arreglo
                'ejercicio_0': ejercicio[0],
                'ejercicio_1': ejercicio[1],
                'ejercicio_2': ejercicio[2],
                'ejercicio_3': ejercicio[3],
                # Fecha de Entrega,  Arreglo
                'fecha_entrega_0': fecha_filtrada[0],
                'fecha_entrega_1': fecha_filtrada[1],
                'fecha_entrega_2': fecha_filtrada[2],
                'fecha_entrega_3': fecha_filtrada[3],
                'fecha_entrega_4': fecha_filtrada[4],
                'fecha_entrega_5': fecha_filtrada[5],
                'fecha_entrega_6': fecha_filtrada[6],
                'fecha_entrega_7': fecha_filtrada[7]
            })
        if 'reporte_ausencias' in self._context:
            reporte = self.env['reporte.ausencias'].browse(self._context['active_id'])
            lines = reporte.get_lines(context_instance.localcontext)
            context_instance.localcontext.update({
                'get_lines': lines,
                'fecha_actual': fields.date.today(),
            })
        if 'reporte_vacaciones_personal' in self._context:
            reporte = self.env['reporte.vacaciones.personal'].browse(self._context['active_id'])
            lines = reporte.get_lines(context_instance.localcontext)
            context_instance.localcontext.update({
                'get_lines': lines,
                'fecha_actual': fields.date.today(),
            })
        if 'reporte_107_consolidado' in self._context:
            reporte = self.env['reporte.107.consolidado'].browse(self._context['active_id'])
            lines = reporte.get_lines(context_instance.localcontext)
            context_instance.localcontext.update({
                'get_lines': lines,
                'ruc_empresa': self.env.user.company_id.partner_id.vat_eliterp,
            })
        res = super(ParserReportesRRHH, self)._extend_parser_context(context_instance, report_xml)
        return res


class ReporteEmpleados(models.TransientModel):
    _name = 'reporte.empleados'

    _description = 'Reporte Empleados'

    def get_estado(self, estado):
        if estado == 'invoice':
            return "Facturado"
        if estado == 'order':
            return "Emitido"
        if estado == 'done':
            return "Cerrado"

    def get_estado_civil(self, estado):
        if estado == 'single':
            return "Soltero(a)"
        if estado == 'married':
            return "Casado(a)"
        if estado == 'widower':
            return "Viudo(a)"
        if estado == 'divorced':
            return "Divorciado(a)"

    def get_lines(self, context):
        data = []
        arg = []
        arg.append(('fecha_ingreso', '>=', context['fecha_inicio']))
        arg.append(('fecha_ingreso', '<=', context['fecha_fin']))
        empleados = self.env['hr.employee'].search(arg)
        count = 0
        for empleado in empleados:
            count += 1
            data.append({
                'numero': count,
                'cedula': empleado.identification_id,
                'nombres': empleado.name,
                'state_laboral': empleado.state_laboral.upper(),
                'fecha_ingreso': empleado.fecha_ingreso,
                'fecha_salida': empleado.fecha_salida if empleado.fecha_salida else '-',
                'cargo': empleado.job_id.name,
                'departamento': empleado.department_id.name,
                'sueldo': empleado.sueldo,
                'acumula_beneficios': empleado.acumula_beneficios.upper() if empleado.acumula_beneficios else '-',
                'direccion': empleado.direccion,
                'telefono': empleado.telefono_personal if empleado.telefono_personal else '-',
                'sexo': empleado.sexo.upper() if empleado.sexo else '-',
                'fecha_nacimiento': empleado.birthday,
                'edad': '-' if not empleado.birthday else (datetime.now().date() - datetime.strptime(empleado.birthday,
                                                                                                     '%Y-%m-%d').date()).days / 365,
                'estado_civil': self.get_estado_civil(empleado.marital),
                'cargas_familiares': len(empleado.line_hijos),
                'nivel_instruccion': empleado.nivel_educacion,
                'tipo_sangre': empleado.tipo_sangre,
            })
        return data

    def imprimir_reporte_empleados_xls(self):
        reporte = []
        reporte.append(self.id)
        result = {
            'type': 'ir.actions.report.xml',
            'report_name': 'elitum_rrhh.reporte_empleados',
            'datas': {'ids': reporte},
            'context': {
                'reporte_empleados': True,
                'fecha_inicio': self.fecha_inicio,
                'fecha_fin': self.fecha_fin,
            }
        }
        return result

    def imprimir_reporte_empleados_pdf(self):
        return self.env['report'].get_action(self, 'elitum_rrhh.reporte_empleados_pdf')

    fecha_inicio = fields.Date('Fecha Inicio')
    fecha_fin = fields.Date('Fecha Fin')


# MARZ
class Reporte107(models.TransientModel):
    _name = 'reporte.107'

    _description = 'Reporte 107'

    def get_valores(self, context):
        arg = [
            ('employee_id', '=', context['empleado']),
            ('state', '=', 'done')
        ]
        empleado = self.env['hr.employee'].search([('id', '=', context['empleado'])])
        gastos = self.env['gastos.anuales.ec'].search([('empleado', '=', context['empleado'])])
        roles = self.env['hr.payslip'].search(arg)
        tabla = self.env['eliterp.tabla.impuesto.renta'].search([('status', '=', True)])
        # Variables
        data_301 = 0.00  # SUELDOS Y SALARIOS
        data_311 = 0.00  # D. TERCER SUELDO
        data_313 = 0.00  # D. CUARTO SUELDO
        data_315 = 0.00  # FONDOS DE RESERVA
        data_351 = 0.00  # APORTE PATRONAL
        data_361 = 0.00  # VIVIENDA
        data_363 = 0.00  # SALUD
        data_365 = 0.00  # EDUCACIÓN
        data_367 = 0.00  # ALIMENTACIÓN
        data_369 = 0.00  # VESTIMENTA
        data_399 = 0.00  # B.IMPONIBLE GRAVADA (TABLA)
        data_c1 = 0.00  # F. BÁSICA
        data_c2 = 0.00  # EXCESO
        data_impuesto = 0.00
        data_c3 = 0.00  # EXCEDENTE
        data_c4 = 0.00  # I. DE FRACCIÓN
        data_401 = 0.00  # I. A LA RENTA CAUSADO
        data_405 = 0.00  # I. ASUMIDO
        data_407 = 0.00  # I. RETENIDO
        data_349 = 0.00  # 301 + 303 + 305 + 381
        # Sumar Saldos Iniciales si existen
        saldo_inicial = self.env['eliterp.saldos.beneficios.sociales'].search(
            [('name', '=', empleado.id), ('status', '=', True)], limit=1)
        ejercicio = context['ejercicio_fiscal']
        if saldo_inicial:
            data_301 = saldo_inicial.wage
            for line in saldo_inicial.lines_rubro:
                if line.rubro == 'decimo_tercero' and line.fecha == ejercicio:
                    data_311 = line.valor
                if line.rubro == 'decimo_cuarto' and line.fecha == ejercicio:
                    data_313 = line.valor
                if line.rubro == 'fondos_reserva' and line.fecha == ejercicio:
                    data_315 = line.valor
        for rol in roles:
            if datetime.strptime(rol.date_to, "%Y-%m-%d").year == context['ejercicio_fiscal']:
                sueldo = rol.input_line_ids.filtered(lambda x: x.name == 'Sueldo')[0].amount
                # INGRESOS
                data_301 += sueldo
                # EGRESOS
                data_351 += rol.input_line_ids_2.filtered(lambda x: x.name == 'IESS Personal 9.45%')[0].amount
        # Comparar Gastos Totales > %50 de Total de Ingresos
        gasto_total = round(
            float(gastos.vivienda + gastos.salud + gastos.educacion + gastos.alimentacion + gastos.vestimenta), 2)
        if gasto_total > (data_301 * 0.5):
            raise UserError(_('Gastos totales de Deducibles mayor al 50% de Ingresos'))
        data_361 = gastos.vivienda
        data_363 = gastos.salud
        data_365 = gastos.educacion
        data_367 = gastos.alimentacion
        data_369 = gastos.vestimenta
        data_gastos = data_361 + data_363 + data_365 + data_367 + data_369
        data_399 = data_301 + 0.00 + 0.00 - data_351 - data_gastos
        # Cálculo con tabla
        for fila in tabla:
            # Máximo valor
            if fila.exceso_hasta == 0.00:
                data_c1 = fila.fraccion_basica
                data_impuesto = fila.impuesto_fraccion_excedente
                data_c4 = fila.impuesto_fraccion_basica
                break
            if (data_399 >= fila.fraccion_basica) and (data_399 < fila.exceso_hasta):
                data_c1 = fila.fraccion_basica
                data_impuesto = fila.impuesto_fraccion_excedente
                data_c4 = fila.impuesto_fraccion_basica
                break
        data_c2 = data_399 - data_c1
        data_c3 = (data_c2 * data_impuesto) / 100
        data_401 = data_c3 + data_c4
        data_407 = abs(data_401)
        data_349 = data_301 + 0.00 + 0.00 + 0.00
        data = {
            'data_105': '0992968168',
            'data_201': empleado.identification_id,
            'data_202': empleado.name,
            'data_301': "%.2f" % data_301,
            'data_311': "%.2f" % data_311,
            'data_313': "%.2f" % data_313,
            'data_315': "%.2f" % data_315,
            'data_351': "%.2f" % data_351,
            'data_361': "%.2f" % data_361,
            'data_363': "%.2f" % data_363,
            'data_365': "%.2f" % data_365,
            'data_367': "%.2f" % data_367,
            'data_369': "%.2f" % data_369,
            'data_399': "%.2f" % data_399,
            'data_401': "%.2f" % data_401,
            'data_405': "%.2f" % data_405,
            'data_407': "%.2f" % data_407,
            'data_349': "%.2f" % data_349
        }
        return data

    def imprimir_reporte_107(self):
        reporte = []
        reporte.append(self.id)
        result = {
            'type': 'ir.actions.report.xml',
            'report_name': 'elitum_rrhh.reporte_107',
            'datas': {
                'ids': reporte
            },
            'context': {
                'reporte_107': True,
                'empresa': self.empresa,
                'ejercicio_fiscal': self.ejercicio_fiscal,
                'empleado': self.empleado.id
            }
        }
        return result

    empleado = fields.Many2one('hr.employee')
    ejercicio_fiscal = fields.Integer()
    empresa = fields.Char()


class ReporteAusencias(models.TransientModel):
    _name = 'reporte.ausencias'

    _description = 'Reporte Ausencias'

    def get_lines(self, context):
        data = []
        arg = []
        arg.append(('state', '=', 'validate'))
        arg.append(('holiday_type', '=', 'employee'))
        arg.append(('date_from', '>=', context['fecha_inicio']))
        arg.append(('date_from', '<=', context['fecha_fin']))
        if context['filtro_ausencia'] != 'todas':
            if isinstance(context['ausencias'], int):
                arg.append(('holiday_status_id', '=', context['ausencias']))
            else:
                arg.append(('holiday_status_id', '=', context['ausencias'].id))
        if context['filtro_empleado'] != 'todos':
            if isinstance(context['empleados'], int):
                arg.append(('employee_id', '=', context['empleados']))
            else:
                arg.append(('employee_id', '=', context['empleados'].id))
        ausencias = self.env['hr.holidays'].search(arg)
        for ausencia in ausencias:
            data.append({
                'estado': ausencia.employee_id.state_laboral,
                'nombre': ausencia.employee_id.name,
                'tipo_ausencia': ausencia.name,
                'fecha_inicial': ausencia.date_from,
                'fecha_final': ausencia.date_to,
                'days': str(ausencia.number_of_days_temp),
                'comentario': ausencia.report_note
            })
        if context['filtro_empleado'] == 'todos':
            data = filter(lambda x: x['estado'] == context['state_laboral'], data)
        data = sorted(data, key=lambda x: (x['nombre'], x['fecha_inicial']))
        ausencias_todos = self.env['hr.holidays'].search([('state', '=', 'validate'),
                                                          ('date_from', '>=', context['fecha_inicio']),
                                                          ('date_from', '<=', context['fecha_fin']),
                                                          ('holiday_type', '=', 'category')])
        for ausencia in ausencias_todos:
            data.append({
                'nombre': u'NÓMINA',
                'tipo_ausencia': ausencia.name,
                'fecha_inicial': ausencia.date_from,
                'fecha_final': ausencia.date_to,
                'days': str(ausencia.number_of_days_temp),
                'comentario': ausencia.report_note
            })
        return data

    def imprimir_reporte_ausencias_xls(self):
        reporte = []
        reporte.append(self.id)
        result = {
            'type': 'ir.actions.report.xml',
            'report_name': 'elitum_rrhh.reporte_ausencias',
            'datas': {
                'ids': reporte
            },
            'context': {
                'reporte_ausencias': True,
                'fecha_inicio': self.fecha_inicio,
                'fecha_fin': self.fecha_fin,
                'filtro_ausencia': self.filtro_ausencia,
                'ausencias': self.ausencias.id if len(self.ausencias) != 0 else '-',
                'filtro_empleado': self.filtro_empleado,
                'empleados': self.empleados.id if len(self.empleados) != 0 else '-',
                'state_laboral': self.state_laboral,
            }
        }
        return result

    def imprimir_reporte_ausencias_pdf(self):
        return self.env['report'].get_action(self, 'elitum_rrhh.reporte_ausencias_pdf')

    filtro_ausencia = fields.Selection([('todas', 'Todas'), ('ausencia', 'Ausencia')], default='todas')
    ausencias = fields.Many2one('hr.holidays.status')
    filtro_empleado = fields.Selection([('todos', 'Todos'), ('empleado', 'Empleado')], default='todos')
    empleados = fields.Many2one('hr.employee')
    fecha_inicio = fields.Date('Fecha Inicio', required=True)
    fecha_fin = fields.Date('Fecha Fin', required=True)
    state_laboral = fields.Selection([('activo', 'Activo'),
                                      ('pasivo', 'Pasivo')], 'Estado', default='activo')


class ReporteVacacionesPersonal(models.TransientModel):
    _name = 'reporte.vacaciones.personal'

    _description = 'Reporte Vacaciones Personal'

    def get_vacaciones(self, empleado):
        data = []
        dias = 0
        fecha_actual = datetime.today().date()
        fecha_ingreso = datetime.strptime(empleado.fecha_ingreso, "%Y-%m-%d").date()
        anos = fecha_actual.year - fecha_ingreso.year
        if anos == 0:
            dias = int(float((datetime.combine(fecha_actual, datetime.min.time()) - datetime.combine(fecha_ingreso,
                                                                                                     datetime.min.time())).days) / float(
                24))
            data.append({
                'periodo': str(fecha_ingreso.year) + "-" + str(fecha_actual.year),
                'dias_vacaciones': dias,
                'vacaciones_tomadas': 0,
                'vacaciones_disponibles': 0,
            })
        if anos >= 1:
            if anos == 1:
                if fecha_actual < fecha_ingreso.replace(year=fecha_actual.year):
                    dias = int(float((datetime.combine(fecha_actual, datetime.min.time()) - datetime.combine(
                        fecha_ingreso, datetime.min.time())).days) / float(24))
                    data.append({
                        'periodo': str(fecha_ingreso.year) + "-" + str(fecha_actual.year),
                        'dias_vacaciones': dias,
                        'vacaciones_tomadas': 0,
                        'vacaciones_disponibles': 0,
                    })
                else:
                    dias = 15
                    data.append({
                        'periodo': str(fecha_ingreso.year) + "-" + str(fecha_actual.year),
                        'dias_vacaciones': dias,
                        'vacaciones_tomadas': 0,
                        'vacaciones_disponibles': 0,
                    })
                    dias = int(float((datetime.combine(fecha_actual, datetime.min.time()) - datetime.combine(
                        fecha_ingreso.replace(year=fecha_actual.year), datetime.min.time())).days) / float(24))
                    data.append({
                        'periodo': str(fecha_actual.year) + "-" + str(fecha_actual.year + 1),
                        'dias_vacaciones': dias,
                        'vacaciones_tomadas': 0,
                        'vacaciones_disponibles': 0,
                    })
            if anos > 1:
                for x in range(1, anos):
                    dias = 15
                    data.append({
                        'periodo': str(fecha_ingreso.year) + "-" + str(fecha_ingreso.year + x),
                        'dias_vacaciones': dias,
                        'vacaciones_tomadas': 0,
                        'vacaciones_disponibles': 0,
                    })
                if fecha_actual < fecha_ingreso.replace(year=fecha_actual.year):
                    dias = int(float((datetime.combine(fecha_actual, datetime.min.time()) - datetime.combine(
                        fecha_ingreso.replace(year=fecha_actual.year - 1), datetime.min.time())).days) / float(24))
                    data.append({'empleado': empleado.id,
                                 'periodo': str(fecha_ingreso.year + 1) + "-" + str(fecha_actual.year),
                                 'dias_vacaciones': dias,
                                 'vacaciones_tomadas': 0,
                                 'vacaciones_disponibles': 0, })
                else:
                    dias = 15
                    data.append({
                        'periodo': str(fecha_ingreso.year) + "-" + str(fecha_actual.year),
                        'dias_vacaciones': dias,
                        'vacaciones_tomadas': 0,
                        'vacaciones_disponibles': 0,
                    })
                    dias = int(float((datetime.combine(fecha_actual, datetime.min.time()) - datetime.combine(
                        fecha_ingreso.replace(year=fecha_actual.year), datetime.min.time())).days) / float(24))
                    data.append({
                        'periodo': str(fecha_actual.year) + "-" + str(fecha_actual.year + 1),
                        'dias_vacaciones': dias,
                        'vacaciones_tomadas': 0,
                        'vacaciones_disponibles': 0,
                    })
        vacaciones_tomadas = self.env['hr.holidays'].get_vacaciones_tomadas(empleado)
        for line in data:
            if vacaciones_tomadas != 0:
                if vacaciones_tomadas == line['dias_vacaciones']:
                    line.update({'vacaciones_tomadas': vacaciones_tomadas,
                                 'vacaciones_disponibles': 0})
                    vacaciones_tomadas = 0
                    continue
                if vacaciones_tomadas - line['dias_vacaciones'] > 0:
                    line.update({
                        'vacaciones_tomadas': line['dias_vacaciones'],
                        'vacaciones_disponibles': 0
                    })
                    vacaciones_tomadas = vacaciones_tomadas - line['dias_vacaciones']
                    continue
                if vacaciones_tomadas - line['dias_vacaciones'] < 0:
                    line.update({
                        'vacaciones_tomadas': vacaciones_tomadas,
                        'vacaciones_disponibles': abs(vacaciones_tomadas - line['dias_vacaciones'])
                    })
                    vacaciones_tomadas = 0
                    continue
            if vacaciones_tomadas == 0:
                line.update({
                    'vacaciones_tomadas': 0,
                    'vacaciones_disponibles': line['dias_vacaciones']
                })
        if vacaciones_tomadas != 0:
            data[-1].update(
                {'vacaciones_disponibles': data[-1].vacaciones_disponibles - vacaciones_tomadas})
        return data

    def get_lines(self, context):
        data = []
        arg = []
        if context['filtro_empleado'] == 'todos':
            arg.append(('state_laboral', '=', context['state_laboral']))
            empleados = self.env['hr.employee'].search(arg)
        else:
            if isinstance(context['empleados'], int):
                empleados = self.env['hr.employee'].search([('id', '=', context['empleados'])])
            else:
                empleados = context['empleados']
        for empleado in empleados:
            if empleado.fecha_ingreso:
                data.append({
                    'nombre': empleado.name,
                    'fecha_ingreso': empleado.fecha_ingreso,
                    'vacaciones': self.get_vacaciones(empleado)
                })
        data = sorted(data, key=lambda x: x['nombre'])
        return data

    def imprimir_reporte_vacaciones_personal_xls(self):
        reporte = []
        reporte.append(self.id)
        result = {
            'type': 'ir.actions.report.xml',
            'report_name': 'elitum_rrhh.reporte_vacaciones_personal',
            'datas': {
                'ids': reporte
            },
            'context': {
                'reporte_vacaciones_personal': True,
                'filtro_empleado': self.filtro_empleado,
                'empleados': self.empleados.id if len(self.empleados) != 0 else False,
                'state_laboral': self.state_laboral,
            }
        }
        return result

    def imprimir_reporte_vacaciones_personal_pdf(self):
        return self.env['report'].get_action(self, 'elitum_rrhh.reporte_vacaciones_personal_pdf')

    filtro_empleado = fields.Selection([('todos', 'Todos'), ('empleado', 'Empleado')], default='todos')
    empleados = fields.Many2one('hr.employee')
    state_laboral = fields.Selection([('activo', 'Activo'),
                                      ('pasivo', 'Pasivo')], 'Estado', default='activo')


class Reporte107Consolidado(models.TransientModel):
    _name = 'reporte.107.consolidado'

    _description = 'Reporte de Impuesto a la Renta'

    def get_rubro_tabla(self, data_399):
        tabla = self.env['eliterp.tabla.impuesto.renta'].search([('status', '=', True)])
        data_c1 = 0.00
        data_impuesto = 0.00
        data_c4 = 0.00
        for fila in tabla:
            if fila.exceso_hasta == 0.00:
                data_c1 = fila.fraccion_basica
                data_impuesto = fila.impuesto_fraccion_excedente
                data_c4 = fila.impuesto_fraccion_basica
                break
            if (data_399 >= fila.fraccion_basica) and (data_399 < fila.exceso_hasta):
                data_c1 = fila.fraccion_basica
                data_impuesto = fila.impuesto_fraccion_excedente
                data_c4 = fila.impuesto_fraccion_basica
                break
        return data_c1, data_impuesto, data_c4

    def get_lines(self, context):
        data = []
        gastos = self.env['gastos.anuales.ec'].search([])
        for registro in gastos:
            data_301 = 0.00  # SUELDOS Y SALARIOS
            data_311 = 0.00  # D. TERCER SUELDO
            data_313 = 0.00  # D. CUARTO SUELDO
            data_315 = 0.00  # FONDOS DE RESERVA
            data_351 = 0.00  # APORTE PATRONAL
            data_361 = 0.00  # VIVIENDA
            data_363 = 0.00  # SALUD
            data_365 = 0.00  # EDUCACIÓN
            data_367 = 0.00  # ALIMENTACIÓN
            data_369 = 0.00  # VESTIMENTA
            data_399 = 0.00  # B.IMPONIBLE GRAVADA (TABLA)
            data_c1 = 0.00  # F. BÁSICA
            data_c2 = 0.00  # EXCESO
            data_impuesto = 0.00
            data_c3 = 0.00  # EXCEDENTE
            data_c4 = 0.00  # I. DE FRACCIÓN
            data_401 = 0.00  # I. A LA RENTA CAUSADO
            data_405 = 0.00  # I. ASUMIDO
            data_407 = 0.00  # I. RETENIDO
            data_349 = 0.00  # 301 + 303 + 305 + 381
            flag = True
            data_individual = {}
            arg = [
                ('employee_id', '=', registro.empleado.id),
                ('state', '=', 'done')
            ]
            roles = self.env['hr.payslip'].search(arg)
            saldo_inicial = self.env['eliterp.saldos.beneficios.sociales'].search(
                [('name', '=', registro.empleado.id), ('status', '=', True)], limit=1)
            ejercicio = context['ejercicio_fiscal']
            if saldo_inicial:
                data_301 = saldo_inicial.wage
                for line in saldo_inicial.lines_rubro:
                    if line.rubro == 'decimo_tercero' and line.fecha == ejercicio:
                        data_311 = line.valor
                    if line.rubro == 'decimo_cuarto' and line.fecha == ejercicio:
                        data_313 = line.valor
                    if line.rubro == 'fondos_reserva' and line.fecha == ejercicio:
                        data_315 = line.valor
            for rol in roles:
                if datetime.strptime(rol.date_to, "%Y-%m-%d").year == ejercicio:
                    sueldo = rol.input_line_ids.filtered(lambda x: x.name == 'Sueldo')[0].amount
                    data_301 += sueldo
                    data_351 += rol.input_line_ids_2.filtered(lambda x: x.name == 'IESS Personal 9.45%')[0].amount
            data_361 = registro.vivienda
            data_363 = registro.salud
            data_365 = registro.educacion
            data_367 = registro.alimentacion
            data_369 = registro.vestimenta
            data_gastos = data_361 + data_363 + data_365 + data_367 + data_369
            data_399 = data_301 + 0.00 + 0.00 - data_351 - data_gastos
            if round(data_gastos, 2) > (data_301 * 0.5):
                flag = False
            data_c1, data_impuesto, data_c4 = self.get_rubro_tabla(data_399)
            data_c2 = data_399 - data_c1
            data_c3 = (data_c2 * data_impuesto) / 100
            data_401 = data_c3 + data_c4
            data_407 = abs(data_401)
            data_349 = data_301 + 0.00 + 0.00 + 0.00
            data_individual = {
                'tipo_documento': 'C',
                'documento': registro.empleado.identification_id,
                'apellidos': registro.empleado.apellidos,
                'nombres': registro.empleado.nombres,
                'establecimiento': '001',
                'tipo_residencia': '01',
                'pais': '593',
                'sueldos': "%.2f" % data_301,
                'iess': "%.2f" % data_351,
                'ingresos_gravados': "%.2f" % data_349,
                'vivienda': "%.2f" % data_361,
                'salud': "%.2f" % data_363,
                'educacion': "%.2f" % data_365,
                'alimentacion': "%.2f" % data_367,
                'vestimenta': "%.2f" % data_369,
                'base_gravada': "%.2f" % data_399,
                'impuesto_causado': "%.2f" % data_401,
                'asumido': "%.2f" % data_405,
                'retenido': "%.2f" % data_407
            }
            if flag:
                data.append(data_individual)
        return data

    def imprimir_reporte_107_consolidado(self):
        reporte = []
        reporte.append(self.id)
        result = {
            'type': 'ir.actions.report.xml',
            'report_name': 'elitum_rrhh.reporte_107_consolidado',
            'datas': {
                'ids': reporte
            },
            'context': {
                'reporte_107_consolidado': True,
                'ejercicio_fiscal': self.ejercicio_fiscal
            }
        }
        return result

    def _get_year(self):
        return datetime.today().date().year - 1

    def _get_company(self):
        return self.env.user.company_id.name

    ejercicio_fiscal = fields.Integer('Ejercicio Fiscal', default=_get_year)
    empresa = fields.Char(u'Compañía', default=_get_company)
