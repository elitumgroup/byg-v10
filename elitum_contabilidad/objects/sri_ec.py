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
from odoo.exceptions import UserError, ValidationError


# MARZ
class TablaImpuestoRenta(models.Model):
    _name = 'eliterp.tabla.impuesto.renta'

    _description = 'Tabla del Impuesto a la Renta'

    @api.multi
    def name_get(self):
        res = []
        for data in self:
            res.append((data.id, "Registro %s" % (data.id)))
        return res

    fraccion_basica = fields.Float(required=True)
    exceso_hasta = fields.Float(required=True)
    impuesto_fraccion_basica = fields.Float(required=True)
    impuesto_fraccion_excedente = fields.Float(required=True)
    status = fields.Boolean(default=True)


class EliterpTipoDocumento(models.Model):
    _name = 'eliterp.type.document'

    _description = 'Tipos de Documento ATS'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string=u'Código', size=2, required=True)
    sustento_ids = fields.Many2many('sustento.tributario',
                                    'rel_type_document_sustento_ids',
                                    'type_document_id',
                                    'sustento_tributario_id',
                                    'Sustentos Tributarios')
    status = fields.Boolean(default=True)


class SustentoTributario(models.Model):
    _name = 'sustento.tributario'

    _description = 'Sustento Tributario'

    name = fields.Char('Nombre', required=True)
    codigo = fields.Char(u'Código', required=True)


class AutorizacionSri(models.Model):
    _name = 'autorizacion.sri'

    _description = u'Autorización SRI'

    @api.multi
    def name_get(self):
        res = []
        for data in self:
            res.append((data.id, "%s - %s" % (data.tipo_comprobante.name, data.numero_autorizacion)))
        return res

    def _check_autorizacion(self, values):
        """
        Verificar no exista una autorización anterior activa
        :param values:
        :return:
        """
        domain = [
            ('code_comprobante', '=', values['code_comprobante']),
            ('numero_establecimiento', '=', values['numero_establecimiento']),
            ('punto_emision', '=', values['punto_emision']),
            ('state', '=', 'activo')
        ]
        result = self.search(domain)
        if result:
            raise UserError("Ya existe una autorización activa para tipo de documento.")
        else:
            return

    @api.model
    def create(self, values):
        self._check_autorizacion(values)
        if values['code_comprobante'] == '07': # Para retenciones
            numero = values['numero_autorizacion']
            new_sequence_withhold = self.env['ir.sequence'].create({'name': u"Retención" + "-" + numero,
                                                                    'code': values['numero_autorizacion'],
                                                                    'prefix': values['numero_establecimiento'] + "-" +
                                                                              values['punto_emision'] + "-",
                                                                    'padding': 9
                                                                    })
            values.update({'sequence_id': new_sequence_withhold.id})
        return super(AutorizacionSri, self).create(values)

    @api.constrains('secuencial_fin')
    def _check_secuencial_fin(self):
        if self.secuencial_fin <= self.secuencial_inico:
            raise ValidationError("Secuencia fin no puede ser menor a la de inicio.")

    @api.onchange('secuencial_inico')
    def _onchange_secuencial_inico(self):
        if self.secuencial_inico:
            if self.code_comprobante == '18':
                self.secuencia = self.secuencial_inico

    @api.multi
    def _update_state(self):
        self.write({'state': 'terminado'})

    numero_establecimiento = fields.Char('No. Establecimiento', size=3, required=True)
    punto_emision = fields.Char('Punto Emisión', size=3, required=True)
    secuencial_inico = fields.Integer(u'Secuencial Inicio', size=9, required=True)
    secuencial_fin = fields.Integer(u'Secuencial Fin', size=9, required=True)
    secuencia = fields.Integer('Próximo No.')
    numero_autorizacion = fields.Char('No. Autorización', required=True, size=10)
    tipo_comprobante = fields.Many2one('eliterp.type.document', 'Tipo Documento', required=True)
    code_comprobante = fields.Char(related='tipo_comprobante.code', string=u'Código')
    state = fields.Selection([('activo', 'Activo'),
                              ('terminado', 'Terminada')], string="Estado", default='activo')
    sequence_id = fields.Many2one('ir.sequence', 'Secuencia')


class AccountJournalPaymentMethod(models.Model):
    _name = 'account.journal.payment.method'

    _description = u'Forma de Pago'

    @api.multi
    def name_get(self):
        res = []
        name_code = []
        for name in self:
            name_code = []
            name_code.append(name.id)
            name_code.append(name.code + " - " + name.name)
            res.append(name_code)
        return res

    code = fields.Char('Código')
    prioridad = fields.Integer('Prioridad')
    name = fields.Char('Nombre')


class CreditoTributario(models.Model):
    _name = 'credito.tributario'

    _description = u'Crédito Tributario'

    @api.multi
    def name_get(self):
        res = []
        name_code = []
        for name in self:
            name_code = []
            name_code.append(name.id)
            name_code.append(u"Crédito de " + name.ano_contable.name + " - " + name.period_id.name)
            res.append(name_code)
        return res

    name = fields.Char('Nombre')
    ano_contable = fields.Many2one(
        'account.period',
        u'Año Contable',
        required=True
    )
    period_id = fields.Many2one(
        'lines.account.period',
        'Período',
        required=True
    )
    mes = fields.Integer(related="period_id.code", store=True)
    ano = fields.Integer(related="ano_contable.ano_contable", store=True)
    valor = fields.Float("Valor IVA", required=True)
    valor_renta = fields.Float(u"Valor Retención IVA", required=True)
    novedades = fields.Text(string='Novedades')
