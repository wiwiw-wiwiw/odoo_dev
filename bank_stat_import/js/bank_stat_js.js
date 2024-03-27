/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import {accountFileUploader} from "@account/components/bills_upload/bills_upload";
import {patch} from "@web/core/utils/patch";

patch(accountFileUploader.component.prototype, {
    async onUploadComplete() {
        const model_name = new URLSearchParams(this.env.config.viewArch.baseURI).get("model");
        if (model_name === "account.move") {
            super.onUploadComplete(...arguments);
        } else {
            let action = {};
            try {
                action = await this.orm.call(
                    model_name,
                    "create_document_from_attachment",
                    ["", this.attachmentIdsToProcess],
                    {
                        context: {...this.extraContext, ...this.env.searchModel.context},
                    }
                );
            } catch (exception) {
                this.notification.add(
                    _t(`File handler "create_document_from_attachment" is not implemented in model ${model_name}`),
                    {
                        title: "Error",
                        type: "danger",
                        sticky: true,
                    }
                );
            }
            this.attachmentIdsToProcess = [];
            if (action.context && action.context.notifications) {
                for (const [file, msg] of Object.entries(action.context.notifications)) {
                    this.notification.add(msg, {
                        title: file,
                        type: "info",
                        sticky: true,
                    });
                }
                delete action.context.notifications;
            }
            if (action) {
                this.action.doAction(action);
            }
        }
    },
});
