# bank_statement_import/models/statement_parsers.py

# -*- coding: utf-8 -*-
from lxml import etree
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class BaseStatementParser:
    """
    Базовый класс парсера банковской выписки. Все конкретные парсеры должны наследоваться от него.
    
    Методы:
        - parse(content): метод для разбора данных, должен быть реализован в подклассах.
        - process_transaction(transaction): обработка отдельной транзакции, определяется в подклассах.
    """
    def parse(self, content):
        """
        Разбор входного контента банковской выписки.
        :param content: Данные файла в формате строки (например, XML или другой текстовый формат).
        :return: Список транзакций (формат определяется подклассом).
        """
        raise NotImplementedError("Подклассы должны реализовать этот метод")

    def process_transaction(self, transaction):
        """
        Обработка отдельной транзакции из выписки.
        :param transaction: Словарь с данными транзакции, полученный из метода parse().
        :return: Обработанная транзакция в универсальном формате.
        """
        raise NotImplementedError("Подклассы должны реализовать этот метод")


class BankStatementParser_BELBBY2X(BaseStatementParser):
    """
    Парсер для обработки банковских выписок ОАО "Банк БелВЭБ".
    
    Формат XML-файла (пример):
    <extractList>
        <turns>
            <docDate>2023-11-25T10:00:00+0300</docDate>
            <crAmount>100.00</crAmount>
            <dbAmount>0.00</dbAmount>
            <naznText>Оплата услуг</naznText>
            <corrName>ООО "Ромашка"</corrName>
            <corrAccount>30120123456789000123</corrAccount>
            <corrBankCode>BELBBY2X</corrBankCode>
            <corrBankName>Банк БелВЭБ</corrBankName>
            <turnType>DEBET</turnType>
        </turns>
    </extractList>
    """
    def parse(self, content):
        xml_etree = etree.fromstring(content)
        transactions = []
        extract_list_elems = xml_etree.find("{*}extractList")
        if extract_list_elems is not None:
            for turn in extract_list_elems.findall("{*}turns"):
                transaction = {
                    'crAmount': turn.findtext("{*}crAmount") or '0',
                    'dbAmount': turn.findtext("{*}dbAmount") or '0',
                    'naznText': turn.findtext("{*}naznText") or '',
                    'docDate': turn.findtext("{*}docDate") or '',
                    'corrName': turn.findtext("{*}corrName") or '',
                    'corrAccount': turn.findtext("{*}corrAccount") or '',
                    'corrBankCode': turn.findtext("{*}corrBankCode") or '',
                    'corrBankName': turn.findtext("{*}corrBankName") or '',
                    'turnType': turn.findtext(".//addParams/entry[key='TurnType']/value") or ''
                }
                transactions.append(transaction)
        return transactions

    def process_transaction(self, transaction):
        """
        Преобразует транзакцию из формата банка БелВЭБ в универсальный формат.
        """
        return {
            'date': datetime.strptime(transaction['docDate'], "%Y-%m-%dT%H:%M:%S%z").date() if transaction['docDate'] else None,
            'amount': float(transaction['dbAmount'] if transaction['turnType'] == "DEBET" else transaction['crAmount']),
            'payment_type': 'outbound' if transaction['turnType'] == "DEBET" else 'inbound',
            'partner_name': transaction['corrName'],
            'partner_account': transaction['corrAccount'],
            'partner_bank_code': transaction['corrBankCode'],
            'partner_bank_name': transaction['corrBankName'],
            'reference': transaction['naznText'],
        }


class BankStatementParser_AKBBBY2X(BaseStatementParser):
    """
    Парсер для обработки банковских выписок АСБ Беларусбанк.
    
    Формат XML-файла (пример):
    <ACCOUNTINFO>
        <ACCOUNT>30120123456789000123</ACCOUNT>
        <CURRENCY Iso="BYN"/>
        <TIMETURN date="25.11.2023"/>
        <OPER>
            <OPERUID>12345</OPERUID>
            <DOCN>INV-2023-001</DOCN>
            <MFOKORR>AKBBBY2X</MFOKORR>
            <ACCKORR>30120123456789000456</ACCKORR>
            <NAMEKORR>ООО "Снежинка"</NAMEKORR>
            <SUMOPER nd="0.00" nk="200.00"/>
            <DETPAY>Оплата товара</DETPAY>
            <VO>123</VO>
        </OPER>
    </ACCOUNTINFO>
    """
    def parse(self, content):
        xml_etree = etree.fromstring(content)
        transactions = []
        for account_info in xml_etree.findall('.//ACCOUNTINFO'):
            account = account_info.findtext('ACCOUNT')
            currency = account_info.find('CURRENCY').get('Iso')
            date = account_info.find('TIMETURN').get('date')

            for oper in account_info.findall('.//OPER'):
                transaction = {
                    'account': account,
                    'currency': currency,
                    'operuid': oper.findtext('OPERUID'),
                    'docN': oper.findtext('DOCN'),
                    'mfokorr': oper.findtext('MFOKORR'),
                    'acckorr': oper.findtext('ACCKORR'),
                    'namekorr': oper.findtext('NAMEKORR'),
                    'dbAmount': oper.find('SUMOPER').get('nd') or '0',
                    'crAmount': oper.find('SUMOPER').get('nk') or '0',
                    'detpay': oper.findtext('DETPAY'),
                    'docDate': date,
                    
                }
                transactions.append(transaction)
        return transactions




    def process_transaction(self, transaction):
        """
        Преобразует транзакцию из формата Беларусбанк в универсальный формат.
        """
   
        payment_type = 'outbound' if float(transaction['dbAmount']) > 0 else 'inbound'
        if payment_type == "outbound":
            amount = float(transaction['dbAmount'])
        if payment_type == "inbound":
            amount = float(transaction['crAmount'])
        
        record_data =  {
            'date': datetime.strptime(transaction['docDate'], "%d.%m.%Y").date() if transaction['docDate'] else None,
            'payment_type': payment_type,
            'amount': amount,
            'partner_name': transaction['namekorr'],
            'partner_account': transaction['acckorr'],
            'partner_bank_code': transaction['mfokorr'],
            'partner_bank_name': '',
            'reference': transaction['detpay'],
            'currency': transaction['currency'],
            
        }
        print("recored_data", record_data)
        return record_data
