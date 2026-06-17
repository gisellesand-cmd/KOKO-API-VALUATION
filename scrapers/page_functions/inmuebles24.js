// pageFunction for apify/playwright-scraper targeting inmuebles24.com.
// Returns array of listing dicts; Apify collects what we return into the dataset.
// Pagination: enqueues `-pagina-{N}.html` URLs up to customData.maxPages.
async function pageFunction(context) {
    const { request, log, page, customData, enqueueRequest } = context;
    const maxPages = (customData && customData.maxPages) || 1;
    const currentPage = (request.userData && request.userData.page) || 1;

    log.info(`inmuebles24: page ${currentPage}/${maxPages} — ${request.url}`);

    // Try multiple selectors; some pages render with different markup.
    const cardSelectors = [
        "div[data-posting-type]",
        "div.postingCard",
        "div.postingCardLayout",
        "div[data-id]",
        "div[data-qa='posting PROPERTY']",
    ];
    let cards = [];
    for (const sel of cardSelectors) {
        cards = await page.$$(sel);
        if (cards.length > 0) {
            log.info(`inmuebles24: matched ${cards.length} cards with "${sel}"`);
            break;
        }
    }

    const results = [];
    for (const card of cards) {
        const listingId =
            (await card.getAttribute("data-id")) ||
            (await card.getAttribute("data-posting-id"));
        if (!listingId) continue;

        const priceText = await firstText(card, [
            "[data-qa='POSTING_CARD_PRICE']",
            ".postingPrices",
            ".price-items",
            ".firstPrice",
            "[class*='price']",
        ]);
        if (!priceText) continue;

        const urlPath = await firstAttr(
            card,
            ["a[href]", "[data-qa='POSTING_CARD_DESCRIPTION'] a", "h3 a"],
            "href",
        );
        if (!urlPath) continue;
        const sourceUrl = new URL(urlPath, "https://www.inmuebles24.com").toString();

        const featureNodes = await card.$$(
            "ul.card-points li, ul.section-icon-features li, [class*='feature']",
        );
        let featuresText = "";
        for (const n of featureNodes) {
            const t = (await n.textContent()) || "";
            featuresText += " " + t.trim();
        }
        featuresText = featuresText.trim();

        const address = await firstText(card, [
            "[data-qa='POSTING_CARD_LOCATION']",
            ".postingLocations",
            "[class*='location']",
        ]);
        const title = await firstText(card, [
            "[data-qa='POSTING_CARD_DESCRIPTION']",
            "h3",
            "h2",
            "[class*='posting-title']",
        ]);

        results.push({
            source_listing_id: String(listingId),
            source_url: sourceUrl,
            title: title || null,
            price_text: priceText,
            features_text: featuresText || null,
            address: address || null,
        });
    }

    if (results.length === 0 && currentPage === 1) {
        log.warning(`inmuebles24: zero listings on page 1 — selectors or anti-bot. URL: ${request.url}`);
    }

    if (currentPage < maxPages && results.length > 0) {
        // URL pattern: ...-en-{location}.html  ->  ...-en-{location}-pagina-{N}.html
        let nextUrl;
        if (/-pagina-\d+\.html$/.test(request.url)) {
            nextUrl = request.url.replace(/-pagina-\d+\.html$/, `-pagina-${currentPage + 1}.html`);
        } else if (/\.html$/.test(request.url)) {
            nextUrl = request.url.replace(/\.html$/, `-pagina-${currentPage + 1}.html`);
        } else {
            const sep = request.url.includes("?") ? "&" : "?";
            nextUrl = `${request.url}${sep}pagina=${currentPage + 1}`;
        }
        await enqueueRequest({ url: nextUrl, userData: { page: currentPage + 1 } });
        log.info(`inmuebles24: enqueued page ${currentPage + 1} -> ${nextUrl}`);
    }

    return results;

    async function firstText(node, selectors) {
        for (const sel of selectors) {
            const el = await node.$(sel);
            if (el) {
                const t = (await el.textContent()) || "";
                const trimmed = t.trim();
                if (trimmed) return trimmed;
            }
        }
        return null;
    }
    async function firstAttr(node, selectors, attr) {
        for (const sel of selectors) {
            const el = await node.$(sel);
            if (el) {
                const v = await el.getAttribute(attr);
                if (v) return v;
            }
        }
        return null;
    }
}
