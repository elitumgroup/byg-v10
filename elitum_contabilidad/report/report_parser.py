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
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _
from itertools import ifilter
from operator import itemgetter
import math

UNIDADES = (
    '', 'Un ', 'Dos ', 'Tres ', 'Cuatro ', 'Cinco ', 'Seis ', 'Siete ', 'Ocho ', 'Nueve ', 'Diez ', 'Once ',
    'Doce ',
    'Trece ', 'Catorce ', 'Quince ', 'Dieciséis ', 'Diecisiete ', 'Dieciocho ', 'Diecinueve ', 'Veinte ')
DECENAS = ('Veinti', 'Treinta ', 'Cuarenta ', 'Cincuenta ', 'Sesenta ', 'Setenta ', 'Ochenta ', 'Noventa ', 'Cien ')
CENTENAS = (
    'Ciento ', 'Doscientos ', 'Trescientos ', 'Cuatrocientos ', 'Quinientos ', 'Seiscientos ', 'Setecientos ',
    'Ochocientos ', 'Novecientos ')

TOTALES = []


class ReporteFacturaCliente(models.AbstractModel):
    _name = 'report.elitum_contabilidad.reporte_factura_cliente'

    def __convertNumber(self, n):
        output = ''
        if (n == '100'):
            output = "Cien "
        elif (n[0] != '0'):
            output = CENTENAS[int(n[0]) - 1]
        k = int(n[1:])
        if (k <= 20):
            output += UNIDADES[k]
        else:
            if ((k > 30) & (n[2] != '0')):
                output += '%sy %s' % (DECENAS[int(n[1]) - 2], UNIDADES[int(n[2])])
            else:
                output += '%s%s' % (DECENAS[int(n[1]) - 2], UNIDADES[int(n[2])])
        return output

    def Numero_a_Texto(self, number_in):
        convertido = ''
        number_str = str(number_in) if (type(number_in) != 'str') else number_in
        number_str = number_str.zfill(9)
        millones, miles, cientos = number_str[:3], number_str[3:6], number_str[6:]
        if (millones):
            if (millones == '001'):
                convertido += 'Un Millon '
            elif (int(millones) > 0):
                convertido += '%sMillones ' % self.__convertNumber(millones)
        if (miles):
            if (miles == '001'):
                convertido += 'Mil '
            elif (int(miles) > 0):
                convertido += '%sMil ' % self.__convertNumber(miles)
        if (cientos):
            if (cientos == '001'):
                convertido += 'Un '
            elif (int(cientos) > 0):
                convertido += '%s ' % self.__convertNumber(cientos)
        return convertido

    def get_amount_to_word(self, j):
        try:
            Arreglo1 = str(j).split(',')
            Arreglo2 = str(j).split('.')
            if (len(Arreglo1) > len(Arreglo2) or len(Arreglo1) == len(Arreglo2)):
                Arreglo = Arreglo1
            else:
                Arreglo = Arreglo2

            if (len(Arreglo) == 2):
                whole = math.floor(j)
                frac = j - whole
                num = str("{0:.2f}".format(frac))[2:]
                return (self.Numero_a_Texto(Arreglo[0]) + 'con ' + num + "/100").capitalize()
            elif (len(Arreglo) == 1):
                return (self.Numero_a_Texto(Arreglo[0]) + 'con ' + '00/100').capitalize()
        except ValueError:
            return "Cero"

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'account.invoice',
            'docs': self.env['account.invoice'].browse(docids),
            'data': data,
            'get_amount_to_word': self.get_amount_to_word,
        }
        return self.env['report'].render('elitum_contabilidad.reporte_factura_cliente', docargs)


