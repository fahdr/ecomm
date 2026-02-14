#!/usr/bin/env npx tsx
/**
 * Seed script — populates the database with realistic demo data for ALL
 * platform services so you can manually test dashboards, storefronts,
 * and every SaaS product in the monorepo.
 *
 * **Usage:**
 *   npx tsx scripts/seed.ts            # Seed core + all running SaaS services
 *   SEED_CORE_ONLY=1 npx tsx scripts/seed.ts  # Seed only the core platform
 *
 * **Prerequisites:**
 *   - Backend running on http://localhost:8000
 *   - Database migrated (alembic upgrade head)
 *   - SaaS services running on their ports (8101-8108) for SaaS seeding
 *
 * **What it creates:**
 *
 *   Core Platform (port 8000):
 *   - 1 user account (demo@example.com / password123)
 *   - 1 store ("Volt Electronics") with Cyberpunk theme
 *   - 6 categories (4 top-level + 2 sub-categories)
 *   - 12 products with rich descriptions, Unsplash images, variants, and SEO metadata
 *   - 3 suppliers linked to products
 *   - 5 discount codes, 4 tax rates, 3 gift cards
 *   - 3 customer accounts with addresses and wishlists
 *   - 14 product reviews, 4 orders with full lifecycle
 *   - 1 refund, 3 segments, 6 upsell rules
 *   - 2 team invitations, 2 webhooks, 2 A/B tests
 *   - 1 custom domain, order notes, cyberpunk theme with 8 blocks
 *
 *   TrendScout (port 8101):
 *   - 3 research runs with keywords, 2 store connections
 *
 *   ContentForge (port 8102):
 *   - 4 custom templates, 3 generation jobs
 *
 *   RankPilot (port 8103):
 *   - 2 sites, 10 tracked keywords, 3 blog posts
 *
 *   FlowSend (port 8104):
 *   - 10 contacts, 2 contact lists, 3 email templates, 2 campaigns, 2 flows
 *
 *   SpyDrop (port 8105):
 *   - 3 competitors, 5 alerts
 *
 *   PostPilot (port 8106):
 *   - 3 social accounts, 6 scheduled posts
 *
 *   AdScale (port 8107):
 *   - 2 ad accounts, 3 campaigns, 4 ad groups, 5 creatives, 2 rules
 *
 *   ShopChat (port 8108):
 *   - 2 chatbots, 8 knowledge base entries
 *
 *   Admin (port 8300):
 *   - 1 admin account (admin@ecomm.com / admin123)
 *
 * **For Developers:**
 *   Each section is self-contained and idempotent. If one feature fails,
 *   subsequent features will still attempt to seed. 409 responses are
 *   silently handled so you can re-run the script safely.
 *
 * **For QA Engineers:**
 *   After running, log in at http://localhost:3000 with demo@example.com
 *   and password123. Browse the storefront at http://localhost:3001?store=volt-electronics.
 *   Check each SaaS dashboard on ports 3101-3108.
 */

// ── Service URLs ────────────────────────────────────────────────────────────

const CORE_API = "http://localhost:8000";
const SERVICES = {
  trendscout:   "http://localhost:8101",
  contentforge: "http://localhost:8102",
  rankpilot:    "http://localhost:8103",
  flowsend:     "http://localhost:8104",
  spydrop:      "http://localhost:8105",
  postpilot:    "http://localhost:8106",
  adscale:      "http://localhost:8107",
  shopchat:     "http://localhost:8108",
};
const ADMIN_API = "http://localhost:8300";

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Makes an HTTP request to the given base URL and path.
 * Returns parsed JSON on success, null on 409 (duplicate), throws on other errors.
 *
 * @param method - HTTP method (GET, POST, PATCH, etc.)
 * @param baseUrl - Base URL of the service
 * @param path - API path (e.g., /api/v1/stores)
 * @param body - Optional request body
 * @param token - Optional Bearer token
 * @returns Parsed JSON response or null
 */
async function api(
  method: string,
  baseUrl: string,
  path: string,
  body?: unknown,
  token?: string
): Promise<any> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${baseUrl}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const text = await res.text();
  if (!res.ok) {
    if (res.status === 409) {
      console.log(`  ⤳ Already exists (409), skipping`);
      return null;
    }
    throw new Error(`${method} ${path} → ${res.status}: ${text}`);
  }
  return text ? JSON.parse(text) : null;
}

/**
 * Convenience wrapper: makes API call to the core platform.
 */
function coreApi(method: string, path: string, body?: unknown, token?: string) {
  return api(method, CORE_API, path, body, token);
}

/**
 * Checks if a service is reachable by hitting its health endpoint.
 *
 * @param baseUrl - Base URL of the service to check
 * @returns true if the service responds, false otherwise
 */
