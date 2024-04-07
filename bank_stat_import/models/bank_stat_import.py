from odoo import models, fields, api
from lxml import etree
import xml.etree.ElementTree as ET
import base64
from datetime import datetime


class BankStatImport(models.Model):
    _name = "bank.stat.import"
    _description = "bank stat import"

    name = fields.Char(string='Наименование')
    date = fields.Date(string='Дата')
    amount = fields.Float(string='Сумма')


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # поиск партнера
    @api.model
    def get_partner_id(self, corrName):
        partner = self.env['res.partner'].search(
            [('name', '=', corrName)], limit=1)
        if not partner:
            # Если партнер не найден, создаем нового партнера
            new_partner = self.env['res.partner'].create({'name': corrName})
            return new_partner.id
        else:
            return partner.id

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
            i = 0
            # print("Step 2 extractList_elems", extractList_elems)
            for turn in extractList_elems.findall("{*}turns"):
                # print("step 3 turn ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||", turn)
                i = i+1
                print(i)
                crAmount = turn.find("{*}crAmount").text
                dbAmount = turn.find("{*}dbAmount").text
                naznText = turn.find("{*}naznText").text
                docDate = turn.find("{*}docDate").text

                date_object = datetime.strptime(docDate, "%Y-%m-%dT%H:%M:%S%z")
                date_only = date_object.date()

                docN = turn.find("{*}docN").text
                corrName = turn.find("{*}corrName").text
                corrAccount = turn.find("{*}corrAccount").text
                corrBankCode = turn.find("{*}corrBankCode").text
                # corrBankName = turn.find("{*}corrBankName").text

                partner_id = self.get_partner_id(corrName)

                print("partner_id ::::: ", partner_id)

                # print("corrName:", corrName)
                # Извлечение значения TurnType
                turn_type_value = turn.find(
                    ".//addParams/entry[key='TurnType']/value")
                turn_type = turn_type_value.text if turn_type_value is not None else None

                # формирование payment_data

                if turn_type == "DEBET":
                    payment_type = "outbound"
                    amount = dbAmount
                elif turn_type == "CREDIT":
                    payment_type = "inbound"
                    amount = crAmount

                payment_data = {
                    # 'turn_type': turn_type, # test
                    'amount': amount,  # сумма
                    'payment_type': payment_type,  # Send or Receive
                    # 'crAmount': crAmount, # test
                    # 'dbAmount': dbAmount, # test
                    'ref': naznText,  # комментарий - назначение платежа
                    'date': date_only,  # дата
                    'partner_id': partner_id,






                }
                # создание платежа
                new_payment = self.env['account.payment'].create(payment_data)
                print("PAYMENT DATA", payment_data)
    # action_vals = {
    # 'type': "ir.actions.act_window",
    # 'name': "Vendor Payments",
    # 'view_mode': "tree,form",
    # 'res_model': "account.payment",
    # 'target': "current",

    # 'domain': ["&", ("partner_type", "=", "supplier"), ("is_internal_transfer", "=", False)],
    #         }

        return  # action_vals