class ReporteLibroMayor(models.AbstractModel):
    _name = 'report.elitum_contabilidad.reporte_libro_mayor'

    def get_saldo_inicial(self, cuenta, fecha_inicio, fecha_fin):
        # MARZ
        lines = self.env['account.move.line'].search(
            [('account_id', '=', cuenta.id), ('date', '>=', '1980-01-01'), ('date', '<', fecha_inicio)])
        saldo = 0.00
        saldo_inicial_cuenta = 0.00
        if cuenta.fecha_saldo_inicial <= fecha_inicio:
            saldo_inicial_cuenta = cuenta.saldo_inicial  # Saldo Inicial (Nueva Compañía)
        for line in lines:
            tipo = (cuenta.code.split("."))[0]
            monto = line.debit - line.credit
            if tipo in ['1', '5']:
                if line.debit < line.credit:
                    if monto > 0:
                        monto = -1 * round(line.debit - line.credit, 2)
            if tipo in ['2', '3', '4']:
                if line.debit < line.credit:
                    if monto < 0:
                        monto = -1 * round(line.debit - line.credit, 2)
                if line.debit > line.credit:
                    if monto > 0:
                        monto = -1 * round(line.debit - line.credit, 2)
            saldo = saldo + monto
        return saldo + saldo_inicial_cuenta

    def get_reporte(self, doc):
        if doc.tipo_reporte == 'all':
            cuentas_base = self.env['account.account'].search([('tipo_contable', '=', 'movimiento')])
        else:
            cuentas_base = doc.cuenta
        cuentas = []
        data_line = []
        data = []
        for c in cuentas_base:
            cuentas.append(c)
        cuentas.sort(key=lambda x: x.code, reverse=False)
        for cuenta in cuentas:
            lines = self.env['account.move.line'].search(
                [('account_id', '=', cuenta.id), ('date', '>=', doc.fecha_inicio), ('date', '<=', doc.fecha_fin)],
                order="date")
            saldo_inicial = self.get_saldo_inicial(cuenta, doc.fecha_inicio, doc.fecha_fin)
            saldo = saldo_inicial
            debe_total = 0.00
            haber_total = 0.00
            data_line = []
            for line in lines:
                debe_total = debe_total + line.debit
                haber_total = haber_total + line.credit
                tipo = (cuenta.code.split("."))[0]
                monto = line.debit - line.credit
                if tipo in ['1', '5']:
                    if line.debit < line.credit:
                        if monto > 0:
                            monto = -1 * round(line.debit - line.credit, 2)
                if tipo in ['2', '3', '4']:
                    if line.debit < line.credit:
                        if monto < 0:
                            monto = -1 * round(line.debit - line.credit, 2)
                    if line.debit > line.credit:
                        if monto > 0:
                            monto = -1 * round(line.debit - line.credit, 2)
                saldo = saldo + monto
                data_line.append({'name': line.move_id.name,
                                  'fecha': line.date,
                                  'detalle': line.name,
                                  'debe': line.debit,
                                  'haber': line.credit,
                                  'saldo': saldo})

            saldo_total = debe_total - haber_total
            if len(lines) != 0:
                if tipo in ['1', '5']:
                    if debe_total < haber_total:
                        if saldo_total > 0:
                            saldo_total = -1 * round(debe_total - haber_total, 2)
                if tipo in ['2', '3', '4']:
                    if debe_total < haber_total:
                        if saldo_total < 0:
                            saldo_total = -1 * round(debe_total - haber_total, 2)
                    if debe_total > haber_total:
                        if saldo_total > 0:
                            saldo_total = -1 * round(debe_total - haber_total, 2)
            saldo_total = saldo_inicial + saldo_total
            data.append({'cuenta': cuenta.name,
                         'code': cuenta.code,
                         'movimientos': data_line,
                         'debe': debe_total,
                         'haber': haber_total,
                         'saldo': saldo_total,
                         'saldo_inicial': saldo_inicial})
        return data

    def get_periodo(self, fecha):
        return (fecha.split("-"))[0]

    @api.model
    def render_html(self, docids, data=None):
        global TOTALES
        TOTALES = []
        docargs = {
            'doc_ids': docids,
            'doc_model': 'account.reporte.libro.mayor',
            'docs': self.env['account.reporte.libro.mayor'].browse(docids),
            'data': data,
            'get_reporte': self.get_reporte,
            'get_periodo': self.get_periodo,
        }
        return self.env['report'].render('elitum_contabilidad.reporte_libro_mayor', docargs)


