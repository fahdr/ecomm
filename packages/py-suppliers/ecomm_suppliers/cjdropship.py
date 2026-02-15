"""
CJDropship supplier client integration.

For Developers:
    Uses the CJDropship Open API when an API key is provided. Falls back
    to realistic demo data when no key is configured, allowing full
    development and testing without API credentials.

    Real API integration points are stubbed and clearly marked with
    ``# TODO: real API`` comments for future implementation.

For QA Engineers:
    In demo mode the client returns a fixed set of 18 products across
    electronics, fashion, home, and beauty categories. Product IDs are
    stable and deterministic, so assertions can target specific products.

For End Users:
    Browse and import products from CJDropship into your store. CJDropship
    specializes in fast shipping from US/EU warehouses and branded packaging.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from ecomm_suppliers.base import BaseSupplierClient, SupplierError
from ecomm_suppliers.models import (
    ProductSearchResult,
    ShippingInfo,
    SupplierProduct,
    SupplierRating,
    SupplierVariant,
)

# CJDropship Open API base URL
_API_BASE = "https://developers.cjdropshipping.com/api/2.0"

# Pattern to extract product ID from CJDropship URLs
_URL_PATTERN = re.compile(r"/product(?:_detail)?/(?:p-)?([A-Za-z0-9-]+)")


def _extract_product_id(url: str) -> str:
    """
    Extract the CJDropship product ID from a product URL.

    Args:
        url: Full CJDropship product URL.

    Returns:
        Product ID string.

    Raises:
        SupplierError: If the URL does not contain a recognizable product ID.
    """
    match = _URL_PATTERN.search(url)
    if match:
        return match.group(1)
    raise SupplierError(
        f"Could not extract product ID from CJDropship URL: {url}",
        supplier="cjdropship",
    )


def _build_demo_products() -> list[dict[str, Any]]:
    """
    Build a list of realistic demo product dicts for CJDropship.

    Returns:
        List of 18 product data dicts spanning electronics, fashion, home,
        and beauty categories. CJDropship products emphasize US/EU warehouse
        availability and faster shipping times.
    """
    return [
        # ── Electronics (4 products) ──────────────────────────────────
        {
            "id": "CJ-ELEC-2891734",
            "title": "Wireless Charging Pad 15W MagSafe Compatible Slim Design",
            "description": (
                "Ultra-slim 15W wireless charging pad with MagSafe-compatible magnetic "
                "alignment ring. Supports Qi fast charging for iPhone 15/14/13 and "
                "Samsung Galaxy S24/S23. Foreign object detection. LED indicator. "
                "Includes USB-C cable. Anti-slip silicone surface."
            ),
            "price": "5.89",
            "category": "electronics",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-charge-pad-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-charge-pad-02.jpg",
            ],
            "variants": [
                {"name": "Color: Black", "sku": "CJ-WC-BK", "price": "5.89", "stock": 8432, "attrs": {"color": "Black"}},
                {"name": "Color: White", "sku": "CJ-WC-WH", "price": "5.89", "stock": 7654, "attrs": {"color": "White"}},
            ],
            "shipping": {"min": 5, "max": 10, "cost": "0.00", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.5, "count": 3421, "positive": 93.2},
        },
        {
            "id": "CJ-ELEC-3847291",
            "title": "Bluetooth Car FM Transmitter QC3.0 Dual USB Charger Bass Boost",
            "description": (
                "Bluetooth 5.3 car FM transmitter with QC3.0 + PD 20W dual-port "
                "charging. Bass boost technology. Hands-free calling with noise "
                "cancellation microphone. LED display shows battery voltage. Supports "
                "TF card and USB flash drive playback. One-key bass enhancement."
            ),
            "price": "4.23",
            "category": "electronics",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-fm-transmit-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-fm-transmit-02.jpg",
            ],
            "variants": [
                {"name": "Type: Standard", "sku": "CJ-FM-STD", "price": "4.23", "stock": 12543, "attrs": {"type": "Standard"}},
                {"name": "Type: With AUX Cable", "sku": "CJ-FM-AUX", "price": "5.49", "stock": 8765, "attrs": {"type": "With AUX Cable"}},
            ],
            "shipping": {"min": 5, "max": 10, "cost": "0.00", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.3, "count": 5678, "positive": 91.5},
        },
        {
            "id": "CJ-ELEC-4918273",
            "title": "Mini Portable Power Bank 5000mAh Capsule Design USB-C/Lightning",
            "description": (
                "Ultra-compact 5000mAh power bank in capsule form factor. Built-in "
                "USB-C and Lightning connectors (no cable needed). Pass-through charging. "
                "LED battery indicator. 2A fast output. Dimensions: 9.5x3.2x2.5cm. "
                "Weight: 105g. Airline-safe capacity."
            ),
            "price": "7.45",
            "category": "electronics",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-powerbank-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-powerbank-02.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-powerbank-03.jpg",
            ],
            "variants": [
                {"name": "Connector: USB-C", "sku": "CJ-PB-USBC", "price": "7.45", "stock": 6789, "attrs": {"connector": "USB-C"}},
                {"name": "Connector: Lightning", "sku": "CJ-PB-LTNG", "price": "7.45", "stock": 5432, "attrs": {"connector": "Lightning"}},
                {"name": "Connector: Micro USB", "sku": "CJ-PB-MUSB", "price": "6.99", "stock": 3456, "attrs": {"connector": "Micro USB"}},
            ],
            "shipping": {"min": 4, "max": 8, "cost": "1.50", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.4, "count": 8921, "positive": 92.7},
        },
        {
            "id": "CJ-ELEC-5729184",
            "title": "Ring Light 10 Inch with Tripod Stand Phone Holder for Streaming",
            "description": (
                "10-inch LED ring light with adjustable tripod stand (17-54 inches). "
                "3 color modes (warm/cool/daylight) with 10 brightness levels each. "
                "Flexible phone holder with 360-degree rotation. USB powered. "
                "Includes Bluetooth remote shutter. Perfect for TikTok, YouTube, and Zoom."
            ),
            "price": "8.92",
            "category": "electronics",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-ringlight-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-ringlight-02.jpg",
            ],
            "variants": [
                {"name": "Size: 10 inch", "sku": "CJ-RL-10", "price": "8.92", "stock": 4567, "attrs": {"size": "10 inch"}},
                {"name": "Size: 12 inch", "sku": "CJ-RL-12", "price": "11.49", "stock": 3210, "attrs": {"size": "12 inch"}},
            ],
            "shipping": {"min": 6, "max": 12, "cost": "3.99", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.3, "count": 14321, "positive": 90.8},
        },
        # ── Fashion (4 products) ─────────────────────────────────────
        {
            "id": "CJ-FASH-6381924",
            "title": "Men's Magnetic Buckle Leather Belt Automatic Ratchet Adjustable",
            "description": (
                "Genuine leather belt with automatic magnetic ratchet buckle. "
                "No holes needed — trim to size and the ratchet adjusts in 1/4 inch "
                "increments. Zinc alloy buckle with brushed finish. Belt width: 35mm. "
                "Fits waist 28-44 inches. Comes in gift box."
            ),
            "price": "6.78",
            "category": "fashion",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-belt-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-belt-02.jpg",
            ],
            "variants": [
                {"name": "Color: Black", "sku": "CJ-BELT-BK", "price": "6.78", "stock": 9876, "attrs": {"color": "Black"}},
                {"name": "Color: Brown", "sku": "CJ-BELT-BR", "price": "6.78", "stock": 7654, "attrs": {"color": "Brown"}},
                {"name": "Color: Navy", "sku": "CJ-BELT-NV", "price": "7.49", "stock": 4321, "attrs": {"color": "Navy"}},
            ],
            "shipping": {"min": 5, "max": 10, "cost": "0.00", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.6, "count": 11234, "positive": 95.1},
        },
        {
            "id": "CJ-FASH-7492831",
            "title": "Women's Compression Leggings High Waist Tummy Control Seamless",
            "description": (
                "Seamless compression leggings with high waist and tummy control panel. "
                "Squat-proof 4-way stretch fabric. Moisture-wicking and breathable. "
                "Hidden waistband pocket for keys/cards. Available in 15 colors. "
                "Sizes XS-XL. Perfect for yoga, gym, and everyday wear."
            ),
            "price": "5.34",
            "category": "fashion",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-leggings-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-leggings-02.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-leggings-03.jpg",
            ],
            "variants": [
                {"name": "Color: Black, Size: S", "sku": "CJ-LEG-BK-S", "price": "5.34", "stock": 3456, "attrs": {"color": "Black", "size": "S"}},
                {"name": "Color: Black, Size: M", "sku": "CJ-LEG-BK-M", "price": "5.34", "stock": 4567, "attrs": {"color": "Black", "size": "M"}},
                {"name": "Color: Grey, Size: S", "sku": "CJ-LEG-GR-S", "price": "5.34", "stock": 2345, "attrs": {"color": "Grey", "size": "S"}},
                {"name": "Color: Grey, Size: M", "sku": "CJ-LEG-GR-M", "price": "5.34", "stock": 3210, "attrs": {"color": "Grey", "size": "M"}},
                {"name": "Color: Navy, Size: M", "sku": "CJ-LEG-NV-M", "price": "5.34", "stock": 2876, "attrs": {"color": "Navy", "size": "M"}},
            ],
            "shipping": {"min": 4, "max": 8, "cost": "0.00", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.5, "count": 23456, "positive": 94.3},
        },
        {
            "id": "CJ-FASH-8374912",
            "title": "Minimalist Watch Men Quartz Ultra Thin Mesh Band Waterproof",
            "description": (
                "Minimalist men's quartz watch with ultra-thin 6.5mm case. Japanese "
                "Miyota movement. 316L stainless steel mesh band with magnetic clasp. "
                "Sapphire-coated crystal glass. 30M water resistant. Dial diameter: "
                "40mm. Available in silver, gold, and rose gold tones."
            ),
            "price": "9.12",
            "category": "fashion",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-watch-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-watch-02.jpg",
            ],
            "variants": [
                {"name": "Color: Silver/White", "sku": "CJ-WATCH-SW", "price": "9.12", "stock": 5432, "attrs": {"color": "Silver/White"}},
                {"name": "Color: Gold/Black", "sku": "CJ-WATCH-GB", "price": "9.12", "stock": 4321, "attrs": {"color": "Gold/Black"}},
                {"name": "Color: Rose Gold/Pink", "sku": "CJ-WATCH-RP", "price": "9.99", "stock": 3210, "attrs": {"color": "Rose Gold/Pink"}},
            ],
            "shipping": {"min": 5, "max": 10, "cost": "1.99", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.4, "count": 7654, "positive": 92.8},
        },
        {
            "id": "CJ-FASH-9281734",
            "title": "Travel Toiletry Bag Waterproof Hanging Organizer Large Capacity",
            "description": (
                "Hanging toiletry organizer bag with waterproof polyester exterior. "
                "Large main compartment, 4 mesh pockets, 2 PVC zip pouches, and "
                "elastic band holders. Sturdy hanging hook. Dimensions: 24x20x10cm. "
                "Folds flat for packing. Reinforced handle and zippers."
            ),
            "price": "4.56",
            "category": "fashion",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-toiletry-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-toiletry-02.jpg",
            ],
            "variants": [
                {"name": "Color: Black", "sku": "CJ-TOIL-BK", "price": "4.56", "stock": 8765, "attrs": {"color": "Black"}},
                {"name": "Color: Grey", "sku": "CJ-TOIL-GR", "price": "4.56", "stock": 6543, "attrs": {"color": "Grey"}},
                {"name": "Color: Navy", "sku": "CJ-TOIL-NV", "price": "4.56", "stock": 5432, "attrs": {"color": "Navy"}},
                {"name": "Color: Pink", "sku": "CJ-TOIL-PK", "price": "4.56", "stock": 4321, "attrs": {"color": "Pink"}},
            ],
            "shipping": {"min": 4, "max": 8, "cost": "0.00", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.6, "count": 18765, "positive": 95.4},
        },
        # ── Home & Garden (5 products) ───────────────────────────────
        {
            "id": "CJ-HOME-1029384",
            "title": "Silicone Kitchen Utensil Set 12-Piece Heat Resistant Non-Stick",
            "description": (
                "12-piece silicone kitchen utensil set with wooden handles. Heat resistant "
                "to 230C / 446F. BPA-free, food-grade silicone. Non-scratch safe for all "
                "cookware including non-stick. Includes: spatula, tongs, whisk, ladle, "
                "slotted spoon, pasta server, basting brush, and more."
            ),
            "price": "11.23",
            "category": "home",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-utensils-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-utensils-02.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-utensils-03.jpg",
            ],
            "variants": [
                {"name": "Color: Black", "sku": "CJ-UTEN-BK", "price": "11.23", "stock": 5678, "attrs": {"color": "Black"}},
                {"name": "Color: Red", "sku": "CJ-UTEN-RD", "price": "11.23", "stock": 4567, "attrs": {"color": "Red"}},
                {"name": "Color: Teal", "sku": "CJ-UTEN-TL", "price": "11.23", "stock": 3456, "attrs": {"color": "Teal"}},
            ],
            "shipping": {"min": 5, "max": 10, "cost": "2.99", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.5, "count": 9876, "positive": 93.9},
        },
        {
            "id": "CJ-HOME-2038471",
            "title": "Magnetic Spice Rack Jars Set 12-Pack with Labels Wall Mounted",
            "description": (
                "Set of 12 magnetic spice jars with stainless steel lids and clear "
                "glass bodies. Neodymium magnets for secure wall or fridge mounting. "
                "Includes 120 pre-printed spice labels and 24 blank labels. "
                "Capacity: 100ml per jar. Shaker and pour openings. Airtight seal."
            ),
            "price": "14.87",
            "category": "home",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-spice-rack-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-spice-rack-02.jpg",
            ],
            "variants": [
                {"name": "Size: 12-Pack", "sku": "CJ-SPICE-12", "price": "14.87", "stock": 3456, "attrs": {"size": "12-Pack"}},
                {"name": "Size: 6-Pack", "sku": "CJ-SPICE-6", "price": "8.99", "stock": 5678, "attrs": {"size": "6-Pack"}},
            ],
            "shipping": {"min": 6, "max": 12, "cost": "3.49", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.4, "count": 6543, "positive": 92.1},
        },
        {
            "id": "CJ-HOME-3847291",
            "title": "Smart Plant Watering Globes Set of 4 Self-Watering Glass Bulbs",
            "description": (
                "Set of 4 hand-blown glass watering globes for automatic plant watering. "
                "Gradually releases water over 1-2 weeks. Suitable for indoor and outdoor "
                "plants. Beautiful decorative design in 4 colors: clear, blue, green, amber. "
                "Stem length: 20cm. Bulb capacity: 150ml each."
            ),
            "price": "8.34",
            "category": "home",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-water-globe-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-water-globe-02.jpg",
            ],
            "variants": [
                {"name": "Set: 4-Pack Mixed Colors", "sku": "CJ-GLOBE-4MX", "price": "8.34", "stock": 4321, "attrs": {"set": "4-Pack Mixed"}},
                {"name": "Set: 4-Pack Clear", "sku": "CJ-GLOBE-4CL", "price": "8.34", "stock": 3210, "attrs": {"set": "4-Pack Clear"}},
            ],
            "shipping": {"min": 5, "max": 10, "cost": "2.49", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.2, "count": 4567, "positive": 89.4},
        },
        {
            "id": "CJ-HOME-4729183",
            "title": "Collapsible Laundry Basket Large Pop-Up Mesh Hamper with Handles",
            "description": (
                "Pop-up collapsible laundry hamper with reinforced mesh construction. "
                "Folds flat to 2cm for easy storage. Heavy-duty carrying handles. "
                "Breathable mesh prevents odors. Capacity: 75 liters. "
                "Spring steel wire frame. Machine washable cover."
            ),
            "price": "3.89",
            "category": "home",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-laundry-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-laundry-02.jpg",
            ],
            "variants": [
                {"name": "Color: White", "sku": "CJ-LAUND-WH", "price": "3.89", "stock": 12345, "attrs": {"color": "White"}},
                {"name": "Color: Black", "sku": "CJ-LAUND-BK", "price": "3.89", "stock": 9876, "attrs": {"color": "Black"}},
                {"name": "Color: Grey", "sku": "CJ-LAUND-GR", "price": "3.89", "stock": 7654, "attrs": {"color": "Grey"}},
            ],
            "shipping": {"min": 4, "max": 8, "cost": "0.00", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.3, "count": 15432, "positive": 91.7},
        },
        {
            "id": "CJ-HOME-5918274",
            "title": "Shower Caddy Corner Shelf Adhesive Wall Mount Stainless Steel",
            "description": (
                "Corner shower caddy shelf in 304 stainless steel with brushed finish. "
                "Strong adhesive mounting (no drilling). Holds up to 8kg. Drainage holes "
                "prevent water buildup. Rust-resistant coating. Dimensions: 25x25x5cm. "
                "Pack of 2 shelves. Includes adhesive pads and screws."
            ),
            "price": "6.45",
            "category": "home",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-shower-caddy-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-shower-caddy-02.jpg",
            ],
            "variants": [
                {"name": "Pack: 2-Pack Silver", "sku": "CJ-CADDY-2SL", "price": "6.45", "stock": 6543, "attrs": {"pack": "2-Pack", "color": "Silver"}},
                {"name": "Pack: 2-Pack Black", "sku": "CJ-CADDY-2BK", "price": "6.45", "stock": 5432, "attrs": {"pack": "2-Pack", "color": "Black"}},
                {"name": "Pack: 3-Pack Silver", "sku": "CJ-CADDY-3SL", "price": "8.99", "stock": 3210, "attrs": {"pack": "3-Pack", "color": "Silver"}},
            ],
            "shipping": {"min": 5, "max": 10, "cost": "1.49", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.5, "count": 8765, "positive": 93.6},
        },
        # ── Beauty & Health (5 products) ─────────────────────────────
        {
            "id": "CJ-BEAU-6018273",
            "title": "Ice Roller for Face and Eyes Stainless Steel Facial Massager",
            "description": (
                "Stainless steel ice roller for facial massage and de-puffing. "
                "Store in freezer for cooling effect. Reduces redness, tightens pores, "
                "and relieves headaches. Ergonomic handle with non-slip grip. "
                "Medical-grade 304 stainless steel. No batteries or gels needed."
            ),
            "price": "2.34",
            "category": "beauty",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-ice-roller-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-ice-roller-02.jpg",
            ],
            "variants": [
                {"name": "Color: Silver", "sku": "CJ-ICE-SL", "price": "2.34", "stock": 18765, "attrs": {"color": "Silver"}},
                {"name": "Color: Rose Gold", "sku": "CJ-ICE-RG", "price": "2.89", "stock": 14321, "attrs": {"color": "Rose Gold"}},
            ],
            "shipping": {"min": 4, "max": 8, "cost": "0.00", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.6, "count": 27654, "positive": 95.8},
        },
        {
            "id": "CJ-BEAU-7192834",
            "title": "LED Face Mask Light Therapy 7 Colors Skin Rejuvenation Device",
            "description": (
                "7-color LED photon therapy face mask for skin rejuvenation. "
                "Red light (630nm) for anti-aging, blue (470nm) for acne treatment, "
                "green (520nm) for pigmentation. USB rechargeable with 15-minute auto "
                "timer. Medical-grade silicone for comfortable fit. "
                "Eye protection goggles included."
            ),
            "price": "15.67",
            "category": "beauty",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-led-mask-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-led-mask-02.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-led-mask-03.jpg",
            ],
            "variants": [
                {"name": "Type: Face Only", "sku": "CJ-LED-FACE", "price": "15.67", "stock": 3456, "attrs": {"type": "Face Only"}},
                {"name": "Type: Face + Neck", "sku": "CJ-LED-BOTH", "price": "22.49", "stock": 2345, "attrs": {"type": "Face + Neck"}},
            ],
            "shipping": {"min": 5, "max": 10, "cost": "2.99", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.3, "count": 8765, "positive": 90.2},
        },
        {
            "id": "CJ-BEAU-8374921",
            "title": "Teeth Whitening Strips 28-Pack Professional Grade Enamel Safe",
            "description": (
                "28 whitening strips (14 treatments) with 6% hydrogen peroxide formula. "
                "Advanced seal technology for no-slip grip. Removes years of stains in "
                "14 days. Enamel-safe and dentist-recommended. Mint flavored for fresh "
                "breath. 30-minute application time. Sensitivity-free formula."
            ),
            "price": "6.89",
            "category": "beauty",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-teeth-strips-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-teeth-strips-02.jpg",
            ],
            "variants": [
                {"name": "Pack: 28 Strips (14 days)", "sku": "CJ-TEETH-28", "price": "6.89", "stock": 9876, "attrs": {"pack": "28 Strips"}},
                {"name": "Pack: 56 Strips (28 days)", "sku": "CJ-TEETH-56", "price": "11.49", "stock": 6543, "attrs": {"pack": "56 Strips"}},
            ],
            "shipping": {"min": 4, "max": 8, "cost": "0.00", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.2, "count": 12345, "positive": 88.9},
        },
        {
            "id": "CJ-BEAU-9281734",
            "title": "Electric Nail Drill Machine Portable USB Rechargeable Manicure Set",
            "description": (
                "Portable electric nail drill with 6 interchangeable heads. "
                "Adjustable speed: 5000-20000 RPM. USB-C rechargeable with 3-hour "
                "battery life. Forward and reverse rotation. LED indicator light. "
                "Compact pen-style design. Includes travel pouch. For natural and "
                "acrylic nails."
            ),
            "price": "8.45",
            "category": "beauty",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-nail-drill-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-nail-drill-02.jpg",
            ],
            "variants": [
                {"name": "Color: White", "sku": "CJ-NAIL-WH", "price": "8.45", "stock": 5678, "attrs": {"color": "White"}},
                {"name": "Color: Pink", "sku": "CJ-NAIL-PK", "price": "8.45", "stock": 6789, "attrs": {"color": "Pink"}},
                {"name": "Color: Black", "sku": "CJ-NAIL-BK", "price": "8.45", "stock": 4567, "attrs": {"color": "Black"}},
            ],
            "shipping": {"min": 5, "max": 10, "cost": "0.00", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.4, "count": 15678, "positive": 93.1},
        },
        {
            "id": "CJ-BEAU-1038274",
            "title": "Hair Scalp Massager Shampoo Brush Silicone Head Scrubber",
            "description": (
                "Silicone scalp massager and shampoo brush with soft flexible bristles. "
                "Ergonomic palm-fit design. Removes buildup and dandruff. Stimulates "
                "blood circulation for healthier hair growth. Suitable for all hair "
                "types. Dishwasher safe. Available in pastel colors."
            ),
            "price": "1.89",
            "category": "beauty",
            "images": [
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-scalp-brush-01.jpg",
                "https://cbu01.alicdn.com/img/ibank/O1CN01cj-scalp-brush-02.jpg",
            ],
            "variants": [
                {"name": "Color: Pink", "sku": "CJ-SCALP-PK", "price": "1.89", "stock": 23456, "attrs": {"color": "Pink"}},
                {"name": "Color: Green", "sku": "CJ-SCALP-GR", "price": "1.89", "stock": 18765, "attrs": {"color": "Green"}},
                {"name": "Color: Purple", "sku": "CJ-SCALP-PR", "price": "1.89", "stock": 15432, "attrs": {"color": "Purple"}},
                {"name": "Color: Blue", "sku": "CJ-SCALP-BL", "price": "1.89", "stock": 12345, "attrs": {"color": "Blue"}},
            ],
            "shipping": {"min": 3, "max": 7, "cost": "0.00", "method": "CJ Packet", "from": "US"},
            "rating": {"avg": 4.7, "count": 45678, "positive": 96.5},
        },
    ]


def _dict_to_product(data: dict[str, Any]) -> SupplierProduct:
    """
    Convert a demo product dict to a SupplierProduct model.

    Args:
        data: Product dict from ``_build_demo_products()``.

    Returns:
        Fully populated SupplierProduct instance.
    """
    variants = [
        SupplierVariant(
            name=v["name"],
            sku=v.get("sku"),
            price=Decimal(v["price"]),
            stock=v.get("stock"),
            image_url=None,
            attributes=v.get("attrs", {}),
        )
        for v in data.get("variants", [])
    ]

    shipping = None
    if data.get("shipping"):
        s = data["shipping"]
        shipping = ShippingInfo(
            estimated_days_min=s["min"],
            estimated_days_max=s["max"],
            shipping_cost=Decimal(s["cost"]),
            shipping_method=s["method"],
            ships_from=s["from"],
        )

    rating = None
    if data.get("rating"):
        r = data["rating"]
        rating = SupplierRating(
            average=r["avg"],
            count=r["count"],
            positive_percent=r.get("positive"),
        )

    return SupplierProduct(
        source="cjdropship",
        source_id=data["id"],
        source_url=f"https://cjdropshipping.com/product/{data['id']}",
        title=data["title"],
        description=data["description"],
        price=Decimal(data["price"]),
        currency="USD",
        images=data.get("images", []),
        variants=variants,
        shipping_info=shipping,
        ratings=rating,
        raw_data=data,
        fetched_at=datetime.now(timezone.utc),
    )


class CJDropshipClient(BaseSupplierClient):
    """
    CJDropship supplier client for searching and importing products.

    For Developers:
        When ``api_key`` is provided, the client authenticates against the
        CJDropship Open API. When ``api_key`` is None, it returns realistic
        demo data for development and testing.

        CJDropship differentiates from AliExpress by offering US/EU warehouse
        fulfillment with faster shipping times (3-10 days vs. 12-25 days).

    For QA Engineers:
        In demo mode, 18 products are available with stable IDs across
        4 categories. CJDropship IDs use the format ``CJ-{CATEGORY}-{NUMBER}``.

    For End Users:
        Import products from CJDropship with faster US-based shipping options.

    Args:
        api_key: CJDropship Open API access token. If None, demo mode is used.
    """

    def __init__(self, api_key: str | None = None) -> None:
        """
        Initialize the CJDropship client.

        Args:
            api_key: CJDropship API access token.
                If not provided, the client operates in demo mode with mock data.
        """
        super().__init__(api_key=api_key)
        self._client: httpx.AsyncClient | None = None
        self._demo_products: list[dict[str, Any]] = _build_demo_products()

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create the shared httpx AsyncClient for real API calls.

        Returns:
            An httpx.AsyncClient instance configured for the CJDropship API.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=_API_BASE,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "CJ-Access-Token": self._api_key or "",
                },
            )
        return self._client

    async def close(self) -> None:
        """
        Close the underlying HTTP client and release resources.

        For Developers:
            Always call this (or use the async context manager) when done
            to prevent resource leaks.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def search_products(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
    ) -> ProductSearchResult:
        """
        Search for products on CJDropship.

        In demo mode, performs a case-insensitive substring match against
        product titles, descriptions, and category names.

        Args:
            query: Search query string (e.g. "wireless charger", "silicone utensils").
            page: Page number for pagination (1-indexed).
            page_size: Number of results per page (default 20, max 200).

        Returns:
            ProductSearchResult containing matching products and pagination info.

        Raises:
            SupplierError: If the search request fails (real API mode only).
        """
        if self.is_demo_mode:
            return self._demo_search(query, page, page_size)

        # TODO: real API — call CJDropship product list endpoint
        try:
            client = await self._get_client()
            resp = await client.get(
                "/product/list",
                params={
                    "productNameEn": query,
                    "pageNum": page,
                    "pageSize": min(page_size, 200),
                },
            )
            if resp.status_code >= 400:
                raise SupplierError(
                    f"CJDropship API error {resp.status_code}: {resp.text[:200]}",
                    status_code=resp.status_code,
                    supplier="cjdropship",
                )
            # TODO: real API — parse response and map to SupplierProduct models
            data = resp.json()
            return ProductSearchResult(
                products=[],
                total_count=data.get("data", {}).get("total", 0),
                page=page,
                page_size=page_size,
            )
        except httpx.HTTPError as exc:
            raise SupplierError(
                f"CJDropship API request failed: {exc}",
                supplier="cjdropship",
            ) from exc

    async def get_product(self, product_id: str) -> SupplierProduct:
        """
        Fetch a single product by its CJDropship product ID.

        In demo mode, looks up the product in the built-in demo data set.

        Args:
            product_id: CJDropship product ID (e.g. "CJ-ELEC-2891734").

        Returns:
            SupplierProduct with full details, variants, shipping, and ratings.

        Raises:
            SupplierError: If the product is not found or the API request fails.
        """
        if self.is_demo_mode:
            return self._demo_get_product(product_id)

        # TODO: real API — call CJDropship product detail endpoint
        try:
            client = await self._get_client()
            resp = await client.get(f"/product/query", params={"pid": product_id})
            if resp.status_code >= 400:
                raise SupplierError(
                    f"CJDropship API error {resp.status_code}: {resp.text[:200]}",
                    status_code=resp.status_code,
                    supplier="cjdropship",
                )
            # TODO: real API — parse response and map to SupplierProduct
            raise SupplierError(
                "Real API response parsing not yet implemented",
                supplier="cjdropship",
            )
        except httpx.HTTPError as exc:
            raise SupplierError(
                f"CJDropship API request failed: {exc}",
                supplier="cjdropship",
            ) from exc

    async def get_product_by_url(self, url: str) -> SupplierProduct:
        """
        Fetch a product by its CJDropship URL.

        Extracts the product ID from the URL and delegates to ``get_product()``.

        Args:
            url: Full CJDropship product URL
                (e.g. "https://cjdropshipping.com/product/CJ-ELEC-2891734").

        Returns:
            SupplierProduct with full details, variants, shipping, and ratings.

        Raises:
            SupplierError: If the URL cannot be parsed or the product is not found.
        """
        product_id = _extract_product_id(url)
        return await self.get_product(product_id)

    def _demo_search(
        self, query: str, page: int, page_size: int
    ) -> ProductSearchResult:
        """
        Search demo products by matching query against title, description, and category.

        Args:
            query: Search query string (case-insensitive).
            page: Page number (1-indexed).
            page_size: Results per page.

        Returns:
            ProductSearchResult with matching demo products.
        """
        query_lower = query.lower()
        matching = [
            p for p in self._demo_products
            if (
                query_lower in p["title"].lower()
                or query_lower in p["description"].lower()
                or query_lower in p.get("category", "").lower()
            )
        ]

        total = len(matching)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = matching[start:end]

        products = [_dict_to_product(d) for d in page_items]
        return ProductSearchResult(
            products=products,
            total_count=total,
            page=page,
            page_size=page_size,
        )

    def _demo_get_product(self, product_id: str) -> SupplierProduct:
        """
        Look up a demo product by ID.

        Args:
            product_id: CJDropship product ID string.

        Returns:
            SupplierProduct if found.

        Raises:
            SupplierError: If no demo product matches the given ID.
        """
        for p in self._demo_products:
            if p["id"] == product_id:
                return _dict_to_product(p)
        raise SupplierError(
            f"Product not found: {product_id}",
            status_code=404,
            supplier="cjdropship",
        )
