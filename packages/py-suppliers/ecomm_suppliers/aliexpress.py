"""
AliExpress supplier client integration.

For Developers:
    Uses the AliExpress Affiliate/Open Platform API when an API key is
    provided. Falls back to realistic demo data when no key is configured,
    allowing full development and testing without API credentials.

    Real API integration points are stubbed and clearly marked with
    ``# TODO: real API`` comments for future implementation.

For QA Engineers:
    In demo mode the client returns a fixed set of 24 products across
    electronics, fashion, home, and beauty categories. Product IDs are
    stable and deterministic, so assertions can target specific products.

For End Users:
    Browse and import products from AliExpress into your store. Products
    include full details, variants, images, shipping estimates, and ratings.
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

# AliExpress Open Platform base URL (real API)
_API_BASE = "https://api-sg.aliexpress.com/sync"

# Pattern to extract product ID from AliExpress URLs
_URL_PATTERN = re.compile(r"/item/(\d+)\.html|/i/(\d+)\.html|product/(\d+)")


def _extract_product_id(url: str) -> str:
    """
    Extract the AliExpress product ID from a product URL.

    Args:
        url: Full AliExpress product URL.

    Returns:
        Product ID string.

    Raises:
        SupplierError: If the URL does not contain a recognizable product ID.
    """
    match = _URL_PATTERN.search(url)
    if match:
        # Return the first non-None captured group
        return next(g for g in match.groups() if g is not None)
    raise SupplierError(
        f"Could not extract product ID from AliExpress URL: {url}",
        supplier="aliexpress",
    )


def _build_demo_products() -> list[dict[str, Any]]:
    """
    Build a list of realistic demo product dicts for AliExpress.

    Returns:
        List of 24 product data dicts spanning electronics, fashion, home, and beauty.
    """
    return [
        # ── Electronics (6 products) ──────────────────────────────────
        {
            "id": "1005006841237901",
            "title": "TWS Wireless Bluetooth 5.3 Earbuds with Active Noise Cancelling",
            "description": (
                "Premium TWS earbuds featuring Bluetooth 5.3 connectivity, hybrid active "
                "noise cancellation up to 35dB, transparency mode, and 30-hour battery life "
                "with charging case. IPX5 waterproof rating for workouts. Touch controls "
                "with customizable gestures. Supports AAC and SBC codecs for high-quality "
                "audio streaming."
            ),
            "price": "18.74",
            "category": "electronics",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/S9d3e7a1b2c4f4a8e9f.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/S1a2b3c4d5e6f7a8b9c.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/Sf1e2d3c4b5a6f7e8d9.jpg",
            ],
            "variants": [
                {"name": "Color: Black", "sku": "AE-TWS-BK", "price": "18.74", "stock": 4832, "attrs": {"color": "Black"}},
                {"name": "Color: White", "sku": "AE-TWS-WH", "price": "18.74", "stock": 3291, "attrs": {"color": "White"}},
                {"name": "Color: Navy Blue", "sku": "AE-TWS-NB", "price": "19.49", "stock": 1847, "attrs": {"color": "Navy Blue"}},
            ],
            "shipping": {"min": 12, "max": 20, "cost": "0.00", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.6, "count": 12847, "positive": 94.2},
        },
        {
            "id": "1005007192384502",
            "title": "USB-C Docking Station 12-in-1 Triple Display HDMI Hub",
            "description": (
                "12-in-1 USB-C docking station with triple display support: 2x HDMI 4K@60Hz, "
                "1x VGA. Features 100W Power Delivery pass-through, Gigabit Ethernet, "
                "3x USB-A 3.0, 1x USB-C 3.0, SD/TF card reader, and 3.5mm audio jack. "
                "Compatible with MacBook Pro, Dell XPS, and Thunderbolt 3/4 laptops."
            ),
            "price": "32.89",
            "category": "electronics",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/H2a3b4c5d6e7f8a9b0c.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/H1b2c3d4e5f6a7b8c9d.jpg",
            ],
            "variants": [
                {"name": "Type: 12-in-1", "sku": "AE-DOCK-12", "price": "32.89", "stock": 2156, "attrs": {"type": "12-in-1"}},
                {"name": "Type: 8-in-1", "sku": "AE-DOCK-8", "price": "24.49", "stock": 3487, "attrs": {"type": "8-in-1"}},
            ],
            "shipping": {"min": 10, "max": 18, "cost": "2.48", "method": "ePacket", "from": "CN"},
            "rating": {"avg": 4.4, "count": 5632, "positive": 91.8},
        },
        {
            "id": "1005006503928103",
            "title": "Portable Mini Projector 1080P WiFi 6 Bluetooth 5.2 Home Theater",
            "description": (
                "Compact LED projector with native 1080P resolution, WiFi 6 for wireless "
                "screen mirroring, Bluetooth 5.2 for external speakers, and 200 ANSI lumens. "
                "Built-in stereo speakers. Supports HDMI, USB, and TF card input. "
                "Keystone correction +/- 50 degrees. Ideal for home cinema and outdoor movies."
            ),
            "price": "67.43",
            "category": "electronics",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/P3c4d5e6f7a8b9c0d1e.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/P2d3e4f5a6b7c8d9e0f.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/P1e2f3a4b5c6d7e8f9a.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/P4f5a6b7c8d9e0f1a2b.jpg",
            ],
            "variants": [
                {"name": "Color: White", "sku": "AE-PROJ-WH", "price": "67.43", "stock": 892, "attrs": {"color": "White"}},
                {"name": "Color: Black", "sku": "AE-PROJ-BK", "price": "67.43", "stock": 1104, "attrs": {"color": "Black"}},
            ],
            "shipping": {"min": 15, "max": 25, "cost": "5.99", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.3, "count": 3218, "positive": 89.5},
        },
        {
            "id": "1005007458192604",
            "title": "Smart Watch Ultra 2.1 Inch AMOLED Fitness Tracker IP68",
            "description": (
                "Premium smartwatch with 2.1 inch AMOLED always-on display, 410x502 "
                "resolution. IP68 waterproof. Heart rate, SpO2, sleep, and stress monitoring. "
                "120+ sports modes. GPS tracking. Bluetooth calling. 7-day battery life. "
                "Compatible with Android 5.0+ and iOS 12+."
            ),
            "price": "24.56",
            "category": "electronics",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/W4d5e6f7a8b9c0d1e2f.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/W3e4f5a6b7c8d9e0f1a.jpg",
            ],
            "variants": [
                {"name": "Color: Black", "sku": "AE-WATCH-BK", "price": "24.56", "stock": 6721, "attrs": {"color": "Black"}},
                {"name": "Color: Silver", "sku": "AE-WATCH-SL", "price": "24.56", "stock": 4203, "attrs": {"color": "Silver"}},
                {"name": "Color: Rose Gold", "sku": "AE-WATCH-RG", "price": "26.99", "stock": 2847, "attrs": {"color": "Rose Gold"}},
            ],
            "shipping": {"min": 12, "max": 20, "cost": "0.00", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.5, "count": 18432, "positive": 93.7},
        },
        {
            "id": "1005006287451305",
            "title": "Mechanical Gaming Keyboard 75% Hot-Swappable RGB Gasket Mount",
            "description": (
                "75% layout mechanical keyboard with gasket mount structure for a softer "
                "typing feel. Hot-swappable switches (3/5 pin). Per-key RGB backlighting "
                "with 19 lighting effects. PBT double-shot keycaps. USB-C detachable cable. "
                "N-key rollover. Compatible with Windows, Mac, and Linux."
            ),
            "price": "39.87",
            "category": "electronics",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/K5e6f7a8b9c0d1e2f3a.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/K4f5a6b7c8d9e0f1a2b.jpg",
            ],
            "variants": [
                {"name": "Switch: Gateron Red", "sku": "AE-KB-RED", "price": "39.87", "stock": 1532, "attrs": {"switch": "Gateron Red"}},
                {"name": "Switch: Gateron Brown", "sku": "AE-KB-BRN", "price": "39.87", "stock": 1847, "attrs": {"switch": "Gateron Brown"}},
                {"name": "Switch: Gateron Blue", "sku": "AE-KB-BLU", "price": "39.87", "stock": 923, "attrs": {"switch": "Gateron Blue"}},
            ],
            "shipping": {"min": 10, "max": 18, "cost": "3.29", "method": "ePacket", "from": "CN"},
            "rating": {"avg": 4.7, "count": 8921, "positive": 96.1},
        },
        {
            "id": "1005007631284506",
            "title": "4K Action Camera WiFi Waterproof 170 Degree Wide Angle EIS",
            "description": (
                "4K/60fps action camera with electronic image stabilization (EIS). "
                "170-degree wide-angle lens. WiFi for phone preview and control. "
                "Waterproof to 40m with included housing. 2-inch IPS touchscreen. "
                "Supports external microphone. Includes mounting accessories kit."
            ),
            "price": "42.15",
            "category": "electronics",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/A6f7a8b9c0d1e2f3a4b.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/A5a6b7c8d9e0f1a2b3c.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/A4b5c6d7e8f9a0b1c2d.jpg",
            ],
            "variants": [
                {"name": "Bundle: Camera Only", "sku": "AE-CAM-ONLY", "price": "42.15", "stock": 2341, "attrs": {"bundle": "Camera Only"}},
                {"name": "Bundle: Camera + Extra Battery", "sku": "AE-CAM-BAT", "price": "48.99", "stock": 1876, "attrs": {"bundle": "Camera + Extra Battery"}},
            ],
            "shipping": {"min": 12, "max": 22, "cost": "0.00", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.4, "count": 6432, "positive": 92.3},
        },
        # ── Fashion (6 products) ─────────────────────────────────────
        {
            "id": "1005006912847207",
            "title": "Vintage Oversized Polarized Sunglasses UV400 Acetate Frame",
            "description": (
                "Retro oversized sunglasses with premium acetate frame and TAC polarized "
                "lenses. UV400 protection blocks 99.9% of harmful UVA/UVB rays. "
                "Lightweight at 28g. Comes with microfiber pouch, hard case, and cleaning "
                "cloth. Available in tortoise, black, and olive colorways."
            ),
            "price": "8.47",
            "category": "fashion",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/F7a8b9c0d1e2f3a4b5c.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/F6b7c8d9e0f1a2b3c4d.jpg",
            ],
            "variants": [
                {"name": "Color: Tortoise", "sku": "AE-SUN-TRT", "price": "8.47", "stock": 8743, "attrs": {"color": "Tortoise"}},
                {"name": "Color: Matte Black", "sku": "AE-SUN-BK", "price": "8.47", "stock": 12321, "attrs": {"color": "Matte Black"}},
                {"name": "Color: Olive Green", "sku": "AE-SUN-OL", "price": "8.47", "stock": 5632, "attrs": {"color": "Olive Green"}},
            ],
            "shipping": {"min": 15, "max": 25, "cost": "0.00", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.5, "count": 21543, "positive": 95.4},
        },
        {
            "id": "1005007381926408",
            "title": "Men's Casual Linen Shirt Long Sleeve Mandarin Collar",
            "description": (
                "100% linen casual shirt with mandarin collar and button-front closure. "
                "Relaxed fit for comfortable all-day wear. Pre-washed for softness. "
                "Chest pocket detail. Available in 8 earth-tone colors. "
                "Machine washable. Sizes S through 3XL."
            ),
            "price": "14.89",
            "category": "fashion",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/M8b9c0d1e2f3a4b5c6d.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/M7c8d9e0f1a2b3c4d5e.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/M6d9e0f1a2b3c4d5e6f.jpg",
            ],
            "variants": [
                {"name": "Color: Khaki, Size: M", "sku": "AE-LINEN-KH-M", "price": "14.89", "stock": 723, "attrs": {"color": "Khaki", "size": "M"}},
                {"name": "Color: Khaki, Size: L", "sku": "AE-LINEN-KH-L", "price": "14.89", "stock": 891, "attrs": {"color": "Khaki", "size": "L"}},
                {"name": "Color: White, Size: M", "sku": "AE-LINEN-WH-M", "price": "14.89", "stock": 654, "attrs": {"color": "White", "size": "M"}},
                {"name": "Color: White, Size: L", "sku": "AE-LINEN-WH-L", "price": "14.89", "stock": 512, "attrs": {"color": "White", "size": "L"}},
                {"name": "Color: Navy, Size: M", "sku": "AE-LINEN-NV-M", "price": "14.89", "stock": 437, "attrs": {"color": "Navy", "size": "M"}},
                {"name": "Color: Navy, Size: L", "sku": "AE-LINEN-NV-L", "price": "14.89", "stock": 621, "attrs": {"color": "Navy", "size": "L"}},
            ],
            "shipping": {"min": 12, "max": 20, "cost": "2.99", "method": "ePacket", "from": "CN"},
            "rating": {"avg": 4.3, "count": 7832, "positive": 90.1},
        },
        {
            "id": "1005006724183909",
            "title": "Women's Crossbody Bag Genuine Leather Minimalist Design",
            "description": (
                "Genuine cowhide leather crossbody bag with minimalist design. "
                "Adjustable strap (120cm max). Top zipper closure with inner zip pocket "
                "and 2 slip pockets. Dimensions: 22x15x8cm. Silver-tone hardware. "
                "RFID-blocking lining. Dust bag included."
            ),
            "price": "22.34",
            "category": "fashion",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/B9c0d1e2f3a4b5c6d7e.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/B8d9e0f1a2b3c4d5e6f.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/B7e0f1a2b3c4d5e6f7a.jpg",
            ],
            "variants": [
                {"name": "Color: Black", "sku": "AE-BAG-BK", "price": "22.34", "stock": 3421, "attrs": {"color": "Black"}},
                {"name": "Color: Brown", "sku": "AE-BAG-BR", "price": "22.34", "stock": 2876, "attrs": {"color": "Brown"}},
                {"name": "Color: Burgundy", "sku": "AE-BAG-BG", "price": "23.99", "stock": 1543, "attrs": {"color": "Burgundy"}},
                {"name": "Color: Tan", "sku": "AE-BAG-TN", "price": "22.34", "stock": 2103, "attrs": {"color": "Tan"}},
            ],
            "shipping": {"min": 10, "max": 18, "cost": "0.00", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.6, "count": 14287, "positive": 94.8},
        },
        {
            "id": "1005007543821710",
            "title": "Unisex Canvas Sneakers Vulcanized Low-Top Classic Design",
            "description": (
                "Classic low-top vulcanized canvas sneakers. Breathable cotton canvas "
                "upper with rubber toe cap. Cushioned insole. Non-slip rubber outsole. "
                "Lace-up closure. Unisex sizing (EU 36-47). Available in 12 colors. "
                "Lightweight and perfect for everyday casual wear."
            ),
            "price": "11.23",
            "category": "fashion",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/S0d1e2f3a4b5c6d7e8f.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/S9e0f1a2b3c4d5e6f7a.jpg",
            ],
            "variants": [
                {"name": "Color: White, Size: EU 40", "sku": "AE-SNK-WH-40", "price": "11.23", "stock": 1543, "attrs": {"color": "White", "size": "EU 40"}},
                {"name": "Color: White, Size: EU 42", "sku": "AE-SNK-WH-42", "price": "11.23", "stock": 1872, "attrs": {"color": "White", "size": "EU 42"}},
                {"name": "Color: Black, Size: EU 40", "sku": "AE-SNK-BK-40", "price": "11.23", "stock": 2341, "attrs": {"color": "Black", "size": "EU 40"}},
                {"name": "Color: Black, Size: EU 42", "sku": "AE-SNK-BK-42", "price": "11.23", "stock": 2654, "attrs": {"color": "Black", "size": "EU 42"}},
                {"name": "Color: Red, Size: EU 40", "sku": "AE-SNK-RD-40", "price": "11.23", "stock": 987, "attrs": {"color": "Red", "size": "EU 40"}},
            ],
            "shipping": {"min": 15, "max": 25, "cost": "3.49", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.4, "count": 32187, "positive": 93.2},
        },
        {
            "id": "1005006891274311",
            "title": "Titanium Steel Cuban Link Chain Necklace Waterproof 18K Gold Plated",
            "description": (
                "Cuban link chain necklace in titanium steel with 18K gold PVD coating. "
                "Waterproof and tarnish-resistant. Width options: 5mm, 7mm, 9mm. "
                "Length options: 45cm, 50cm, 55cm, 60cm. Lobster claw clasp. "
                "Weight: 35-80g depending on size. Hypoallergenic."
            ),
            "price": "9.87",
            "category": "fashion",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/C1e2f3a4b5c6d7e8f9a.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/C0f1a2b3c4d5e6f7a8b.jpg",
            ],
            "variants": [
                {"name": "Width: 5mm, Length: 50cm", "sku": "AE-CHAIN-5-50", "price": "9.87", "stock": 5432, "attrs": {"width": "5mm", "length": "50cm"}},
                {"name": "Width: 7mm, Length: 50cm", "sku": "AE-CHAIN-7-50", "price": "13.49", "stock": 3876, "attrs": {"width": "7mm", "length": "50cm"}},
                {"name": "Width: 9mm, Length: 50cm", "sku": "AE-CHAIN-9-50", "price": "17.99", "stock": 2143, "attrs": {"width": "9mm", "length": "50cm"}},
                {"name": "Width: 5mm, Length: 60cm", "sku": "AE-CHAIN-5-60", "price": "11.49", "stock": 4321, "attrs": {"width": "5mm", "length": "60cm"}},
            ],
            "shipping": {"min": 12, "max": 20, "cost": "0.00", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.7, "count": 28743, "positive": 96.3},
        },
        {
            "id": "1005007218374212",
            "title": "Women's High Waist Wide Leg Pants Pleated Palazzo Trousers",
            "description": (
                "Elegant wide-leg palazzo pants with high waist and pleated front. "
                "Lightweight chiffon-like polyester blend. Hidden side zipper. "
                "Flowy drape for a sophisticated silhouette. Available in solid "
                "colors and prints. Sizes XS through XXL. Length: full/ankle."
            ),
            "price": "16.43",
            "category": "fashion",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/T2f3a4b5c6d7e8f9a0b.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/T1a2b3c4d5e6f7a8b9c.jpg",
            ],
            "variants": [
                {"name": "Color: Black, Size: M", "sku": "AE-PANT-BK-M", "price": "16.43", "stock": 1243, "attrs": {"color": "Black", "size": "M"}},
                {"name": "Color: Black, Size: L", "sku": "AE-PANT-BK-L", "price": "16.43", "stock": 987, "attrs": {"color": "Black", "size": "L"}},
                {"name": "Color: Beige, Size: M", "sku": "AE-PANT-BG-M", "price": "16.43", "stock": 876, "attrs": {"color": "Beige", "size": "M"}},
                {"name": "Color: Beige, Size: L", "sku": "AE-PANT-BG-L", "price": "16.43", "stock": 654, "attrs": {"color": "Beige", "size": "L"}},
            ],
            "shipping": {"min": 12, "max": 22, "cost": "2.49", "method": "ePacket", "from": "CN"},
            "rating": {"avg": 4.2, "count": 9832, "positive": 88.7},
        },
        # ── Home & Garden (6 products) ───────────────────────────────
        {
            "id": "1005006543219813",
            "title": "LED Strip Lights 10M RGB Smart WiFi App Control Music Sync",
            "description": (
                "10-meter LED strip light with WiFi smart control via Tuya/Smart Life app. "
                "RGB color changing with 16 million colors. Music sync mode with built-in "
                "microphone. Works with Alexa and Google Home. Cuttable every 3 LEDs. "
                "Self-adhesive 3M tape backing. 12V power adapter included."
            ),
            "price": "7.92",
            "category": "home",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/H3a4b5c6d7e8f9a0b1c.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/H2b3c4d5e6f7a8b9c0d.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/H1c4d5e6f7a8b9c0d1e.jpg",
            ],
            "variants": [
                {"name": "Length: 5M", "sku": "AE-LED-5M", "price": "7.92", "stock": 14321, "attrs": {"length": "5M"}},
                {"name": "Length: 10M", "sku": "AE-LED-10M", "price": "12.49", "stock": 9876, "attrs": {"length": "10M"}},
                {"name": "Length: 15M", "sku": "AE-LED-15M", "price": "16.99", "stock": 5432, "attrs": {"length": "15M"}},
                {"name": "Length: 20M", "sku": "AE-LED-20M", "price": "21.49", "stock": 3210, "attrs": {"length": "20M"}},
            ],
            "shipping": {"min": 12, "max": 20, "cost": "0.00", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.3, "count": 45321, "positive": 91.2},
        },
        {
            "id": "1005007382719414",
            "title": "Electric Milk Frother Handheld Rechargeable 3-Speed Stainless Steel",
            "description": (
                "Rechargeable handheld milk frother with 3-speed motor (12000/16000/19000 RPM). "
                "304 stainless steel whisk head. Creates rich froth in 15-20 seconds. "
                "USB-C charging with indicator light. Includes stand/holder. "
                "Works for cappuccino, latte, matcha, protein shakes, and eggs."
            ),
            "price": "6.34",
            "category": "home",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/L4b5c6d7e8f9a0b1c2d.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/L3c4d5e6f7a8b9c0d1e.jpg",
            ],
            "variants": [
                {"name": "Color: Silver", "sku": "AE-FROTH-SL", "price": "6.34", "stock": 8765, "attrs": {"color": "Silver"}},
                {"name": "Color: Black", "sku": "AE-FROTH-BK", "price": "6.34", "stock": 7432, "attrs": {"color": "Black"}},
            ],
            "shipping": {"min": 12, "max": 20, "cost": "1.49", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.5, "count": 18743, "positive": 93.8},
        },
        {
            "id": "1005006821937615",
            "title": "Minimalist Floating Wall Shelf Set Iron and Wood Rustic Decor",
            "description": (
                "Set of 3 floating wall shelves with rustic wood boards and black iron "
                "brackets. Dimensions: 40x15cm, 30x15cm, 20x15cm. Paulownia wood with "
                "natural grain finish. Load capacity: 5kg per shelf. Includes mounting "
                "hardware. Perfect for living room, bedroom, or bathroom display."
            ),
            "price": "13.78",
            "category": "home",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/R5c6d7e8f9a0b1c2d3e.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/R4d5e6f7a8b9c0d1e2f.jpg",
            ],
            "variants": [
                {"name": "Style: 3-Piece Set", "sku": "AE-SHELF-3", "price": "13.78", "stock": 4321, "attrs": {"style": "3-Piece Set"}},
                {"name": "Style: Single Large", "sku": "AE-SHELF-1L", "price": "8.99", "stock": 2876, "attrs": {"style": "Single Large"}},
            ],
            "shipping": {"min": 15, "max": 25, "cost": "4.99", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.4, "count": 7654, "positive": 92.1},
        },
        {
            "id": "1005007492837116",
            "title": "Bamboo Desk Organizer with Wireless Charging Pad Multi-Slot",
            "description": (
                "Premium bamboo desktop organizer with built-in 15W Qi wireless charging pad. "
                "Multiple compartments for phone, tablet, pens, glasses, and accessories. "
                "Dimensions: 28x20x15cm. USB-C input. Compatible with all Qi-enabled devices. "
                "Anti-slip rubber feet. Natural bamboo finish."
            ),
            "price": "19.45",
            "category": "home",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/D6d7e8f9a0b1c2d3e4f.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/D5e6f7a8b9c0d1e2f3a.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/D4f7a8b9c0d1e2f3a4b.jpg",
            ],
            "variants": [
                {"name": "Type: With Wireless Charger", "sku": "AE-DESK-WC", "price": "19.45", "stock": 2654, "attrs": {"type": "With Wireless Charger"}},
                {"name": "Type: Without Charger", "sku": "AE-DESK-NC", "price": "12.99", "stock": 3987, "attrs": {"type": "Without Charger"}},
            ],
            "shipping": {"min": 12, "max": 22, "cost": "3.49", "method": "ePacket", "from": "CN"},
            "rating": {"avg": 4.6, "count": 5432, "positive": 94.5},
        },
        {
            "id": "1005006917284317",
            "title": "Aromatherapy Essential Oil Diffuser 300ml Wood Grain Ultrasonic",
            "description": (
                "300ml capacity ultrasonic essential oil diffuser with wood grain finish. "
                "7-color LED night light. Timer settings: 1H/3H/6H/continuous. "
                "Whisper-quiet operation (<36dB). Auto shut-off when water runs low. "
                "Covers up to 30 sqm. BPA-free ABS material. Comes with measuring cup."
            ),
            "price": "11.23",
            "category": "home",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/G7e8f9a0b1c2d3e4f5a.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/G6f7a8b9c0d1e2f3a4b.jpg",
            ],
            "variants": [
                {"name": "Color: Light Wood", "sku": "AE-DIFF-LW", "price": "11.23", "stock": 6543, "attrs": {"color": "Light Wood"}},
                {"name": "Color: Dark Wood", "sku": "AE-DIFF-DW", "price": "11.23", "stock": 5432, "attrs": {"color": "Dark Wood"}},
                {"name": "Color: White", "sku": "AE-DIFF-WH", "price": "11.23", "stock": 4321, "attrs": {"color": "White"}},
            ],
            "shipping": {"min": 12, "max": 20, "cost": "0.00", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.5, "count": 23456, "positive": 94.1},
        },
        {
            "id": "1005007291847518",
            "title": "Portable Blender Personal Size USB-C Rechargeable 6 Blades 380ml",
            "description": (
                "Personal portable blender with 6 stainless steel blades and 380ml capacity. "
                "USB-C rechargeable with 4000mAh battery (15-20 blends per charge). "
                "One-button operation. BPA-free Tritan material. Blend smoothies, shakes, "
                "and baby food in 30 seconds. Safety lock prevents accidental start."
            ),
            "price": "9.87",
            "category": "home",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/E8f9a0b1c2d3e4f5a6b.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/E7a8b9c0d1e2f3a4b5c.jpg",
            ],
            "variants": [
                {"name": "Color: Pink", "sku": "AE-BLEND-PK", "price": "9.87", "stock": 7654, "attrs": {"color": "Pink"}},
                {"name": "Color: White", "sku": "AE-BLEND-WH", "price": "9.87", "stock": 8765, "attrs": {"color": "White"}},
                {"name": "Color: Blue", "sku": "AE-BLEND-BL", "price": "9.87", "stock": 5432, "attrs": {"color": "Blue"}},
                {"name": "Color: Green", "sku": "AE-BLEND-GR", "price": "9.87", "stock": 4321, "attrs": {"color": "Green"}},
            ],
            "shipping": {"min": 12, "max": 20, "cost": "1.99", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.3, "count": 34567, "positive": 91.5},
        },
        # ── Beauty & Health (6 products) ─────────────────────────────
        {
            "id": "1005006432918719",
            "title": "Jade Face Roller and Gua Sha Set Natural Xiuyan Jade Skincare Tool",
            "description": (
                "Authentic Xiuyan jade face roller with dual-ended design (large roller "
                "for cheeks/forehead, small roller for under-eye area). Includes matching "
                "gua sha scraping tool. Zinc alloy frame with silent rolling. "
                "Comes in premium gift box. Promotes lymphatic drainage and reduces puffiness."
            ),
            "price": "4.87",
            "category": "beauty",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/J9a0b1c2d3e4f5a6b7c.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/J8b9c0d1e2f3a4b5c6d.jpg",
            ],
            "variants": [
                {"name": "Material: Jade Green", "sku": "AE-JADE-GR", "price": "4.87", "stock": 15432, "attrs": {"material": "Jade Green"}},
                {"name": "Material: Rose Quartz", "sku": "AE-JADE-RQ", "price": "5.49", "stock": 12876, "attrs": {"material": "Rose Quartz"}},
                {"name": "Material: Amethyst", "sku": "AE-JADE-AM", "price": "6.99", "stock": 8432, "attrs": {"material": "Amethyst"}},
            ],
            "shipping": {"min": 12, "max": 20, "cost": "0.00", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.6, "count": 43210, "positive": 95.7},
        },
        {
            "id": "1005007183724620",
            "title": "Electric Scalp Massager IPX7 Waterproof 4 Massage Heads",
            "description": (
                "Electric scalp massager with 4 detachable massage heads and 84 silicone "
                "kneading nodes. 2 vibration modes and 2 rotation directions. IPX7 waterproof "
                "for shower use. USB-C rechargeable with 90-minute battery life. "
                "Promotes blood circulation and relieves headache tension."
            ),
            "price": "12.34",
            "category": "beauty",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/N0b1c2d3e4f5a6b7c8d.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/N9c0d1e2f3a4b5c6d7e.jpg",
            ],
            "variants": [
                {"name": "Color: White", "sku": "AE-SCALP-WH", "price": "12.34", "stock": 5432, "attrs": {"color": "White"}},
                {"name": "Color: Purple", "sku": "AE-SCALP-PR", "price": "12.34", "stock": 4321, "attrs": {"color": "Purple"}},
                {"name": "Color: Rose Gold", "sku": "AE-SCALP-RG", "price": "13.99", "stock": 3210, "attrs": {"color": "Rose Gold"}},
            ],
            "shipping": {"min": 12, "max": 20, "cost": "1.99", "method": "ePacket", "from": "CN"},
            "rating": {"avg": 4.4, "count": 16543, "positive": 92.4},
        },
        {
            "id": "1005006827194321",
            "title": "Vitamin C Serum 30ml with Hyaluronic Acid Brightening Anti-Aging",
            "description": (
                "30ml Vitamin C brightening serum with 20% L-Ascorbic Acid, Hyaluronic Acid, "
                "and Vitamin E. Reduces dark spots and hyperpigmentation. Boosts collagen "
                "production. Lightweight, fast-absorbing formula. Suitable for all skin types. "
                "Cruelty-free. Dropper applicator included."
            ),
            "price": "3.47",
            "category": "beauty",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/V1c2d3e4f5a6b7c8d9e.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/V0d1e2f3a4b5c6d7e8f.jpg",
            ],
            "variants": [
                {"name": "Size: 30ml", "sku": "AE-VITC-30", "price": "3.47", "stock": 23456, "attrs": {"size": "30ml"}},
                {"name": "Size: 50ml", "sku": "AE-VITC-50", "price": "5.29", "stock": 15432, "attrs": {"size": "50ml"}},
            ],
            "shipping": {"min": 15, "max": 25, "cost": "0.00", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.3, "count": 28765, "positive": 90.8},
        },
        {
            "id": "1005007492183722",
            "title": "LED Teeth Whitening Kit Blue Light Accelerator Gel Pen Set",
            "description": (
                "At-home LED teeth whitening kit with blue light accelerator mouthpiece. "
                "Includes 3 whitening gel pens (35% carbamide peroxide). 16-minute timer "
                "with auto shut-off. USB rechargeable. Removes stains from coffee, tea, and "
                "wine. Up to 8 shades whiter in 7 days. Enamel-safe formula."
            ),
            "price": "8.92",
            "category": "beauty",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/U2d3e4f5a6b7c8d9e0f.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/U1e2f3a4b5c6d7e8f9a.jpg",
            ],
            "variants": [
                {"name": "Kit: Standard (3 gels)", "sku": "AE-TEETH-STD", "price": "8.92", "stock": 6543, "attrs": {"kit": "Standard"}},
                {"name": "Kit: Premium (6 gels)", "sku": "AE-TEETH-PRE", "price": "13.49", "stock": 3876, "attrs": {"kit": "Premium"}},
            ],
            "shipping": {"min": 12, "max": 20, "cost": "1.49", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.1, "count": 12345, "positive": 87.3},
        },
        {
            "id": "1005006738291423",
            "title": "Derma Roller Microneedling Set 0.25mm Titanium 540 Needles",
            "description": (
                "Professional-grade derma roller with 540 titanium micro-needles at 0.25mm "
                "depth. Stimulates collagen and elastin production. Enhances skincare "
                "absorption by up to 300%. Includes protective travel case and spray bottle. "
                "Replace roller head every 3 months. Suitable for face, neck, and body."
            ),
            "price": "2.89",
            "category": "beauty",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/X3e4f5a6b7c8d9e0f1a.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/X2f3a4b5c6d7e8f9a0b.jpg",
            ],
            "variants": [
                {"name": "Needle: 0.25mm", "sku": "AE-DERMA-025", "price": "2.89", "stock": 18765, "attrs": {"needle": "0.25mm"}},
                {"name": "Needle: 0.50mm", "sku": "AE-DERMA-050", "price": "3.29", "stock": 14321, "attrs": {"needle": "0.50mm"}},
                {"name": "Needle: 1.00mm", "sku": "AE-DERMA-100", "price": "3.49", "stock": 9876, "attrs": {"needle": "1.00mm"}},
            ],
            "shipping": {"min": 12, "max": 20, "cost": "0.00", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.5, "count": 38921, "positive": 94.6},
        },
        {
            "id": "1005007321847924",
            "title": "Silk Satin Pillowcase Set of 2 Mulberry Silk Hair and Skin Care",
            "description": (
                "Set of 2 pillowcases in 100% 6A grade mulberry silk (22 momme). "
                "Reduces hair frizz and prevents sleep creases. Hidden zipper closure. "
                "Standard size: 50x75cm. OEKO-TEX certified. Machine washable on delicate. "
                "Thermoregulating for year-round comfort."
            ),
            "price": "15.67",
            "category": "beauty",
            "images": [
                "https://ae-pic-a1.aliexpress-media.com/kf/Y4f5a6b7c8d9e0f1a2b.jpg",
                "https://ae-pic-a1.aliexpress-media.com/kf/Y3a4b5c6d7e8f9a0b1c.jpg",
            ],
            "variants": [
                {"name": "Color: Champagne", "sku": "AE-SILK-CH", "price": "15.67", "stock": 4321, "attrs": {"color": "Champagne"}},
                {"name": "Color: Silver Grey", "sku": "AE-SILK-SG", "price": "15.67", "stock": 3876, "attrs": {"color": "Silver Grey"}},
                {"name": "Color: Blush Pink", "sku": "AE-SILK-BP", "price": "15.67", "stock": 5432, "attrs": {"color": "Blush Pink"}},
                {"name": "Color: White", "sku": "AE-SILK-WH", "price": "15.67", "stock": 6543, "attrs": {"color": "White"}},
                {"name": "Color: Navy", "sku": "AE-SILK-NV", "price": "15.67", "stock": 2987, "attrs": {"color": "Navy"}},
            ],
            "shipping": {"min": 12, "max": 20, "cost": "0.00", "method": "AliExpress Standard Shipping", "from": "CN"},
            "rating": {"avg": 4.7, "count": 19876, "positive": 96.2},
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
        source="aliexpress",
        source_id=data["id"],
        source_url=f"https://www.aliexpress.com/item/{data['id']}.html",
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


class AliExpressClient(BaseSupplierClient):
    """
    AliExpress supplier client for searching and importing products.

    For Developers:
        When ``api_key`` is provided, the client makes real HTTP calls to
        the AliExpress Open Platform API. When ``api_key`` is None, it
        returns realistic demo data for development and testing.

        Real API endpoints are stubbed with ``# TODO: real API`` markers.

    For QA Engineers:
        In demo mode, 24 products are available with stable IDs across
        4 categories: electronics, fashion, home, and beauty. Use
        ``search_products(query="electronics")`` to filter by category.

    For End Users:
        Import products from AliExpress by searching or pasting a product URL.

    Args:
        api_key: AliExpress Open Platform API key. If None, demo mode is used.
    """

    def __init__(self, api_key: str | None = None) -> None:
        """
        Initialize the AliExpress client.

        Args:
            api_key: AliExpress Open Platform API key.
                If not provided, the client operates in demo mode with mock data.
        """
        super().__init__(api_key=api_key)
        self._client: httpx.AsyncClient | None = None
        self._demo_products: list[dict[str, Any]] = _build_demo_products()

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create the shared httpx AsyncClient for real API calls.

        Returns:
            An httpx.AsyncClient instance configured for AliExpress API.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=_API_BASE,
                timeout=30.0,
                headers={"Content-Type": "application/json"},
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
        Search for products on AliExpress.

        In demo mode, performs a case-insensitive substring match against
        product titles, descriptions, and category names.

        Args:
            query: Search query string (e.g. "wireless earbuds", "yoga mat").
            page: Page number for pagination (1-indexed).
            page_size: Number of results per page (default 20, max 50).

        Returns:
            ProductSearchResult containing matching products and pagination info.

        Raises:
            SupplierError: If the search request fails (real API mode only).
        """
        if self.is_demo_mode:
            return self._demo_search(query, page, page_size)

        # TODO: real API — call AliExpress affiliate product search endpoint
        # Example endpoint: /aliexpress.affiliate.product.query
        try:
            client = await self._get_client()
            resp = await client.post(
                "/aliexpress.affiliate.product.query",
                json={
                    "app_key": self._api_key,
                    "keywords": query,
                    "page_no": page,
                    "page_size": min(page_size, 50),
                    "target_currency": "USD",
                    "target_language": "EN",
                    "sort": "SALE_PRICE_ASC",
                },
            )
            if resp.status_code >= 400:
                raise SupplierError(
                    f"AliExpress API error {resp.status_code}: {resp.text[:200]}",
                    status_code=resp.status_code,
                    supplier="aliexpress",
                )
            # TODO: real API — parse response and map to SupplierProduct models
            data = resp.json()
            return ProductSearchResult(
                products=[],
                total_count=data.get("total_record_count", 0),
                page=page,
                page_size=page_size,
            )
        except httpx.HTTPError as exc:
            raise SupplierError(
                f"AliExpress API request failed: {exc}",
                supplier="aliexpress",
            ) from exc

    async def get_product(self, product_id: str) -> SupplierProduct:
        """
        Fetch a single product by its AliExpress product ID.

        In demo mode, looks up the product in the built-in demo data set.

        Args:
            product_id: AliExpress product ID (numeric string).

        Returns:
            SupplierProduct with full details, variants, shipping, and ratings.

        Raises:
            SupplierError: If the product is not found or the API request fails.
        """
        if self.is_demo_mode:
            return self._demo_get_product(product_id)

        # TODO: real API — call AliExpress product detail endpoint
        # Example endpoint: /aliexpress.affiliate.product.detail
        try:
            client = await self._get_client()
            resp = await client.post(
                "/aliexpress.affiliate.product.detail",
                json={
                    "app_key": self._api_key,
                    "product_ids": product_id,
                    "target_currency": "USD",
                    "target_language": "EN",
                },
            )
            if resp.status_code >= 400:
                raise SupplierError(
                    f"AliExpress API error {resp.status_code}: {resp.text[:200]}",
                    status_code=resp.status_code,
                    supplier="aliexpress",
                )
            # TODO: real API — parse response and map to SupplierProduct
            raise SupplierError(
                "Real API response parsing not yet implemented",
                supplier="aliexpress",
            )
        except httpx.HTTPError as exc:
            raise SupplierError(
                f"AliExpress API request failed: {exc}",
                supplier="aliexpress",
            ) from exc

    async def get_product_by_url(self, url: str) -> SupplierProduct:
        """
        Fetch a product by its AliExpress URL.

        Extracts the product ID from the URL and delegates to ``get_product()``.

        Args:
            url: Full AliExpress product URL
                (e.g. "https://www.aliexpress.com/item/1005006841237901.html").

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
            product_id: AliExpress product ID string.

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
            supplier="aliexpress",
        )