class ReporteFlujoCaja(models.AbstractModel):
    _name = 'report.elitum_contabilidad.reporte_flujo_caja'

    def get_monto(self, lineas, periodo):
        for linea in lineas:
            movimientos = self.env['account.move.line'].search([('account_id', '=', linea.account_id.id),
                                                                ('date', '>=', periodo.fecha_inicio),
                                                                ('date', '<=', periodo.fecha_fin)])
            credit = 0.00
            debit = 0.00
            for line in movimientos:
                credit += line.credit
                debit += line.debit
            monto = round(debit - credit, 2)
        return monto

    def get_reporte(self, tipo, doc):
        data = []
        rubros = self.env['account.reporte.flujo.caja'].search([('tipo', '=', 'tipo')])
        for rubro in rubros:
            data.append({'name': rubro.name,
                         'monto': self.get_monto(rubro.lines_account_ids, rubro.periodo)})
        return data

    @api.model
    def render_html(self, docids, data=None):
        global TOTALES
        TOTALES = []
        docargs = {
            'doc_ids': docids,
            'doc_model': 'account.reporte.flujo.caja',
            'docs': self.env['account.reporte.flujo.caja'].browse(docids),
            'data': data,
            'get_reporte': self.get_reporte,
        }
        return self.env['report'].render('elitum_contabilidad.reporte_flujo_caja', docargs)


