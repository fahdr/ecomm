#!/usr/bin/env npx tsx
/**
 * Seed script — populates the database with realistic demo data for all
 * platform features so you can manually test the dashboard and storefront.
 *
 * **Usage:**
 *   npx tsx scripts/seed.ts
 *
 * **Prerequisites:**
 *   - Backend running on http://localhost:8000
 *   - Database migrated (alembic upgrade head)
 *
 * **What it creates:**
 *   - 1 user account (demo@example.com / password123)
 *   - 1 store ("Volt Electronics") with Cyberpunk theme
 *   - 6 categories (4 top-level + 2 sub-categories)
 *   - 12 products with rich descriptions, Unsplash images, variants, and SEO metadata
 *     (includes low-stock items for inventory alerts, compare_at_price for Sale badges)
 *   - 3 suppliers linked to products
 *   - 5 discount codes (mix of percentage & fixed)
 *   - 4 tax rates (US states + UK VAT)
 *   - 3 gift cards
 *   - 3 customer accounts with addresses and wishlists
 *   - 12 product reviews
 *   - 4 orders with full lifecycle (pending → paid → shipped → delivered)
 *   - 1 refund
 *   - 3 customer segments
 *   - 4 upsell/cross-sell rules
 *   - 2 team member invitations
 *   - 2 webhook endpoints
 *   - 2 A/B tests
 *   - 1 custom domain
 *   - Order notes on all orders
 *   - Cyberpunk theme activated with custom block layout (countdown, carousel, trust badges)
 *
 * **For Developers:**
 *   Each section is self-contained and idempotent. If one feature fails,
 *   subsequent features will still attempt to seed. 409 responses are
 *   silently handled so you can re-run the script safely.
 *
 * **For QA Engineers:**
 *   After running, log in at http://localhost:3000 with demo@example.com
 *   and password123. Browse the storefront at http://localhost:3001?store=volt-electronics.
 *   Verify: product badges (New/Sale), inventory alerts (low-stock items),
 *   order notes, theme blocks, customer accounts.
 */

const API = "http://localhost:8000";

// ── Helpers ──────────────────────────────────────────────────────────────────

async function api(
  method: string,
  path: string,
  body?: unknown,
  token?: string
): Promise<any> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const text = await res.text();
  if (!res.ok) {
    // Don't throw on 409 (duplicate) — lets us re-run the script
    if (res.status === 409) {
      console.log(`  ⤳ Already exists (409), skipping`);
      return null;
    }
    throw new Error(`${method} ${path} → ${res.status}: ${text}`);
  }
  return text ? JSON.parse(text) : null;
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

// ── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  console.log("\n=== Dropshipping Platform — Seed Script ===\n");

  // ── 1. User ────────────────────────────────────────────────────────────────
  console.log("1. Creating user account...");
  let token: string;
  const authRes = await api("POST", "/api/v1/auth/register", {
    email: "demo@example.com",
    password: "password123",
  });
  if (authRes) {
    token = authRes.access_token;
    console.log("   ✓ Created demo@example.com / password123");
  } else {
    // 409 — user already exists, log in instead
    console.log("   ⤳ User exists, logging in...");
    const loginRes = await api("POST", "/api/v1/auth/login", {
      email: "demo@example.com",
      password: "password123",
    });
    token = loginRes.access_token;
    console.log("   ✓ Logged in as demo@example.com");
  }

  // Wait for token to be valid (DB commit race condition)
  await sleep(500);

  // ── 2. Store ───────────────────────────────────────────────────────────────
  console.log("\n2. Creating store...");
  let store: any;
  try {
    store = await api("POST", "/api/v1/stores", {
      name: "Volt Electronics",
      niche: "electronics",
      description: "Premium consumer electronics and accessories for the modern tech enthusiast. We source the latest gadgets directly from top manufacturers worldwide — laptops, smartphones, audio gear, and essential accessories at competitive prices with fast shipping.",
    }, token);
    console.log(`   ✓ Store "${store.name}" (slug: ${store.slug})`);
  } catch (e: any) {
    // Store might already exist — try to find it
    console.log("   ⤳ Store creation failed, fetching existing stores...");
    const stores = await api("GET", "/api/v1/stores", undefined, token);
    const items = stores.items || stores;
    store = Array.isArray(items) ? items[0] : items;
    if (!store) throw new Error("No store found and creation failed");
    console.log(`   ✓ Using existing store "${store.name}" (${store.id})`);
  }

  const storeId = store.id;
  const slug = store.slug;

  // Wait for store creation to commit (DB race condition)
  await sleep(500);

  // ── 3. Categories ──────────────────────────────────────────────────────────
  console.log("\n3. Creating categories...");
  const categoryMap: Record<string, string> = {};

  // Fetch existing categories first (for idempotent re-runs)
  try {
    const existing = await api("GET", `/api/v1/stores/${storeId}/categories?per_page=50`, undefined, token) as any;
    const catItems = existing?.items ?? (Array.isArray(existing) ? existing : []);
    for (const cat of catItems) {
      categoryMap[cat.name] = cat.id;
    }
    if (Object.keys(categoryMap).length > 0) {
      console.log(`   ↳ Found ${Object.keys(categoryMap).length} existing categories`);
    }
  } catch { /* ignore */ }

  const categories = [
    { name: "Laptops & Computers", description: "Powerful laptops and desktop computers for work, creativity, and gaming. From ultrabooks to full tower workstations.", image_url: "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400" },
    { name: "Smartphones", description: "Latest flagship and mid-range smartphones from top brands. 5G connectivity, pro cameras, and all-day battery life.", image_url: "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400" },
    { name: "Audio & Headphones", description: "Premium audio equipment — wireless earbuds, over-ear headphones, and portable speakers with studio-grade sound.", image_url: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400" },
    { name: "Accessories", description: "Essential tech accessories — chargers, cables, docks, cases, and everything you need to complete your setup.", image_url: "https://images.unsplash.com/photo-1625772452859-1c03d5bf1137?w=400" },
  ];

  for (const cat of categories) {
    if (categoryMap[cat.name]) {
      console.log(`   ↳ ${cat.name} already exists`);
      continue;
    }
    try {
      const created = await api("POST", `/api/v1/stores/${storeId}/categories`, cat, token);
      if (created) {
        categoryMap[cat.name] = created.id;
        console.log(`   ✓ ${cat.name}`);
      }
    } catch (e: any) {
      console.log(`   ✗ ${cat.name}: ${e.message}`);
    }
  }

  // Sub-categories
  if (categoryMap["Laptops & Computers"] && !categoryMap["Gaming Laptops"]) {
    try {
      const sub1 = await api("POST", `/api/v1/stores/${storeId}/categories`, {
        name: "Gaming Laptops",
        description: "High-performance gaming laptops with dedicated GPUs, high-refresh displays, and RGB keyboards",
        parent_id: categoryMap["Laptops & Computers"],
      }, token);
      if (sub1) {
        categoryMap["Gaming Laptops"] = sub1.id;
        console.log("   ✓ Gaming Laptops (sub-category)");
      }
    } catch (e: any) {
      console.log(`   ✗ Gaming Laptops: ${e.message}`);
    }
  }

  if (categoryMap["Accessories"] && !categoryMap["Phone Cases"]) {
    try {
      const sub2 = await api("POST", `/api/v1/stores/${storeId}/categories`, {
        name: "Phone Cases",
        description: "Protective cases, clear covers, and rugged phone cases for all major smartphones",
        parent_id: categoryMap["Accessories"],
      }, token);
      if (sub2) {
        categoryMap["Phone Cases"] = sub2.id;
        console.log("   ✓ Phone Cases (sub-category)");
      }
    } catch (e: any) {
      console.log(`   ✗ Phone Cases: ${e.message}`);
    }
  }

  // ── 4. Products ────────────────────────────────────────────────────────────
  console.log("\n4. Creating products...");
  const products: any[] = [];
  const productDefs = [
    // ── 1. ProBook Ultra 15 (Laptop — SALE badge: has compare_at_price) ──
    {
      title: "ProBook Ultra 15",
      description: "The ProBook Ultra 15 redefines what a professional ultrabook can be. Powered by the latest Intel Core i7-13700H processor with 16GB LPDDR5 RAM and a blazing-fast 512GB NVMe SSD, it delivers desktop-class performance in a slim 1.4kg chassis.\n\nThe stunning 15.6-inch 4K OLED display covers 100% DCI-P3 with HDR600 support, making it ideal for content creation, photo editing, and media consumption. The edge-to-edge glass panel features an anti-reflective coating for comfortable viewing in any environment.\n\nAll-day battery life (up to 14 hours) means you can leave the charger at home. Thunderbolt 4, Wi-Fi 6E, and a full-size backlit keyboard round out the package. Available in Silver and Space Gray finishes.",
      price: "1299.99",
      compare_at_price: "1499.99",
      cost: "780.00",
      status: "active",
      images: [
        "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=800&q=80",
        "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=800&q=80",
        "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=800&q=80",
      ],
      category_id: categoryMap["Laptops & Computers"],
      seo_title: "ProBook Ultra 15 — 4K OLED Ultrabook | Volt Electronics",
      seo_description: "Premium 15.6-inch ultrabook with Intel Core i7, 4K OLED display, 16GB RAM, and all-day battery. Perfect for professionals on the go.",
      variants: [
        { name: "Silver / 16GB RAM / 512GB", sku: "PBU-SLV-16", price: null, inventory_count: 25 },
        { name: "Space Gray / 32GB RAM / 1TB", sku: "PBU-GRY-32", price: "1499.99", inventory_count: 15 },
        { name: "Silver / 16GB RAM / 1TB", sku: "PBU-SLV-16-1T", price: "1399.99", inventory_count: 18 },
      ],
    },
    // ── 2. TitanForce RTX Gaming Laptop ──
    {
      title: "TitanForce RTX Gaming Laptop",
      description: "Dominate every game with the TitanForce RTX. This 17.3-inch gaming powerhouse features an NVIDIA RTX 4070 GPU with 8GB GDDR6X, paired with an AMD Ryzen 9 7945HX processor and 32GB DDR5 RAM.\n\nThe 240Hz QHD display with 3ms response time and NVIDIA G-Sync eliminates tearing and ghosting, giving you a competitive edge in fast-paced titles. The per-key RGB keyboard with N-key rollover ensures every keystroke registers.\n\nAdvanced cooling with quad-fan design and liquid metal thermal compound keeps temps low during marathon sessions. A 1TB PCIe Gen 4 SSD loads games in seconds. Dual speakers with DTS:X Ultra deliver immersive 3D audio.",
      price: "1899.99",
      cost: "1150.00",
      status: "active",
      images: [
        "https://images.unsplash.com/photo-1593642702821-c8da6771f0c6?w=800&q=80",
        "https://images.unsplash.com/photo-1587831990711-23ca6441447b?w=800&q=80",
        "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=800&q=80",
      ],
      category_id: categoryMap["Gaming Laptops"],
      seo_title: "TitanForce RTX Gaming Laptop — RTX 4070 240Hz | Volt Electronics",
      seo_description: "17.3-inch gaming laptop with RTX 4070, 240Hz QHD display, 32GB RAM, and advanced quad-fan cooling. Built for competitive gaming.",
      variants: [
        { name: "Standard (RTX 4070 / 32GB)", sku: "TFRX-STD", price: null, inventory_count: 10 },
        { name: "Ultimate (RTX 4080 / 64GB)", sku: "TFRX-ULT", price: "2499.99", inventory_count: 5 },
      ],
    },
    // ── 3. Galaxy Nova X (Smartphone — SALE badge) ──
    {
      title: "Galaxy Nova X",
      description: "The Galaxy Nova X is the most advanced smartphone we've ever offered. Its 6.7-inch Dynamic AMOLED 2X display delivers vivid colors with 2600 nits peak brightness — readable even in direct sunlight.\n\nThe revolutionary 200MP main camera with OIS captures incredible detail day or night. The dedicated 3x optical zoom and 12MP ultrawide round out a versatile triple-camera system. Record cinema-grade 8K video at 30fps or slow-motion 4K at 120fps.\n\nPowered by the Snapdragon 8 Gen 3, with 5G Sub-6/mmWave connectivity and a 5000mAh battery with 45W wired + 15W wireless charging. IP68 water and dust resistance means it goes everywhere you do.",
      price: "999.99",
      compare_at_price: "1149.99",
      cost: "620.00",
      status: "active",
      images: [
        "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=800&q=80",
        "https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=800&q=80",
        "https://images.unsplash.com/photo-1565849904461-04a58ad377e0?w=800&q=80",
        "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=800&q=80",
      ],
      category_id: categoryMap["Smartphones"],
      seo_title: "Galaxy Nova X — 200MP Camera Flagship Phone | Volt Electronics",
      seo_description: "6.7-inch flagship smartphone with 200MP camera, 8K video, Snapdragon 8 Gen 3, and 5G. Available in Midnight Black, Ocean Blue, and Rose Gold.",
      variants: [
        { name: "Midnight Black / 256GB", sku: "GNX-BLK-256", price: null, inventory_count: 50 },
        { name: "Ocean Blue / 512GB", sku: "GNX-BLU-512", price: "1099.99", inventory_count: 30 },
        { name: "Rose Gold / 256GB", sku: "GNX-GLD-256", price: null, inventory_count: 20 },
      ],
    },
    // ── 4. PixelBudz Pro ANC (Earbuds) ──
    {
      title: "PixelBudz Pro ANC",
      description: "Experience pure sound with the PixelBudz Pro ANC — our best-selling true wireless earbuds. Custom 11mm titanium drivers deliver rich bass and crystal-clear highs across the full frequency range.\n\nThe adaptive Active Noise Cancellation uses 6 microphones to analyze and neutralize ambient sound in real time. Switch to Transparency mode with a tap to hear your surroundings when needed.\n\nIPX5 water resistance handles workouts and rain. The compact charging case provides 30 hours of total battery life (7h per charge). Multipoint connection lets you seamlessly switch between laptop and phone. Spatial audio with head tracking creates an immersive 3D soundstage.",
      price: "179.99",
      cost: "85.00",
      status: "active",
      images: [
        "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=800&q=80",
        "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=800&q=80",
        "https://images.unsplash.com/photo-1572569511254-d8f925fe2cbb?w=800&q=80",
      ],
      category_id: categoryMap["Audio & Headphones"],
      seo_title: "PixelBudz Pro ANC — Wireless Earbuds with Active Noise Cancellation",
      seo_description: "True wireless earbuds with adaptive ANC, 30-hour battery, spatial audio, and IPX5 water resistance. Premium titanium drivers for studio-quality sound.",
      variants: [
        { name: "Charcoal", sku: "PBP-CHR", price: null, inventory_count: 100 },
        { name: "Pearl White", sku: "PBP-WHT", price: null, inventory_count: 80 },
        { name: "Midnight Blue", sku: "PBP-BLU", price: null, inventory_count: 45 },
      ],
    },
    // ── 5. SoundStage Over-Ear Headphones ──
    {
      title: "SoundStage Over-Ear Headphones",
      description: "The SoundStage Over-Ear is an audiophile's dream at a real-world price. Planar magnetic drivers with ultra-thin diaphragms produce an expansive soundstage with pinpoint imaging — you'll hear details in your music you never knew existed.\n\nMemory foam ear cushions wrapped in protein leather distribute weight evenly for hours of fatigue-free listening. The adjustable headband uses aircraft-grade aluminum for lightweight durability.\n\nDual-mode connectivity: low-latency aptX HD Bluetooth 5.3 for wireless freedom, or the included 3.5mm cable with inline DAC for wired audiophile mode. 40-hour battery life with quick charge (10 min = 3 hours). Folds flat into the included hard-shell carry case.",
      price: "349.99",
      compare_at_price: "429.99",
      cost: "195.00",
      status: "active",
      images: [
        "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&q=80",
        "https://images.unsplash.com/photo-1583394838336-acd977736f90?w=800&q=80",
        "https://images.unsplash.com/photo-1487215078519-e21cc028cb29?w=800&q=80",
      ],
      category_id: categoryMap["Audio & Headphones"],
      seo_title: "SoundStage Over-Ear — Planar Magnetic Wireless Headphones",
      seo_description: "Premium over-ear headphones with planar magnetic drivers, memory foam cushions, aptX HD Bluetooth, and 40-hour battery. Wired and wireless modes.",
      variants: [
        { name: "Matte Black", sku: "SS-BLK", price: null, inventory_count: 40 },
        { name: "Champagne Gold", sku: "SS-GLD", price: null, inventory_count: 22 },
      ],
    },
    // ── 6. HyperCharge 65W GaN Charger ──
    {
      title: "HyperCharge 65W GaN Charger",
      description: "Replace every charger you own with one device. The HyperCharge 65W uses 3rd-generation Gallium Nitride (GaN) technology to deliver full laptop charging power from a charger smaller than a deck of cards.\n\nThree ports — 2x USB-C (65W + 30W) and 1x USB-A (18W) — charge your laptop, phone, and tablet simultaneously with intelligent power distribution. PPS support for Samsung Super Fast Charging, USB PD 3.0 for MacBook, and Qualcomm Quick Charge 4+ for universal compatibility.\n\nFoldable prongs tuck flush for travel. Built-in thermal monitoring and multi-layer circuit protection keep your devices safe. Available in minimalist White and Black finishes.",
      price: "49.99",
      cost: "18.00",
      status: "active",
      images: [
        "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=800&q=80",
        "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=800&q=80",
      ],
      category_id: categoryMap["Accessories"],
      seo_title: "HyperCharge 65W GaN Charger — 3-Port USB-C Travel Charger",
      seo_description: "Ultra-compact 65W GaN charger with 3 ports. Charges laptops, phones, and tablets simultaneously. Foldable prongs for travel. PPS and PD 3.0 support.",
      variants: [
        { name: "White", sku: "HC65-WHT", price: null, inventory_count: 200 },
        { name: "Black", sku: "HC65-BLK", price: null, inventory_count: 150 },
      ],
    },
    // ── 7. ArmorShield Pro Case ──
    {
      title: "ArmorShield Pro Case",
      description: "Military-grade protection that doesn't sacrifice style. The ArmorShield Pro exceeds MIL-STD-810G drop test standards — certified to survive 10-foot drops onto concrete.\n\nThe dual-layer design pairs a shock-absorbing TPU inner frame with a rigid polycarbonate outer shell. Raised 2mm bezels protect the screen and camera from flat-surface drops. Built-in MagSafe ring for wireless charging and magnetic accessories.\n\nAnti-yellowing technology keeps the clear version crystal-transparent over time. Antimicrobial coating resists 99.9% of surface bacteria. Precision cutouts for all ports and buttons. Compatible with Galaxy Nova X.",
      price: "39.99",
      cost: "8.50",
      status: "active",
      images: [
        "https://images.unsplash.com/photo-1601593346740-925612772716?w=800&q=80",
        "https://images.unsplash.com/photo-1586953208270-767889fa9b0e?w=800&q=80",
      ],
      category_id: categoryMap["Phone Cases"],
      seo_title: "ArmorShield Pro Case — Military-Grade MagSafe Phone Case",
      seo_description: "Military-grade drop protection case with MagSafe. Dual-layer design, raised bezels, anti-yellowing technology. For Galaxy Nova X.",
      variants: [
        { name: "Crystal Clear", sku: "ASP-CLR", price: null, inventory_count: 300 },
        { name: "Frosted Black", sku: "ASP-FBK", price: null, inventory_count: 250 },
        { name: "Navy Blue", sku: "ASP-NVY", price: null, inventory_count: 180 },
      ],
    },
    // ── 8. FlexiDock USB-C Hub ──
    {
      title: "FlexiDock USB-C Hub",
      description: "Transform your laptop into a full desktop workstation with one cable. The FlexiDock 12-in-1 docking station delivers dual 4K@60Hz output, blazing data transfer, and 100W pass-through charging via a single USB-C connection.\n\nPorts: 2x HDMI 2.0 (4K@60Hz), 2x USB-A 3.0, 1x USB-C 3.0, SD + microSD card readers, Gigabit Ethernet, 3.5mm audio jack, and 100W USB-C PD pass-through. Supports extended and mirrored display modes.\n\nThe CNC-machined aluminum unibody acts as a passive heatsink — no fans, no noise. Compact 155mm × 65mm footprint sits neatly on any desk. Universal compatibility with USB-C/Thunderbolt laptops, tablets, and iPads.",
      price: "89.99",
      compare_at_price: "119.99",
      cost: "42.00",
      status: "active",
      images: [
        "https://images.unsplash.com/photo-1625842268584-8f3296236761?w=800&q=80",
        "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=800&q=80",
      ],
      category_id: categoryMap["Accessories"],
      seo_title: "FlexiDock 12-in-1 USB-C Hub — Dual 4K Docking Station",
      seo_description: "12-in-1 USB-C docking station with dual 4K HDMI, 100W PD, Ethernet, card readers. Aluminum unibody design. One cable to connect everything.",
      variants: [
        { name: "Silver", sku: "FD-SLV", price: null, inventory_count: 60 },
        { name: "Space Gray", sku: "FD-GRY", price: null, inventory_count: 45 },
      ],
    },
    // ── 9. NovaBand Smartwatch (NEW product — low stock for inventory alert) ──
    {
      title: "NovaBand Smartwatch",
      description: "Your health and fitness companion, reimagined. The NovaBand tracks heart rate, SpO2, sleep quality, stress levels, and 100+ workout types with medical-grade sensors and GPS.\n\nThe 1.43-inch AMOLED always-on display is bright enough for outdoor runs (1500 nits) and beautiful enough for formal dinners. 5ATM water resistance for swimming. NFC for contactless payments.\n\n7-day battery life with typical use (14 days in power saver mode). Compatible with iOS and Android. Includes interchangeable sport band and classic leather strap.",
      price: "249.99",
      compare_at_price: "299.99",
      cost: "120.00",
      status: "active",
      images: [
        "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80",
        "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?w=800&q=80",
        "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=800&q=80",
      ],
      category_id: categoryMap["Accessories"],
      seo_title: "NovaBand Smartwatch — Health & Fitness GPS Watch",
      seo_description: "Advanced smartwatch with heart rate, SpO2, GPS, NFC payments, and 7-day battery. AMOLED always-on display. 100+ workout modes.",
      variants: [
        { name: "Obsidian Black / Sport Band", sku: "NB-BLK-SPT", price: null, inventory_count: 3 },
        { name: "Arctic White / Sport Band", sku: "NB-WHT-SPT", price: null, inventory_count: 2 },
        { name: "Obsidian Black / Leather Strap", sku: "NB-BLK-LTH", price: "279.99", inventory_count: 4 },
      ],
    },
    // ── 10. VoltBeam Portable Speaker (NEW product) ──
    {
      title: "VoltBeam Portable Speaker",
      description: "Big sound, pocket-sized. The VoltBeam packs dual 48mm drivers and a passive bass radiator into a waterproof cylinder that weighs just 540g.\n\nWith 360° sound projection and 20W peak output, it fills any room — or poolside patio — with surprisingly deep, clear audio. PartySync lets you link 100+ VoltBeam speakers for synchronized multi-room playback.\n\nIPX7 waterproof (submersible to 1 meter for 30 minutes), dustproof, and built to survive drops from 1.5m. 16-hour battery life. USB-C fast charging (15 min = 3 hours). Built-in microphone for hands-free calls. Available in four vibrant colors.",
      price: "79.99",
      cost: "32.00",
      status: "active",
      images: [
        "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=800&q=80",
        "https://images.unsplash.com/photo-1558089687-f282ffcbc126?w=800&q=80",
      ],
      category_id: categoryMap["Audio & Headphones"],
      seo_title: "VoltBeam Portable Speaker — IPX7 Waterproof Bluetooth Speaker",
      seo_description: "20W portable Bluetooth speaker with 360° sound, IPX7 waterproof, 16-hour battery. Link 100+ speakers with PartySync. Perfect for outdoors.",
      variants: [
        { name: "Midnight Black", sku: "VB-BLK", price: null, inventory_count: 75 },
        { name: "Electric Blue", sku: "VB-BLU", price: null, inventory_count: 60 },
        { name: "Sunset Orange", sku: "VB-ORG", price: null, inventory_count: 55 },
        { name: "Forest Green", sku: "VB-GRN", price: null, inventory_count: 40 },
      ],
    },
    // ── 11. MagFloat Wireless Charger (NEW — low stock for inventory alerts) ──
    {
      title: "MagFloat Wireless Charger",
      description: "A charger that levitates your phone. The MagFloat uses electromagnetic suspension to hold your device in mid-air while wirelessly charging at 15W — a mesmerizing desk piece that doubles as a conversation starter.\n\nMagSafe-compatible alignment ensures perfect coil positioning every time. Built-in cooling fan prevents heat buildup for safe overnight charging. LED ring glows softly during charge, dims when complete.\n\nAnti-slip weighted base with premium anodized aluminum finish. Compatible with all Qi-enabled devices. Includes 30W USB-C power adapter in box.",
      price: "69.99",
      compare_at_price: "89.99",
      cost: "28.00",
      status: "active",
      images: [
        "https://images.unsplash.com/photo-1586816879360-004f5b0c51e5?w=800&q=80",
        "https://images.unsplash.com/photo-1618577557026-eb6e76ceb8c9?w=800&q=80",
      ],
      category_id: categoryMap["Accessories"],
      seo_title: "MagFloat Wireless Charger — Levitating MagSafe Charger",
      seo_description: "Levitating wireless charger with MagSafe alignment, 15W fast charge, and LED ring. Premium aluminum design. Includes 30W adapter.",
      variants: [
        { name: "Silver", sku: "MF-SLV", price: null, inventory_count: 4 },
        { name: "Space Black", sku: "MF-BLK", price: null, inventory_count: 2 },
      ],
    },
    // ── 12. ClearView Monitor Light Bar (NEW — draft product for variety) ──
    {
      title: "ClearView Monitor Light Bar",
      description: "Eliminate screen glare and eye strain with the ClearView — a sleek asymmetric light bar that clips onto any monitor (up to 35mm thick) without screws or adhesive.\n\nThe asymmetric optical design illuminates your desk without casting reflections on the screen. Stepless dimming from 50 to 500 lux. Adjustable color temperature from 2700K warm to 6500K daylight — match your environment or follow your circadian rhythm.\n\nTouch-sensitive controls on the bar for instant brightness and temperature adjustments. Auto-dimming ambient sensor option. USB-C powered — plugs directly into your monitor's USB port. Minimal 45cm × 3cm footprint. Flicker-free for video calls.",
      price: "59.99",
      cost: "22.00",
      status: "active",
      images: [
        "https://images.unsplash.com/photo-1593062096033-9a26b09da705?w=800&q=80",
        "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=800&q=80",
      ],
      category_id: categoryMap["Accessories"],
      seo_title: "ClearView Monitor Light Bar — Asymmetric Desk Lamp",
      seo_description: "Asymmetric monitor light bar with stepless dimming, adjustable color temperature, and USB-C power. Zero screen glare. Clips onto any monitor.",
      variants: [
        { name: "Black", sku: "CV-BLK", price: null, inventory_count: 90 },
        { name: "Silver", sku: "CV-SLV", price: null, inventory_count: 65 },
      ],
    },
  ];

  for (const pDef of productDefs) {
    try {
      const product = await api("POST", `/api/v1/stores/${storeId}/products`, pDef, token);
      if (product) {
        products.push(product);
        console.log(`   ✓ ${pDef.title} — $${pDef.price}${pDef.compare_at_price ? ` (was $${pDef.compare_at_price})` : ""}`);
      }
    } catch (e: any) {
      console.log(`   ✗ ${pDef.title}: ${e.message}`);
    }
  }

  // ── 4b. Assign products to categories ─────────────────────────────────────
  console.log("\n4b. Assigning products to categories...");
  const catProductMap: Record<string, string[]> = {};
  for (let i = 0; i < productDefs.length; i++) {
    const def = productDefs[i];
    const product = products[i];
    if (def.category_id && product?.id) {
      if (!catProductMap[def.category_id]) catProductMap[def.category_id] = [];
      catProductMap[def.category_id].push(product.id);
    }
  }
  for (const [catId, prodIds] of Object.entries(catProductMap)) {
    try {
      await api("POST", `/api/v1/stores/${storeId}/categories/${catId}/products`, { product_ids: prodIds }, token);
      console.log(`   ✓ Assigned ${prodIds.length} product(s) to category ${catId}`);
    } catch (e: any) {
      console.log(`   ✗ Category ${catId}: ${e.message}`);
    }
  }

  // ── 5. Suppliers ───────────────────────────────────────────────────────────
  console.log("\n5. Creating suppliers...");
  const suppliers: any[] = [];
  const supplierDefs = [
    {
      name: "TechSource Global",
      website: "https://techsource-global.com",
      contact_email: "orders@techsource-global.com",
      contact_phone: "+1-555-0100",
      notes: "Primary laptop and computer supplier. Ships from Shenzhen, 7-10 day lead time. MOQ 10 units. Volume discounts available above 50 units. Accepts wire transfer and Alibaba Trade Assurance.",
    },
    {
      name: "MobileFirst Supply Co.",
      website: "https://mobilefirst-supply.com",
      contact_email: "support@mobilefirst-supply.com",
      contact_phone: "+1-555-0200",
      notes: "Smartphone and accessories supplier. Ships from Hong Kong, 5-7 day lead time. Offers dropship packaging with custom branding. Minimum order $500. Accepts PayPal and wire transfer.",
    },
    {
      name: "AudioPrime Distributors",
      website: "https://audioprime-dist.com",
      contact_email: "wholesale@audioprime-dist.com",
      contact_phone: "+44-20-7946-0958",
      notes: "UK-based audio equipment distributor. Ships globally, 3-5 day lead time within Europe, 7-12 days to US. Authorized dealer for premium brands. NET30 payment terms available for established accounts.",
    },
  ];

  for (const sDef of supplierDefs) {
    try {
      const supplier = await api("POST", `/api/v1/stores/${storeId}/suppliers`, sDef, token);
      if (supplier) {
        suppliers.push(supplier);
        console.log(`   ✓ ${sDef.name}`);
      }
    } catch (e: any) {
      console.log(`   ✗ ${sDef.name}: ${e.message}`);
    }
  }

  // Link products to suppliers
  if (suppliers.length > 0 && products.length > 0) {
    console.log("   Linking products to suppliers...");
    const productSupplierLinks = [
      { productIdx: 0, supplierIdx: 0, cost: "780.00", sku: "TS-PBU15" },     // ProBook → TechSource
      { productIdx: 1, supplierIdx: 0, cost: "1150.00", sku: "TS-TFRX" },     // TitanForce → TechSource
      { productIdx: 2, supplierIdx: 1, cost: "620.00", sku: "MF-GNX" },       // Galaxy Nova → MobileFirst
      { productIdx: 3, supplierIdx: 2, cost: "85.00", sku: "AP-PBP" },        // PixelBudz → AudioPrime
      { productIdx: 4, supplierIdx: 2, cost: "195.00", sku: "AP-SS" },        // SoundStage → AudioPrime
      { productIdx: 5, supplierIdx: 1, cost: "18.00", sku: "MF-HC65" },       // HyperCharge → MobileFirst
      { productIdx: 6, supplierIdx: 1, cost: "8.50", sku: "MF-ASP" },         // ArmorShield → MobileFirst
      { productIdx: 7, supplierIdx: 0, cost: "42.00", sku: "TS-FD" },         // FlexiDock → TechSource
      { productIdx: 8, supplierIdx: 1, cost: "120.00", sku: "MF-NB" },        // NovaBand → MobileFirst
      { productIdx: 9, supplierIdx: 2, cost: "32.00", sku: "AP-VB" },         // VoltBeam → AudioPrime
      { productIdx: 10, supplierIdx: 1, cost: "28.00", sku: "MF-MFWC" },      // MagFloat → MobileFirst
      { productIdx: 11, supplierIdx: 0, cost: "22.00", sku: "TS-CV" },        // ClearView → TechSource
    ];

    for (const link of productSupplierLinks) {
      if (products[link.productIdx] && suppliers[link.supplierIdx]) {
        try {
          await api(
            "POST",
            `/api/v1/stores/${storeId}/products/${products[link.productIdx].id}/suppliers`,
            {
              supplier_id: suppliers[link.supplierIdx].id,
              supplier_cost: link.cost,
              supplier_sku: link.sku,
              is_primary: true,
            },
            token
          );
          console.log(`   ✓ ${products[link.productIdx].title} → ${suppliers[link.supplierIdx].name} ($${link.cost})`);
        } catch (e: any) {
          console.log(`   ✗ Link failed: ${e.message}`);
        }
      }
    }
  }

  // ── 6. Discounts ───────────────────────────────────────────────────────────
  console.log("\n6. Creating discount codes...");
  const discountDefs = [
    { code: "WELCOME10", discount_type: "percentage", value: 10, description: "10% off for new customers", starts_at: new Date().toISOString(), max_uses: 500 },
    { code: "SUMMER25", discount_type: "percentage", value: 25, description: "Summer sale — 25% off everything", starts_at: new Date().toISOString(), expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString() },
    { code: "FLAT20", discount_type: "fixed_amount", value: 20, description: "$20 off orders over $100", starts_at: new Date().toISOString(), minimum_order_amount: 100 },
    { code: "AUDIO15", discount_type: "percentage", value: 15, description: "15% off audio products", starts_at: new Date().toISOString(), applies_to: "specific_categories", category_ids: categoryMap["Audio & Headphones"] ? [categoryMap["Audio & Headphones"]] : undefined },
    { code: "BIGSPEND50", discount_type: "fixed_amount", value: 50, description: "$50 off orders over $500", starts_at: new Date().toISOString(), minimum_order_amount: 500, max_uses: 100 },
  ];

  for (const dDef of discountDefs) {
    try {
      await api("POST", `/api/v1/stores/${storeId}/discounts`, dDef, token);
      console.log(`   ✓ ${dDef.code} — ${dDef.discount_type === "percentage" ? `${dDef.value}%` : `$${dDef.value}`} off`);
    } catch (e: any) {
      console.log(`   ✗ ${dDef.code}: ${e.message}`);
    }
  }

  // ── 7. Tax Rates ───────────────────────────────────────────────────────────
  console.log("\n7. Creating tax rates...");
  const taxDefs = [
    { name: "California Sales Tax", rate: 7.25, country: "US", state: "CA" },
    { name: "New York Sales Tax", rate: 8.875, country: "US", state: "NY" },
    { name: "Texas Sales Tax", rate: 6.25, country: "US", state: "TX" },
    { name: "UK VAT", rate: 20, country: "GB", is_inclusive: true },
  ];

  for (const tDef of taxDefs) {
    try {
      await api("POST", `/api/v1/stores/${storeId}/tax-rates`, tDef, token);
      console.log(`   ✓ ${tDef.name} — ${tDef.rate}%`);
    } catch (e: any) {
      console.log(`   ✗ ${tDef.name}: ${e.message}`);
    }
  }

  // ── 8. Gift Cards ──────────────────────────────────────────────────────────
  console.log("\n8. Creating gift cards...");
  const giftCardDefs = [
    { initial_balance: 25, customer_email: "alice@example.com" },
    { initial_balance: 50, customer_email: "bob@example.com" },
    { initial_balance: 100, customer_email: "carol@example.com" },
  ];

  for (const gcDef of giftCardDefs) {
    try {
      const gc = await api("POST", `/api/v1/stores/${storeId}/gift-cards`, gcDef, token);
      if (gc) console.log(`   ✓ $${gcDef.initial_balance} card → ${gcDef.customer_email} (${gc.code})`);
    } catch (e: any) {
      console.log(`   ✗ $${gcDef.initial_balance} card: ${e.message}`);
    }
  }

  // ── 9. Customer Accounts ──────────────────────────────────────────────────
  console.log("\n9. Registering customer accounts...");
  const customerTokens: Record<string, string> = {};
  const customerDefs = [
    { email: "alice@example.com", password: "password123", first_name: "Alice", last_name: "Martinez" },
    { email: "bob@example.com", password: "password123", first_name: "Bob", last_name: "Johnson" },
    { email: "carol@example.com", password: "password123", first_name: "Carol", last_name: "Davis" },
  ];

  for (const cDef of customerDefs) {
    try {
      const res = await api("POST", `/api/v1/public/stores/${slug}/customers/register`, cDef);
      if (res) {
        customerTokens[cDef.email] = res.access_token;
        console.log(`   ✓ ${cDef.first_name} ${cDef.last_name} (${cDef.email})`);
      }
    } catch (e: any) {
      // Already exists — try login
      if (e.message.includes("400")) {
        try {
          const loginRes = await api("POST", `/api/v1/public/stores/${slug}/customers/login`, {
            email: cDef.email,
            password: cDef.password,
          });
          if (loginRes) {
            customerTokens[cDef.email] = loginRes.access_token;
            console.log(`   ⤳ ${cDef.email} already exists, logged in`);
          }
        } catch {
          console.log(`   ✗ ${cDef.email}: could not register or login`);
        }
      } else {
        console.log(`   ✗ ${cDef.email}: ${e.message}`);
      }
    }
  }

  // ── 9b. Customer Addresses ────────────────────────────────────────────────
  console.log("\n9b. Adding customer addresses...");
  const addressDefs: { email: string; addresses: any[] }[] = [
    {
      email: "alice@example.com",
      addresses: [
        { label: "Home", line1: "742 Evergreen Terrace", city: "San Francisco", state: "CA", postal_code: "94102", country: "US", phone: "+1-555-0101", is_default: true },
        { label: "Work", line1: "1 Market Street", line2: "Suite 400", city: "San Francisco", state: "CA", postal_code: "94105", country: "US", phone: "+1-555-0102", is_default: false },
      ],
    },
    {
      email: "bob@example.com",
      addresses: [
        { label: "Home", line1: "350 Fifth Avenue", line2: "Suite 3300", city: "New York", state: "NY", postal_code: "10118", country: "US", phone: "+1-555-0202", is_default: true },
      ],
    },
    {
      email: "carol@example.com",
      addresses: [
        { label: "Home", line1: "1600 Pennsylvania Avenue NW", city: "Washington", state: "DC", postal_code: "20500", country: "US", is_default: true },
      ],
    },
  ];

  for (const { email, addresses } of addressDefs) {
    const custToken = customerTokens[email];
    if (!custToken) {
      console.log(`   ⤳ No token for ${email}, skipping addresses`);
      continue;
    }
    for (const addr of addresses) {
      try {
        await api("POST", `/api/v1/customer/addresses`, addr, custToken);
        console.log(`   ✓ ${email} — ${addr.label} (${addr.city}, ${addr.state})`);
      } catch (e: any) {
        console.log(`   ✗ ${email} address: ${e.message}`);
      }
    }
  }

  // ── 9c. Customer Wishlists ────────────────────────────────────────────────
  console.log("\n9c. Adding items to wishlists...");
  if (products.length >= 8) {
    const wishlistDefs = [
      { email: "alice@example.com", productIndices: [1, 4, 8] },   // Alice wants: TitanForce, SoundStage, NovaBand
      { email: "bob@example.com", productIndices: [0, 9] },         // Bob wants: ProBook, VoltBeam
      { email: "carol@example.com", productIndices: [2, 10] },      // Carol wants: Galaxy Nova, MagFloat
    ];

    for (const { email, productIndices } of wishlistDefs) {
      const custToken = customerTokens[email];
      if (!custToken) continue;
      for (const idx of productIndices) {
        if (products[idx]) {
          try {
            await api("POST", `/api/v1/customer/wishlist`, { product_id: products[idx].id }, custToken);
            console.log(`   ✓ ${email} → ${products[idx].title}`);
          } catch (e: any) {
            console.log(`   ✗ ${email} wishlist: ${e.message}`);
          }
        }
      }
    }
  }

  // ── 10. Orders (via public checkout) ───────────────────────────────────────
  console.log("\n10. Creating orders via checkout...");
  const orders: any[] = [];

  if (products.length >= 8) {
    const orderDefs = [
      {
        customer_email: "alice@example.com",
        items: [
          { product_id: products[0].id, variant_id: products[0].variants?.[0]?.id, quantity: 1 },
          { product_id: products[5].id, variant_id: products[5].variants?.[0]?.id, quantity: 2 },
        ],
        shipping_address: {
          name: "Alice Martinez",
          line1: "742 Evergreen Terrace",
          city: "San Francisco",
          state: "CA",
          postal_code: "94102",
          country: "US",
          phone: "+1-555-0101",
        },
        label: "Alice — ProBook + 2x HyperCharge",
      },
      {
        customer_email: "bob@example.com",
        items: [
          { product_id: products[2].id, variant_id: products[2].variants?.[0]?.id, quantity: 1 },
          { product_id: products[6].id, variant_id: products[6].variants?.[0]?.id, quantity: 1 },
        ],
        shipping_address: {
          name: "Bob Johnson",
          line1: "350 Fifth Avenue",
          line2: "Suite 3300",
          city: "New York",
          state: "NY",
          postal_code: "10118",
          country: "US",
          phone: "+1-555-0202",
        },
        label: "Bob — Galaxy Nova + ArmorShield",
      },
      {
        customer_email: "carol@example.com",
        items: [
          { product_id: products[3].id, variant_id: products[3].variants?.[0]?.id, quantity: 1 },
          { product_id: products[4].id, variant_id: products[4].variants?.[0]?.id, quantity: 1 },
        ],
        shipping_address: {
          name: "Carol Davis",
          line1: "1600 Pennsylvania Avenue NW",
          city: "Washington",
          state: "DC",
          postal_code: "20500",
          country: "US",
        },
        label: "Carol — PixelBudz + SoundStage",
      },
      {
        customer_email: "dave@example.com",
        items: [
          { product_id: products[1].id, variant_id: products[1].variants?.[0]?.id, quantity: 1 },
          { product_id: products[7].id, variant_id: products[7].variants?.[0]?.id, quantity: 1 },
        ],
        shipping_address: {
          name: "Dave Sullivan",
          line1: "2101 NASA Parkway",
          city: "Houston",
          state: "TX",
          postal_code: "77058",
          country: "US",
          phone: "+1-555-0404",
        },
        label: "Dave — TitanForce + FlexiDock",
      },
    ];

    for (const oDef of orderDefs) {
      try {
        const checkout = await api("POST", `/api/v1/public/stores/${slug}/checkout`, {
          customer_email: oDef.customer_email,
          items: oDef.items,
          shipping_address: oDef.shipping_address,
        });
        if (checkout) {
          orders.push(checkout);
          console.log(`   ✓ ${oDef.label} (order: ${checkout.order_id})`);
        }
      } catch (e: any) {
        console.log(`   ✗ ${oDef.label}: ${e.message}`);
      }
    }

    // Simulate order lifecycle: pending → paid → shipped → delivered
    await sleep(300);
    if (orders.length >= 4) {
      // First, mark all orders as paid (simulates Stripe webhook)
      for (let i = 0; i < orders.length; i++) {
        const names = ["Alice", "Bob", "Carol", "Dave"];
        try {
          await api(
            "PATCH",
            `/api/v1/stores/${storeId}/orders/${orders[i].order_id}`,
            { status: "paid" },
            token
          );
          console.log(`   ✓ ${names[i]} → paid`);
        } catch (e: any) {
          console.log(`   ✗ ${names[i]} → paid: ${e.message}`);
        }
      }

      // Alice's order: fulfill with tracking (shipped)
      try {
        await api(
          "POST",
          `/api/v1/stores/${storeId}/orders/${orders[0].order_id}/fulfill`,
          { tracking_number: "1Z999AA10123456784", carrier: "UPS" },
          token
        );
        console.log("   ✓ Alice → shipped (UPS: 1Z999AA10123456784)");
      } catch (e: any) {
        console.log(`   ✗ Alice → shipped: ${e.message}`);
      }

      // Bob's order: fulfill then deliver (complete lifecycle)
      try {
        await api(
          "POST",
          `/api/v1/stores/${storeId}/orders/${orders[1].order_id}/fulfill`,
          { tracking_number: "9400111899223100001234", carrier: "USPS" },
          token
        );
        console.log("   ✓ Bob → shipped (USPS: 9400111899223100001234)");
        await api(
          "POST",
          `/api/v1/stores/${storeId}/orders/${orders[1].order_id}/deliver`,
          {},
          token
        );
        console.log("   ✓ Bob → delivered");
      } catch (e: any) {
        console.log(`   ✗ Bob fulfillment: ${e.message}`);
      }

      // Carol stays as paid (awaiting fulfillment)
      // Dave stays as paid (awaiting fulfillment)
      console.log("   ℹ Carol & Dave remain as paid (awaiting fulfillment)");
    }
  } else {
    console.log("   ⤳ Not enough products for orders, skipping");
  }

  // ── 11. Refund ─────────────────────────────────────────────────────────────
  console.log("\n11. Creating refund...");
  if (orders.length >= 3) {
    try {
      await api("POST", `/api/v1/stores/${storeId}/refunds`, {
        order_id: orders[2].order_id,
        reason: "Customer received wrong color variant",
        reason_details: "Customer ordered Pearl White PixelBudz but received Charcoal. Issuing full refund for the earbuds while customer ships the item back.",
        amount: 179.99,
      }, token);
      console.log("   ✓ Refund for Carol's order — $179.99");
    } catch (e: any) {
      console.log(`   ✗ Refund: ${e.message}`);
    }
  } else {
    console.log("   ⤳ No orders to refund, skipping");
  }

  // ── 12. Reviews ────────────────────────────────────────────────────────────
  console.log("\n12. Creating product reviews...");
  if (products.length >= 10) {
    const reviewDefs = [
      // ProBook Ultra reviews
      { productSlug: products[0].slug, rating: 5, title: "Best laptop I've ever owned", body: "The 4K OLED display is absolutely stunning. Battery easily lasts 10+ hours. The build quality is exceptional — feels premium without being heavy. Typing on the keyboard is a joy. Highly recommended for any professional.", customer_name: "Alice M.", customer_email: "alice@example.com" },
      { productSlug: products[0].slug, rating: 4, title: "Great machine, minor quirks", body: "Performance is excellent and the display is beautiful. Only downside is the webcam quality — it's passable for calls but nothing special. Fan noise under heavy load is noticeable but not loud.", customer_name: "Tom K.", customer_email: "tom@example.com" },
      { productSlug: products[0].slug, rating: 5, title: "Perfect for development", body: "As a software developer, this laptop handles everything I throw at it. Docker containers, multiple IDEs, dozens of browser tabs — never breaks a sweat. The 32GB model is worth the upgrade.", customer_name: "Sarah L.", customer_email: "sarah@example.com" },

      // Galaxy Nova reviews
      { productSlug: products[2].slug, rating: 5, title: "Camera is mind-blowing", body: "The 200MP camera produces incredibly detailed shots. Night mode is the best I've seen on any phone. The 8K video capability is future-proof. Battery lasts a full day even with heavy camera use.", customer_name: "Bob J.", customer_email: "bob@example.com" },
      { productSlug: products[2].slug, rating: 4, title: "Almost perfect flagship", body: "Beautiful display, fast performance, great cameras. The phone is a bit large for one-handed use, and the 512GB model is expensive. But overall it's the best Android phone you can buy right now.", customer_name: "Lisa P.", customer_email: "lisa@example.com" },
      { productSlug: products[2].slug, rating: 3, title: "Good but overpriced", body: "Solid phone with great features, but the price is hard to justify when competitors offer 90% of the experience for 60% of the cost. The camera bump is also quite prominent.", customer_name: "Mark R.", customer_email: "mark@example.com" },

      // PixelBudz reviews
      { productSlug: products[3].slug, rating: 5, title: "ANC is incredible", body: "These earbuds block out everything — office chatter, airplane noise, city traffic. Sound quality rivals much more expensive headphones. The spatial audio feature is a nice bonus for movies.", customer_name: "Carol D.", customer_email: "carol@example.com" },
      { productSlug: products[3].slug, rating: 4, title: "Great value for the price", body: "Comfortable fit, good sound, excellent battery life. The ANC is effective but not quite at the level of the premium Sony or Bose options. For the price though, absolutely worth it.", customer_name: "Dave S.", customer_email: "dave@example.com" },

      // SoundStage reviews
      { productSlug: products[4].slug, rating: 5, title: "Audiophile approved", body: "These are reference-grade headphones at a fraction of the price. The planar magnetic drivers produce clean, detailed sound across all frequencies. The memory foam cushions are so comfortable I forget I'm wearing them.", customer_name: "James W.", customer_email: "james@example.com" },

      // HyperCharge reviews
      { productSlug: products[5].slug, rating: 5, title: "Replaced all my chargers", body: "One charger for everything — laptop, phone, tablet. The 65W output charges my MacBook Pro at full speed. Incredibly compact for a 3-port charger. The foldable prongs are perfect for travel.", customer_name: "Nina H.", customer_email: "nina@example.com" },
      { productSlug: products[5].slug, rating: 4, title: "Almost perfect charger", body: "Great charger overall. Charges my phone super fast and can handle my laptop too. Only complaint is it gets quite warm under full load, but that seems normal for GaN chargers.", customer_name: "Ryan F.", customer_email: "ryan@example.com" },

      // ArmorShield review
      { productSlug: products[6].slug, rating: 5, title: "Survived a 6-foot drop", body: "Dropped my phone face-down on concrete from my car roof. Phone was completely fine thanks to this case. The raised bezels saved the camera too. Slim enough that it doesn't add much bulk.", customer_name: "Pat G.", customer_email: "pat@example.com" },

      // NovaBand review
      { productSlug: products[8].slug, rating: 5, title: "My daily health companion", body: "The sleep tracking alone is worth the price. I discovered I was waking up 12 times a night — adjusted my routine and now sleep like a baby. Heart rate monitoring is accurate compared to my chest strap. Battery lasts a full week.", customer_name: "Alice M.", customer_email: "alice@example.com" },

      // VoltBeam review
      { productSlug: products[9].slug, rating: 4, title: "Punches way above its size", body: "Brought this to a beach barbecue and it filled the whole patio with sound. Bass is surprisingly deep for something this small. Only wish it had a built-in handle. The PartySync feature worked perfectly with my friend's speaker.", customer_name: "Dave S.", customer_email: "dave@example.com" },
    ];

    for (const rDef of reviewDefs) {
      try {
        await api("POST", `/api/v1/public/stores/${slug}/products/${rDef.productSlug}/reviews`, {
          rating: rDef.rating,
          title: rDef.title,
          body: rDef.body,
          customer_name: rDef.customer_name,
          customer_email: rDef.customer_email,
        });
        console.log(`   ✓ ${rDef.customer_name} → ${rDef.productSlug} (${rDef.rating}★)`);
      } catch (e: any) {
        console.log(`   ✗ ${rDef.customer_name}: ${e.message}`);
      }
    }
  } else {
    console.log("   ⤳ Not enough products for reviews, skipping");
  }

  // ── 13. Segments ───────────────────────────────────────────────────────────
  console.log("\n13. Creating customer segments...");
  const segmentDefs = [
    { name: "High-Value Customers", description: "Customers who have spent over $500 lifetime", segment_type: "manual" },
    { name: "Repeat Buyers", description: "Customers with 2 or more orders", segment_type: "manual" },
    { name: "VIP Early Access", description: "Hand-picked customers for early access to new products", segment_type: "manual" },
  ];

  for (const sDef of segmentDefs) {
    try {
      await api("POST", `/api/v1/stores/${storeId}/segments`, sDef, token);
      console.log(`   ✓ ${sDef.name} (${sDef.segment_type})`);
    } catch (e: any) {
      console.log(`   ✗ ${sDef.name}: ${e.message}`);
    }
  }

  // ── 14. Upsells ────────────────────────────────────────────────────────────
  console.log("\n14. Creating upsell rules...");
  if (products.length >= 12) {
    const upsellDefs = [
      { source: 0, target: 5, type: "cross_sell", title: "Charge it faster", description: "Pair your ProBook with our 65W GaN charger", discount: 10, position: 1 },
      { source: 2, target: 6, type: "cross_sell", title: "Protect your investment", description: "Add a military-grade case for your Galaxy Nova", discount: 15, position: 1 },
      { source: 3, target: 4, type: "upsell", title: "Upgrade your audio", description: "Love the PixelBudz? Experience the full-size SoundStage headphones", discount: 5, position: 1 },
      { source: 0, target: 7, type: "bundle", title: "Complete your setup", description: "Add the FlexiDock hub and connect everything", discount: 20, position: 2 },
      { source: 8, target: 10, type: "cross_sell", title: "Charge in style", description: "Pair your NovaBand with the levitating MagFloat charger", discount: 10, position: 1 },
      { source: 0, target: 11, type: "cross_sell", title: "Light up your workspace", description: "Add the ClearView monitor light bar for eye-friendly illumination", discount: 5, position: 3 },
    ];

    for (const uDef of upsellDefs) {
      try {
        await api("POST", `/api/v1/stores/${storeId}/upsells`, {
          source_product_id: products[uDef.source].id,
          target_product_id: products[uDef.target].id,
          upsell_type: uDef.type,
          title: uDef.title,
          description: uDef.description,
          discount_percentage: uDef.discount,
          position: uDef.position,
        }, token);
        console.log(`   ✓ ${products[uDef.source].title} → ${products[uDef.target].title} (${uDef.type})`);
      } catch (e: any) {
        console.log(`   ✗ ${uDef.title}: ${e.message}`);
      }
    }
  } else {
    console.log("   ⤳ Not enough products for upsells, skipping");
  }

  // ── 15. Team ───────────────────────────────────────────────────────────────
  console.log("\n15. Inviting team members...");
  const teamDefs = [
    { email: "marketing@voltelectronics.com", role: "editor" },
    { email: "support@voltelectronics.com", role: "viewer" },
  ];

  for (const tDef of teamDefs) {
    try {
      await api("POST", `/api/v1/stores/${storeId}/team/invite`, tDef, token);
      console.log(`   ✓ ${tDef.email} (${tDef.role})`);
    } catch (e: any) {
      console.log(`   ✗ ${tDef.email}: ${e.message}`);
    }
  }

  // ── 16. Webhooks ───────────────────────────────────────────────────────────
  console.log("\n16. Creating webhooks...");
  const webhookDefs = [
    { url: "https://hooks.voltelectronics.com/orders", events: ["order.created", "order.paid", "order.shipped", "order.delivered"], secret: "whsec_volt_orders_2024" },
    { url: "https://hooks.voltelectronics.com/inventory", events: ["product.updated", "product.created"], secret: "whsec_volt_inventory_2024" },
  ];

  for (const wDef of webhookDefs) {
    try {
      await api("POST", `/api/v1/stores/${storeId}/webhooks`, wDef, token);
      console.log(`   ✓ ${wDef.url} (${wDef.events.length} events)`);
    } catch (e: any) {
      console.log(`   ✗ ${wDef.url}: ${e.message}`);
    }
  }

  // ── 17. A/B Tests ──────────────────────────────────────────────────────────
  console.log("\n17. Creating A/B tests...");
  const abTestDefs = [
    {
      name: "Checkout Button Color",
      description: "Test whether a green vs blue checkout button improves conversion rate",
      metric: "conversion_rate",
      variants: [
        { name: "Blue (Control)", weight: 50, is_control: true, description: "Current blue checkout button" },
        { name: "Green", weight: 50, description: "Green checkout button with 'Buy Now' text" },
      ],
    },
    {
      name: "Product Page Layout",
      description: "Compare single-column vs two-column product page layout for add-to-cart rate",
      metric: "add_to_cart_rate",
      variants: [
        { name: "Single Column (Control)", weight: 34, is_control: true, description: "Current single-column layout" },
        { name: "Two Column", weight: 33, description: "Image left, details right layout" },
        { name: "Gallery Focus", weight: 33, description: "Large image gallery with compact details below" },
      ],
    },
  ];

  for (const abDef of abTestDefs) {
    try {
      await api("POST", `/api/v1/stores/${storeId}/ab-tests`, abDef, token);
      console.log(`   ✓ ${abDef.name} (${abDef.variants.length} variants)`);
    } catch (e: any) {
      console.log(`   ✗ ${abDef.name}: ${e.message}`);
    }
  }

  // ── 18. Domain ─────────────────────────────────────────────────────────────
  console.log("\n18. Setting custom domain...");
  try {
    await api("POST", `/api/v1/stores/${storeId}/domain`, { domain: "shop.voltelectronics.com" }, token);
    console.log("   ✓ shop.voltelectronics.com");
  } catch (e: any) {
    console.log(`   ✗ Domain: ${e.message}`);
  }

  // ── 19. Order Notes ───────────────────────────────────────────────────────
  console.log("\n19. Adding order notes...");
  try {
    const ordersRes = await api("GET", `/api/v1/stores/${storeId}/orders?per_page=4`, undefined, token);
    const orderItems = ordersRes?.items || ordersRes || [];
    const notesSamples = [
      "VIP customer — include free Volt Electronics sticker pack with shipment. Alice has ordered 3x in the past month.",
      "Customer requested gift wrapping. Use blue paper with silver ribbon. Include handwritten 'Happy Birthday' card.",
      "Expedited shipping requested via email support. Customer is traveling internationally on the 15th — must arrive before then.",
      "Return customer — 3rd order this month. Consider adding to VIP Early Access segment. Apply loyalty discount on next order.",
    ];
    for (let i = 0; i < Math.min(orderItems.length, notesSamples.length); i++) {
      try {
        await api("PATCH", `/api/v1/stores/${storeId}/orders/${orderItems[i].id}`, {
          notes: notesSamples[i],
        }, token);
        console.log(`   ✓ Note on order ${orderItems[i].id.slice(0, 8)}...`);
      } catch (e: any) {
        console.log(`   ✗ Note: ${e.message}`);
      }
    }
  } catch (e: any) {
    console.log(`   ✗ Order notes: ${e.message}`);
  }

  // ── 20. Activate Cyberpunk theme with custom blocks ────────────────────────
  console.log("\n20. Activating Cyberpunk theme with Volt Electronics blocks...");
  try {
    // List all themes for the store and find the Cyberpunk preset
    const themes = await api("GET", `/api/v1/stores/${storeId}/themes`, undefined, token);
    const themeList = themes || [];
    const cyberpunk = themeList.find((t: any) => t.name?.toLowerCase() === "cyberpunk");

    if (cyberpunk) {
      // Activate Cyberpunk
      await api("POST", `/api/v1/stores/${storeId}/themes/${cyberpunk.id}/activate`, {}, token);
      console.log("   ✓ Cyberpunk theme activated");

      // Customize blocks for Volt Electronics
      const voltBlocks = [
        {
          id: "hero",
          type: "hero_banner",
          enabled: true,
          config: {
            title: "THE FUTURE IS NOW",
            subtitle: "Next-gen electronics for next-gen people. Laptops, phones, audio — all at unbeatable prices.",
            cta_text: "SHOP THE DROP",
            cta_link: "/products",
            bg_type: "gradient",
            text_position: "left",
            height: "full",
            overlay_style: "gradient",
          },
        },
        {
          id: "countdown",
          type: "countdown_timer",
          enabled: true,
          config: {
            title: "FLASH SALE — UP TO 25% OFF",
            subtitle: "Limited time. Don't miss out on premium electronics at the lowest prices of the year.",
            target_date: "2026-12-31T23:59:59",
            cta_text: "USE CODE: SUMMER25",
            cta_link: "/products",
            bg_style: "transparent",
          },
        },
        {
          id: "featured",
          type: "featured_products",
          enabled: true,
          config: {
            title: "TRENDING NOW",
            count: 8,
            columns: 4,
            show_prices: true,
            show_badges: true,
          },
        },
        {
          id: "carousel",
          type: "product_carousel",
          enabled: true,
          config: {
            title: "HOT DROPS",
            count: 12,
            auto_scroll: true,
            interval: 3000,
            show_prices: true,
          },
        },
        {
          id: "categories",
          type: "categories_grid",
          enabled: true,
          config: {
            title: "EXPLORE BY CATEGORY",
            columns: 4,
            show_product_count: true,
          },
        },
        {
          id: "testimonials",
          type: "testimonials",
          enabled: true,
          config: {
            title: "WHAT OUR CUSTOMERS SAY",
            layout: "cards",
            items: [
              {
                quote: "The ProBook Ultra is hands-down the best laptop I've ever used. The 4K OLED display is insane for content creation.",
                author: "Sarah L.",
                role: "Software Developer",
              },
              {
                quote: "PixelBudz Pro ANC changed my commute. I can't believe this sound quality at this price point.",
                author: "Dave S.",
                role: "Music Producer",
              },
              {
                quote: "Fast shipping, great packaging, and the products are exactly as described. Volt Electronics is my go-to store now.",
                author: "Alice M.",
                role: "Verified Buyer",
              },
            ],
          },
        },
        {
          id: "trust",
          type: "trust_badges",
          enabled: true,
          config: {
            badges: [
              { icon: "zap", title: "Same-Day Shipping", description: "Orders before 2PM ship today" },
              { icon: "shield", title: "2-Year Warranty", description: "On all electronics" },
              { icon: "rotate-ccw", title: "30-Day Returns", description: "No questions asked" },
              { icon: "headphones", title: "24/7 Support", description: "Real humans, real help" },
            ],
            columns: 4,
          },
        },
        {
          id: "newsletter",
          type: "newsletter",
          enabled: true,
          config: {
            title: "JOIN THE VOLT NETWORK",
            subtitle: "Get early access to flash sales, new product drops, and exclusive discount codes.",
            button_text: "SUBSCRIBE",
          },
        },
      ];

      await api("PATCH", `/api/v1/stores/${storeId}/themes/${cyberpunk.id}`, {
        blocks: voltBlocks,
      }, token);
      console.log("   ✓ Custom Volt Electronics blocks applied (8 blocks)");
    } else {
      console.log("   ✗ Cyberpunk preset not found, skipping");
    }
  } catch (e: any) {
    console.log(`   ✗ Theme: ${e.message}`);
  }

  // ── Summary ────────────────────────────────────────────────────────────────
  console.log("\n" + "=".repeat(60));
  console.log("  Seed complete!");
  console.log("=".repeat(60));
  console.log(`
  Store Owner Login:   demo@example.com / password123
  Customer Logins:     alice@example.com / bob@example.com / carol@example.com
                       (all use password123)
  Dashboard:           http://localhost:3000
  Storefront:          http://localhost:3001?store=${slug}
  API Docs:            http://localhost:8000/docs
  Store ID:            ${storeId}

  Demo Highlights:
  ─────────────────────────────────────────────────────────
  • 12 products with rich descriptions, Unsplash images, and variants
  • 4 products with Sale badges (compare_at_price set)
  • 3 low-stock products for inventory alert demos
  • Cyberpunk theme with 8 custom blocks
  • 4 orders across full lifecycle (pending → paid → shipped → delivered)
  • 3 customers with addresses and wishlists
  • 14 product reviews across 8 products
`);
}

main().catch((err) => {
  console.error("\nSeed script failed:", err.message);
  process.exit(1);
});
