#!/usr/bin/env npx tsx
/**
 * Seed script — populates the database with realistic dummy data for all
 * Phase 1 features so you can manually test the dashboard and storefront.
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
 *   - 1 store ("Volt Electronics")
 *   - 6 categories (nested hierarchy)
 *   - 8 products across categories
 *   - 3 suppliers linked to products
 *   - 5 discount codes (mix of percentage & fixed)
 *   - 4 tax rates (US states)
 *   - 3 gift cards
 *   - 12 product reviews
 *   - 4 orders with items (various statuses)
 *   - 1 refund
 *   - 3 customer segments
 *   - 4 upsell/cross-sell rules
 *   - 2 team member invitations
 *   - 2 webhook endpoints
 *   - 2 A/B tests
 *   - 1 custom domain
 *
 * **For Developers:**
 *   Each section is self-contained. If one feature fails, subsequent
 *   features will still attempt to seed.
 *
 * **For QA Engineers:**
 *   After running, log in at http://localhost:3000 with demo@example.com
 *   and password123. Browse the storefront at http://localhost:3001?store=volt-electronics.
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
      description: "Premium consumer electronics and accessories for the modern tech enthusiast. We source the latest gadgets directly from top manufacturers worldwide.",
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

  // ── 3. Categories ──────────────────────────────────────────────────────────
  console.log("\n3. Creating categories...");
  const categoryMap: Record<string, string> = {};
  const categories = [
    { name: "Laptops & Computers", description: "Powerful laptops and desktop computers for work and gaming", image_url: "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400" },
    { name: "Smartphones", description: "Latest smartphones from top brands", image_url: "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400" },
    { name: "Audio & Headphones", description: "Premium audio equipment and wireless headphones", image_url: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400" },
    { name: "Accessories", description: "Cables, cases, chargers and more", image_url: "https://images.unsplash.com/photo-1625772452859-1c03d5bf1137?w=400" },
  ];

  for (const cat of categories) {
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
  if (categoryMap["Laptops & Computers"]) {
    try {
      const sub1 = await api("POST", `/api/v1/stores/${storeId}/categories`, {
        name: "Gaming Laptops",
        description: "High-performance gaming laptops with dedicated GPUs",
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

  if (categoryMap["Accessories"]) {
    try {
      const sub2 = await api("POST", `/api/v1/stores/${storeId}/categories`, {
        name: "Phone Cases",
        description: "Protective cases and covers for smartphones",
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
      description: "15.6-inch ultrabook with Intel Core i7, 16GB RAM, 512GB SSD. Perfect for professionals who need power on the go. Features a stunning 4K OLED display and all-day battery life.",
      price: "1299.99",
      status: "active",
      category_id: categoryMap["Laptops & Computers"],
      variants: [
        { name: "Silver / 16GB", sku: "PBU-SLV-16", price: null, inventory_count: 25 },
        { name: "Space Gray / 32GB", sku: "PBU-GRY-32", price: "1499.99", inventory_count: 15 },
      ],
    },
    {
      title: "TitanForce RTX Gaming Laptop",
      description: "17.3-inch gaming beast with RTX 4070, 32GB RAM, 1TB SSD. 240Hz refresh rate display for competitive gaming. RGB keyboard with per-key lighting.",
      price: "1899.99",
      status: "active",
      category_id: categoryMap["Gaming Laptops"],
      variants: [
        { name: "Standard", sku: "TFRX-STD", price: null, inventory_count: 10 },
      ],
    },
    {
      title: "Galaxy Nova X",
      description: "6.7-inch flagship smartphone with 200MP camera, 8K video recording, 5000mAh battery. Features the latest Snapdragon processor and 5G connectivity.",
      price: "999.99",
      status: "active",
      category_id: categoryMap["Smartphones"],
      variants: [
        { name: "Midnight Black / 256GB", sku: "GNX-BLK-256", price: null, inventory_count: 50 },
        { name: "Ocean Blue / 512GB", sku: "GNX-BLU-512", price: "1099.99", inventory_count: 30 },
        { name: "Rose Gold / 256GB", sku: "GNX-GLD-256", price: null, inventory_count: 20 },
      ],
    },
    {
      title: "PixelBudz Pro ANC",
      description: "True wireless earbuds with active noise cancellation, 30-hour battery life, and spatial audio. IPX5 water resistant with premium titanium drivers.",
      price: "179.99",
      status: "active",
      category_id: categoryMap["Audio & Headphones"],
      variants: [
        { name: "Charcoal", sku: "PBP-CHR", price: null, inventory_count: 100 },
        { name: "Pearl White", sku: "PBP-WHT", price: null, inventory_count: 80 },
      ],
    },
    {
      title: "SoundStage Over-Ear Headphones",
      description: "Premium over-ear headphones with planar magnetic drivers, memory foam cushions, and balanced audio profile. Wired and wireless modes with aptX HD.",
      price: "349.99",
      status: "active",
      category_id: categoryMap["Audio & Headphones"],
      variants: [
        { name: "Matte Black", sku: "SS-BLK", price: null, inventory_count: 40 },
      ],
    },
    {
      title: "HyperCharge 65W GaN Charger",
      description: "Ultra-compact 65W GaN charger with 3 ports (2x USB-C, 1x USB-A). PPS support for Samsung and USB PD 3.0 for MacBook. Foldable prongs for travel.",
      price: "49.99",
      status: "active",
      category_id: categoryMap["Accessories"],
      variants: [
        { name: "White", sku: "HC65-WHT", price: null, inventory_count: 200 },
        { name: "Black", sku: "HC65-BLK", price: null, inventory_count: 150 },
      ],
    },
    {
      title: "ArmorShield Pro Case",
      description: "Military-grade drop protection case with MagSafe compatibility. Slim profile with raised bezels for camera and screen protection. Available for Galaxy Nova X.",
      price: "39.99",
      status: "active",
      category_id: categoryMap["Phone Cases"],
      variants: [
        { name: "Clear", sku: "ASP-CLR", price: null, inventory_count: 300 },
        { name: "Frosted Black", sku: "ASP-FBK", price: null, inventory_count: 250 },
      ],
    },
    {
      title: "FlexiDock USB-C Hub",
      description: "12-in-1 USB-C docking station with dual HDMI 4K@60Hz, 2x USB 3.0, SD/microSD, Ethernet, and 100W power delivery. Aluminum unibody design.",
      price: "89.99",
      status: "active",
      category_id: categoryMap["Accessories"],
      variants: [
        { name: "Silver", sku: "FD-SLV", price: null, inventory_count: 60 },
      ],
    },
  ];

  for (const pDef of productDefs) {
    try {
      const product = await api("POST", `/api/v1/stores/${storeId}/products`, pDef, token);
      if (product) {
        products.push(product);
        console.log(`   ✓ ${pDef.title} — $${pDef.price}`);
      }
    } catch (e: any) {
      console.log(`   ✗ ${pDef.title}: ${e.message}`);
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
      notes: "Primary laptop and computer supplier. Ships from Shenzhen, 7-10 day lead time. MOQ 10 units. Volume discounts available above 50 units.",
    },
    {
      name: "MobileFirst Supply Co.",
      website: "https://mobilefirst-supply.com",
      contact_email: "support@mobilefirst-supply.com",
      contact_phone: "+1-555-0200",
      notes: "Smartphone and accessories supplier. Ships from Hong Kong, 5-7 day lead time. Offers dropship packaging with custom branding.",
    },
    {
      name: "AudioPrime Distributors",
      website: "https://audioprime-dist.com",
      contact_email: "wholesale@audioprime-dist.com",
      contact_phone: "+44-20-7946-0958",
      notes: "UK-based audio equipment distributor. Ships globally, 3-5 day lead time within Europe, 7-12 days to US. Authorized dealer for premium brands.",
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
      { productIdx: 0, supplierIdx: 0, cost: "780.00", sku: "TS-PBU15" },    // ProBook → TechSource
      { productIdx: 1, supplierIdx: 0, cost: "1150.00", sku: "TS-TFRX" },    // TitanForce → TechSource
      { productIdx: 2, supplierIdx: 1, cost: "620.00", sku: "MF-GNX" },      // Galaxy Nova → MobileFirst
      { productIdx: 3, supplierIdx: 2, cost: "85.00", sku: "AP-PBP" },       // PixelBudz → AudioPrime
      { productIdx: 4, supplierIdx: 2, cost: "195.00", sku: "AP-SS" },       // SoundStage → AudioPrime
      { productIdx: 5, supplierIdx: 1, cost: "18.00", sku: "MF-HC65" },      // HyperCharge → MobileFirst
      { productIdx: 6, supplierIdx: 1, cost: "8.50", sku: "MF-ASP" },        // ArmorShield → MobileFirst
      { productIdx: 7, supplierIdx: 0, cost: "42.00", sku: "TS-FD" },        // FlexiDock → TechSource
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

  // ── 9. Orders (via public checkout) ────────────────────────────────────────
  console.log("\n9. Creating orders via checkout...");
  const orders: any[] = [];

  if (products.length >= 4) {
    const orderDefs = [
      {
        customer_email: "alice@example.com",
        items: [
          { product_id: products[0].id, variant_id: products[0].variants?.[0]?.id, quantity: 1 },
          { product_id: products[5].id, variant_id: products[5].variants?.[0]?.id, quantity: 2 },
        ],
        label: "Alice — ProBook + 2x HyperCharge",
      },
      {
        customer_email: "bob@example.com",
        items: [
          { product_id: products[2].id, variant_id: products[2].variants?.[0]?.id, quantity: 1 },
          { product_id: products[6].id, variant_id: products[6].variants?.[0]?.id, quantity: 1 },
        ],
        label: "Bob — Galaxy Nova + ArmorShield",
      },
      {
        customer_email: "carol@example.com",
        items: [
          { product_id: products[3].id, variant_id: products[3].variants?.[0]?.id, quantity: 1 },
          { product_id: products[4].id, variant_id: products[4].variants?.[0]?.id, quantity: 1 },
        ],
        label: "Carol — PixelBudz + SoundStage",
      },
      {
        customer_email: "dave@example.com",
        items: [
          { product_id: products[1].id, variant_id: products[1].variants?.[0]?.id, quantity: 1 },
          { product_id: products[7].id, variant_id: products[7].variants?.[0]?.id, quantity: 1 },
        ],
        label: "Dave — TitanForce + FlexiDock",
      },
    ];

    for (const oDef of orderDefs) {
      try {
        const checkout = await api("POST", `/api/v1/public/stores/${slug}/checkout`, {
          customer_email: oDef.customer_email,
          items: oDef.items,
        });
        if (checkout) {
          orders.push(checkout);
          console.log(`   ✓ ${oDef.label} (order: ${checkout.order_id})`);
        }
      } catch (e: any) {
        console.log(`   ✗ ${oDef.label}: ${e.message}`);
      }
    }

    // Update order statuses to simulate lifecycle
    await sleep(300);
    if (orders.length >= 4) {
      const statusUpdates = [
        { idx: 0, status: "paid", label: "Alice → paid" },
        { idx: 1, status: "paid", label: "Bob → paid" },
        { idx: 2, status: "paid", label: "Carol → paid" },
        { idx: 3, status: "paid", label: "Dave → paid" },
      ];

      for (const su of statusUpdates) {
        try {
          await api(
            "PATCH",
            `/api/v1/stores/${storeId}/orders/${orders[su.idx].order_id}`,
            { status: su.status },
            token
          );
          console.log(`   ✓ ${su.label}`);
        } catch (e: any) {
          console.log(`   ✗ ${su.label}: ${e.message}`);
        }
      }

      // Further status updates for variety
      try {
        await api("PATCH", `/api/v1/stores/${storeId}/orders/${orders[0].order_id}`, { status: "shipped" }, token);
        console.log("   ✓ Alice → shipped");
      } catch (e: any) {
        console.log(`   ✗ Alice → shipped: ${e.message}`);
      }

      try {
        await api("PATCH", `/api/v1/stores/${storeId}/orders/${orders[1].order_id}`, { status: "shipped" }, token);
        await api("PATCH", `/api/v1/stores/${storeId}/orders/${orders[1].order_id}`, { status: "delivered" }, token);
        console.log("   ✓ Bob → shipped → delivered");
      } catch (e: any) {
        console.log(`   ✗ Bob status: ${e.message}`);
      }
    }
  } else {
    console.log("   ⤳ Not enough products for orders, skipping");
  }

  // ── 10. Refund ─────────────────────────────────────────────────────────────
  console.log("\n10. Creating refund...");
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

  // ── 11. Reviews ────────────────────────────────────────────────────────────
  console.log("\n11. Creating product reviews...");
  if (products.length >= 6) {
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

  // ── 12. Segments ───────────────────────────────────────────────────────────
  console.log("\n12. Creating customer segments...");
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

  // ── 13. Upsells ────────────────────────────────────────────────────────────
  console.log("\n13. Creating upsell rules...");
  if (products.length >= 8) {
    const upsellDefs = [
      { source: 0, target: 5, type: "cross_sell", title: "Charge it faster", description: "Pair your ProBook with our 65W GaN charger", discount: 10, position: 1 },
      { source: 2, target: 6, type: "cross_sell", title: "Protect your investment", description: "Add a military-grade case for your Galaxy Nova", discount: 15, position: 1 },
      { source: 3, target: 4, type: "upsell", title: "Upgrade your audio", description: "Love the PixelBudz? Experience the full-size SoundStage headphones", discount: 5, position: 1 },
      { source: 0, target: 7, type: "bundle", title: "Complete your setup", description: "Add the FlexiDock hub and connect everything", discount: 20, position: 2 },
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

  // ── 14. Team ───────────────────────────────────────────────────────────────
  console.log("\n14. Inviting team members...");
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

  // ── 15. Webhooks ───────────────────────────────────────────────────────────
  console.log("\n15. Creating webhooks...");
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

  // ── 16. A/B Tests ──────────────────────────────────────────────────────────
  console.log("\n16. Creating A/B tests...");
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

  // ── 17. Domain ─────────────────────────────────────────────────────────────
  console.log("\n17. Setting custom domain...");
  try {
    await api("POST", `/api/v1/stores/${storeId}/domain`, { domain: "shop.voltelectronics.com" }, token);
    console.log("   ✓ shop.voltelectronics.com");
  } catch (e: any) {
    console.log(`   ✗ Domain: ${e.message}`);
  }

  // ── Summary ────────────────────────────────────────────────────────────────
  console.log("\n" + "=".repeat(55));
  console.log("  Seed complete!");
  console.log("=".repeat(55));
  console.log(`
  Login:      demo@example.com / password123
  Dashboard:  http://localhost:3000
  Storefront: http://localhost:3001?store=${slug}
  API Docs:   http://localhost:8000/docs
  Store ID:   ${storeId}
`);
}

main().catch((err) => {
  console.error("\nSeed script failed:", err.message);
  process.exit(1);
});
