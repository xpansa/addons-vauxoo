# -*- encoding: utf-8 -*-
###########################################################################
#    Module Writen to OpenERP, Open Source Management Solution
#
#    Copyright (c) 2011 Vauxoo - http://www.vauxoo.com
#    All Rights Reserved.
#    info moylop260 (moylop260@vauxoo.com)
############################################################################
#    Coded by: moylop260 (moylop260@vauxoo.com)
#    Coded by: isaac (isaac@vauxoo.com)
#    Financed by: http://www.sfsoluciones.com (aef@sfsoluciones.com)
############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
import wizard
import netsvc
import pooler
import time
import base64
import StringIO
import csv
import tempfile
import os
import sys
import codecs
from tools.misc import ustr
try:
    from SOAPpy import WSDL
except:
    print "Package SOAPpy missed"
    pass
import time


class wizard_cancel_invoice_pac_sf(osv.osv_memory):
    _name='wizard.cancel.invoice.pac.sf'

    def sf_cancel(self, cr, uid, ids, context=None):
        print 'esta dentro del cancel'
        user = 'testing@solucionfactible.com'
        password = 'timbrado.SF.16672'

        context_id=context.get('active_ids',[])
        print context_id
        print 'context= ',context

        invoice_obj = self.pool.get('account.invoice')
        company_obj = self.pool.get('res.company.facturae.certificate')
        invoice_brw = invoice_obj.browse(cr, uid, context_id, context)[0]
        company_brw = company_obj.browse(cr, uid, [invoice_brw.company_id.id], context)[0]
        print 'el invoice_brw',invoice_brw

        #~ params=[user, password, cfdi, cerCSD, keyCSD, contrasenaCSD, zip]
        print 'company_id es: ',invoice_brw.company_id.id

        cerCSD = company_brw.certificate_file#base64.encodestring(company_brw.certificate_file)
        keyCSD = company_brw.certificate_key_file#base64.encodestring(company_brw.certificate_key_file)
        contrasenaCSD = company_brw.certificate_password
        uuids = invoice_brw.cfdi_folio_fiscal#cfdi_folio_fiscal

        print 'el certificate file es: ',cerCSD
        print 'el certificate key file es: ',keyCSD
        print 'el certificate password es: ',contrasenaCSD
        print 'el uuids folio fiscal es: ',uuids


        print '----------------------------inicia envio a pac-------------------------------'

        #~ wsdl_url = 'http://testing.solucionfactible.com/ws/services/TimbradoCFD?wsdl'  moy
        #~ wsdl_url='http://testing.solucionfactible.com/cfdi/timbrado/test/timbrado.jsp'
        wsdl_url = 'http://testing.solucionfactible.com/ws/services/Timbrado?wsdl'
        namespace = 'http://timbrado.ws.cfdi.solucionfactible.com'

        wsdl_client = False
        #try:
        #wsdl_client = WSDL.Proxy( wsdl_url, namespace )
        wsdl_client = WSDL.SOAPProxy( wsdl_url, namespace )
        #except:
            #pass
        if True:#if wsdl_client:
            params = [user, password, uuids, cerCSD, keyCSD, contrasenaCSD ]
            print '-----------------inicia llamado al web service'
            wsdl_client.soapproxy.config.dumpSOAPOut = 0
            wsdl_client.soapproxy.config.dumpSOAPIn = 0
            wsdl_client.soapproxy.config.debug = 0
            wsdl_client.soapproxy.config.dict_encoding='UTF-8'
            print 'antes de obtener resultado params es: ',params
            resultado = wsdl_client.cancelar(*params)
            print "-------------------resultado:",resultado
            #~ msg = resultado['resultados']['mensaje']
            #~ status = resultado['resultados']['status']
            print "--------------El resultado es: ",resultado



        return{}
    """
    def _get_file(self, cr, uid, data, context={}):
        if not context:
            context = {}
        #context.update( {'date': data['form']['date']} )
        pool = pooler.get_pool(cr.dbname)
        invoice_obj = pool.get('account.invoice')
        ids = data['ids']
        id = ids[0]
        invoice = invoice_obj.browse(cr, uid, [id], context=context)[0]
        fname_invoice = invoice.fname_invoice and invoice.fname_invoice + '.xml' or ''
        aids = pool.get('ir.attachment').search(cr, uid, [('datas_fname','=',invoice.fname_invoice+'.xml'),('res_model','=','account.invoice'),('res_id','=',id)])
        xml_data = ""
        if aids:
            brow_rec = pool.get('ir.attachment').browse(cr, uid, aids[0])
            if brow_rec.datas:
                xml_data = base64.decodestring(brow_rec.datas)
        else:
            fname, xml_data = invoice_obj._get_facturae_invoice_xml_data(cr, uid, ids, context=context)
            pool.get('ir.attachment').create(cr, uid, {
                    'name': fname_invoice,
                    'datas': base64.encodestring(xml_data),
                    'datas_fname': fname_invoice,
                    'res_model': 'account.invoice',
                    'res_id': invoice.id,
                }, context=context)

        fdata = base64.encodestring( xml_data )
        msg = "Presiona clic en el boton 'subir archivo'"
        return {'file': fdata, 'fname': fname_invoice, 'msg': msg}

    def SF_Cancel(self, cr, uid, ids, context={}):
        pool = pooler.get_pool(cr.dbname)
        invoice_obj = pool.get('account.invoice')
        #invoice_obj = self.pool.get('account.invoice')
        data = self.read(cr, uid, ids)[0]
        cfd_data = base64.decodestring( data['file'] or '' )
        invoice_ids = context.get('active_ids',[]),
        invoice = invoice_obj.browse(cr, uid, invoice_ids, context=context)[0]
        msg = 'no se pudo subir el archivo'
        if cfd_data:
            #wsdl_url = 'http://testing.solucionfactible.com/ws/services/Timbrado?wsdl'###Agregarlo a un modelo dinamico
            wsdl_url = 'http://testing.solucionfactible.com/ws/services/TimbradoCFD?wsdl'
            namespace = 'http://timbradocfd.ws.cfdi.solucionfactible.com'
            wsdl_client = False
            #try:
            #wsdl_client = WSDL.Proxy( wsdl_url, namespace )
            wsdl_client = WSDL.SOAPProxy( wsdl_url, namespace )
            #except:
                #pass
            if True:#if wsdl_client:
                user = 'testing@solucionfactible.com'
                password = 'timbrado.SF.16672'
                file_globals = invoice_obj._get_file_globals(cr, uid, invoice_ids, context=context)
                fname_cer_no_pem = file_globals['fname_cer']
                cerCSD = fname_cer_no_pem and base64.encodestring( open(fname_cer_no_pem, "r" ).read() ) or ''
                fname_key_no_pem = file_globals['fname_key']
                keyCSD = fname_key_no_pem and base64.encodestring( open(fname_key_no_pem, "r" ).read() ) or ''
                cfdi = base64.encodestring( cfd_data.replace(codecs.BOM_UTF8,'') )
                zip = False#Validar si es un comprimido zip, con la extension del archivo
                contrasenaCSD = file_globals.get('password', '')
                params = [user, password, cfdi, cerCSD, keyCSD, contrasenaCSD, zip]
                wsdl_client.soapproxy.config.dumpSOAPOut = 0
                wsdl_client.soapproxy.config.dumpSOAPIn = 0
                wsdl_client.soapproxy.config.debug = 0
                wsdl_client.soapproxy.config.dict_encoding='UTF-8'
                resultado = wsdl_client.timbrar(*params)
                print "resultado",resultado
                msg = resultado['resultados']['mensaje']
                status = resultado['resultados']['status']
                print "[status]",[status]
                if status == '200' or status == '307':
                    fecha_timbrado = resultado['resultados']['fechaTimbrado'] or False
                    fecha_timbrado = fecha_timbrado and time.strftime('%Y-%m-%d %H:%M:%S', time.strptime(fecha_timbrado[:19], '%Y-%m-%dT%H:%M:%S')) or False
                    cfdi_data = {
                        #'cfdi_cbb': base64.decodestring( resultado['resultados']['qrCode'] or '' ) or False,
                        'cfdi_cbb': resultado['resultados']['qrCode'] or False,#ya lo regresa en base64
                        'cfdi_sello': resultado['resultados']['selloSAT'] or False,
                        'cfdi_no_certificado': resultado['resultados']['certificadoSAT'] or False,
                        'cfdi_cadena_original': resultado['resultados']['cadenaOriginal'] or False,
                        'cfdi_fecha_timbrado': fecha_timbrado,
                        'cfdi_xml': base64.decodestring( resultado['resultados']['cfdiTimbrado'] or '' ),#este se necesita en uno que no es base64
                        'cfdi_folio_fiscal': resultado['resultados']['uuid'] or '' ,
                    }
                    invoice_obj.cfdi_data_write(cr, uid, [invoice.id], cfdi_data, context=context)
                    msg = msg + "\nAsegurese de que su archivo realmente haya sido generado correctamente ante el SAT\nhttps://www.consulta.sat.gob.mx/sicofi_web/moduloECFD_plus/ValidadorCFDI/Validador%20cfdi.html"
                    #open("D:\\cfdi_b64.xml", "wb").write( resultado['resultados']['cfdiTimbrado'] or '' )
                    #open("D:\\cfdi.xml", "wb").write( base64.decodestring( resultado['resultados']['cfdiTimbrado'] or '' ) )
                elif status == '500':#documento no es un cfd version 2, probablemente ya es un CFD version 3
                    msg = "Probablemente el archivo XML ya ha sido timbrado previamente y no es necesario volverlo a subir.\nO puede ser que el formato del archivo, no es el correcto.\nPor favor, visualice el archivo para corroborarlo y seguir con el siguiente paso o comuniquese con su administrador del sistema."
        return {'file': data['file'], 'msg': msg}
    """
wizard_cancel_invoice_pac_sf()

