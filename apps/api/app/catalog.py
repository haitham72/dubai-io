"""Host-owned catalog of fictional sandbox merchants (demo_fixture).

Order totals are rebuilt here, never from numbers a mini-app sends (ARCHITECTURE.md
§6.4). Prices are fixed and published; there is no quote path.
"""
from decimal import Decimal

PROVENANCE = "demo_fixture"
AS_OF = "2026-10-13"
LAUNDRY_SLOTS = ("Today 18:00", "Today 21:00", "Tomorrow 08:00")

# provider_id -> name, service, items {item_id: (name, price_aed)}, pickup slots
PROVIDERS = {
    "marinaexpress": ("Marina Express Laundry", "laundry", {"press": ("Shirt wash + press", "6")}, LAUNDRY_SLOTS),
    "foldpress": ("Fold & Press Laundry", "laundry", {"iron": ("Shirt ironing", "5")}, LAUNDRY_SLOTS),
    "palmquick": ("Palm Quick Press", "laundry", {"press": ("Shirt pressing", "4")}, LAUNDRY_SLOTS),
    "nest-clean": ("Nest Helpers", "cleaning", {"h2": ("2 hours", "90"), "h4": ("4 hours (bundle)", "160")}, ("Tomorrow 09:00", "Tomorrow 14:00", "Sat 10:00")),
    "fixit": ("FixIt Pros", "ac", {"chk": ("AC check", "150"), "deep": ("Deep clean + gas top-up", "220")}, ("Today 17:00", "Tomorrow 09:00", "Tomorrow 14:00")),
    "paws-van": ("Paws & Co. Mobile", "grooming", {"bath": ("Bath + dry", "120"), "full": ("Bath + trim + nails (bundle)", "220")}, ("Thu 10:00", "Thu 15:00", "Fri 11:00")),
    "shine": ("Shine at Home", "carwash", {"ext": ("Exterior wash", "45"), "full": ("Exterior + interior", "75")}, ("Today 19:00", "Tomorrow 08:00", "Tomorrow 18:00")),
    "palmleaf": ("Palm Leaf Pharmacy", "pharmacy", {"para": ("Paracetamol 500mg ×24", "9"), "ors": ("Oral rehydration salts ×10", "18"), "spf": ("Sunscreen SPF 50", "59"),
                                                   "nasal": ("Saline nasal spray", "22"), "plast": ("Blister plasters", "16"), "lip": ("Lip balm", "12")}, ()),
    "bloom": ("Bloom Care", "pharmacy", {"jetlag": ("Jet-lag kit", "79"), "sun": ("Sun care kit", "95"), "baby": ("Baby travel kit", "68")}, ()),
    "nightowl": ("Night Owl Pharmacy 24h", "pharmacy", {"rx": ("Prescription review", "0")}, ()),
    "nest-maid": ("Nest Helpers", "maid", {"place": ("Placement (Filipina)", "6400")}, ("Call back today", "Visit Sat 10:00", "Visit Sun 16:00")),
}


class CatalogError(ValueError):
    pass


def price_order(provider_id: str, items: list[dict], slot: str | None) -> dict:
    """Resolve requested items by id or exact catalog name; quantities only come from the request."""
    entry = PROVIDERS.get(provider_id)
    if entry is None:
        raise CatalogError("Unknown provider")
    name, service, catalog, slots = entry
    by_name = {label: key for key, (label, _) in catalog.items()}
    lines = {}
    for item in items:
        key = item.get("id") if item.get("id") in catalog else by_name.get(item.get("name"))
        if key is None:
            raise CatalogError("Item is not in this provider's published list")
        qty = int(item.get("qty") or 0)
        if not 1 <= qty <= 20:
            raise CatalogError("Quantity must be 1 to 20")
        lines[key] = lines.get(key, 0) + qty
    if not lines:
        raise CatalogError("Choose at least one item")
    if slot and slots and slot not in slots:
        raise CatalogError("Slot is not one of the provider's published slots")
    priced = [{"id": key, "name": catalog[key][0], "qty": qty, "price_aed": catalog[key][1]} for key, qty in sorted(lines.items())]
    total = sum((Decimal(line["price_aed"]) * line["qty"] for line in priced), Decimal("0"))
    return {"provider_id": provider_id, "provider": name, "service": service, "lines": priced,
            "slot": slot or None, "total_aed": str(total), "provenance": PROVENANCE, "as_of": AS_OF}
