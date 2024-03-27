/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import {accountFileUploader} from "@account/components/bills_upload/bills_upload";
import {patch} from "@web/core/utils/patch";

patch(accountFileUploader.component.prototype, {
    async onUploadComplete() {
        // const model_name = new URLSearchParams(this.env.config.viewArch.baseURI).get("model");
        // console.log(this.env.searchModel.resModel)
        const domain = [['id', '=', this.env.config.actionId]]
        const fieldNames = ["name", "res_model"]
        const action_record = await this.orm.searchRead(this.env.config.actionType, domain, fieldNames, { limit: 1 });
        const model_name = action_record[0].res_model
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
                return
            }
            try{
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
                this.action.doAction(action);
            }catch{
                this.notification.add(
                    _t(`In model ${model_name} method "create_document_from_attachment" does not return valid action`),
                    {
                        title: "Error",
                        type: "danger",
                        sticky: true,
                    }
                );
            }
            
            
        }
    },
});
