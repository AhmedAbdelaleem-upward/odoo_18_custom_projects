/** @odoo-module */

import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

/**
 * Payment Reminder Banner
 * 
 * This module fetches banners configuration from the Upward master
 * and displays a colored banner at the top of the screen for client instances.
 */

function createBanner(message, color) {
    const existing = document.querySelector(".o_payment_reminder_banner");
    if (existing) {
        existing.parentNode.removeChild(existing);
    }

    const banner = document.createElement("div");
    banner.className = "o_payment_reminder_banner";
    banner.style.position = "fixed";
    banner.style.top = "0";
    banner.style.left = "0";
    banner.style.right = "0";
    banner.style.zIndex = "9999";
    banner.style.padding = "8px 16px";
    banner.style.color = "#ffffff";
    banner.style.textAlign = "center";
    banner.style.fontWeight = "bold";
    banner.style.direction = "rtl";

    let backgroundColor = "#28a745"; // green
    if (color === "yellow") {
        backgroundColor = "#ffc107";
        banner.style.color = "#000000";
    } else if (color === "red") {
        backgroundColor = "#dc3545";
    }
    banner.style.backgroundColor = backgroundColor;

    banner.textContent = message || _t("There is an important payment reminder from your provider.");

    document.body.appendChild(banner);

    // Push the webclient down slightly so it is not hidden.
    const webClient = document.querySelector(".o_web_client");
    if (webClient) {
        webClient.style.marginTop = "40px";
    }
}

function removeBanner() {
    const banner = document.querySelector(".o_payment_reminder_banner");
    if (banner && banner.parentNode) {
        banner.parentNode.removeChild(banner);
    }
    const webClient = document.querySelector(".o_web_client");
    if (webClient) {
        webClient.style.marginTop = "";
    }
}

async function fetchAndRenderBanner() {
    try {
        const data = await rpc("/payment_reminder/client/banner_config", {});
        if (data && data.active) {
            createBanner(data.message, data.color);
        } else {
            removeBanner();
        }
    } catch (error) {
        console.warn("Payment reminder banner fetch failed:", error);
        removeBanner();
    }
}

// Initial load
if (document.readyState === "complete" || document.readyState === "interactive") {
    fetchAndRenderBanner();
} else {
    document.addEventListener("DOMContentLoaded", fetchAndRenderBanner);
}

// Refresh periodically (every 10 minutes) to keep up to date.
setInterval(fetchAndRenderBanner, 10 * 60 * 1000);
