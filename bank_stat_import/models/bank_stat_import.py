# -*- coding: utf-8 -*-

from odoo import models, api, fields
from .statement_parsers import BankStatementParser_BELBBY2X, BankStatementParser_AKBBBY2X
import base64
import logging

_logger = logging.getLogger(__name__)

class BankStatImport(models.TransientModel):
    """
    TransientModel для обработки импорта банковских выписок. Этот класс отвечает
    за чтение вложенных файлов, выбор подходящего парсера на основе переданного типа,
    обработку транзакций и создание платежных записей в системе.
    """
    _name = 'bank.statement.import'
    _description = 'Bank Statement Import'

    def create_document_from_attachment(self, attachment_ids, parser_type):
        """
        Обрабатывает файл банковской выписки и создает записи платежей.

        :param attachment_ids: список ID вложений (ir.attachment), содержащих файл выписки.
        :param parser_type: строка, определяющая тип парсера для обработки файла. 
                            Поддерживаемые значения: 'BELBBY2X', 'AKBBBY2X'.

        Алгоритм работы:
        1. Получение вложений из модели ir.attachment.
        2. Декодирование данных из файлов.
        3. Выбор подходящего парсера на основе parser_type.
        4. Парсинг содержимого файла в список транзакций.
        5. Обработка транзакций: создание платежей, партнёров и их банковских счетов.

        Ожидаемый формат входных данных:
        - XML-файлы в формате, соответствующем документации к парсерам.
        """
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        for attachment in attachments:
            # Выбор парсера на основе переданного типа
            if parser_type == 'BELBBY2X':
                parser = BankStatementParser_BELBBY2X()
            elif parser_type == 'AKBBBY2X':
                parser = BankStatementParser_AKBBBY2X()
            else:
                raise ValueError("Неподдерживаемый тип парсера")

            # Декодирование содержимого файла
            content_data = base64.b64decode(attachment.datas)
         #   _logger.info("Начало парсинга файла: %s", attachment.name)
            transactions = parser.parse(content_data)

            if not transactions:
                # Если транзакции не найдены, вывести уведомление
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Внимание',
                        'message': 'Файл не содержит транзакций',
                        'type': 'warning',
                        'sticky': False,
                    }
                }

            # Обработка транзакций
            for transaction in transactions:
                processed_transaction = parser.process_transaction(transaction)
            #    _logger.debug("Обработка транзакции: %s", processed_transaction)

                # Поиск или создание партнера
                partner_id = self._get_partner_id(processed_transaction['partner_name'])

                # Поиск или создание банковского счета партнера
                partner_bank_id = self._get_partner_bank_id(
                    processed_transaction['partner_account'],
                    processed_transaction['partner_bank_code'],
                    processed_transaction['partner_bank_name'],
                    partner_id
                )

                # Создание платежа
                payment_data = {
                    'amount': processed_transaction['amount'],
                    'payment_type': processed_transaction['payment_type'],
                    'ref': processed_transaction['reference'],
                    'date': processed_transaction['date'],
                    'partner_id': partner_id,
                    'partner_bank_id': partner_bank_id,
                }
               # _logger.info("Создание платежа с данными: %s", payment_data)
                self.env['account.payment'].create(payment_data)

        # Возвращаем действие для открытия платежей
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('partner_bank_id', '!=', False)],
        }

    @api.model
    def _get_partner_id(self, partner_name):
        """
        Поиск или создание партнера по имени.

        :param partner_name: Имя партнера.
        :return: ID найденного или созданного партнера.
        """
        partner = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({'name': partner_name})
        return partner.id

    @api.model
    def _get_partner_bank_id(self, account_number, bank_code, bank_name, partner_id):
        """
        Поиск или создание банковского счета партнера.

        :param account_number: Номер счета партнера.
        :param bank_code: Код банка партнера (например, BIC).
        :param bank_name: Название банка партнера.
        :param partner_id: ID партнера в системе.
        :return: ID найденного или созданного банковского счета партнера.
        """
        # Поиск существующего банковского счета
        partner_bank = self.env['res.partner.bank'].search([('acc_number', '=', account_number)], limit=1)
        if partner_bank:
            return partner_bank.id

        # Поиск или создание записи банка
        bank = self.env['res.bank'].search([('bic', '=', bank_code)], limit=1)
        if not bank:
            bank = self.env['res.bank'].create({'name': bank_name or bank_code, 'bic': bank_code})

        # Создание банковского счета партнера
        partner_bank = self.env['res.partner.bank'].create({
            'acc_number': account_number,
            'bank_id': bank.id,
            'partner_id': partner_id,
        })
        return partner_bank.id