class ReporteEstadoFinanciero(models.AbstractModel):
    _name = 'report.elitum_contabilidad.reporte_estado_financiero'

    def get_saldo_resultado(self, cuenta, tipo, doc):
        '''Obtenemos el saldo del Estado de Resultados'''
        arg = []
        arg.append(('account_id', '=', cuenta))
        arg.append(('date', '>=', doc.fecha_inicio))
        arg.append(('date', '<=', doc.fecha_fin))
        if doc.tipo_centro_costo != 'all':
            arg.append(('analytic_account_id', '=', doc.analytic_account_id.id))
        if doc.tipo_proyecto != 'all':
            arg.append(('project_id', '=', doc.project_id.id))
        movimientos = self.env['account.move.line'].search(arg)
        saldo_inicial_cuenta = 0.00
        saldo_inicial = self.env['account.account'].search([
            ('id', '=', cuenta),
            ('fecha_saldo_inicial', '>=', doc.fecha_inicio),
            ('fecha_saldo_inicial', '<=', doc.fecha_fin)
        ])
        if saldo_inicial:
            saldo_inicial_cuenta = saldo_inicial[0].saldo_inicial  # Saldo Inicial (Nueva Compañía)
        credit = 0.00
        debit = 0.00
        for line in movimientos:
            credit += line.credit
            debit += line.debit
        monto = round(debit - credit, 2)
        if tipo == '5':
            if debit < credit:
                if monto > 0:
                    monto = -1 * round(debit - credit, 2)
        if tipo == '4':
            if debit < credit:
                if monto < 0:
                    monto = -1 * round(debit - credit, 2)
            if debit > credit:
                if monto > 0:
                    monto = -1 * round(debit - credit, 2)
        return monto + saldo_inicial_cuenta

    def estado_resultado(self, doc):
        '''Obtener el monto dde Estado de Resultados'''
        cuentas_contables = self.env['account.account'].search([('user_type_id.name', '!=', 'odoo')], order="code")
        cuentas = []
        movimientos = []
        padre = False
        total_movimiento = 0.00
        cuentas_4 = cuentas_contables.filtered(lambda x: (x.code.split("."))[0] == '4')
        cuentas_5 = cuentas_contables.filtered(lambda x: (x.code.split("."))[0] == '5')
        total_ingresos = 0.00
        total_gastos = 0.00
        for cuenta in cuentas_4:
            if cuentas == []:
                cuentas.append({'code': self.env['account.account'].search([('code', '=', '4')])[0].code,
                                'name': 'INGRESOS',
                                'tipo': 'padre',
                                'sub_cuenta': [],
                                'monto': 0.00,
                                'cuenta': self.env['account.account'].search([('code', '=', '4')])[0],
                                'padre': padre})
            else:
                if cuenta.tipo_contable == 'vista':
                    padre = self.buscar_padre(cuenta)
                    cuentas = self.update_saldo(cuentas)
                    cuentas.append({'code': cuenta.code,
                                    'tipo': 'vista',
                                    'sub_cuenta': [],
                                    'name': cuenta.name,
                                    'monto': 0.00,
                                    'cuenta': cuenta,
                                    'padre': padre})
                else:
                    monto_movimiento = self.get_saldo_resultado(cuenta.id, '4', doc)
                    padre = self.buscar_padre(cuenta)
                    print (cuenta.code)
                    index = map(itemgetter('code'), cuentas).index(padre)
                    cuentas[index]['sub_cuenta'].append({'code': cuenta.code,
                                                         'tipo': 'movimiento',
                                                         'name': cuenta.name,
                                                         'monto': monto_movimiento})
                    cuentas[index]['monto'] = cuentas[index]['monto'] + monto_movimiento
        cuentas = self.update_saldo(cuentas)
        total_ingresos = cuentas[0]['monto']
        cuentas = []
        movimientos = []
        padre = False
        total_movimiento = 0.00
        for cuenta in cuentas_5:
            if cuentas == []:
                cuentas.append({'code': self.env['account.account'].search([('code', '=', '5')])[0].code,
                                'name': 'GASTOS',
                                'tipo': 'padre',
                                'sub_cuenta': [],
                                'monto': 0.00,
                                'cuenta': self.env['account.account'].search([('code', '=', '5')])[0],
                                'padre': padre})
            else:
                if cuenta.tipo_contable == 'vista':
                    padre = self.buscar_padre(cuenta)
                    cuentas = self.update_saldo(cuentas)
                    cuentas.append({'code': cuenta.code,
                                    'tipo': 'vista',
                                    'sub_cuenta': [],
                                    'name': cuenta.name,
                                    'monto': 0.00,
                                    'cuenta': cuenta,
                                    'padre': padre})
                else:
                    monto_movimiento = self.get_saldo_resultado(cuenta.id, '5', doc)
                    padre = self.buscar_padre(cuenta)
                    print (cuenta.code)
                    index = map(itemgetter('code'), cuentas).index(padre)
                    cuentas[index]['sub_cuenta'].append({'code': cuenta.code,
                                                         'tipo': 'movimiento',
                                                         'name': cuenta.name,
                                                         'monto': monto_movimiento})
                    cuentas[index]['monto'] = cuentas[index]['monto'] + monto_movimiento
        cuentas = self.update_saldo(cuentas)
        total_gastos = cuentas[0]['monto']
        return total_ingresos - total_gastos

    def update_saldo(self, cuentas):
        '''Actualizamos el saldo de la Cuenta Padre'''
        cuentas = cuentas[::-1]
        if len(cuentas) == 1:
            return cuentas[::-1]
        for cuenta in cuentas:
            cuenta['monto'] = 0.00
            total = 0.00
            if cuenta['sub_cuenta'] != []:
                for sub_cuenta in cuenta['sub_cuenta']:
                    total = total + sub_cuenta['monto']
                cuenta['monto'] = total
        for x in range(len(cuentas)):
            for y in range(len(cuentas)):
                if cuentas[x]['padre'] == cuentas[y]['code']:
                    cuentas[y]['monto'] = cuentas[y]['monto'] + cuentas[x]['monto']
        return cuentas[::-1]

    def get_saldo(self, cuenta, tipo, doc):
        '''Obtenemos el saldo de la cuenta y verificamos su naturaleza'''
        # MARZ
        arg = []
        arg.append(('account_id', '=', cuenta.id))
        arg.append(('date', '>=', doc.fecha_inicio))
        arg.append(('date', '<=', doc.fecha_fin))
        if doc.tipo_centro_costo != 'all':
            arg.append(('analytic_account_id', '=', doc.analytic_account_id.id))
        if doc.tipo_proyecto != 'all':
            arg.append(('project_id', '=', doc.project_id.id))
        movimientos = self.env['account.move.line'].search(arg)
        credit = 0.00
        debit = 0.00
        if cuenta.code == '3.3.3':
            date_object = datetime.strptime(doc.fecha_fin, "%Y-%m-%d")
            final = date_object.replace(year=date_object.year - 1)
            movimiento = self.env['account.move.line'].search([('account_id', '=', cuenta.id),
                                                               ('date', '=', str(final))])
            movimientos = movimientos | movimiento
        for line in movimientos:
            credit += line.credit
            debit += line.debit
        monto = round(debit - credit, 2)
        if tipo == '1':
            if debit < credit:
                if monto > 0:
                    monto = -1 * round(debit - credit, 2)
        if tipo in ('2', '3'):
            if debit < credit:
                if monto < 0:
                    monto = -1 * round(debit - credit, 2)
            if debit > credit:
                if monto > 0:
                    monto = -1 * round(debit - credit, 2)
        # Saldo Inicial de la cuenta
        if cuenta.code != '3.3.3':
            monto = monto + self.env['report.elitum_contabilidad.reporte_libro_mayor'].get_saldo_inicial(cuenta,
                                                                                                         doc.fecha_inicio,
                                                                                                         doc.fecha_fin)
        return monto

    def buscar_padre(self, cuenta):
        '''Buscamos la cuenta padre de la cuenta'''
        split = cuenta.code.split(".")[:len(cuenta.code.split(".")) - 1]
        codigo = ""
        for code in split:
            if codigo == "":
                codigo = codigo + str(code)
            else:
                codigo = codigo + "." + str(code)
        return codigo

    def get_reporte(self, tipo, doc):
        '''Reporte General'''
        cuentas_contables = self.env['account.account'].search([('user_type_id.name', '!=', 'odoo')], order="code")
        cuentas = []
        movimientos = []
        padre = False
        total_movimiento = 0.00
        for cuenta in cuentas_contables:
            if (cuenta.code.split("."))[0] == tipo:
                if cuentas == []:
                    # Cuentas Principales (Sin Movimiento)
                    if tipo == '1':
                        name = "ACTIVOS"
                    if tipo == '2':
                        name = "PASIVOS"
                    if tipo == '3':
                        name = "PATRIMONIO NETO"
                    cuentas.append({'code': self.env['account.account'].search([('code', '=', tipo)])[0].code,
                                    'name': name,
                                    'tipo': 'padre',
                                    'sub_cuenta': [],
                                    'monto': 0.00,
                                    'cuenta': self.env['account.account'].search([('code', '=', tipo)])[0],
                                    'padre': padre})
                else:
                    if cuenta.tipo_contable == 'vista':
                        # Cuentas Vistas
                        padre = self.buscar_padre(cuenta)
                        cuentas = self.update_saldo(cuentas)
                        cuentas.append({'code': cuenta.code,
                                        'tipo': 'vista',
                                        'sub_cuenta': [],
                                        'name': cuenta.name,
                                        'monto': 0.00,
                                        'cuenta': cuenta,
                                        'padre': padre})
                    else:
                        # Cuentas con Movimientos
                        conciliacion_bancaria = []
                        if cuenta.user_type_id.type == 'bank':
                            conciliacion_bancaria = self.env['concilacion.bancaria'].search(
                                [('fecha_inicio', '=', doc.fecha_inicio),
                                 ('fecha_fin', '=', doc.fecha_fin),
                                 ('account_id', '=', cuenta.id)])
                            if len(conciliacion_bancaria) != 0:
                                monto_movimiento = conciliacion_bancaria[0].saldo_cuenta
                            else:
                                monto_movimiento = self.get_saldo(cuenta, tipo, doc)
                        else:
                            monto_movimiento = self.get_saldo(cuenta, tipo, doc)
                        padre = self.buscar_padre(cuenta)
                        if cuenta.code:  # Imprimimos Cuentas (tipo = movimiento)
                            print (cuenta.code)
                        index = map(itemgetter('code'), cuentas).index(padre)
                        cuentas[index]['sub_cuenta'].append({'code': cuenta.code,
                                                             'tipo': 'movimiento',
                                                             'name': cuenta.name,
                                                             'monto': round(monto_movimiento, 2)})
                        cuentas[index]['monto'] = cuentas[index]['monto'] + monto_movimiento
            cuentas = self.update_saldo(cuentas)
        if tipo == '1':
            TOTALES.append({'total_activo': cuentas[0]['monto']})
        if tipo == '2':
            TOTALES.append({'total_pasivo': cuentas[0]['monto']})
        if tipo == '3':
            movimientos = []
            cuenta_estado = filter(lambda x: x['code'] == '3.3', cuentas)[0]
            if cuenta_estado['monto'] != 0.00:
                # MARZ
                monto = self.estado_resultado(doc)
                movimientos_internos = {}
                if monto >= 0:
                    movimientos_internos['code'] = '3.3.1.1'
                    movimientos_internos['tipo'] = 'movimiento'
                    movimientos_internos['name'] = 'GANANCIA NETA DEL PERIODO'
                    movimientos_internos['monto'] = monto
                else:
                    movimientos_internos['code'] = '3.3.2.1'
                    movimientos_internos['tipo'] = 'movimiento'
                    movimientos_internos['name'] = '(-) PERDIDA NETA DEL PERIODO'
                    movimientos_internos['monto'] = monto
                for cuenta in cuentas:
                    if cuenta['code'] == '3.3':
                        cuenta['sub_cuenta'].append(movimientos_internos)
                TOTALES.append({'total_patrimonio': cuentas[0]['monto'] + monto})
                return cuentas
            # Si Estado de Resultados es igual a 0
            monto = self.estado_resultado(doc)
            if monto >= 0:
                movimientos.append({'code': '3.3.1.1',
                                    'tipo': 'movimiento',
                                    'name': 'GANANCIA NETA DEL PERIODO',
                                    'monto': monto})
            else:
                movimientos.append({'code': '3.3.2.1',
                                    'tipo': 'movimiento',
                                    'name': '(-) PERDIDA NETA DEL PERIODO',
                                    'monto': monto})
            cuentas.append({'code': '3.3',
                            'tipo': 'vista',
                            'sub_cuenta': movimientos,
                            'name': 'RESULTADO DEL EJERCICIO',
                            'monto': monto,
                            'cuenta': False,
                            'padre': False})
            cuentas[0]['monto'] = cuentas[0]['monto'] + monto
            TOTALES.append({'total_patrimonio': cuentas[0]['monto']})
        return cuentas

    def get_total_activo(self):
        return TOTALES[0]['total_activo']

    def get_total_pasivo(self):
        return TOTALES[1]['total_pasivo']

    def get_total_patrimonio(self):
        return TOTALES[2]['total_patrimonio']

    def get_total_ejercicio(self):
        return TOTALES[1]['total_pasivo'] + TOTALES[2]['total_patrimonio']

    def get_periodo(self, fecha):
        return (fecha.split("-"))[0]

    # MARZ
    def get_cuentas_orden(self, lista):
        lista_ordenada = sorted(lista, key=lambda k: int(k['code'].replace('.', '')))
        return lista_ordenada

    @api.model
    def render_html(self, docids, data=None):
        global TOTALES
        TOTALES = []
        docargs = {
            'doc_ids': docids,
            'doc_model': 'account.reportes.financieros',
            'docs': self.env['account.reportes.financieros'].browse(docids),
            'data': data,
            'get_reporte': self.get_reporte,
            'get_total_activo': self.get_total_activo,
            'get_total_pasivo': self.get_total_pasivo,
            'get_total_patrimonio': self.get_total_patrimonio,
            'get_total_ejercicio': self.get_total_ejercicio,
            'get_periodo': self.get_periodo,
            # MARZ
            'get_cuentas_orden': self.get_cuentas_orden,
        }
        return self.env['report'].render('elitum_contabilidad.reporte_estado_financiero', docargs)


