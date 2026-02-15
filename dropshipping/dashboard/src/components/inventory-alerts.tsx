/**
 * Inventory alert component for the store overview page.
 *
 * Fetches products with low stock (inventory_count < 5 on any variant)
 * and renders warning cards with links to the product edit page.
 *
 * **For Developers:**
 *   Mount this on the store overview page. It fetches products from
 *   the store's product list and filters client-side for low stock
 *   variants. Each alert links to the product detail page.
 *
 * **For QA Engineers:**
 *   - Shows warnings for products with any variant under 5 units.
 *   - Each alert shows product name, variant name, and remaining stock.
 *   - Clicking an alert navigates to the product edit page.
 *   - Empty state: nothing rendered if no low-stock products.
 *
 * **For End Users:**
 *   See which products are running low on stock so you can reorder
 *   from your supplier before they sell out.
 *
 * @module components/inventory-alerts
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle } from "lucide-react";

/** A product variant with low stock. */
interface LowStockItem {
  productId: string;
  productTitle: string;
  variantName: string;
  stock: number;
}

/** Props for InventoryAlerts. */
interface InventoryAlertsProps {
  storeId: string;
}

/**
 * Render inventory alert cards for low-stock products.
 *
 * @param props - Component props.
 * @param props.storeId - The current store UUID.
 * @returns Alert cards or null if no low-stock items.
 */
export function InventoryAlerts({ storeId }: InventoryAlertsProps) {
  const [lowStock, setLowStock] = useState<LowStockItem[]>([]);

  useEffect(() => {
    if (!storeId) return;

    async function fetchProducts() {
      const res = await api.get<any>(`/api/v1/stores/${storeId}/products?per_page=100`);
      if (!res.data) return;

      const products = Array.isArray(res.data) ? res.data : res.data.items ?? [];
      const alerts: LowStockItem[] = [];

      for (const p of products) {
        if (!p.variants || p.variants.length === 0) continue;
        for (const v of p.variants) {
          if (v.inventory_count !== undefined && v.inventory_count < 5) {
            alerts.push({
              productId: p.id,
              productTitle: p.title,
              variantName: v.name || "Default",
              stock: v.inventory_count,
            });
          }
        }
      }

      setLowStock(alerts);
    }

    fetchProducts();
  }, [storeId]);

  if (lowStock.length === 0) return null;

  return (
    <Card className="border-amber-300/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-heading flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          Low Stock Alerts
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {lowStock.slice(0, 5).map((item, i) => (
            <Link
              key={`${item.productId}-${item.variantName}-${i}`}
              href={`/stores/${storeId}/products/${item.productId}`}
              className="flex items-center justify-between p-2.5 rounded-lg border border-amber-200/50 hover:bg-amber-50/30 dark:hover:bg-amber-900/10 transition-colors"
            >
              <div>
                <span className="text-sm font-medium">{item.productTitle}</span>
                <p className="text-xs text-muted-foreground">{item.variantName}</p>
              </div>
              <span className="text-sm font-bold text-amber-600">
                {item.stock} left
              </span>
            </Link>
          ))}
          {lowStock.length > 5 && (
            <p className="text-xs text-muted-foreground text-center pt-1">
              +{lowStock.length - 5} more low stock items
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
