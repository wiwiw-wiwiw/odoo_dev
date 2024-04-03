from odoo import models, fields, api
from lxml import etree
import xml.etree.ElementTree as ET
import base64



class BankStatImport(models.Model):
    _name = "bank.stat.import"
    _description = "bank stat import"

    name = fields.Char(string='Наименование')
    date = fields.Date(string='Дата')
    amount = fields.Float(string='Сумма')

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def create_document_from_attachment(self, attachment_ids):
        # print("**create_document_from_attachment**")
        # print("attachment_ids:", attachment_ids)

        attachments = self.env['ir.attachment'].browse(attachment_ids)
        for attachment in attachments:
            # print("**attachment**")
            # print("name:", attachment.name)

            content_data = base64.b64decode(attachment.datas)
            xml_etree = etree.fromstring(content_data)

            extractList_elems = xml_etree.find("{*}extractList")
            # print(extractList_elems)

            for turn in extractList_elems.findall("{*}turns"):
                crAmount = turn.find("{*}crAmount").text
                naznText = turn.find("{*}naznText").text
                # print("crAmount", crAmount, "naznText", naznText)

                payment_data = {
                    'amount': crAmount, 
                    'ref': naznText
                    }
                new_payment = self.env['account.payment'].create(payment_data)
                print("PAYMENT DATA", payment_data)
            
               
        return {
            # 'type': 'ir.actions.act_window',
            # 'name': 'Vendor Payments',
            # 'view_mode': 'tree,form',
            # 'res_model': 'account.payment',
            # 'target': 'current',
            
            # 'domain': ["&", ("partner_type", "=", "supplier"), ("is_internal_transfer", "=", False)],
        }