class ReporteEstadoResultado(models.AbstractModel):
    _name = 'report.elitum_contabilidad.reporte_estado_resultado'

    def update_saldo(self, cuentas):
        cuentas = cuentas[::-1]
        if len(cuentas) == 1:
            return cuentas[::-1]
        for cuenta in cuentas:
            cuenta['monto'] = 0.00
            total = 0.00
            if cuenta['sub_cuenta'] != []:
                for sub_cuenta in cuenta['sub_cuenta']:
                    total = total + sub_cuenta['monto']
                cuenta['monto'] = total
        for x in range(len(cuentas)):
            for y in range(len(cuentas)):
                if cuentas[x]['padre'] == cuentas[y]['code']:
                    cuentas[y]['monto'] = cuentas[y]['monto'] + cuentas[x]['monto']
        return cuentas[::-1]

    def get_saldo(self, cuenta, tipo, doc):
        arg = []
        arg.append(('account_id', '=', cuenta))
        arg.append(('date', '>=', doc.fecha_inicio))
        arg.append(('date', '<=', doc.fecha_fin))
        if doc.tipo_centro_costo != 'all':
            arg.append(('analytic_account_id', '=', doc.analytic_account_id.id))
        if doc.tipo_proyecto != 'all':
            arg.append(('project_id', '=', doc.project_id.id))
        movimientos = self.env['account.move.line'].search(arg)
        saldo_inicial_cuenta = 0.00
        saldo_inicial = self.env['account.account'].search([
            ('id', '=', cuenta),
            ('fecha_saldo_inicial', '>=', doc.fecha_inicio),
            ('fecha_saldo_inicial', '<=', doc.fecha_fin)
        ])
        if saldo_inicial:
            saldo_inicial_cuenta = saldo_inicial[0].saldo_inicial  # Saldo Inicial (Nueva Compañía)
        credit = 0.00
        debit = 0.00
        for line in movimientos:
            credit += line.credit
            debit += line.debit
        monto = round(debit - credit, 2)
        if tipo == '5':
            if debit < credit:
                if monto > 0:
                    monto = -1 * round(debit - credit, 2)
        if tipo == '4':
            if debit < credit:
                if monto < 0:
                    monto = -1 * round(debit - credit, 2)
            if debit > credit:
                if monto > 0:
                    monto = -1 * round(debit - credit, 2)
        return monto + saldo_inicial_cuenta

    def buscar_padre(self, cuenta):
        split = cuenta.code.split(".")[:len(cuenta.code.split(".")) - 1]
        codigo = ""
        for code in split:
            if codigo == "":
                codigo = codigo + str(code)
            else:
                codigo = codigo + "." + str(code)
        return codigo

    def get_reporte(self, tipo, doc):
        cuentas_contables = self.env['account.account'].search([('user_type_id.name', '!=', 'odoo')], order="code")
        cuentas_contables = cuentas_contables.filtered(lambda x: (x.code.split("."))[0] == tipo)
        cuentas = []
        movimientos = []
        padre = False
        cuenta_code_comparativo = False
        total_movimiento = 0.00
        for cuenta in cuentas_contables:
            if (cuenta.code.split("."))[0] == tipo:
                if cuentas == []:
                    if tipo == '4':
                        name = "INGRESOS"
                    if tipo == '5':
                        name = "COSTOS Y GASTOS"
                    cuentas.append({'code': self.env['account.account'].search([('code', '=', tipo)])[0].code,
                                    'name': name,
                                    'tipo': 'padre',
                                    'sub_cuenta': [],
                                    'monto': 0.00,
                                    'cuenta': self.env['account.account'].search([('code', '=', tipo)])[0],
                                    'padre': padre})
                else:
                    if cuenta.tipo_contable == 'vista':
                        padre = self.buscar_padre(cuenta)
                        cuentas = self.update_saldo(cuentas)
                        cuentas.append({'code': cuenta.code,
                                        'tipo': 'vista',
                                        'sub_cuenta': [],
                                        'name': cuenta.name,
                                        'monto': 0.00,
                                        'cuenta': cuenta,
                                        'padre': padre})
                    else:
                        padre = self.buscar_padre(cuenta)
                        print (cuenta.code)
                        index = map(itemgetter('code'), cuentas).index(padre)
                        cuentas[index]['sub_cuenta'].append({'code': cuenta.code,
                                                             'tipo': 'movimiento',
                                                             'name': cuenta.name,
                                                             'monto': self.get_saldo(cuenta.id, tipo, doc)})
                        cuentas[index]['monto'] = cuentas[index]['monto'] + self.get_saldo(cuenta.id, tipo, doc)
        cuentas = self.update_saldo(cuentas)
        if tipo == '4':
            TOTALES.append({'total_ingresos': cuentas[0]['monto']})
        if tipo == '5':
            TOTALES.append({'total_gastos': cuentas[0]['monto']})
        return cuentas

    def get_total_ejercicio(self):
        return TOTALES[0]['total_ingresos'] - TOTALES[1]['total_gastos']

    def get_resultado(self):
        if TOTALES[0]['total_ingresos'] - TOTALES[1]['total_gastos'] >= 0:
            return True
        else:
            return False

    def get_periodo(self, fecha):
        return (fecha.split("-"))[0]

    @api.model
    def render_html(self, docids, data=None):
        global TOTALES
        TOTALES = []
        docargs = {
            'doc_ids': docids,
            'doc_model': 'account.reporte.estado.resultado',
            'docs': self.env['account.reporte.estado.resultado'].browse(docids),
            'data': data,
            'get_reporte': self.get_reporte,
            'get_total_ejercicio': self.get_total_ejercicio,
            'get_resultado': self.get_resultado,
            'get_periodo': self.get_periodo,
        }
        return self.env['report'].render('elitum_contabilidad.reporte_estado_resultado', docargs)


