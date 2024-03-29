import xml.etree.ElementTree as ET
from odoo import models
from odoo import models, fields, api
import base64
from lxml import etree
import logging

# Создание логгера для текущего модуля
_logger = logging.getLogger(__name__)

# Установка уровня логирования на DEBUG для вывода всех сообщений
_logger.setLevel(logging.DEBUG)

# Создание обработчика для вывода сообщений в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Определение формата сообщений
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Добавление обработчика к логгеру
_logger.addHandler(console_handler)


class BankStatImport(models.Model):
    _name = "bank.stat.import"
    _description = "bank stat import"

    name = fields.Char(string='Наименование')
    date = fields.Date(string='Дата')
    amount = fields.Float(string='Сумма')


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def create_document_from_attachment(self, attachment_ids):
        try:
            for attachment_id in attachment_ids:
                attachment = self.env['ir.attachment'].browse(attachment_id)
                try:
                    # Декодирование данных из формата base64
                    decoded_data = base64.b64decode(attachment.datas)

                    # Попытка декодировать данные с использованием UTF-8
                    try:
                        string_content = decoded_data.decode("utf-8")
                        # Вывод результатов парсинга в консоль
                        print("Parsed content of attachment:", string_content)
                        
                    except UnicodeDecodeError:
                        # Если возникает ошибка с кодировкой
                        print(f"error decoding file - {attachment.name} with UTF-8 encoding")

                        # Пропустить обработку данного файла
                        continue

                    

                    try:
                           

                        # Парсинг XML-данных с использованием xml.etree.ElementTree
                        xml_tree = ET.fromstring(string_content)
                        print(xml_tree)

                        # Находим все элементы TotalDeb
                        # total_deb_elements = xml_tree.findall(".//entry[key = 'TotalDeb']/value")

                        total_deb_elements = xml_tree.findall(
                            ".//descBalance/extractList/additionalParams/entry[key='TotalDeb']/value")




                        # Проверяем, нашлись ли элементы
                        if total_deb_elements:
                            print("Элементы TotalDeb найдены в дереве.")
                        else:
                            print("Элементы TotalDeb не найдены в дереве.")    
                        # Обрабатываем каждый найденный элемент TotalDeb



                        
                        for total_deb_element in total_deb_elements:
                            # Получаем значение элемента Value внутри TotalDeb
                            amount = float(
                                total_deb_element.find('value').text)

                            # Создаем запись в account.payment с найденной суммой
                            payment_data = {
                                'amount': amount,
                                # словарь  для создания записи
                            }
                            new_payment = self.create(payment_data)
                            # Выводим информацию о созданной записи в консоль
                            print("Created payment with amount:", amount)
                    except Exception as e:
                        _logger.exception("An error occurred: %s", e)

                    # TODO: Обработка данных
                except Exception as e:
                    _logger.exception("An error occurred: %s", e)
                    # print(f"Error processing file {attachment.name}: {e}")
        except Exception as e:
            _logger.exception("An error occurred: %s", e)
            # print(f"Error processing attachments: {e}")
        # return self.env.ref('base.action_res_users').read()[0] # заглушка от ошибки в интерфейсе по поводу того что нет действия
        return

        # Создание нескольких записей сразу
        # new_payments = self.env['account.payment'].create(payment_data_list)

        # пример :::

    # def create_document_from_attachment(self, attachment_ids):
    #     print("**create_document_from_attachment**")
    #     print("attachment_ids:", attachment_ids)

    #     attachments = self.env['ir.attachment'].browse(attachment_ids)
    #     for attachment in attachments:
    #         print("**attachment**")
    #         print("name:", attachment.name)

    #         # print("datas:", attachment.datas)

    #         file_name = attachment.name
    #         base64_data = attachment.datas
    #         bytes_content = base64.b64decode(base64_data)

    #         # Декодируем байты напрямую в строку (без лишнего кодирования)
    #         string_content = bytes_content.decode("utf-8")
    #         print("string_content", string_content)
    #         # Парсим XML-строку с помощью lxml.etree.fromstring
    #         xml_tree = etree.fromstring(string_content)
    #         print(xml_tree)

    #     return {}
