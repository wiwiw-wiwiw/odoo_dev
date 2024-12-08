# bank_statement_import/models/bank_stat_import.py
# -*- coding: utf-8 -*-
from odoo import models, api, fields
from .statement_parsers import BankStatementParser_BELBBY2X, BankStatementParser_AKBBBY2X
import base64
import logging

_logger = logging.getLogger(__name__)

class BankStatImport(models.TransientModel):
    """
    TransientModel для обработки импорта банковских выписок.
    Отвечает за чтение вложенных файлов, выбор парсера,
    обработку транзакций и создание платежных записей.
    """
    _name = 'bank.statement.import'
    _description = 'Bank Statement Import'

    def create_document_from_attachment(self, attachment_ids, parser_type):
        """
        Обрабатывает файл банковской выписки и создает записи платежей.
        
        :param attachment_ids: Список ID вложений (ir.attachment)
        :param parser_type: Тип парсера ('BELBBY2X', 'AKBBBY2X')
        :return: Действие открытия созданных платежей или уведомление
        """
        attachments = self.env['ir.attachment'].browse(attachment_ids)

        # Проверка на наличие вложений
        if not attachments:
            raise ValueError("Вложения не найдены или отсутствуют.")

        for attachment in attachments:
            # Логика выбора парсера
            parser = self._get_parser(parser_type)

            # Декодирование содержимого файла
            try:
                content_data = base64.b64decode(attachment.datas)
                _logger.info("Файл %s успешно декодирован", attachment.name)
            except Exception as e:
                _logger.error("Ошибка декодирования файла %s: %s", attachment.name, str(e))
                raise ValueError("Ошибка декодирования файла.")

            # Парсинг транзакций с хэшами
            transactions_dict, transaction_hashes = parser.parse_and_process(content_data)
        
            # Фильтрация дубликатов
            filtered_transactions = self._filter_transactions(transactions_dict, transaction_hashes)
        
            if not filtered_transactions:
                _logger.warning("Файл %s не содержит новых транзакций", attachment.name)
                return self._notify("Файл не содержит новых транзакций.", 'warning')

            # Создание платежей
            self._create_payments_from_transactions(filtered_transactions)

        return self._notify("Импорт завершён успешно.", 'success')

    def _get_parser(self, parser_type):
        """
        Возвращает парсер на основе переданного типа.
        """
        parsers = {
            'BELBBY2X': BankStatementParser_BELBBY2X,
            'AKBBBY2X': BankStatementParser_AKBBBY2X,
        }
        parser_class = parsers.get(parser_type)
        if not parser_class:
            raise ValueError(f"Неподдерживаемый тип парсера: {parser_type}")
        return parser_class()

    def _filter_transactions(self, transactions_dict, transaction_hashes):
        """
        Фильтрация транзакций, исключая уже существующие в account.payments.
        
        :param transactions_dict: Словарь транзакций с хэшами в качестве ключей
        :param transaction_hashes: Список хэшей транзакций
        :return: Список словарей новых транзакций, готовых к загрузке
        """
        # Получаем существующие хэши из account.payments
        existing_hashes = self.env['account.payment'].search([
            ('transaction_hash', 'in', transaction_hashes)
        ]).mapped('transaction_hash')

        #print(existing_hashes)
    
        # Фильтруем транзакции: оставляем только новые
        filtered_transactions = [
            transaction 
            for hash_key, transaction in transactions_dict.items() 
            if hash_key not in existing_hashes
        ]

        #print(filtered_transactions)

        return filtered_transactions

    def _create_payments_from_transactions(self, transactions):
        """
        Создание платежей из отфильтрованных транзакций.
        
        :param transactions: Список транзакций для создания
        """
        payment_data = []

        for transaction in transactions:
            partner_id = self._get_or_create_partner(transaction['partner_name'])
            partner_bank_id = self._get_or_create_partner_bank(
                transaction.get('partner_account', ''),
                transaction.get('partner_bank_code', ''),
                transaction.get('partner_bank_name', ''),
                partner_id
            )

            payment_data.append({
                'amount': transaction['amount'],
                'payment_type': transaction['payment_type'],
                'ref': transaction['reference'],
                'date': transaction['date'],
                'partner_id': partner_id,
                'partner_bank_id': partner_bank_id,
                'transaction_hash': transaction['transaction_hash'],
            })
        #print(payment_data)
        if payment_data:
            self.env['account.payment'].create(payment_data)

    @api.model
    def _get_or_create_partner(self, partner_name):
        """
        Поиск или создание партнера по имени.
        """
        partner = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({'name': partner_name})
        return partner.id

    @api.model
    def _get_or_create_partner_bank(self, account_number, bank_code, bank_name, partner_id):
        """
        Поиск или создание банковского счета партнёра.
        """
        partner_bank = self.env['res.partner.bank'].search([('acc_number', '=', account_number)], limit=1)
        if partner_bank:
            return partner_bank.id

        bank = self.env['res.bank'].search([('bic', '=', bank_code)], limit=1)
        if not bank:
            bank = self.env['res.bank'].create({
                'name': bank_name or bank_code, 
                'bic': bank_code
            })

        partner_bank = self.env['res.partner.bank'].create({
            'acc_number': account_number,
            'bank_id': bank.id,
            'partner_id': partner_id,
        })
        return partner_bank.id

    def _notify(self, message, message_type):
        """
        Генерирует уведомление для интерфейса Odoo.
        """
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Уведомление',
                'message': message,
                'type': message_type,
                'sticky': False,
            },
        }