class ReporteConcilacionBancaria(models.AbstractModel):
    _name = 'report.elitum_contabilidad.reporte_concilacion_bancaria'

    def get_total_lineas(self, doc):
        valor = 0.00
        for line in doc.lineas_movimientos_bancarios_ids:
            if line.check:
                valor += line.valor
        return valor + doc.saldo_inicial

    def get_resumen_lineas(self, doc):
        data = []
        for line in doc.lineas_movimientos_bancarios_ids:
            agregado = any(d['tipo'] == line.tipo for d in data)
            if not agregado:
                data.append({
                    'tipo': line.tipo,
                    'name': line.tipo.name,
                    'valor': line.valor,
                    'cantidad': 1
                })
            else:
                index = map(itemgetter('tipo'), data).index(line.tipo)
                data[index].update({
                    'valor': data[index]['valor'] + line.valor,
                    'cantidad': data[index]['cantidad'] + 1
                })
        return data

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'concilacion.bancaria',
            'docs': self.env['concilacion.bancaria'].browse(docids),
            'data': data,
            'get_total_lineas': self.get_total_lineas,
            'get_resumen_lineas': self.get_resumen_lineas,
        }
        return self.env['report'].render('elitum_contabilidad.reporte_concilacion_bancaria', docargs)


# MARZ
class ReporteCheque(models.AbstractModel):
    _name = 'report.elitum_contabilidad.reporte_cheque_matricial'

    def get_lugar_fecha(self, fecha):
        if fecha:
            ano = datetime.strptime(fecha, "%Y-%m-%d").year
            mes = self.env['hr.payslip'].get_mes(datetime.strptime(fecha, "%Y-%m-%d").month)
            dia = datetime.strptime(fecha, "%Y-%m-%d").day
            return "Guayaquil, " + str(dia) + " de " + mes + " del " + str(ano)

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'cheques.eliterp',
            'docs': self.env['cheques.eliterp'].browse(docids),
            'data': data,
            'get_amount_to_word': self.env['report.elitum_contabilidad.reporte_factura_cliente'].get_amount_to_word,
            'get_lugar_fecha': self.get_lugar_fecha,
        }
        return self.env['report'].render('elitum_contabilidad.reporte_cheque_matricial', docargs)