async function isServiceUp(baseUrl: string): Promise<boolean> {
  try {
    const res = await fetch(`${baseUrl}/health`, { signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Registers or logs in a user on the given service.
 * Returns the access token.
 *
 * @param baseUrl - Base URL of the service
 * @param email - User email
 * @param password - User password
 * @returns JWT access token
 */
async function getServiceToken(baseUrl: string, email: string, password: string): Promise<string> {
  try {
    const res = await api("POST", baseUrl, "/api/v1/auth/register", { email, password });
    if (res?.access_token) return res.access_token;
  } catch {
    // User exists, try login
  }
  const loginRes = await api("POST", baseUrl, "/api/v1/auth/login", { email, password });
  return loginRes.access_token;
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

// ── Core Platform Seeder ─────────────────────────────────────────────────────

async function seedCorePlatform() {
  console.log("\n╔══════════════════════════════════════════════════════════╗");
  console.log("║          CORE PLATFORM — Volt Electronics               ║");
  console.log("╚══════════════════════════════════════════════════════════╝\n");

  // ── 1. User ────────────────────────────────────────────────────────────────
  console.log("1. Creating user account...");
  let token: string;
  const authRes = await coreApi("POST", "/api/v1/auth/register", {
    email: "demo@example.com",
    password: "password123",
  });
  if (authRes) {
    token = authRes.access_token;
    console.log("   ✓ Created demo@example.com / password123");
  } else {
    console.log("   ⤳ User exists, logging in...");
    const loginRes = await coreApi("POST", "/api/v1/auth/login", {
      email: "demo@example.com",
      password: "password123",
    });
    token = loginRes.access_token;
    console.log("   ✓ Logged in as demo@example.com");
  }

  await sleep(500);

  // ── 2. Store ───────────────────────────────────────────────────────────────
  console.log("\n2. Creating store...");
  let store: any;
  try {
    store = await coreApi("POST", "/api/v1/stores", {
      name: "Volt Electronics",
      niche: "electronics",
      description: "Premium consumer electronics and accessories for the modern tech enthusiast. We source the latest gadgets directly from top manufacturers worldwide — laptops, smartphones, audio gear, and essential accessories at competitive prices with fast shipping.",
    }, token);
    console.log(`   ✓ Store "${store.name}" (slug: ${store.slug})`);
  } catch (e: any) {
    console.log("   ⤳ Store creation failed, fetching existing stores...");
    const stores = await coreApi("GET", "/api/v1/stores", undefined, token);
    const items = stores.items || stores;
    store = Array.isArray(items) ? items[0] : items;
    if (!store) throw new Error("No store found and creation failed");
    console.log(`   ✓ Using existing store "${store.name}" (${store.id})`);
  }

  const storeId = store.id;
  const slug = store.slug;
  await sleep(500);

  // ── 3. Categories ──────────────────────────────────────────────────────────
  console.log("\n3. Creating categories...");
  const categoryMap: Record<string, string> = {};

  try {
    const existing = await coreApi("GET", `/api/v1/stores/${storeId}/categories?per_page=50`, undefined, token) as any;
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
      const created = await coreApi("POST", `/api/v1/stores/${storeId}/categories`, cat, token);
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
      const sub1 = await coreApi("POST", `/api/v1/stores/${storeId}/categories`, {
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
      const sub2 = await coreApi("POST", `/api/v1/stores/${storeId}/categories`, {
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
      const product = await coreApi("POST", `/api/v1/stores/${storeId}/products`, pDef, token);
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
      await coreApi("POST", `/api/v1/stores/${storeId}/categories/${catId}/products`, { product_ids: prodIds }, token);
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
      const supplier = await coreApi("POST", `/api/v1/stores/${storeId}/suppliers`, sDef, token);
      if (supplier) {
        suppliers.push(supplier);
        console.log(`   ✓ ${sDef.name}`);
      }
    } catch (e: any) {
      console.log(`   ✗ ${sDef.name}: ${e.message}`);
    }
  }

  if (suppliers.length > 0 && products.length > 0) {
    console.log("   Linking products to suppliers...");
    const productSupplierLinks = [
      { productIdx: 0, supplierIdx: 0, cost: "780.00", sku: "TS-PBU15" },
      { productIdx: 1, supplierIdx: 0, cost: "1150.00", sku: "TS-TFRX" },
      { productIdx: 2, supplierIdx: 1, cost: "620.00", sku: "MF-GNX" },
      { productIdx: 3, supplierIdx: 2, cost: "85.00", sku: "AP-PBP" },
      { productIdx: 4, supplierIdx: 2, cost: "195.00", sku: "AP-SS" },
      { productIdx: 5, supplierIdx: 1, cost: "18.00", sku: "MF-HC65" },
      { productIdx: 6, supplierIdx: 1, cost: "8.50", sku: "MF-ASP" },
      { productIdx: 7, supplierIdx: 0, cost: "42.00", sku: "TS-FD" },
      { productIdx: 8, supplierIdx: 1, cost: "120.00", sku: "MF-NB" },
      { productIdx: 9, supplierIdx: 2, cost: "32.00", sku: "AP-VB" },
      { productIdx: 10, supplierIdx: 1, cost: "28.00", sku: "MF-MFWC" },
      { productIdx: 11, supplierIdx: 0, cost: "22.00", sku: "TS-CV" },
    ];

    for (const link of productSupplierLinks) {
      if (products[link.productIdx] && suppliers[link.supplierIdx]) {
        try {
          await coreApi(
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

  // ── 6-20: Discounts, Tax, Gift Cards, Customers, Orders, etc. ──────────────
  // (Sections 6-20 remain identical to the original seed script)

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
      await coreApi("POST", `/api/v1/stores/${storeId}/discounts`, dDef, token);
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
      await coreApi("POST", `/api/v1/stores/${storeId}/tax-rates`, tDef, token);
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
      const gc = await coreApi("POST", `/api/v1/stores/${storeId}/gift-cards`, gcDef, token);
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
      const res = await coreApi("POST", `/api/v1/public/stores/${slug}/customers/register`, cDef);
      if (res) {
        customerTokens[cDef.email] = res.access_token;
        console.log(`   ✓ ${cDef.first_name} ${cDef.last_name} (${cDef.email})`);
      }
    } catch (e: any) {
      if (e.message.includes("400")) {
        try {
          const loginRes = await coreApi("POST", `/api/v1/public/stores/${slug}/customers/login`, {
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
        await coreApi("POST", `/api/v1/customer/addresses`, addr, custToken);
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
      { email: "alice@example.com", productIndices: [1, 4, 8] },
      { email: "bob@example.com", productIndices: [0, 9] },
      { email: "carol@example.com", productIndices: [2, 10] },
    ];

    for (const { email, productIndices } of wishlistDefs) {
      const custToken = customerTokens[email];
      if (!custToken) continue;
      for (const idx of productIndices) {
        if (products[idx]) {
          try {
            await coreApi("POST", `/api/v1/customer/wishlist`, { product_id: products[idx].id }, custToken);
            console.log(`   ✓ ${email} → ${products[idx].title}`);
          } catch (e: any) {
            console.log(`   ✗ ${email} wishlist: ${e.message}`);
          }
        }
      }
    }
  }

  // ── 10. Orders ─────────────────────────────────────────────────────────────
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
        shipping_address: { name: "Alice Martinez", line1: "742 Evergreen Terrace", city: "San Francisco", state: "CA", postal_code: "94102", country: "US", phone: "+1-555-0101" },
        label: "Alice — ProBook + 2x HyperCharge",
      },
      {
        customer_email: "bob@example.com",
        items: [
          { product_id: products[2].id, variant_id: products[2].variants?.[0]?.id, quantity: 1 },
          { product_id: products[6].id, variant_id: products[6].variants?.[0]?.id, quantity: 1 },
        ],
        shipping_address: { name: "Bob Johnson", line1: "350 Fifth Avenue", line2: "Suite 3300", city: "New York", state: "NY", postal_code: "10118", country: "US", phone: "+1-555-0202" },
        label: "Bob — Galaxy Nova + ArmorShield",
      },
      {
        customer_email: "carol@example.com",
        items: [
          { product_id: products[3].id, variant_id: products[3].variants?.[0]?.id, quantity: 1 },
          { product_id: products[4].id, variant_id: products[4].variants?.[0]?.id, quantity: 1 },
        ],
        shipping_address: { name: "Carol Davis", line1: "1600 Pennsylvania Avenue NW", city: "Washington", state: "DC", postal_code: "20500", country: "US" },
        label: "Carol — PixelBudz + SoundStage",
      },
      {
        customer_email: "dave@example.com",
        items: [
          { product_id: products[1].id, variant_id: products[1].variants?.[0]?.id, quantity: 1 },
          { product_id: products[7].id, variant_id: products[7].variants?.[0]?.id, quantity: 1 },
        ],
        shipping_address: { name: "Dave Sullivan", line1: "2101 NASA Parkway", city: "Houston", state: "TX", postal_code: "77058", country: "US", phone: "+1-555-0404" },
        label: "Dave — TitanForce + FlexiDock",
      },
    ];

    for (const oDef of orderDefs) {
      try {
        const checkout = await coreApi("POST", `/api/v1/public/stores/${slug}/checkout`, {
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

    await sleep(300);
    if (orders.length >= 4) {
      for (let i = 0; i < orders.length; i++) {
        const names = ["Alice", "Bob", "Carol", "Dave"];
        try {
          await coreApi("PATCH", `/api/v1/stores/${storeId}/orders/${orders[i].order_id}`, { status: "paid" }, token);
          console.log(`   ✓ ${names[i]} → paid`);
        } catch (e: any) {
          console.log(`   ✗ ${names[i]} → paid: ${e.message}`);
        }
      }

      try {
        await coreApi("POST", `/api/v1/stores/${storeId}/orders/${orders[0].order_id}/fulfill`, { tracking_number: "1Z999AA10123456784", carrier: "UPS" }, token);
        console.log("   ✓ Alice → shipped (UPS: 1Z999AA10123456784)");
      } catch (e: any) {
        console.log(`   ✗ Alice → shipped: ${e.message}`);
      }

      try {
        await coreApi("POST", `/api/v1/stores/${storeId}/orders/${orders[1].order_id}/fulfill`, { tracking_number: "9400111899223100001234", carrier: "USPS" }, token);
        console.log("   ✓ Bob → shipped (USPS: 9400111899223100001234)");
        await coreApi("POST", `/api/v1/stores/${storeId}/orders/${orders[1].order_id}/deliver`, {}, token);
        console.log("   ✓ Bob → delivered");
      } catch (e: any) {
        console.log(`   ✗ Bob fulfillment: ${e.message}`);
      }

      console.log("   ℹ Carol & Dave remain as paid (awaiting fulfillment)");
    }
  } else {
    console.log("   ⤳ Not enough products for orders, skipping");
  }

  // ── 11. Refund ─────────────────────────────────────────────────────────────
  console.log("\n11. Creating refund...");
  if (orders.length >= 3) {
    try {
      await coreApi("POST", `/api/v1/stores/${storeId}/refunds`, {
        order_id: orders[2].order_id,
        reason: "Customer received wrong color variant",
        reason_details: "Customer ordered Pearl White PixelBudz but received Charcoal. Issuing full refund for the earbuds while customer ships the item back.",
        amount: 179.99,
      }, token);
      console.log("   ✓ Refund for Carol's order — $179.99");
    } catch (e: any) {
      console.log(`   ✗ Refund: ${e.message}`);
    }
  }

  // ── 12. Reviews ────────────────────────────────────────────────────────────
  console.log("\n12. Creating product reviews...");
  if (products.length >= 10) {
    const reviewDefs = [
      { productSlug: products[0].slug, rating: 5, title: "Best laptop I've ever owned", body: "The 4K OLED display is absolutely stunning. Battery easily lasts 10+ hours. The build quality is exceptional — feels premium without being heavy. Typing on the keyboard is a joy. Highly recommended for any professional.", customer_name: "Alice M.", customer_email: "alice@example.com" },
      { productSlug: products[0].slug, rating: 4, title: "Great machine, minor quirks", body: "Performance is excellent and the display is beautiful. Only downside is the webcam quality — it's passable for calls but nothing special. Fan noise under heavy load is noticeable but not loud.", customer_name: "Tom K.", customer_email: "tom@example.com" },
      { productSlug: products[0].slug, rating: 5, title: "Perfect for development", body: "As a software developer, this laptop handles everything I throw at it. Docker containers, multiple IDEs, dozens of browser tabs — never breaks a sweat. The 32GB model is worth the upgrade.", customer_name: "Sarah L.", customer_email: "sarah@example.com" },
      { productSlug: products[2].slug, rating: 5, title: "Camera is mind-blowing", body: "The 200MP camera produces incredibly detailed shots. Night mode is the best I've seen on any phone. The 8K video capability is future-proof. Battery lasts a full day even with heavy camera use.", customer_name: "Bob J.", customer_email: "bob@example.com" },
      { productSlug: products[2].slug, rating: 4, title: "Almost perfect flagship", body: "Beautiful display, fast performance, great cameras. The phone is a bit large for one-handed use, and the 512GB model is expensive. But overall it's the best Android phone you can buy right now.", customer_name: "Lisa P.", customer_email: "lisa@example.com" },
      { productSlug: products[2].slug, rating: 3, title: "Good but overpriced", body: "Solid phone with great features, but the price is hard to justify when competitors offer 90% of the experience for 60% of the cost. The camera bump is also quite prominent.", customer_name: "Mark R.", customer_email: "mark@example.com" },
      { productSlug: products[3].slug, rating: 5, title: "ANC is incredible", body: "These earbuds block out everything — office chatter, airplane noise, city traffic. Sound quality rivals much more expensive headphones. The spatial audio feature is a nice bonus for movies.", customer_name: "Carol D.", customer_email: "carol@example.com" },
      { productSlug: products[3].slug, rating: 4, title: "Great value for the price", body: "Comfortable fit, good sound, excellent battery life. The ANC is effective but not quite at the level of the premium Sony or Bose options. For the price though, absolutely worth it.", customer_name: "Dave S.", customer_email: "dave@example.com" },
      { productSlug: products[4].slug, rating: 5, title: "Audiophile approved", body: "These are reference-grade headphones at a fraction of the price. The planar magnetic drivers produce clean, detailed sound across all frequencies. The memory foam cushions are so comfortable I forget I'm wearing them.", customer_name: "James W.", customer_email: "james@example.com" },
      { productSlug: products[5].slug, rating: 5, title: "Replaced all my chargers", body: "One charger for everything — laptop, phone, tablet. The 65W output charges my MacBook Pro at full speed. Incredibly compact for a 3-port charger. The foldable prongs are perfect for travel.", customer_name: "Nina H.", customer_email: "nina@example.com" },
      { productSlug: products[5].slug, rating: 4, title: "Almost perfect charger", body: "Great charger overall. Charges my phone super fast and can handle my laptop too. Only complaint is it gets quite warm under full load, but that seems normal for GaN chargers.", customer_name: "Ryan F.", customer_email: "ryan@example.com" },
      { productSlug: products[6].slug, rating: 5, title: "Survived a 6-foot drop", body: "Dropped my phone face-down on concrete from my car roof. Phone was completely fine thanks to this case. The raised bezels saved the camera too. Slim enough that it doesn't add much bulk.", customer_name: "Pat G.", customer_email: "pat@example.com" },
      { productSlug: products[8].slug, rating: 5, title: "My daily health companion", body: "The sleep tracking alone is worth the price. I discovered I was waking up 12 times a night — adjusted my routine and now sleep like a baby. Heart rate monitoring is accurate compared to my chest strap. Battery lasts a full week.", customer_name: "Alice M.", customer_email: "alice@example.com" },
      { productSlug: products[9].slug, rating: 4, title: "Punches way above its size", body: "Brought this to a beach barbecue and it filled the whole patio with sound. Bass is surprisingly deep for something this small. Only wish it had a built-in handle. The PartySync feature worked perfectly with my friend's speaker.", customer_name: "Dave S.", customer_email: "dave@example.com" },
    ];

    for (const rDef of reviewDefs) {
      try {
        await coreApi("POST", `/api/v1/public/stores/${slug}/products/${rDef.productSlug}/reviews`, {
          rating: rDef.rating, title: rDef.title, body: rDef.body,
          customer_name: rDef.customer_name, customer_email: rDef.customer_email,
        });
        console.log(`   ✓ ${rDef.customer_name} → ${rDef.productSlug} (${rDef.rating}★)`);
      } catch (e: any) {
        console.log(`   ✗ ${rDef.customer_name}: ${e.message}`);
      }
    }
  }

  // ── 13. Segments ───────────────────────────────────────────────────────────
  console.log("\n13. Creating customer segments...");
  for (const sDef of [
    { name: "High-Value Customers", description: "Customers who have spent over $500 lifetime", segment_type: "manual" },
    { name: "Repeat Buyers", description: "Customers with 2 or more orders", segment_type: "manual" },
    { name: "VIP Early Access", description: "Hand-picked customers for early access to new products", segment_type: "manual" },
  ]) {
    try {
      await coreApi("POST", `/api/v1/stores/${storeId}/segments`, sDef, token);
      console.log(`   ✓ ${sDef.name}`);
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
        await coreApi("POST", `/api/v1/stores/${storeId}/upsells`, {
          source_product_id: products[uDef.source].id, target_product_id: products[uDef.target].id,
          upsell_type: uDef.type, title: uDef.title, description: uDef.description,
          discount_percentage: uDef.discount, position: uDef.position,
        }, token);
        console.log(`   ✓ ${products[uDef.source].title} → ${products[uDef.target].title} (${uDef.type})`);
      } catch (e: any) {
        console.log(`   ✗ ${uDef.title}: ${e.message}`);
      }
    }
  }

  // ── 15. Team ───────────────────────────────────────────────────────────────
  console.log("\n15. Inviting team members...");
  for (const tDef of [
    { email: "marketing@voltelectronics.com", role: "editor" },
    { email: "support@voltelectronics.com", role: "viewer" },
  ]) {
    try {
      await coreApi("POST", `/api/v1/stores/${storeId}/team/invite`, tDef, token);
      console.log(`   ✓ ${tDef.email} (${tDef.role})`);
    } catch (e: any) {
      console.log(`   ✗ ${tDef.email}: ${e.message}`);
    }
  }

  // ── 16. Webhooks ───────────────────────────────────────────────────────────
  console.log("\n16. Creating webhooks...");
  for (const wDef of [
    { url: "https://hooks.voltelectronics.com/orders", events: ["order.created", "order.paid", "order.shipped", "order.delivered"], secret: "whsec_volt_orders_2024" },
    { url: "https://hooks.voltelectronics.com/inventory", events: ["product.updated", "product.created"], secret: "whsec_volt_inventory_2024" },
  ]) {
    try {
      await coreApi("POST", `/api/v1/stores/${storeId}/webhooks`, wDef, token);
      console.log(`   ✓ ${wDef.url} (${wDef.events.length} events)`);
    } catch (e: any) {
      console.log(`   ✗ ${wDef.url}: ${e.message}`);
    }
  }

  // ── 17. A/B Tests ──────────────────────────────────────────────────────────
  console.log("\n17. Creating A/B tests...");
  for (const abDef of [
    {
      name: "Checkout Button Color", description: "Test whether a green vs blue checkout button improves conversion rate", metric: "conversion_rate",
      variants: [
        { name: "Blue (Control)", weight: 50, is_control: true, description: "Current blue checkout button" },
        { name: "Green", weight: 50, description: "Green checkout button with 'Buy Now' text" },
      ],
    },
    {
      name: "Product Page Layout", description: "Compare single-column vs two-column product page layout for add-to-cart rate", metric: "add_to_cart_rate",
      variants: [
        { name: "Single Column (Control)", weight: 34, is_control: true, description: "Current single-column layout" },
        { name: "Two Column", weight: 33, description: "Image left, details right layout" },
        { name: "Gallery Focus", weight: 33, description: "Large image gallery with compact details below" },
      ],
    },
  ]) {
    try {
      await coreApi("POST", `/api/v1/stores/${storeId}/ab-tests`, abDef, token);
      console.log(`   ✓ ${abDef.name} (${abDef.variants.length} variants)`);
    } catch (e: any) {
      console.log(`   ✗ ${abDef.name}: ${e.message}`);
    }
  }

  // ── 18. Domain ─────────────────────────────────────────────────────────────
  console.log("\n18. Setting custom domain...");
  try {
    await coreApi("POST", `/api/v1/stores/${storeId}/domain`, { domain: "shop.voltelectronics.com" }, token);
    console.log("   ✓ shop.voltelectronics.com");
  } catch (e: any) {
    console.log(`   ✗ Domain: ${e.message}`);
  }

  // ── 19. Order Notes ───────────────────────────────────────────────────────
  console.log("\n19. Adding order notes...");
  try {
    const ordersRes = await coreApi("GET", `/api/v1/stores/${storeId}/orders?per_page=4`, undefined, token);
    const orderItems = ordersRes?.items || ordersRes || [];
    const notesSamples = [
      "VIP customer — include free Volt Electronics sticker pack with shipment. Alice has ordered 3x in the past month.",
      "Customer requested gift wrapping. Use blue paper with silver ribbon. Include handwritten 'Happy Birthday' card.",
      "Expedited shipping requested via email support. Customer is traveling internationally on the 15th — must arrive before then.",
      "Return customer — 3rd order this month. Consider adding to VIP Early Access segment. Apply loyalty discount on next order.",
    ];
    for (let i = 0; i < Math.min(orderItems.length, notesSamples.length); i++) {
      try {
        await coreApi("PATCH", `/api/v1/stores/${storeId}/orders/${orderItems[i].id}`, { notes: notesSamples[i] }, token);
        console.log(`   ✓ Note on order ${orderItems[i].id.slice(0, 8)}...`);
      } catch (e: any) {
        console.log(`   ✗ Note: ${e.message}`);
      }
    }
  } catch (e: any) {
    console.log(`   ✗ Order notes: ${e.message}`);
  }

  // ── 20. Activate Cyberpunk theme ──────────────────────────────────────────
  console.log("\n20. Activating Cyberpunk theme with Volt Electronics blocks...");
  try {
    const themes = await coreApi("GET", `/api/v1/stores/${storeId}/themes`, undefined, token);
    const themeList = themes || [];
    const cyberpunk = themeList.find((t: any) => t.name?.toLowerCase() === "cyberpunk");

    if (cyberpunk) {
      await coreApi("POST", `/api/v1/stores/${storeId}/themes/${cyberpunk.id}/activate`, {}, token);
      console.log("   ✓ Cyberpunk theme activated");

      const voltBlocks = [
        { id: "hero", type: "hero_banner", enabled: true, config: { title: "THE FUTURE IS NOW", subtitle: "Next-gen electronics for next-gen people. Laptops, phones, audio — all at unbeatable prices.", cta_text: "SHOP THE DROP", cta_link: "/products", bg_type: "gradient", text_position: "left", height: "full", overlay_style: "gradient" } },
        { id: "countdown", type: "countdown_timer", enabled: true, config: { title: "FLASH SALE — UP TO 25% OFF", subtitle: "Limited time. Don't miss out on premium electronics at the lowest prices of the year.", target_date: "2026-12-31T23:59:59", cta_text: "USE CODE: SUMMER25", cta_link: "/products", bg_style: "transparent" } },
        { id: "featured", type: "featured_products", enabled: true, config: { title: "TRENDING NOW", count: 8, columns: 4, show_prices: true, show_badges: true } },
        { id: "carousel", type: "product_carousel", enabled: true, config: { title: "HOT DROPS", count: 12, auto_scroll: true, interval: 3000, show_prices: true } },
        { id: "categories", type: "categories_grid", enabled: true, config: { title: "EXPLORE BY CATEGORY", columns: 4, show_product_count: true } },
        { id: "testimonials", type: "testimonials", enabled: true, config: { title: "WHAT OUR CUSTOMERS SAY", layout: "cards", items: [
          { quote: "The ProBook Ultra is hands-down the best laptop I've ever used. The 4K OLED display is insane for content creation.", author: "Sarah L.", role: "Software Developer" },
          { quote: "PixelBudz Pro ANC changed my commute. I can't believe this sound quality at this price point.", author: "Dave S.", role: "Music Producer" },
          { quote: "Fast shipping, great packaging, and the products are exactly as described. Volt Electronics is my go-to store now.", author: "Alice M.", role: "Verified Buyer" },
        ] } },
        { id: "trust", type: "trust_badges", enabled: true, config: { badges: [
          { icon: "zap", title: "Same-Day Shipping", description: "Orders before 2PM ship today" },
          { icon: "shield", title: "2-Year Warranty", description: "On all electronics" },
          { icon: "rotate-ccw", title: "30-Day Returns", description: "No questions asked" },
          { icon: "headphones", title: "24/7 Support", description: "Real humans, real help" },
        ], columns: 4 } },
        { id: "newsletter", type: "newsletter", enabled: true, config: { title: "JOIN THE VOLT NETWORK", subtitle: "Get early access to flash sales, new product drops, and exclusive discount codes.", button_text: "SUBSCRIBE" } },
      ];

      await coreApi("PATCH", `/api/v1/stores/${storeId}/themes/${cyberpunk.id}`, { blocks: voltBlocks }, token);
      console.log("   ✓ Custom Volt Electronics blocks applied (8 blocks)");
    } else {
      console.log("   ✗ Cyberpunk preset not found, skipping");
    }
  } catch (e: any) {
    console.log(`   ✗ Theme: ${e.message}`);
  }

  return { token, storeId, slug, products };
}

// ── SaaS Service Seeders ─────────────────────────────────────────────────────

/**
 * Seeds TrendScout with research runs and store connections.
 */
async function seedTrendScout(token: string) {
  const baseUrl = SERVICES.trendscout;
  console.log("\n╔══════════════════════════════════════════════════════════╗");
  console.log("║          TRENDSCOUT — AI Product Research                ║");
  console.log("╚══════════════════════════════════════════════════════════╝\n");

  const svcToken = await getServiceToken(baseUrl, "demo@example.com", "password123");

  // Research Runs
  console.log("  Creating research runs...");
  const researchRuns = [
    { keywords: ["wireless earbuds", "noise cancelling", "ANC"], sources: ["aliexpress", "google_trends"] },
    { keywords: ["smart home gadgets", "IoT devices", "home automation"], sources: ["aliexpress", "amazon"] },
    { keywords: ["portable projector", "mini projector", "camping projector"], sources: ["google_trends"] },
  ];
  for (const run of researchRuns) {
    try {
      await api("POST", baseUrl, "/api/v1/research/runs", run, svcToken);
      console.log(`   ✓ Research: ${run.keywords.join(", ")}`);
    } catch (e: any) {
      console.log(`   ✗ Research: ${e.message}`);
    }
  }

  // Store Connections
  console.log("  Creating store connections...");
  const connections = [
    { platform: "shopify", store_url: "https://volt-electronics.myshopify.com", api_key: "shpat_demo_key_001" },
    { platform: "woocommerce", store_url: "https://shop.voltelectronics.com", api_key: "ck_demo_key_001", api_secret: "cs_demo_secret_001" },
  ];
  for (const conn of connections) {
    try {
      await api("POST", baseUrl, "/api/v1/connections", conn, svcToken);
      console.log(`   ✓ ${conn.platform}: ${conn.store_url}`);
    } catch (e: any) {
      console.log(`   ✗ ${conn.platform}: ${e.message}`);
    }
  }
}

/**
 * Seeds ContentForge with templates and generation jobs.
 */
async function seedContentForge(token: string) {
  const baseUrl = SERVICES.contentforge;
  console.log("\n╔══════════════════════════════════════════════════════════╗");
  console.log("║          CONTENTFORGE — AI Content Generator             ║");
  console.log("╚══════════════════════════════════════════════════════════╝\n");

  const svcToken = await getServiceToken(baseUrl, "demo@example.com", "password123");

  // Custom Templates
  console.log("  Creating content templates...");
  const templates = [
    { name: "Volt Brand Voice", description: "Tech-forward, energetic tone for Volt Electronics products", tone: "energetic", style: "concise", content_types: ["title", "description", "meta_description"] },
    { name: "SEO Product Copy", description: "Keyword-optimized product descriptions for search ranking", tone: "professional", style: "detailed", content_types: ["title", "description", "meta_description", "tags"] },
    { name: "Social Media Captions", description: "Short, punchy captions for Instagram and TikTok", tone: "casual", style: "concise", content_types: ["title", "description"] },
    { name: "Email Newsletter", description: "Warm, engaging copy for email campaigns", tone: "friendly", style: "detailed", content_types: ["title", "description"] },
  ];
  for (const tmpl of templates) {
    try {
      await api("POST", baseUrl, "/api/v1/templates", tmpl, svcToken);
      console.log(`   ✓ Template: ${tmpl.name}`);
    } catch (e: any) {
      console.log(`   ✗ Template ${tmpl.name}: ${e.message}`);
    }
  }

  // Generation Jobs
  console.log("  Creating generation jobs...");
  const jobs = [
    { source_type: "manual", source_data: { product_name: "ProBook Ultra 15", description: "Professional ultrabook with 4K OLED display", content_types: ["title", "description", "meta_description"] } },
    { source_type: "manual", source_data: { product_name: "PixelBudz Pro ANC", description: "True wireless earbuds with noise cancellation", content_types: ["title", "description", "tags"] } },
    { source_type: "manual", source_data: { product_name: "NovaBand Smartwatch", description: "Health and fitness smartwatch with AMOLED display", content_types: ["title", "description", "meta_description"] } },
  ];
  for (const job of jobs) {
    try {
      await api("POST", baseUrl, "/api/v1/content/generate", job, svcToken);
      console.log(`   ✓ Job: ${job.source_data.product_name}`);
    } catch (e: any) {
      console.log(`   ✗ Job ${job.source_data.product_name}: ${e.message}`);
    }
  }
}

/**
 * Seeds RankPilot with sites, keywords, and blog posts.
 */
async function seedRankPilot(token: string) {
  const baseUrl = SERVICES.rankpilot;
  console.log("\n╔══════════════════════════════════════════════════════════╗");
  console.log("║          RANKPILOT — Automated SEO Engine                ║");
  console.log("╚══════════════════════════════════════════════════════════╝\n");

  const svcToken = await getServiceToken(baseUrl, "demo@example.com", "password123");

  // Sites
  console.log("  Creating sites...");
  const sites: any[] = [];
  const siteDefs = [
    { domain: "voltelectronics.com", sitemap_url: "https://voltelectronics.com/sitemap.xml" },
    { domain: "blog.voltelectronics.com", sitemap_url: "https://blog.voltelectronics.com/sitemap.xml" },
  ];
  for (const site of siteDefs) {
    try {
      const created = await api("POST", baseUrl, "/api/v1/sites", site, svcToken);
      if (created) sites.push(created);
      console.log(`   ✓ Site: ${site.domain}`);
    } catch (e: any) {
      console.log(`   ✗ Site ${site.domain}: ${e.message}`);
    }
  }

  if (sites.length > 0) {
    // Keywords
    console.log("  Tracking keywords...");
    const keywords = [
      "best gaming laptop 2026", "wireless earbuds review", "USB-C hub comparison",
      "smartwatch fitness tracker", "portable bluetooth speaker", "GaN charger 65W",
      "phone case military grade", "4K OLED laptop", "noise cancelling earbuds",
      "monitor light bar desk",
    ];
    for (const kw of keywords) {
      try {
        await api("POST", baseUrl, "/api/v1/keywords", { site_id: sites[0].id, keyword: kw }, svcToken);
        console.log(`   ✓ Keyword: "${kw}"`);
      } catch (e: any) {
        console.log(`   ✗ Keyword "${kw}": ${e.message}`);
      }
    }

    // Blog Posts
    console.log("  Creating blog posts...");
    const blogPosts = [
      { site_id: sites[0].id, title: "Top 10 Gaming Laptops for 2026", slug: "top-gaming-laptops-2026", content: "The gaming laptop market continues to push boundaries with RTX 50-series GPUs and 240Hz OLED displays. Here are our top picks for every budget...", status: "published" },
      { site_id: sites[0].id, title: "Wireless Earbuds Buying Guide", slug: "wireless-earbuds-guide", content: "Choosing the right wireless earbuds can be overwhelming with hundreds of options. We break down what matters: ANC quality, battery life, comfort, and sound signature...", status: "published" },
      { site_id: sites[0].id, title: "Why GaN Chargers Are the Future", slug: "gan-chargers-future", content: "Gallium Nitride (GaN) technology is revolutionizing how we charge our devices. Smaller, cooler, and more efficient than traditional silicon chargers...", status: "draft" },
    ];
    for (const post of blogPosts) {
      try {
        await api("POST", baseUrl, "/api/v1/blog_posts", post, svcToken);
        console.log(`   ✓ Blog: "${post.title}" (${post.status})`);
      } catch (e: any) {
        console.log(`   ✗ Blog "${post.title}": ${e.message}`);
      }
    }
  }
}

/**
 * Seeds FlowSend with contacts, lists, templates, campaigns, and flows.
 */
async function seedFlowSend(token: string) {
  const baseUrl = SERVICES.flowsend;
  console.log("\n╔══════════════════════════════════════════════════════════╗");
  console.log("║          FLOWSEND — Smart Email Marketing                ║");
  console.log("╚══════════════════════════════════════════════════════════╝\n");

  const svcToken = await getServiceToken(baseUrl, "demo@example.com", "password123");

  // Contacts
  console.log("  Creating contacts...");
  const contacts = [
    { email: "alice@example.com", first_name: "Alice", last_name: "Martinez", tags: ["customer", "vip", "electronics"] },
    { email: "bob@example.com", first_name: "Bob", last_name: "Johnson", tags: ["customer", "electronics"] },
    { email: "carol@example.com", first_name: "Carol", last_name: "Davis", tags: ["customer", "audio"] },
    { email: "dave@example.com", first_name: "Dave", last_name: "Sullivan", tags: ["customer", "gaming"] },
    { email: "emma@example.com", first_name: "Emma", last_name: "Wilson", tags: ["prospect", "newsletter"] },
    { email: "frank@example.com", first_name: "Frank", last_name: "Chen", tags: ["prospect", "newsletter"] },
    { email: "grace@example.com", first_name: "Grace", last_name: "Kim", tags: ["customer", "vip"] },
    { email: "henry@example.com", first_name: "Henry", last_name: "Park", tags: ["prospect"] },
    { email: "ivy@example.com", first_name: "Ivy", last_name: "Thompson", tags: ["customer", "accessories"] },
    { email: "jack@example.com", first_name: "Jack", last_name: "Brown", tags: ["prospect", "newsletter"] },
  ];
  for (const contact of contacts) {
    try {
      await api("POST", baseUrl, "/api/v1/contacts", contact, svcToken);
      console.log(`   ✓ Contact: ${contact.first_name} ${contact.last_name}`);
    } catch (e: any) {
      console.log(`   ✗ Contact ${contact.email}: ${e.message}`);
    }
  }

  // Contact Lists
  console.log("  Creating contact lists...");
  const lists: any[] = [];
  const listDefs = [
    { name: "VIP Customers", description: "High-value customers with 2+ purchases", list_type: "static" },
    { name: "Newsletter Subscribers", description: "All newsletter opt-ins", list_type: "static" },
  ];
  for (const list of listDefs) {
    try {
      const created = await api("POST", baseUrl, "/api/v1/contacts/lists", list, svcToken);
      if (created) lists.push(created);
      console.log(`   ✓ List: ${list.name}`);
    } catch (e: any) {
      console.log(`   ✗ List ${list.name}: ${e.message}`);
    }
  }

  // Email Templates
  console.log("  Creating email templates...");
  const emailTemplates: any[] = [];
  const tmplDefs = [
    { name: "Welcome Series", subject: "Welcome to Volt Electronics, {{first_name}}!", body: "Hi {{first_name}},\n\nThanks for joining the Volt family! Here's 10% off your first order: WELCOME10\n\nBrowse our latest drops at voltelectronics.com", variables: ["first_name"] },
    { name: "Flash Sale Alert", subject: "FLASH SALE: Up to 25% off everything!", body: "Hey {{first_name}},\n\nOur biggest sale of the season is live! Use code SUMMER25 for 25% off.\n\nShop now before it's gone.", variables: ["first_name"] },
    { name: "Order Follow-Up", subject: "How's your {{product_name}}, {{first_name}}?", body: "Hi {{first_name}},\n\nIt's been a week since your {{product_name}} arrived. We'd love to hear what you think!\n\nLeave a review and get 15% off your next order.", variables: ["first_name", "product_name"] },
  ];
  for (const tmpl of tmplDefs) {
    try {
      const created = await api("POST", baseUrl, "/api/v1/templates", tmpl, svcToken);
      if (created) emailTemplates.push(created);
      console.log(`   ✓ Template: ${tmpl.name}`);
    } catch (e: any) {
      console.log(`   ✗ Template ${tmpl.name}: ${e.message}`);
    }
  }

  // Campaigns
  console.log("  Creating campaigns...");
  if (emailTemplates.length > 0 && lists.length > 0) {
    const campaigns = [
      { name: "Summer Flash Sale", subject: "FLASH SALE: Up to 25% off everything!", template_id: emailTemplates[1]?.id, list_id: lists[0]?.id, scheduled_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString() },
      { name: "New Arrivals Newsletter", subject: "Just Dropped: 3 New Products You'll Love", template_id: emailTemplates[0]?.id, list_id: lists[1]?.id },
    ];
    for (const camp of campaigns) {
      try {
        await api("POST", baseUrl, "/api/v1/campaigns", camp, svcToken);
        console.log(`   ✓ Campaign: ${camp.name}`);
      } catch (e: any) {
        console.log(`   ✗ Campaign ${camp.name}: ${e.message}`);
      }
    }
  }

  // Flows
  console.log("  Creating automation flows...");
  const flows = [
    { name: "Welcome Flow", trigger_type: "new_subscriber", steps: [{ type: "send_email", template_id: emailTemplates[0]?.id, delay_hours: 0 }] },
    { name: "Post-Purchase Review Request", trigger_type: "order_delivered", steps: [{ type: "send_email", template_id: emailTemplates[2]?.id, delay_hours: 168 }] },
  ];
  for (const flow of flows) {
    try {
      await api("POST", baseUrl, "/api/v1/flows", flow, svcToken);
      console.log(`   ✓ Flow: ${flow.name}`);
    } catch (e: any) {
      console.log(`   ✗ Flow ${flow.name}: ${e.message}`);
    }
  }
}

/**
 * Seeds SpyDrop with competitors and alerts.
 */
async function seedSpyDrop(token: string) {
  const baseUrl = SERVICES.spydrop;
  console.log("\n╔══════════════════════════════════════════════════════════╗");
  console.log("║          SPYDROP — Competitor Intelligence               ║");
  console.log("╚══════════════════════════════════════════════════════════╝\n");

  const svcToken = await getServiceToken(baseUrl, "demo@example.com", "password123");

  // Competitors
  console.log("  Adding competitors...");
  const competitors: any[] = [];
  const compDefs = [
    { name: "TechHaven Store", url: "https://techhaven-store.com", platform: "shopify" },
    { name: "GadgetWorld Pro", url: "https://gadgetworldpro.com", platform: "woocommerce" },
    { name: "ElectroDeal Direct", url: "https://electrodeal-direct.com", platform: "custom" },
  ];
  for (const comp of compDefs) {
    try {
      const created = await api("POST", baseUrl, "/api/v1/competitors", comp, svcToken);
      if (created) competitors.push(created);
      console.log(`   ✓ Competitor: ${comp.name} (${comp.platform})`);
    } catch (e: any) {
      console.log(`   ✗ Competitor ${comp.name}: ${e.message}`);
    }
  }

  // Alerts
  console.log("  Creating price alerts...");
  if (competitors.length > 0) {
    const alerts = [
      { competitor_id: competitors[0]?.id, alert_type: "price_drop", threshold: 10.0 },
      { competitor_id: competitors[0]?.id, alert_type: "new_product", threshold: null },
      { competitor_id: competitors[1]?.id, alert_type: "price_drop", threshold: 15.0 },
      { competitor_id: competitors[1]?.id, alert_type: "out_of_stock", threshold: null },
      { competitor_id: competitors[2]?.id, alert_type: "price_drop", threshold: 20.0 },
    ];
    for (const alert of alerts) {
      try {
        await api("POST", baseUrl, "/api/v1/alerts", alert, svcToken);
        console.log(`   ✓ Alert: ${alert.alert_type} (threshold: ${alert.threshold ?? "N/A"})`);
      } catch (e: any) {
        console.log(`   ✗ Alert: ${e.message}`);
      }
    }
  }
}

/**
 * Seeds PostPilot with social accounts and scheduled posts.
 */
async function seedPostPilot(token: string) {
  const baseUrl = SERVICES.postpilot;
  console.log("\n╔══════════════════════════════════════════════════════════╗");
  console.log("║          POSTPILOT — Social Media Automation             ║");
  console.log("╚══════════════════════════════════════════════════════════╝\n");

  const svcToken = await getServiceToken(baseUrl, "demo@example.com", "password123");

  // Social Accounts
  console.log("  Connecting social accounts...");
  const accounts = [
    { platform: "instagram", connected_account_id: "volt_electronics_ig", is_connected: true },
    { platform: "facebook", connected_account_id: "volt_electronics_fb", is_connected: true },
    { platform: "tiktok", connected_account_id: "volt_electronics_tt", is_connected: true },
  ];
  for (const acct of accounts) {
    try {
      await api("POST", baseUrl, "/api/v1/accounts", acct, svcToken);
      console.log(`   ✓ ${acct.platform}: @${acct.connected_account_id}`);
    } catch (e: any) {
      console.log(`   ✗ ${acct.platform}: ${e.message}`);
    }
  }

  // Scheduled Posts
  console.log("  Creating scheduled posts...");
  const posts = [
    { content: "The ProBook Ultra 15 just dropped. 4K OLED, all-day battery, under 1.4kg. This is the one.", platforms: ["instagram", "facebook"], scheduled_for: new Date(Date.now() + 1 * 24 * 60 * 60 * 1000).toISOString() },
    { content: "POV: You just got the PixelBudz Pro ANC and the world goes silent. Pure bliss.", platforms: ["tiktok", "instagram"], scheduled_for: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString() },
    { content: "FLASH SALE: 25% off everything with code SUMMER25. Link in bio.", platforms: ["instagram", "facebook", "tiktok"], scheduled_for: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString() },
    { content: "The MagFloat charger literally levitates your phone while charging. Future is now.", platforms: ["tiktok"], scheduled_for: new Date(Date.now() + 4 * 24 * 60 * 60 * 1000).toISOString() },
    { content: "Unboxing the TitanForce RTX Gaming Laptop. RTX 4070, 240Hz display, quad-fan cooling.", platforms: ["tiktok", "instagram"], scheduled_for: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString() },
    { content: "Customer review: 'The SoundStage headphones are audiophile-grade at a real-world price.' Shop now.", platforms: ["facebook"], scheduled_for: new Date(Date.now() + 6 * 24 * 60 * 60 * 1000).toISOString() },
  ];
  for (const post of posts) {
    try {
      await api("POST", baseUrl, "/api/v1/posts", post, svcToken);
      console.log(`   ✓ Post: "${post.content.slice(0, 50)}..." → ${post.platforms.join(", ")}`);
    } catch (e: any) {
      console.log(`   ✗ Post: ${e.message}`);
    }
  }
}

/**
 * Seeds AdScale with ad accounts, campaigns, ad groups, creatives, and rules.
 */
async function seedAdScale(token: string) {
  const baseUrl = SERVICES.adscale;
  console.log("\n╔══════════════════════════════════════════════════════════╗");
  console.log("║          ADSCALE — AI Ad Campaign Manager                ║");
  console.log("╚══════════════════════════════════════════════════════════╝\n");

  const svcToken = await getServiceToken(baseUrl, "demo@example.com", "password123");

  // Ad Accounts
  console.log("  Creating ad accounts...");
  const adAccounts: any[] = [];
  const acctDefs = [
    { ad_account_id: "fb_volt_001", platform: "facebook", is_connected: true },
    { ad_account_id: "gads_volt_001", platform: "google", is_connected: true },
  ];
  for (const acct of acctDefs) {
    try {
      const created = await api("POST", baseUrl, "/api/v1/accounts", acct, svcToken);
      if (created) adAccounts.push(created);
      console.log(`   ✓ Ad Account: ${acct.platform} (${acct.ad_account_id})`);
    } catch (e: any) {
      console.log(`   ✗ Ad Account ${acct.platform}: ${e.message}`);
    }
  }

  if (adAccounts.length > 0) {
    // Campaigns
    console.log("  Creating campaigns...");
    const campaigns: any[] = [];
    const campDefs = [
      { ad_account_id: adAccounts[0]?.id, name: "Summer Electronics Sale", objective: "conversions", budget_daily: 75.00, budget_lifetime: 2250.00, start_date: "2026-06-01", end_date: "2026-08-31", status: "active" },
      { ad_account_id: adAccounts[0]?.id, name: "ProBook Launch Campaign", objective: "awareness", budget_daily: 50.00, budget_lifetime: 1500.00, start_date: "2026-03-01", end_date: "2026-04-30", status: "active" },
      { ad_account_id: adAccounts[1]?.id, name: "Google Shopping - Electronics", objective: "conversions", budget_daily: 100.00, budget_lifetime: 3000.00, start_date: "2026-01-01", end_date: "2026-12-31", status: "active" },
    ];
    for (const camp of campDefs) {
      try {
        const created = await api("POST", baseUrl, "/api/v1/campaigns", camp, svcToken);
        if (created) campaigns.push(created);
        console.log(`   ✓ Campaign: ${camp.name} ($${camp.budget_daily}/day)`);
      } catch (e: any) {
        console.log(`   ✗ Campaign ${camp.name}: ${e.message}`);
      }
    }

    // Ad Groups
    console.log("  Creating ad groups...");
    if (campaigns.length > 0) {
      const adGroups = [
        { campaign_id: campaigns[0]?.id, name: "Tech Enthusiasts 18-35", target_audience: { age_min: 18, age_max: 35, interests: ["technology", "gadgets"] }, bid_strategy: "auto" },
        { campaign_id: campaigns[0]?.id, name: "Gamers 18-45", target_audience: { age_min: 18, age_max: 45, interests: ["gaming", "esports"] }, bid_strategy: "auto" },
        { campaign_id: campaigns[1]?.id, name: "Business Professionals 25-55", target_audience: { age_min: 25, age_max: 55, interests: ["business", "productivity"] }, bid_strategy: "auto" },
        { campaign_id: campaigns[2]?.id, name: "Shopping Intent - Electronics", target_audience: { interests: ["electronics", "online shopping"] }, bid_strategy: "auto" },
      ];
      for (const ag of adGroups) {
        try {
          await api("POST", baseUrl, "/api/v1/ad_groups", ag, svcToken);
          console.log(`   ✓ Ad Group: ${ag.name}`);
        } catch (e: any) {
          console.log(`   ✗ Ad Group ${ag.name}: ${e.message}`);
        }
      }
    }

    // Creatives
    console.log("  Creating ad creatives...");
    if (campaigns.length > 0) {
      const creatives = [
        { campaign_id: campaigns[0]?.id, headline: "Summer Sale: 25% Off All Electronics", body: "Premium tech at unbeatable prices. Shop laptops, earbuds, and more.", image_url: "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=800", cta: "Shop Now", status: "active" },
        { campaign_id: campaigns[0]?.id, headline: "NovaBand Smartwatch — Track Everything", body: "Heart rate, SpO2, sleep, 100+ workouts. 7-day battery. Starting at $249.", image_url: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800", cta: "Learn More", status: "active" },
        { campaign_id: campaigns[1]?.id, headline: "ProBook Ultra 15 — Your New Superpower", body: "4K OLED, Intel i7, 14-hour battery. The ultrabook professionals have been waiting for.", image_url: "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=800", cta: "Shop Now", status: "active" },
        { campaign_id: campaigns[1]?.id, headline: "Work Anywhere, Compromise Nowhere", body: "The ProBook Ultra weighs just 1.4kg and lasts all day. Try it risk-free.", image_url: "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=800", cta: "Order Now", status: "active" },
        { campaign_id: campaigns[2]?.id, headline: "Volt Electronics — Premium Tech, Fair Prices", body: "Free shipping on orders over $50. 30-day returns. 2-year warranty.", image_url: "https://images.unsplash.com/photo-1625772452859-1c03d5bf1137?w=800", cta: "Shop Now", status: "active" },
      ];
      for (const creative of creatives) {
        try {
          await api("POST", baseUrl, "/api/v1/creatives", creative, svcToken);
          console.log(`   ✓ Creative: "${creative.headline}"`);
        } catch (e: any) {
          console.log(`   ✗ Creative: ${e.message}`);
        }
      }
    }

    // Optimization Rules
    console.log("  Creating optimization rules...");
    if (campaigns.length > 0) {
      const rules = [
        { campaign_id: campaigns[0]?.id, rule_type: "budget_scaling", condition: { metric: "roas", operator: ">", value: 3.0 }, action: "increase_budget", budget_increment: 25.00 },
        { campaign_id: campaigns[0]?.id, rule_type: "pause_underperformer", condition: { metric: "cpc", operator: ">", value: 5.0 }, action: "pause_ad_group" },
      ];
      for (const rule of rules) {
        try {
          await api("POST", baseUrl, "/api/v1/rules", rule, svcToken);
          console.log(`   ✓ Rule: ${rule.rule_type} (${rule.condition.metric} ${rule.condition.operator} ${rule.condition.value})`);
        } catch (e: any) {
          console.log(`   ✗ Rule ${rule.rule_type}: ${e.message}`);
        }
      }
    }
  }
}

/**
 * Seeds ShopChat with chatbots and knowledge base entries.
 */
async function seedShopChat(token: string) {
  const baseUrl = SERVICES.shopchat;
  console.log("\n╔══════════════════════════════════════════════════════════╗");
  console.log("║          SHOPCHAT — AI Shopping Assistant                ║");
  console.log("╚══════════════════════════════════════════════════════════╝\n");

  const svcToken = await getServiceToken(baseUrl, "demo@example.com", "password123");

  // Chatbots
  console.log("  Creating chatbots...");
  const chatbots: any[] = [];
  const botDefs = [
    { name: "VoltBot", personality: "friendly", welcome_message: "Hey! Welcome to Volt Electronics. I can help you find the perfect gadget, check order status, or answer questions. What's on your mind?", theme_config: { primary_color: "#00FF88", text_color: "#FFFFFF", position: "bottom-right", size: "medium" } },
    { name: "TechExpert", personality: "professional", welcome_message: "Hello! I'm your Volt Electronics tech advisor. I can provide detailed product comparisons, technical specifications, and personalized recommendations. How can I assist you?", theme_config: { primary_color: "#3B82F6", text_color: "#FFFFFF", position: "bottom-right", size: "large" } },
  ];
  for (const bot of botDefs) {
    try {
      const created = await api("POST", baseUrl, "/api/v1/chatbots", bot, svcToken);
      if (created) chatbots.push(created);
      console.log(`   ✓ Chatbot: ${bot.name} (${bot.personality})`);
    } catch (e: any) {
      console.log(`   ✗ Chatbot ${bot.name}: ${e.message}`);
    }
  }

  // Knowledge Base
  if (chatbots.length > 0) {
    console.log("  Adding knowledge base entries...");
    const kbEntries = [
      { chatbot_id: chatbots[0]?.id, source_type: "faq", title: "Shipping Policy", content: "We offer free standard shipping on orders over $50. Standard shipping takes 5-7 business days. Express shipping (2-3 days) is available for $9.99. Same-day delivery is available in select metro areas for $14.99." },
      { chatbot_id: chatbots[0]?.id, source_type: "faq", title: "Return Policy", content: "30-day no-questions-asked return policy on all products. Items must be in original packaging. Refunds are processed within 3-5 business days. Free return shipping for defective items." },
      { chatbot_id: chatbots[0]?.id, source_type: "faq", title: "Warranty Information", content: "All electronics come with a 2-year manufacturer warranty. Extended 3-year warranty available for purchase. Warranty covers manufacturing defects but not accidental damage." },
      { chatbot_id: chatbots[0]?.id, source_type: "faq", title: "Payment Methods", content: "We accept Visa, Mastercard, American Express, PayPal, Apple Pay, and Google Pay. Buy Now Pay Later available through Klarna (4 interest-free payments). Gift cards also accepted." },
      { chatbot_id: chatbots[0]?.id, source_type: "product_catalog", title: "Laptop Collection", content: "ProBook Ultra 15 ($1299.99) — Professional ultrabook with 4K OLED display. TitanForce RTX ($1899.99) — Gaming laptop with RTX 4070 and 240Hz display. Both ship with free next-day delivery." },
      { chatbot_id: chatbots[0]?.id, source_type: "product_catalog", title: "Audio Collection", content: "PixelBudz Pro ANC ($179.99) — True wireless earbuds with adaptive ANC. SoundStage Over-Ear ($349.99) — Planar magnetic headphones. VoltBeam Speaker ($79.99) — IPX7 waterproof portable speaker." },
      { chatbot_id: chatbots[0]?.id, source_type: "custom", title: "Brand Voice Guide", content: "Volt Electronics is a premium yet approachable electronics brand. Use enthusiastic but honest language. Always mention our 2-year warranty and 30-day returns. Avoid overselling — let product specs speak for themselves." },
      { chatbot_id: chatbots[0]?.id, source_type: "policy", title: "Price Match Guarantee", content: "We match prices from authorized US retailers. Send us a link to the lower price and we'll match it within 24 hours. Price match valid for 14 days after purchase. Excludes clearance and third-party marketplace sellers." },
    ];
    for (const entry of kbEntries) {
      try {
        await api("POST", baseUrl, "/api/v1/knowledge", entry, svcToken);
        console.log(`   ✓ KB: ${entry.title} (${entry.source_type})`);
      } catch (e: any) {
        console.log(`   ✗ KB ${entry.title}: ${e.message}`);
      }
    }
  }
}

/**
 * Seeds Admin dashboard with an admin account.
 */
async function seedAdmin() {
  console.log("\n╔══════════════════════════════════════════════════════════╗");
  console.log("║          ADMIN — Super Admin Dashboard                   ║");
  console.log("╚══════════════════════════════════════════════════════════╝\n");

  try {
    await api("POST", ADMIN_API, "/api/v1/admin/auth/setup", {
      email: "admin@ecomm.com",
      password: "admin123",
    });
    console.log("   ✓ Admin account created: admin@ecomm.com / admin123");
  } catch (e: any) {
    if (e.message.includes("409") || e.message.includes("400")) {
      console.log("   ⤳ Admin account already exists");
    } else {
      console.log(`   ✗ Admin setup: ${e.message}`);
    }
  }
}

// ── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  console.log("\n" + "═".repeat(60));
  console.log("  DROPSHIPPING PLATFORM + SAAS SUITE — Seed Script");
  console.log("═".repeat(60));

  // Always seed core platform
  const { token } = await seedCorePlatform();

  // Environment variable controls:
  //   SEED_CORE_ONLY=1      — seed only the core platform
  //   SEED_SERVICE=trendscout — seed only a specific SaaS service (requires core first)
  //   SEED_ADMIN_ONLY=1     — seed only the admin dashboard
  //   (no env vars)         — seed everything that's running

  const seedService = process.env.SEED_SERVICE?.toLowerCase();
  const coreOnly = process.env.SEED_CORE_ONLY === "1";
  const adminOnly = process.env.SEED_ADMIN_ONLY === "1";

  if (coreOnly) {
    console.log("\n  ℹ SEED_CORE_ONLY=1 — skipping SaaS services\n");
  } else if (adminOnly) {
    const adminUp = await isServiceUp(ADMIN_API);
    if (adminUp) {
      await seedAdmin();
    } else {
      console.log(`\n  ⤳ Admin (${ADMIN_API}) is not running`);
    }
  } else {
    // All available service seeders
    const serviceSeeds: { name: string; key: string; url: string; seeder: (token: string) => Promise<void> }[] = [
      { name: "TrendScout",   key: "trendscout",   url: SERVICES.trendscout,   seeder: seedTrendScout },
      { name: "ContentForge", key: "contentforge", url: SERVICES.contentforge, seeder: seedContentForge },
      { name: "RankPilot",    key: "rankpilot",    url: SERVICES.rankpilot,    seeder: seedRankPilot },
      { name: "FlowSend",     key: "flowsend",     url: SERVICES.flowsend,     seeder: seedFlowSend },
      { name: "SpyDrop",      key: "spydrop",      url: SERVICES.spydrop,      seeder: seedSpyDrop },
      { name: "PostPilot",    key: "postpilot",    url: SERVICES.postpilot,    seeder: seedPostPilot },
      { name: "AdScale",      key: "adscale",      url: SERVICES.adscale,      seeder: seedAdScale },
      { name: "ShopChat",     key: "shopchat",     url: SERVICES.shopchat,     seeder: seedShopChat },
    ];

    // Filter to a single service if SEED_SERVICE is set
    const toSeed = seedService
      ? serviceSeeds.filter(s => s.key === seedService)
      : serviceSeeds;

    if (seedService && toSeed.length === 0) {
      console.log(`\n  ✗ Unknown service: "${seedService}". Valid: ${serviceSeeds.map(s => s.key).join(", ")}`);
    }

    for (const svc of toSeed) {
      const up = await isServiceUp(svc.url);
      if (up) {
        try {
          await svc.seeder(token);
        } catch (e: any) {
          console.log(`\n   ✗ ${svc.name} seeding failed: ${e.message}`);
        }
      } else {
        console.log(`\n  ⤳ ${svc.name} (${svc.url}) is not running — skipping`);
      }
    }

    // Seed Admin if running (unless targeting a specific service)
    if (!seedService) {
      const adminUp = await isServiceUp(ADMIN_API);
      if (adminUp) {
        try {
          await seedAdmin();
        } catch (e: any) {
          console.log(`\n   ✗ Admin seeding failed: ${e.message}`);
        }
      } else {
        console.log(`\n  ⤳ Admin (${ADMIN_API}) is not running — skipping`);
      }
    }
  }

  // ── Summary ────────────────────────────────────────────────────────────────
  console.log("\n" + "═".repeat(60));
  console.log("  Seed complete!");
  console.log("═".repeat(60));
  console.log(`
  ── Core Platform ──────────────────────────────────────────
  Store Owner:     demo@example.com / password123
  Customers:       alice@example.com / bob@example.com / carol@example.com
                   (all use password123)
  Dashboard:       http://localhost:3000
  Storefront:      http://localhost:3001?store=volt-electronics
  API Docs:        http://localhost:8000/docs

  ── SaaS Services ──────────────────────────────────────────
  TrendScout:      http://localhost:8101  (Dashboard: 3101)
  ContentForge:    http://localhost:8102  (Dashboard: 3102)
  RankPilot:       http://localhost:8103  (Dashboard: 3103)
  FlowSend:        http://localhost:8104  (Dashboard: 3104)
  SpyDrop:         http://localhost:8105  (Dashboard: 3105)
  PostPilot:       http://localhost:8106  (Dashboard: 3106)
  AdScale:         http://localhost:8107  (Dashboard: 3107)
  ShopChat:        http://localhost:8108  (Dashboard: 3108)

  ── Infrastructure ─────────────────────────────────────────
  LLM Gateway:     http://localhost:8200
  Admin:           http://localhost:8300  (Dashboard: 3300)
  Master Landing:  http://localhost:3200
  Admin Login:     admin@ecomm.com / admin123

  ── Demo Highlights ────────────────────────────────────────
  Core: 12 products, 4 orders, 3 customers, 14 reviews, cyberpunk theme
  TrendScout: 3 research runs, 2 store connections
  ContentForge: 4 templates, 3 generation jobs
  RankPilot: 2 sites, 10 keywords, 3 blog posts
  FlowSend: 10 contacts, 3 templates, 2 campaigns, 2 flows
  SpyDrop: 3 competitors, 5 price alerts
  PostPilot: 3 social accounts, 6 scheduled posts
  AdScale: 2 ad accounts, 3 campaigns, 5 creatives
  ShopChat: 2 chatbots, 8 knowledge base entries
`);
}

main().catch((err) => {
  console.error("\nSeed script failed:", err.message);
  process.exit(1);
});
