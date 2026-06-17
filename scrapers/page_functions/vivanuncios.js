// pageFunction for apify/playwright-scraper targeting vivanuncios.com.mx.
// Returns array of listing dicts. Pagination uses the .../v1c1098p{N} URL suffix.
async function pageFunction(context) {
    const { request, log, page, customData, enqueueRequest } = context;
    const maxPages = (customData && customData.maxPages) || 1;
    const currentPage = (request.userData && request.userData.page) || 1;

    log.info(`vivanuncios: page ${currentPage}/${maxPages} — ${request.url}`);

    const cardSelectors = [
        "article[data-q='ad-tile']",
        "div.tileV2",
        "li.tileV2",
        "div[data-adid]",
        "div.posting-card",
    ];
    let cards = [];
    for (const sel of cardSelectors) {
        cards = await page.$$(sel);
        if (cards.length > 0) {
            log.info(`vivanuncios: matched ${cards.length} cards with "${sel}"`);
            break;
        }
    }

    const results = [];
    for (const card of cards) {
        const listingId =
            (await card.getAttribute("data-adid")) ||
            (await card.getAttribute("data-ad-id")) ||
            (await card.getAttribute("data-id"));
        if (!listingId) continue;

        const priceText = await firstText(card, [
            "div.price",
            "span.ad-price",
            "[class*='price']",
            "[data-q='ad-price']",
        ]);
        if (!priceText) continue;

        const urlPath = await firstAttr(
            card,
            ["a[href]", "h2 a", "[data-q='ad-title'] a"],
            "href",
        );
        if (!urlPath) continue;
        const sourceUrl = new URL(urlPath, "https://www.vivanuncios.com.mx").toString();

        const featureNodes = await card.$$(
            "ul.features li, ul.attributes li, [class*='feature'], [class*='attribute']",
        );
        let featuresText = "";
        for (const n of featureNodes) {
            const t = (await n.textContent()) || "";
            featuresText += " " + t.trim();
        }
        featuresText = featuresText.trim();

        const address = await firstText(card, [
            "div.location",
            "[data-q='ad-location']",
            "[class*='location']",
        ]);
        const title = await firstText(card, [
            "h2",
            "h3",
            "[data-q='ad-title']",
            "[class*='title']",
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
        log.warning(`vivanuncios: zero listings on page 1. URL: ${request.url}`);
    }

    if (currentPage < maxPages && results.length > 0) {
        // URL ends with /v1c1098p{N} — increment N.
        let nextUrl;
        if (/p\d+$/.test(request.url)) {
            nextUrl = request.url.replace(/p\d+$/, `p${currentPage + 1}`);
        } else {
            nextUrl = `${request.url}p${currentPage + 1}`;
        }
        await enqueueRequest({ url: nextUrl, userData: { page: currentPage + 1 } });
        log.info(`vivanuncios: enqueued page ${currentPage + 1} -> ${nextUrl}`);
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
