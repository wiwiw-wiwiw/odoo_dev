from odoo import models, fields, api
from lxml import etree
import base64
from datetime import datetime

class BankStatImport(models.Model):
    _name = "bank.stat.import"
    _description = "Bank Statement Import"

    name = fields.Char(string='Наименование')
    date = fields.Date(string='Дата')
    amount = fields.Float(string='Сумма')


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Поиск партнера по названию из corrName
    @api.model
    def get_partner_id(self, corrName):
        """
        Получает ID партнера по имени. Если партнер не найден, создает нового.
        :param corrName: Имя контрагента из банковской выписки
        :return: ID партнера
        """
        partner = self.env['res.partner'].search([('name', '=', corrName)], limit=1)
        if not partner:
            # Е создаем нового партнера, если партнер не наден
            new_partner = self.env['res.partner'].create({'name': corrName})
            return new_partner.id
        return partner.id

    # Проверка существования счета партнера и банка
    @api.model
    def get_partner_bank_id(self, corrAccount, corrBankCode, corrBankName, partner_id):
        """
        Получает ID банковского счета партнера. Если счет или банк не существует, создает их.
        :param corrAccount: Номер счета партнера
        :param corrBankCode: BIC код банка
        :param corrBankName: Название банка
        :param partner_id: ID партнера
        :return: ID банковского счета партнера
        """
        # Поиск банковского счета партнера
        partner_bank = self.env['res.partner.bank'].search([
            ('acc_number', '=', corrAccount)
        ], limit=1)

        if partner_bank:
            return partner_bank.id
        else:
            # Проверка существования банка
            partner_bank_bank = self.env['res.bank'].search([
                ('bic', '=', corrBankCode)
            ], limit=1)

            # Создание нового банка, если он не найден
            if not partner_bank_bank:
                partner_bank_bank = self.env['res.bank'].create({
                    'name': corrBankName,
                    'bic': corrBankCode
                })

            # создание банковского счета партнера
            new_partner_bank = self.env['res.partner.bank'].create({
                'acc_number': corrAccount,
                'bank_id': partner_bank_bank.id,
                'partner_id': partner_id
            })

            return new_partner_bank.id

    # разбираем xml, создаем документ в одоо c транзакциями (или как их там, проводками, платежами)
    def create_document_from_attachment(self, attachment_ids):
        """
        Парсит XML файл с банковской выпиской и создает записи платежей на его основе.
        :param attachment_ids: ID вложений, содержащих XML файл
        """
        # Получение вложений по ID
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        for attachment in attachments:
            # Декодирование данных XML из формата Base64
            content_data = base64.b64decode(attachment.datas)
            xml_etree = etree.fromstring(content_data)

            # Поиск списка транзакций в XML
            extractList_elems = xml_etree.find("{*}extractList")
            i = 0  # Счетчик для тестирования и отладки
            for turn in extractList_elems.findall("{*}turns"):
                i += 1
                print(i)  # Отладочный вывод номера транзакции

                # Извлечение данных с обработкой отсутствующих значений
                crAmount = turn.find("{*}crAmount").text or '0'
                dbAmount = turn.find("{*}dbAmount").text or '0'
                naznText = turn.find("{*}naznText").text or ''
                docDate = turn.find("{*}docDate").text or ''

                # преобразование  даты в формат datetime.date
                date_only = datetime.strptime(docDate, "%Y-%m-%dT%H:%M:%S%z").date() if docDate else None

                # остальные данные......
                docN = turn.find("{*}docN").text or ''
                corrName = turn.find("{*}corrName").text or ''
                corrAccount = turn.find("{*}corrAccount").text or ''
                corrBankCode = turn.find("{*}corrBankCode").text or ''
                corrBankName_elem = turn.find("{*}corrBankName")
                corrBankName = corrBankName_elem.text if corrBankName_elem is not None else ''

                #  получение или создание ID партнера и банковского счета партнера
                partner_id = self.get_partner_id(corrName)
                partner_bank_id = self.get_partner_bank_id(corrAccount, corrBankCode, corrBankName, partner_id)

                #    извлечение значения TurnType для определения типа платежа
                turn_type_value = turn.find(".//addParams/entry[key='TurnType']/value")
                turn_type = turn_type_value.text if turn_type_value is not None else None

                # Установка типа платежа и суммы (правильно ли тут?)
                if turn_type == "DEBET":
                    payment_type = "outbound"
                    amount = float(dbAmount)
                elif turn_type == "CREDIT":
                    payment_type = "inbound"
                    amount = float(crAmount)
                else:
                    # Пропуск транзакции, если тип неизвестен (что делать с такими?)
                    continue

                # Формирование данных для создания платежа
                payment_data = {
                    'amount': amount,
                    'payment_type': payment_type,
                    'ref': naznText,
                    'date': date_only,
                    'partner_id': partner_id,
                    'partner_bank_id': partner_bank_id,
                }

                # Создание записи платежа, если сумма больше нуля (спросить нужно ли это)
                if amount > 0:
                    new_payment = self.env['account.payment'].create(payment_data)
                    print("PAYMENT DATA", payment_data)  # выводим в консоль данные по платежу

        # return  # Функция завершена (дописать, обновление страницы)
        return {
            'status': 'success',
            'statistics': stats.get_summary()
        }

"""

логирование некоректных данных в xml

добавить счетчики и вывести результат импорта выписки:
сетчик нулевых транзакциях
счетчик количестве дебетовых транзакций
счетчик количество кредитовых транзакци
счетчик успешно обработанные транзакции
счетчик неизвестных BIC кодов
счетчик новых банковских счетов
счетчик транзакций без назначения платежа
return {
            'name': _("Send"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move.send',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'default_mail_template_id': template and template.id or False,
            },
визард
передать аттачи в изард и дать пользователю выбрать банк (а может попытатьс угадать)
ок

"""

