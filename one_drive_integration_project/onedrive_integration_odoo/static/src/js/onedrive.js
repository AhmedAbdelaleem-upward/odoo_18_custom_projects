/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef } from "@odoo/owl";

export class OnedriveDashboard extends Component {
    static template = "OnedriveDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.inputRef = useRef("all_files");
        this.state = useState({
            files: [],
        });
        this.synchronize();
    }

    /**
     * Opens a file upload dialog on click of the "Upload" button.
     */
    async upload() {
        this.action.doAction({
            name: "Upload File",
            type: 'ir.actions.act_window',
            res_model: 'upload.file',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
        });
    }

    /**
     * Retrieves and displays files from OneDrive on click of the "Import" button.
     */
    async synchronize() {
        const result = await this.orm.call(
            'onedrive.dashboard',
            'action_synchronize_onedrive',
            [[]]
        );

        if (!result) {
            this.action.doAction({
                type: 'ir.actions.client',
                tag: 'display_notification',
                params: {
                    message: 'Please setup credentials',
                    type: 'warning',
                }
            });
            return;
        }

        this.state.files = result;
    }

    /**
     * Filters files displayed based on file type (e.g., image, all files).
     *
     * @param {Object} ev - The click event object.
     */
    filter_file_type(ev) {
        const value = ev.currentTarget.getAttribute("value");

        document.querySelectorAll(".onedrive-card").forEach(card => {
            const ext = card.dataset.ext;

            // Show all
            if (value === "allfiles") {
                card.parentElement.style.display = "";
                return;
            }

            // Image group
            if (value === "image") {
                if (["png", "jpg", "jpeg"].includes(ext)) {
                    card.parentElement.style.display = "";
                } else {
                    card.parentElement.style.display = "none";
                }
                return;
            }

            // Exact match (mdb, pdf, xlsx, etc.)
            if (ext === value) {
                card.parentElement.style.display = "";
            } else {
                card.parentElement.style.display = "none";
            }
        });
    }

    downloadFile(file) {
        const link = document.createElement('a');
        link.href = file.download_url;
        link.download = file.name;
        link.style.display = 'none';

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    async readMDB(file) {
        console.log("READ MDB CLICKED:", file.name, file.download_url);

        if (!file.name || !file.download_url) {
            this.action.doAction({
                type: 'ir.actions.client',
                tag: 'display_notification',
                params: {
                    message: "File information missing",
                    type: 'danger',
                }
            });
            return;
        }

        try {
            const result = await this.orm.call(
                'onedrive.dashboard',
                'action_read_mdb_file',
                [[], file.download_url, file.name]
            );

            // Execute the returned action (opens tree view)
            if (result) {
                this.action.doAction(result);
            }
        } catch (error) {
            this.action.doAction({
                type: 'ir.actions.client',
                tag: 'display_notification',
                params: {
                    message: `Error reading MDB: ${error.message || error}`,
                    type: 'danger',
                }
            });
        }
    }
}

registry.category("actions").add("onedrive_dashboard", OnedriveDashboard);
