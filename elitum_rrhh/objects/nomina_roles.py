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


class GastosAnualesEc(models.Model):
    _name = 'gastos.anuales.ec'

    _description = 'Gastos Anuales'

    # MARZ
    @api.multi
    def name_get(self):
        res = []
        for data in self:
            res.append((data.id, "Gastos de %s" % (data.empleado.name)))
        return res

    @api.multi
    def imprimir_reporte_107(self):
        company = self.env.user.company_id.name
        context = {
            'default_empleado': self.empleado.id,
            'default_ejercicio_fiscal': datetime.today().date().year - 1,
            'default_empresa': company
        }
        return {
            'name': "Retenciones en la Fuente del Impuesto a la Renta",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'reporte.107',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

    @api.onchange('empleado')
    def onchange_empleado(self):
        if self.empleado:
            sueldo = self.env['hr.contract'].search([('employee_id', '=', self.empleado.id)])[0].wage
            self.sueldo_mensual = sueldo
            self.sueldo_anual = sueldo * 12

    def validation_rubros(self, vals):
        tabla = self.env['eliterp.tabla.gastos.deducibles'].search([('status', '=', 'True')])
        validation = True
        nombre = ''
        for registro in tabla:
            nombre = registro.name
            if nombre == 'Salud' and 'salud' in vals:
                if vals['salud'] > registro.valor:
                    validation = False
                    break
            if nombre == 'Vestimenta' and 'vestimenta' in vals:
                if vals['vestimenta'] > registro.valor:
                    validation = False
                    break
            if nombre == u'Alimentación' and 'alimentacion' in vals:
                if vals['alimentacion'] > registro.valor:
                    validation = False
                    break
            if nombre == 'Vivienda' and 'vivienda' in vals:
                if vals['vivienda'] > registro.valor:
                    validation = False
                    break
            if nombre == u'Educación' and 'educacion' in vals:
                if vals['educacion'] > registro.valor:
                    validation = False
                    break
        if not validation:
            raise UserError(_('Monto mayor al configurado para gastos de %s') % nombre)
        return True

    @api.model
    def create(self, vals):
        '''Sobreescribimos Método (CREATE) del modelo'''
        self.validation_rubros(vals)
        res = super(GastosAnualesEc, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        '''Sobreescribimos Método (PUT) del modelo'''
        self.validation_rubros(vals)
        res = super(GastosAnualesEc, self).write(vals)
        return res

    empleado = fields.Many2one('hr.employee', required=True)
    sueldo_mensual = fields.Float()
    salud = fields.Float()
    vestimenta = fields.Float()
    alimentacion = fields.Float()
    vivienda = fields.Float()
    educacion = fields.Float()
    sueldo_anual = fields.Float()

    _sql_constraints = [
        ('empleado_gastos_uniq', 'unique (empleado)', "Soló se puede crear un registro por Empleado")]


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    type_structure = fields.Selection([('acumulado', 'Acumulado'), ('mensualizado', 'Mensualizado')])


class hrPayslipRunLine(models.Model):
    _name = 'hr.payslip.run.line'

    _description = u'Modelo - Líneas de Rol'

    name = fields.Char('Nombre')
    departamento = fields.Char('Departamento')
    fecha_ingreso = fields.Date('Fecha Ingreso')
    dias_trabajados = fields.Integer(u'Días Trabajados')
    sueldo = fields.Float('Sueldo')
    he_extra = fields.Float('HE 100%')
    he_suple = fields.Float('HE 50%')
    fondos_reserva = fields.Float('Fondos Reserva')
    decimo_tercero = fields.Float(u'Décimo Tercero')
    decimo_cuarto = fields.Float(u'Décimo Cuarto')
    otros_ingresos = fields.Float('Otros Ingresos')
    total_ingresos = fields.Float('Total Ingresos')
    anticipo_quincena = fields.Float('Anticipo Quincena')
    iess_personal = fields.Float('IESS 9.45%')
    # MARZ
    iess_patronal = fields.Float('IESS 17.60%')  # Nuevo 25-01-2018
    prestamo_anticipo_quincena = fields.Float(u'Préstamo Anticipo Sueldo')
    prestamo_quirografario = fields.Float(u'Préstamo Quirografario')
    prestamo_hipotecario = fields.Float(u'Préstamo Hipotecario')
    multas = fields.Float('Multas')
    faltas_atrasos = fields.Float('Faltas y Atrasos')
    plan_celular = fields.Float('Plan Celular')
    otros_egresos = fields.Float('Otros Egresos')
    total_egresos = fields.Float('Total Egresos')
    neto_recibir = fields.Float('Neto a Recibir')
    rol_id = fields.Many2one('hr.payslip', 'Rol de')
    payslip_run_id = fields.Many2one('hr.payslip.run', u'Período')


# MARZ
class HrPayslipRunCancelReason(models.Model):
    _name = 'eliterp.nomina.cancel.reason'

    _description = u'Modelo - Razón para Negar Rol Consolidado'

    hr_payslip_run_id = fields.Many2one('hr.payslip.run', required=True)
    description = fields.Text(u'Descripción', required=True)

    def nomina_cancel(self):
        nomina_id = self.env['hr.payslip.run'].browse(self._context['active_id'])
        nomina_id.update({
            'state': 'canceled'
        })
        for rol in nomina_id.input_line_hr_run:
            rol.rol_id.write({'state': 'cancel'})
        return nomina_id


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    @api.model
    def _default_journal(self):
        '''Diario de Nómina'''
        return self.env['account.journal'].search([('name', '=', 'Nomina')])[0].id

    @api.multi
    def for_approval_nomina(self):
        '''Solicitar Aprobación'''
        if len(self.input_line_hr_run) == 0:
            raise except_orm("Error", "No hay Roles en el Nómina")
        self.update({'state': 'for_approval'})

    @api.multi
    def approved_nomina(self):
        '''Aprobar'''
        for rol in self.input_line_hr_run:
            rol.rol_id.write({'state': 'done',
                              'usuario_aprobacion': self._uid})
        self.update({'state': 'approved',
                     'usuario_aprobacion': self._uid})

    def action_nomina_cancel_reason(self):
        ''''Díalogo Negar Rol Consolidado'''
        context = {
            'default_hr_payslip_run_id': self.id
        }
        return {
            'name': "Explique la Razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.nomina.cancel.reason',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

    @api.one
    def confirm_nomina(self):
        '''Contabilizar'''
        move_id = self.env['account.move'].create({'journal_id': self.journal_id.id,
                                                   'date': self.date_end,
                                                   })
        sueldo = 0.00
        he_extra = 0.00
        he_suple = 0.00
        fondos_reserva = 0.00
        fondos_reserva_retenidos = 0.00
        decimo_tercero = 0.00
        decimo_cuarto = 0.00
        otros_ingresos = 0.00
        total_ingresos = 0.00
        anticipo_quincena = 0.00
        # MARZ
        prestamo_anticipo_quincena = 0.00
        iess_personal = 0.00
        iess_patronal = 0.00
        prestamo_quirografario = 0.00
        prestamo_hipotecario = 0.00
        multas = 0.00
        faltas_atrasos = 0.00
        plan_celular = 0.00
        otros_egresos = 0.00
        total_egresos = 0.00
        neto_recibir = 0.00
        provisiones_decimo_tercero_empleados = []
        provisiones_decimo_cuarto_empleados = []
        anticipos_empleados = []
        flag_beneficios = False
        for rol in self.input_line_hr_run:
            sueldo += round(rol.sueldo, 3)
            iess_personal += round(rol.iess_personal, 3)
            iess_patronal += round(rol.iess_patronal, 3)
            # MARZ
            prestamo_anticipo_quincena += round(rol.prestamo_anticipo_quincena, 3)
            prestamo_quirografario += round(rol.prestamo_quirografario, 3)
            prestamo_hipotecario += round(rol.prestamo_hipotecario, 3)
            otros_ingresos += round(rol.otros_ingresos, 3)
            anticipos_empleados.append(
                {'empleado': rol.rol_id.employee_id.name, 'monto': round(rol.anticipo_quincena, 3),
                 'cuenta': rol.rol_id.employee_id.account_advance_payment.id})
            if rol.decimo_tercero == 0.00:
                provisiones_decimo_tercero_empleados.append(rol)
            else:
                decimo_tercero += round(rol.decimo_tercero, 3)
            if rol.decimo_cuarto == 0.00:
                provisiones_decimo_cuarto_empleados.append(rol)
            else:
                decimo_cuarto += round(rol.decimo_cuarto, 3)
            multas += round(rol.multas, 3)
            faltas_atrasos += round(rol.faltas_atrasos, 3)
            plan_celular += round(rol.plan_celular, 3)
            otros_egresos += round(rol.otros_egresos, 3)
            neto_recibir += round(rol.neto_recibir, 3)
            if not rol.rol_id.employee_id.acumula_beneficios:
                raise except_orm("Error", "Defina en el Empleado si acumula o no Beneficios")
            ''' TODO - Por el momomento!
            beneficios = rol.rol_id.employee_id.acumula_beneficios
            if beneficios == 'si' and rol.rol_id.employee_id.tiempo_laboral == True:
                flag_beneficios = True
                fondos_reserva_retenidos += round((float(rol.rol_id.employee_id.sueldo) * float(8.33)) / float(100), 3)
            # MARZ
            elif beneficios == 'no'
                rol.rol_id.employee_id.tiempo_laboral or rol.rol_id.employee_id.regla_fondo_reserva:
                    fondos_reserva += round((float(rol.rol_id.employee_id.sueldo) * float(8.33)) / float(100), 3)'''
        provision_decimo_tercero = 0.00
        for decimo_tercero_obj in provisiones_decimo_tercero_empleados:
            provision_decimo_tercero += round(decimo_tercero_obj.sueldo / 12.00, 3)
        provision_decimo_cuarto = 0.00
        for decimo_cuarto_obj in provisiones_decimo_cuarto_empleados:
            # Cambio de 375 a 386 (2018)
            provision_decimo_cuarto += round((float(375) / 360) * decimo_cuarto_obj.dias_trabajados, 3)
        if flag_beneficios == True:
            regla = self.env['hr.salary.rule'].search([('name', '=', 'Fondos de Reserva Retenidos')])[0]
            self.env['account.move.line'].with_context(check_move_validity=False).create(
                {'name': regla.name,
                 'journal_id': self.journal_id.id,
                 'account_id': regla.account_id.id,
                 'move_id': move_id.id,
                 'debit': 0.00,
                 'credit': round(fondos_reserva_retenidos, 3),
                 'date': self.date_end
                 })
            print('Fondo de Rerserva Retenidos', round(fondos_reserva_retenidos, 3))

        regla = self.env['hr.salary.rule'].search([('name', '=', 'IESS Personal 9.45%')])[0]
        iess_p = round(iess_personal, 3)
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': 0.00,
             'credit': iess_p,
             'date': self.date_end
             })
        print('IESS PERSONAL', iess_p)
        c = 0.00

        regla = self.env['hr.salary.rule'].search([('name', '=', 'IESS Patronal 12.15%')])[0]
        iess_pa = round((float(sueldo * 12.15)) / 100, 3)
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': 0.00,
             'credit': iess_pa,
             'date': self.date_end
             })
        print('IESS PATRONAL', iess_pa)

        # MARZ 17.60% (Nuevo, soló al Gerente General)
        regla = self.env['hr.salary.rule'].search([('name', '=', 'IESS Personal 17.60%')])[0]
        ip = round(iess_patronal, 3)
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': 0.00,
             'credit': ip,
             'date': self.date_end
             })
        print('IESS PERSONAL (17.60%)', ip)


        regla = self.env['hr.salary.rule'].search([('name', '=', 'Nomina a Pagar')])[0]
        nr = round(neto_recibir, 3)
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': 0.00,
             'credit': nr,
             'date': self.date_end
             })
        print('Nomina a Pagar', nr)

        prestamo_quiro = u'Préstamo Quirografario'
        regla = self.env['hr.salary.rule'].search([('name', '=', prestamo_quiro)])[0]
        pq = round(prestamo_quirografario, 3)
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': 0.00,
             'credit': pq,
             'date': self.date_end
             })
        print('P. Quiro', pq)


        ae = sum_a = 0.00
        for anticipo in anticipos_empleados:
            a = round(anticipo['monto'], 3)
            self.env['account.move.line'].with_context(check_move_validity=False).create(
                {'name': anticipo['empleado'],
                 'journal_id': self.journal_id.id,
                 'account_id': anticipo['cuenta'],
                 'move_id': move_id.id,
                 'debit': 0.00,
                 'credit': a,
                 'date': self.date_end
                 })
            sum_a += a
        print('aniticipo', sum_a)

        regla = self.env['hr.salary.rule'].search([('name', '=', 'Multas')])[0]
        mul = round(multas, 3)
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': 0.00,
             'credit': mul,
             'date': self.date_end
             })

        print('Multas', mul)

        regla = self.env['hr.salary.rule'].search([('name', '=', 'Faltas y Atrasos')])[0]
        fa = round(faltas_atrasos, 3)
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': 0.00,
             'credit': fa,
             'date': self.date_end
             })

        print ('faltas', fa)

        regla = self.env['hr.salary.rule'].search([('name', '=', 'Plan Celular')])[0]
        pce =  round(plan_celular, 3)
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': 0.00,
             'credit': pce,
             'date': self.date_end
             })
        print ('Plan Celular', pce)

        regla = self.env['hr.salary.rule'].search([('name', '=', 'Otros Egresos')])[0]
        oegr = round(otros_egresos, 3)
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': 0.00,
             'credit': oegr,
             'date': self.date_end
             })
        print ('Otros Egresos', oegr)

        # MARZ
        regla = self.env['hr.salary.rule'].search([('name', '=', u'Préstamo - Anticipo Sueldo')])[0]
        paq = round(prestamo_anticipo_quincena, 3)
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': 0.00,
             'credit': paq,
             'date': self.date_end
             })
        print ('P Anticipo Quincena', paq)

        decimo_tercero_name = u'Provision Décimo Tercero'
        regla = self.env['hr.salary.rule'].search([('name', '=', decimo_tercero_name)])[0]
        pvdt = round(provision_decimo_tercero, 3)
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': 0.00,
             'credit': pvdt,
             'date': self.date_end
             })

        print ('10tercero', pvdt)

        decimo_cuarto_name = u'Provision Décimo Cuarto'
        decimo_cuarto_name.encode('utf-8')
        pvdc = round(provision_decimo_cuarto, 3)
        regla = self.env['hr.salary.rule'].search([('name', '=', decimo_cuarto_name)])[0]
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': 0.00,
             'credit': pvdc,
             'date': self.date_end
             })

        print ('10Cuarto', pvdc)


        regla = self.env['hr.salary.rule'].search([('name', '=', 'Vacaciones')])[0]
        vacaciones = round(sueldo / 24, 2)
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': 0.00,
             'credit': vacaciones,
             'date': self.date_end
             })

        print ('Vacaciones', vacaciones)

        c = iess_p + iess_pa + ip + nr + pq + sum_a + mul + fa + pce + oegr + paq + pvdt + pvdc + vacaciones

        print ('DEBE')

        d = 0.00

        decimo_tercero_name = u'Décimo Tercero'
        dte = round(decimo_tercero, 3) + round(provision_decimo_tercero, 3)
        regla = self.env['hr.salary.rule'].search([('name', '=', decimo_tercero_name)])[0]
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': dte,
             'credit': 0.00,
             'date': self.date_end
             })

        print ('10tercero', dte)


        decimo_cuarto_name = u'Décimo Cuarto'
        decimo_cuarto_name.encode('utf-8')
        dcu = round(decimo_cuarto, 3) + round(provision_decimo_cuarto, 3)
        regla = self.env['hr.salary.rule'].search([('name', '=', decimo_cuarto_name)])[0]
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': dcu,
             'credit': 0.00,
             'date': self.date_end
             })

        print ('10cuerto', dcu)

        regla = self.env['hr.salary.rule'].search([('name', '=', "Patronal (gastos)")])[0]
        paga = round((float(sueldo * 12.15)) / 100, 3)
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': paga,
             'credit': 0.00,
             'date': self.date_end
             })

        print ('Patronal', paga)

        prestamo_hipo = u'Préstamos Hipotecarios'
        regla = self.env['hr.salary.rule'].search([('name', '=', prestamo_hipo)])[0]
        phip = round(prestamo_hipotecario, 3)
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': phip,
             'credit': 0.00,
             'date': self.date_end
             })

        print ('Hipotecarias', phip)

        regla = self.env['hr.salary.rule'].search([('name', '=', 'Otros Ingresos')])[0]
        oing = round(otros_ingresos, 3)
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': oing,
             'credit': 0.00,
             'date': self.date_end
             })

        print ('Otros Ingresos', oing)

        regla = self.env['hr.salary.rule'].search([('name', '=', 'Vacaciones Provision')])[0]
        vacaciones_ = round(sueldo / 24, 2)
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': vacaciones_,
             'credit': 0.00,
             'date': self.date_end
             })

        print ('Vacaciones Provision', vacaciones_)

        regla = self.env['hr.salary.rule'].search([('name', '=', 'Fondos de Reserva')])[0]
        fdr = 67.099 * 2 # TODO
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': fdr,
             'credit': 0.00,
             'date': self.date_end
             })
        print('Fondo de Rerserva', fdr)


        print ('Sueldo', round(sueldo, 3))

        regla = self.env['hr.salary.rule'].search([('name', '=', "Sueldo")])[0]
        suel = round(sueldo, 3)

        print ('Sueldo', suel)

        d = dte + dcu + paga + phip + oing + vacaciones_ + fdr + suel

        print ('C: ', c)
        print ('D: ', d)

        descuadre = c - d

        print ('Diferencia: ', descuadre)
        self.env['account.move.line'].with_context(check_move_validity=True).create(
            {'name': regla.name,
             'journal_id': self.journal_id.id,
             'account_id': regla.account_id.id,
             'move_id': move_id.id,
             'debit': suel,
             'credit': 0.00,
             'date': self.date_end
             })





        move_id.post()
        nombre_separada = move_id.name.split("-")
        fecha_separada = self.date_start.split("-")
        new_name = "NOM" + "-" + fecha_separada[0] + "-" + fecha_separada[1] + "-" + nombre_separada[1]
        move_id.write({'ref': u"Nómina" + "-" + self.name,
                       'name': new_name, 'date': self.date_end})
        self.update({'state': 'closed', 'move_id': move_id.id})

    def imprimir_rol_consolidado(self):
        '''Imprimir Rol Consolidado'''
        return self.env['report'].get_action(self, 'elitum_rrhh.reporte_rol_consolidado')

    @api.multi
    def add_roles(self):
        '''Añadir Roles'''
        roles = self.env['hr.payslip'].search(
            [('date_from', '>=', self.date_start), ('date_from', '<=', self.date_end), ('state', '=', 'draft')])
        if len(roles) == 0:
            raise except_orm("Error", "No hay roles en el Período selecionado")
        else:
            input_line_hr_run = self.input_line_hr_run.browse([])
            for rol in roles:
                decimo_cuarto = u'Décimo Cuarto'
                decimo_cuarto_parcial = u'Décimo Cuarto Jornada Parcial'
                decimo_cuarto.encode('utf-8')
                decimo_tercero = u'Décimo Tercero'
                prestamo_quiro = u'Préstamo Quirografario'
                prestamo_hipo = u'Préstamos Hipotecarios'
                data = {
                    'name': rol.employee_id.name,
                    'departamento': rol.employee_id.department_id.name,
                    'fecha_ingreso': rol.employee_id.fecha_ingreso,
                    'dias_trabajados': rol.dias_trabajados,
                    'sueldo': rol.input_line_ids.filtered(lambda x: x.name == 'Sueldo')[0].amount,
                    'he_extra': rol.input_line_ids.filtered(lambda x: x.name == 'Horas Extras Extraordinarias')[
                        0].amount if rol.input_line_ids.filtered(
                        lambda x: x.name == 'Horas Extras Extraordinarias') else 0.00,
                    'he_suple': rol.input_line_ids.filtered(lambda x: x.name == 'Horas Extras Suplementarias')[
                        0].amount if rol.input_line_ids.filtered(
                        lambda x: x.name == 'Horas Extras Suplementarias') else 0.00,
                    'fondos_reserva': rol.input_line_ids.filtered(lambda x: x.name == 'Fondos de Reserva')[
                        0].amount if rol.input_line_ids.filtered(lambda x: x.name == 'Fondos de Reserva') else 0.00,
                    'decimo_tercero': rol.input_line_ids.filtered(lambda x: x.name == decimo_tercero)[
                        0].amount if rol.input_line_ids.filtered(
                        lambda x: x.name == decimo_cuarto or x.name == decimo_cuarto_parcial) else 0.00,
                    # MARZ
                    'decimo_cuarto':
                        rol.input_line_ids.filtered(
                            lambda x: x.name == decimo_cuarto or x.name == decimo_cuarto_parcial)[
                            0].amount if rol.input_line_ids.filtered(lambda x: x.name == decimo_tercero) else 0.00,
                    'otros_ingresos': rol.input_line_ids.filtered(lambda x: x.name == 'Otros Ingresos')[
                        0].amount if rol.input_line_ids.filtered(lambda x: x.name == 'Otros Ingresos') else 0.00,
                    'total_ingresos': sum(line.amount for line in rol.input_line_ids),
                    'anticipo_quincena': rol.input_line_ids_2.filtered(lambda x: x.name == 'Anticipo de quincena')[
                        0].amount if rol.input_line_ids_2.filtered(
                        lambda x: x.name == 'Anticipo de quincena') else 0.00,
                    # MARZ
                    'prestamo_anticipo_quincena':
                        rol.input_line_ids_2.filtered(lambda x: x.name == u'Préstamo - Anticipo Sueldo')[0].amount
                        if rol.input_line_ids_2.filtered(lambda x: x.name == u'Préstamo - Anticipo Sueldo') else 0.00,
                    'iess_personal': rol.input_line_ids_2.filtered(lambda x: x.name == 'IESS Personal 9.45%')[
                        0].amount if rol.input_line_ids_2.filtered(lambda x: x.name == 'IESS Personal 9.45%') else 0.00,
                    # MARZ
                    'iess_patronal': rol.input_line_ids_2.filtered(lambda x: x.name == 'IESS Personal 17.60%')[
                        0].amount if rol.input_line_ids_2.filtered(
                        lambda x: x.name == 'IESS Personal 17.60%') else 0.00,
                    'prestamo_quirografario': rol.input_line_ids_2.filtered(lambda x: x.name == prestamo_quiro)[
                        0].amount if rol.input_line_ids_2.filtered(lambda x: x.name == prestamo_quiro) else 0.00,
                    'prestamo_hipotecario': rol.input_line_ids_2.filtered(lambda x: x.name == prestamo_hipo)[
                        0].amount if rol.input_line_ids_2.filtered(lambda x: x.name == prestamo_hipo) else 0.00,
                    'multas': rol.input_line_ids_2.filtered(lambda x: x.name == 'Multas')[
                        0].amount if rol.input_line_ids_2.filtered(lambda x: x.name == 'Multas') else 0.00,
                    'faltas_atrasos': rol.input_line_ids_2.filtered(lambda x: x.name == 'Faltas y Atrasos')[
                        0].amount if rol.input_line_ids_2.filtered(lambda x: x.name == 'Faltas y Atrasos') else 0.00,
                    'plan_celular': rol.input_line_ids_2.filtered(lambda x: x.name == 'Plan Celular')[
                        0].amount if rol.input_line_ids_2.filtered(lambda x: x.name == 'Plan Celular') else 0.00,
                    'otros_egresos': rol.input_line_ids_2.filtered(lambda x: x.name == 'Otros Egresos')[
                        0].amount if rol.input_line_ids_2.filtered(lambda x: x.name == 'Otros Egresos') else 0.00,
                    'total_egresos': sum(line.amount for line in rol.input_line_ids_2),
                    'neto_recibir': rol.neto_recibir,
                    'rol_id': rol.id
                }
                input_line_hr_run += input_line_hr_run.new(data)
            self.input_line_hr_run = input_line_hr_run

    @api.one
    @api.depends('state')
    def _total_monto_nomina(self):
        '''Calcular Total de Nómina'''
        self.total_monto_nomina = sum(line.neto_recibir for line in self.input_line_hr_run)

    @api.one
    def _numero_empleados(self):
        '''No. de Empleados en Nómina'''
        self.numero_empleados = len(self.input_line_hr_run)

    @api.one
    def _check_user_confirm(self):
        # ?, No necesario
        '''Verificar qué usuario pueda Aprobar la Nómina'''
        # if self.env['rrhh.nivel.aprobacion'].search([])[0].nivel_1_nomina.id == self._uid:
        self.aprobado_confirmar = True

    # MARZ
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('for_approval', 'Para Aprobación'),
        ('approved', 'Aprobado'),
        ('closed', 'Contabilizado'),
        ('canceled', 'Negado')
    ], string='Status', index=True, readonly=True, copy=False, default='draft')
    input_line_hr_run = fields.One2many('hr.payslip.run.line', 'payslip_run_id', string="Linea de Nómina")
    move_id = fields.Many2one('account.move', string="Asiento Contable")
    journal_id = fields.Many2one('account.journal', string="Diario", default=_default_journal)
    total_monto_nomina = fields.Float('Total de Nómina', compute='_total_monto_nomina', store=True)
    numero_empleados = fields.Integer('Numero de Empleados', compute='_numero_empleados', )
    aprobado_confirmar = fields.Boolean('Aprobado para Confirmar?', compute='_check_user_confirm')  # ?, No necesario
    usuario_aprobacion = fields.Many2one('res.users', u'Usuario de Aprobación')
    notas = fields.Text('Notas')


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    account_id = fields.Many2one('account.account', string="Cuenta Contable",
                                 domain=[('tipo_contable', '=', 'movimiento')])


