/** @odoo-module **/

import { accountFileUploader } from '@account/components/bills_upload/bills_upload'
import { patch } from '@web/core/utils/patch'

patch(accountFileUploader.component.prototype, 'bank_stat_parser', {
	async onUploadComplete() {
		const modelName = 'account.payment' // Имя модели, в которой определен метод
		if (this.env.modelName === 'bank.stat.parser') {
			// Проверка, что это нужная модель
			try {
				// Вызываем метод 'create_payments_from_xml_attachment'
				await this.orm.call(
					modelName,
					'create_payments_from_xml_attachment',
					[this.attachmentIdsToProcess],
					{ context: this.env.context }
				)
				// Тут можно добавить логику обработки после успешного завершения операции
			} catch (error) {
				this.displayNotification({
					type: 'danger',
					message: error.message || 'Failed to process the XML file.',
				})
			} finally {
				// Очищаем список ID обработанных вложений
				this.attachmentIdsToProcess = []
			}
		} else {
			// Для других моделей используем базовое поведение компонента
			super.onUploadComplete(...arguments)
		}
	},
})
