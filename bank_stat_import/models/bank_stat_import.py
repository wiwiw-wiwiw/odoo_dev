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
    Этот класс отвечает за чтение вложенных файлов, выбор подходящего парсера,
    обработку транзакций и создание платежных записей.
    """
    _name = 'bank.statement.import'
    _description = 'Bank Statement Import'

    def create_document_from_attachment(self, attachment_ids, parser_type):
        """
        Обрабатывает файл банковской выписки и создает записи платежей.
        
        :param attachment_ids: Список ID вложений (ir.attachment).
        :param parser_type: Тип парсера ('BELBBY2X', 'AKBBBY2X').
        :return: Действие открытия созданных платежей или уведомление об ошибке.
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

            # Парсинг транзакций
            transactions = parser.parse(content_data)
            if not transactions:
                _logger.warning("Файл %s не содержит транзакций", attachment.name)
                return self._notify("Файл не содержит транзакций.", 'warning')

            # Обработка транзакций
            self._process_transactions(transactions, parser)

        # Успешный импорт
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

    def _process_transactions(self, transactions, parser):
        """
        Обрабатывает транзакции, создаёт партнёров, счета и платежи.
        """
        for transaction in transactions:
            processed = parser.process_transaction(transaction)
            _logger.debug("Обработка транзакции: %s", processed)

            partner_id = self._get_or_create_partner(processed['partner_name'])
            partner_bank_id = self._get_or_create_partner_bank(
                processed['partner_account'],
                processed['partner_bank_code'],
                processed['partner_bank_name'],
                partner_id
            )

            # Создание платежа
            payment_data = {
                'amount': processed['amount'],
                'payment_type': processed['payment_type'],
                'ref': processed['reference'],
                'date': processed['date'],
                'partner_id': partner_id,
                'partner_bank_id': partner_bank_id,
            }
            self.env['account.payment'].create(payment_data)
            _logger.info("Создан платёж: %s", payment_data)

    @api.model
    def _get_or_create_partner(self, partner_name):
        """
        Поиск или создание партнера по имени.
        """
        partner = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({'name': partner_name})
            _logger.info("Создан новый партнёр: %s", partner_name)
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
            bank = self.env['res.bank'].create({'name': bank_name or bank_code, 'bic': bank_code})
            _logger.info("Создан новый банк: %s (%s)", bank_name, bank_code)

        partner_bank = self.env['res.partner.bank'].create({
            'acc_number': account_number,
            'bank_id': bank.id,
            'partner_id': partner_id,
        })
        _logger.info("Создан банковский счёт: %s для партнёра %s", account_number, partner_id)
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