class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'
    _order = 'amount desc'

    account_id = fields.Many2one('account.account', domain=[('tipo_contable', '=', 'movimiento')])
    total = fields.Float('Total')
    contract_id = fields.Many2one('hr.contract', string='Contract', required=False,
                                  help="The contract for which applied this input")


class HrPayslipInput2(models.Model):
    _name = 'hr.payslip.input.2'
    _description = u'Modelo - Línea de Egresos'
    _order = 'amount desc'

    name = fields.Char(string='Description', required=True)
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(required=True, help="The code that can be used in the salary rules")
    amount = fields.Float(help="It is used in computation. For e.g. A rule for sales having "
                               "1% commission of basic salary for per product can defined in expression "
                               "like result = inputs.SALEURO.amount * contract.wage*0.01.")
    contract_id = fields.Many2one('hr.contract', string='Contract', required=False,
                                  help="The contract for which applied this input")
    account_id = fields.Many2one('account.account', domain=[('tipo_contable', '=', 'movimiento')])
    total = fields.Float('Total')


class HrPayslipInput3(models.Model):
    _name = 'hr.payslip.input.3'
    _description = u'Modelo - Línea de Provisión'
    _order = 'amount desc'

    name = fields.Char(string='Description', required=True)
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(required=True, help="The code that can be used in the salary rules")
    amount = fields.Float(help="It is used in computation. For e.g. A rule for sales having "
                               "1% commission of basic salary for per product can defined in expression "
                               "like result = inputs.SALEURO.amount * contract.wage*0.01.")
    contract_id = fields.Many2one('hr.contract', string='Contract', required=False,
                                  help="The contract for which applied this input")
    account_id = fields.Many2one('account.account', domain=[('tipo_contable', '=', 'movimiento')])
    total = fields.Float('Total')


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def imprimir_rol_pago(self):
        '''Imprimir'''
        return self.env['report'].get_action(self, 'elitum_rrhh.reporte_rol_pago')

    def get_mes(self, mes):
        '''Obtenemos nombre del Mes por número'''
        if mes == 1:
            return 'Enero'
        if mes == 2:
            return 'Febrero'
        if mes == 3:
            return 'Marzo'
        if mes == 4:
            return 'Abril'
        if mes == 5:
            return 'Mayo'
        if mes == 6:
            return 'Junio'
        if mes == 7:
            return 'Julio'
        if mes == 8:
            return 'Agosto'
        if mes == 9:
            return 'Septiembre'
        if mes == 10:
            return 'Octubre'
        if mes == 11:
            return 'Noviembre'
        if mes == 12:
            return 'Diciembre'

    @api.model
    def create(self, vals):
        res = super(HrPayslip, self).create(vals)
        res.write({'number': self.get_mes(datetime.strptime(res.date_from, "%Y-%m-%d").month) + "-" + str(
            datetime.strptime(res.date_from, "%Y-%m-%d").year)})
        return res

    @api.one
    @api.depends('input_line_ids_2', 'input_line_ids')
    def _compute_neto_recibir(self):
        self.neto_recibir = round(sum(round(line.amount, 3) for line in self.input_line_ids), 3) - round(sum(
            round(line2.amount, 3) for line2 in self.input_line_ids_2), 3)

    @api.onchange('contract_id')
    def onchange_contract(self):
        if not self.contract_id:
            self.struct_id = False
        self.with_context(contract=True).onchange_employee()
        return

    @api.multi
    def action_payslip_done(self):
        return self.write({'state': 'done'})

    @api.model
    def get_inputs(self, employee_id, date_from, date_to, contrato):
        res = []
        structure_ids = employee_id.payroll_structure_id.id
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
        inputs = self.env['hr.salary.rule'].browse(sorted_rule_ids)
        # MARZ
        local_dict = {
            'contract': contrato,
            'employee': employee_id,
            'payslip': self,
            'result': 0.00
        }

        for input in inputs:
            if input.condition_select == 'python':
                safe_eval(input.condition_python, local_dict, mode='exec', nocopy=True)
                monto = local_dict['result']
            else:
                monto = 0.00
            input_data = {
                'name': input.name,
                'code': input.code,
                'account_id': input.account_id.id,
                'amount': monto,
                'type': input.category_id.name
            }
            res += [input_data]
        return res

    @api.onchange('employee_id', 'date_from')
    def onchange_employee(self):
        # MARZ
        contrato = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)])
        self.show_days_parcial = contrato.show_days_for_jornada_parcial
        self.days_parcial = contrato.days_for_jornada_parcial

        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return

        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to

        ttyme = datetime.fromtimestamp(time.mktime(time.strptime(date_from, "%Y-%m-%d")))
        self.name = _('Salary Slip of %s for %s') % (employee.name, tools.ustr(ttyme.strftime('%B-%Y')))
        self.company_id = employee.company_id

        if not employee.payroll_structure_id:
            return
        self.struct_id = employee.payroll_structure_id

        # MARZ
        input_line_ids = self.get_inputs(employee, date_from, date_to, contrato)
        input_lines = self.input_line_ids.browse([])
        input_lines_2 = self.input_line_ids_2.browse([])
        input_lines_3 = self.input_line_ids_3.browse([])
        for r in input_line_ids:
            if r['type'] == 'Ingresos':
                input_lines += input_lines.new(r)
            if r['type'] == 'Egresos':
                input_lines_2 += input_lines_2.new(r)
            if r['type'] == 'Provision':
                input_lines_3 += input_lines_3.new(r)

        self.input_line_ids = input_lines
        self.input_line_ids_2 = input_lines_2
        self.input_line_ids_3 = input_lines_3

        dias_ausencias = 0.00
        ausencias = self.env['hr.holidays'].search([('state', '=', 'validate'),
                                                    ('holiday_type', '=', 'employee'),
                                                    ('date_from', '>=', self.date_from),
                                                    ('date_from', '<=', self.date_to),
                                                    ('employee_id', '=', self.employee_id.id)])
        if len(ausencias) != 0:
            for ausencia in ausencias:
                dias_ausencias += ausencia.number_of_days_temp

        ausencias = self.env['hr.holidays'].search([('state', '=', 'validate'),
                                                    ('date_from', '>=', self.date_from),
                                                    ('date_from', '<=', self.date_to),
                                                    ('holiday_type', '=', 'category')])

        if len(ausencias) != 0:
            for ausencia in ausencias:
                for line in ausencia.category_id.line_employe_category:
                    if line.employee_id == self.employee_id.id:
                        dias_ausencias += ausencia.number_of_days_temp

        self.numero_ausencias = dias_ausencias

        return

    dias_trabajados = fields.Integer(string=u"Días Trabajados", default=30)
    # MARZ
    show_days_parcial = fields.Boolean(related="contract_id.show_days_for_jornada_parcial", store=False)
    days_parcial = fields.Integer(related="contract_id.days_for_jornada_parcial", store=False)
    numero_ausencias = fields.Integer(string=u"Días Ausencias", default=0)
    input_line_ids_2 = fields.One2many('hr.payslip.input.2', 'payslip_id', string='Payslip Inputs',
                                       readonly=True, states={'draft': [('readonly', False)]})
    input_line_ids_3 = fields.One2many('hr.payslip.input.3', 'payslip_id', string='Payslip Inputs',
                                       readonly=True, states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', 'Salary Journal', readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 default=lambda self: self.env['account.journal'].search([('type', '=', 'general')],
                                                                                         limit=1))
    neto_recibir = fields.Float('Neto a Recibir', compute='_compute_neto_recibir', store=True)
    usuario_aprobacion = fields.Many2one('res.users', 'Usuario aprobacion')


