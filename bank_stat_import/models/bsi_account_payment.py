# -*- coding: utf-8 -*-
from odoo import models, fields, api
import hashlib

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    transaction_hash = fields.Char(
        string='Хэш транзакции', 
        index=True, 
        help='Уникальный хэш для идентификации и предотвращения дублей транзакций',
        copy=False
    )

    @api.model
    def _generate_transaction_hash(self, date, amount, reference):
        """
        Генерация хэша транзакции.
        
        Args:
            date (date): Дата транзакции
            amount (float): Сумма транзакции
            reference (str): Назначение платежа
        
        Returns:
            str: Сгенерированный хэш транзакции
        """
        # Преобразование входных данных в строку
        hash_string = f"{date}|{amount}|{reference}"
        
        # Использование SHA-256 для более надежного хэширования
        return hashlib.sha256(hash_string.encode()).hexdigest()

    @api.model
    def _check_transaction_duplicate(self, transaction_hash):
        """
        Проверка наличия платежа с таким хэшем.
        
        Args:
            transaction_hash (str): Хэш транзакции для проверки
        
        Returns:
            bool: True, если дубликат найден, иначе False
        """
        existing_payment = self.search([
            ('transaction_hash', '=', transaction_hash)
        ], limit=1)
        
        return bool(existing_payment)