"""Labeled seed utterances for milli.run intent classification.

Kept deliberately separate from ShopWorld's held-out scenario language: this is
NLU *training* split, and the leakage rule (README §6) forbids reusing it as
held-out test text. The Bitext importers (scenarios/) can extend this list with
provenance-tagged utterances for a larger training set.
"""

from typing import List, Tuple

# (utterance, intent_label)
TRAINING_UTTERANCES: List[Tuple[str, str]] = [
    # WISMO
    ("where is my order", "WISMO"),
    ("i still have not received my package", "WISMO"),
    ("my order has not arrived yet", "WISMO"),
    ("can you check on my shipment status", "WISMO"),
    ("tracking has not updated in days", "WISMO"),
    ("when will my order be delivered", "WISMO"),
    ("my package is late", "WISMO"),
    ("any update on my delivery", "WISMO"),
    # CANCEL
    ("cancel my order", "CANCEL"),
    ("i want to cancel my purchase", "CANCEL"),
    ("please cancel order before it ships", "CANCEL"),
    ("can i stop this order", "CANCEL"),
    ("i changed my mind cancel it", "CANCEL"),
    ("call off my order", "CANCEL"),
    ("do not ship cancel please", "CANCEL"),
    # ADDRESS_CHANGE
    ("change my shipping address", "ADDRESS_CHANGE"),
    ("i need to update my delivery address", "ADDRESS_CHANGE"),
    ("can you ship to a different address", "ADDRESS_CHANGE"),
    ("i moved please update the address", "ADDRESS_CHANGE"),
    ("wrong address on my order fix it", "ADDRESS_CHANGE"),
    ("send it to my new house instead", "ADDRESS_CHANGE"),
    # REFUND
    ("i want a refund", "REFUND"),
    ("please refund my money", "REFUND"),
    ("can i get my money back", "REFUND"),
    ("i would like a refund for this order", "REFUND"),
    ("give me a refund please", "REFUND"),
    ("refund this charge", "REFUND"),
    ("i need my payment returned", "REFUND"),
    # RETURN
    ("how do i return this", "RETURN"),
    ("i want to return the item", "RETURN"),
    ("can i send this back", "RETURN"),
    ("i need to return my purchase", "RETURN"),
    ("start a return for me", "RETURN"),
    ("this does not fit i want to return it", "RETURN"),
    ("how do i send back this product", "RETURN"),
    # OTHER (non-actionable / out of scope)
    ("do you have this in blue", "OTHER"),
    ("what are your store hours", "OTHER"),
    ("thanks for the help", "OTHER"),
    ("is this product in stock", "OTHER"),
    ("can i speak to a manager", "OTHER"),
    ("what payment methods do you accept", "OTHER"),
]