class SalaryAdvanceLineEliterp(models.Model):
    _name = 'salary.advanced.line.eliterp'

    _description = u'Modelo - Líneas de Anticipo'

    employee_id = fields.Many2one('hr.employee', string='Empleado')
    account_id = fields.Many2one('account.account', string="Cuenta", domain=[('tipo_contable', '=', 'movimiento')])
    amount_salary = fields.Float('Monto Anticipo', default=0.00)
    salary_advanced_id = fields.Many2one('salary.advanced.eliterp', 'Anticipo')


class SalaryAdvanceEliterp(models.Model):
    _name = 'salary.advanced.eliterp'

    _description = 'Modelo - Anticipo'

    def imprimir_anticipo_quincena(self):
        '''Imprimir Anticipo'''
        return self.env['report'].get_action(self, 'elitum_rrhh.reporte_anticipo_quincena')

    def cargar_empleados(self):
        '''Cargar Empleados'''
        list = []
        for empleado in self.env['hr.employee'].search([('state_laboral', '=', 'activo')]):
            list.append([0, 0, {'employee_id': empleado.id,
                                'account_id': empleado.account_advance_payment.id,
                                'amount_salary': float((empleado.sueldo * 40) / 100)}])
        return self.write({'line_salary_advanced': list})

    @api.one
    @api.depends('line_salary_advanced')
    def _get_total(self):
        '''Total de Línea de Anticipo'''
        self.amount_total = sum(line.amount_salary for line in self.line_salary_advanced)

    def confirmar_anticipo(self):
        '''Contabilizar Anticipo'''
        move_id = self.env['account.move'].create({'journal_id': self.journal_id.id,
                                                   'date': self.date
                                                   })
        self.env['account.move.line'].with_context(check_move_validity=False).create({'name': self.account_id.name,
                                                                                      'journal_id': self.journal_id.id,
                                                                                      'account_id': self.account_id.id,
                                                                                      'move_id': move_id.id,
                                                                                      'debit': 0.0,
                                                                                      'credit': self.amount_total,
                                                                                      'date': self.date})
        count = len(self.line_salary_advanced)
        for line in self.line_salary_advanced:
            count -= 1
            if count == 0:
                self.env['account.move.line'].with_context(check_move_validity=True).create(
                    {'name': line.account_id.name,
                     'journal_id': self.journal_id.id,
                     'account_id': line.account_id.id,
                     'move_id': move_id.id,
                     'credit': 0.0,
                     'debit': line.amount_salary,
                     'date': self.date})
            else:
                self.env['account.move.line'].with_context(check_move_validity=False).create(
                    {'name': line.account_id.name,
                     'journal_id': self.journal_id.id,
                     'account_id': line.account_id.id,
                     'move_id': move_id.id,
                     'credit': 0.0,
                     'debit': line.amount_salary,
                     'date': self.date})

        move_id.post()
        move_id.write({'ref': "Anticipo" + " " + move_id.name[:4]})
        return self.write({'name': move_id.name, 'state': 'contabilizado', 'move_id': move_id.id})

    @api.model
    def _default_journal(self):
        '''Diario de Anticipo de Quincena'''
        return self.env['account.journal'].search([('name', '=', 'Anticipo de Quincena')])[0].id

    name = fields.Char('No.Documento')
    periodo = fields.Selection([('enero', 'Enero'),
                                ('febrero', 'Febrero'),
                                ('marzo', 'Marzo'),
                                ('abril', 'Abril'),
                                ('mayo', 'Mayo'),
                                ('junio', 'Junio'),
                                ('julio', 'Julio'),
                                ('agosto', 'Agosto'),
                                ('septiembre', 'Septiembre'),
                                ('octubre', 'Octubre'),
                                ('noviembre', 'Noviembre'),
                                ('diciembre', 'Diciembre')], string='Mes')
    date = fields.Date('Fecha de Emisión', default=fields.Date.context_today)
    account_id = fields.Many2one('account.account', string="Cuenta", domain=[('tipo_contable', '=', 'movimiento')])
    line_salary_advanced = fields.One2many('salary.advanced.line.eliterp', 'salary_advanced_id')
    move_id = fields.Many2one('account.move', string='Asiento Contable')
    amount_total = fields.Float('Cantidad Total', compute='_get_total', store=True)
    journal_id = fields.Many2one('account.journal', string="Diario De Anticipo", default=_default_journal)
    state = fields.Selection([('draft', 'Borrador'), ('open', 'Confirmado'), ('contabilizado', 'Contabilizado')],
                             string="Estado", default='draft')
