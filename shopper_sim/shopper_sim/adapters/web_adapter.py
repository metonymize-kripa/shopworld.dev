"""Web adapter -- form-driven storefront transport.

Drives a headless browser (Playwright) and maps the abstract dialogue onto DOM
interactions: a shopper "utterance" becomes a search query typed into a box or
a form submission; a "merchant turn" becomes the resulting page state read back
as structured text + fields. The SAME dialogue policy drives this adapter, so a
multistep return on a Shopify storefront is tested with the identical state
machine, just a different binding.

Shell only: a per-merchant page-model config supplies the selectors. Playwright
is imported lazily so offline tests have no browser dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import MerchantAdapter, MerchantTurn


@dataclass(frozen=True)
class PageModel:
    """Per-merchant selector/semantics config (confirmed at onboarding).

    A Shopify preset ships defaults; the auto-mapper proposes these and a human
    confirms them. Only structural selectors live here, never test answers.
    """

    search_input: str = "input[type=search]"
    search_results: str = "[data-product-card]"
    add_to_cart: str = "button[name=add]"
    cart_drawer: str = "[data-cart]"
    chat_widget_input: str | None = None  # if the store has an embedded agent
    chat_widget_output: str | None = None
    extra: dict[str, str] = field(default_factory=dict)


SHOPIFY_PRESET = PageModel()


class PlaywrightWebAdapter(MerchantAdapter):
    """Maps dialogue turns onto DOM actions via Playwright.

    Shell implementation: the structure is complete; the actual page driving is
    delegated to helper methods that a real deployment fills in against the
    merchant's PageModel.
    """

    def __init__(self, base_url: str, page_model: PageModel = SHOPIFY_PRESET,
                 headless: bool = True) -> None:
        self._base_url = base_url
        self._pm = page_model
        self._headless = headless
        self._browser = None
        self._page = None

    def open_session(self, scenario_id: str, seed: int) -> None:  # pragma: no cover
        from playwright.sync_api import sync_playwright  # lazy

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self._headless)
        self._page = self._browser.new_page()
        self._page.goto(self._base_url)

    def send(self, utterance: str) -> MerchantTurn:  # pragma: no cover
        if self._page is None:
            raise RuntimeError("session not open")
        # If the store has an embedded chat agent, prefer it for multistep.
        if self._pm.chat_widget_input and self._pm.chat_widget_output:
            self._page.fill(self._pm.chat_widget_input, utterance)
            self._page.keyboard.press("Enter")
            self._page.wait_for_timeout(500)
            text = self._page.inner_text(self._pm.chat_widget_output)
            return MerchantTurn(text=text, has_question="?" in text)
        # Otherwise treat as a search-driven single-shot interaction.
        self._page.fill(self._pm.search_input, utterance)
        self._page.keyboard.press("Enter")
        self._page.wait_for_timeout(500)
        cards = self._page.query_selector_all(self._pm.search_results)
        summary = f"{len(cards)} results for your query."
        fields = {"result_count": str(len(cards))}
        return MerchantTurn(text=summary, fields=fields)

    def close_session(self) -> None:  # pragma: no cover
        if self._browser is not None:
            self._browser.close()
        if getattr(self, "_pw", None) is not None:
            self._pw.stop()
