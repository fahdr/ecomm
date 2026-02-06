/**
 * Shopping cart context provider for the storefront.
 *
 * Manages cart state with localStorage persistence. Provides functions
 * to add, remove, update quantity, and clear cart items. The cart is
 * scoped per browser (localStorage) and does not require authentication.
 *
 * **For Developers:**
 *   Use the ``useCart()`` hook in client components to access cart state
 *   and actions. Cart items are stored as an array of ``CartItem`` objects
 *   in localStorage under the key ``"cart"``.
 *
 * **For QA Engineers:**
 *   - Cart persists across page reloads (localStorage).
 *   - Adding the same product+variant combination increases quantity.
 *   - Removing an item fully deletes it from the cart.
 *   - ``clearCart()`` empties the entire cart.
 *   - ``cartTotal`` computes the sum of (price * quantity) for all items.
 *   - ``cartCount`` is the total number of individual items.
 *
 * **For End Users:**
 *   Your shopping cart is saved in your browser. Items stay in your cart
 *   even if you close the tab and come back later.
 */

"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

/**
 * Represents a single item in the shopping cart.
 */
export interface CartItem {
  /** UUID of the product. */
  productId: string;
  /** UUID of the specific variant, if any. */
  variantId: string | null;
  /** Product display title. */
  title: string;
  /** Variant display name, if any. */
  variantName: string | null;
  /** Unit price as a number. */
  price: number;
  /** Quantity of this item in the cart. */
  quantity: number;
  /** First product image URL, if available. */
  image: string | null;
  /** Product slug for linking back to the product page. */
  slug: string;
}

/**
 * Shape of the cart context value.
 */
interface CartContextValue {
  /** Current cart items. */
  items: CartItem[];
  /** Add an item to the cart (or increment quantity if already present). */
  addItem: (item: CartItem) => void;
  /** Remove an item by product ID and variant ID. */
  removeItem: (productId: string, variantId: string | null) => void;
  /** Update the quantity of a specific item. */
  updateQuantity: (
    productId: string,
    variantId: string | null,
    quantity: number
  ) => void;
  /** Clear all items from the cart. */
  clearCart: () => void;
  /** Total number of items in the cart. */
  cartCount: number;
  /** Total price of all items in the cart. */
  cartTotal: number;
}

const CartContext = createContext<CartContextValue | null>(null);

const CART_STORAGE_KEY = "cart";

/**
 * Load cart items from localStorage.
 *
 * @returns The saved cart items array, or empty array if none saved.
 */
function loadCart(): CartItem[] {
  if (typeof window === "undefined") return [];
  try {
    const saved = localStorage.getItem(CART_STORAGE_KEY);
    return saved ? JSON.parse(saved) : [];
  } catch {
    return [];
  }
}

/**
 * Save cart items to localStorage.
 *
 * @param items - The cart items to persist.
 */
function saveCart(items: CartItem[]): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
}

/**
 * Cart provider component that manages cart state and localStorage persistence.
 *
 * @param props - Provider props.
 * @param props.children - Child components that can consume the cart context.
 * @returns A context provider wrapping the children with cart functionality.
 */
export function CartProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);
  const [loaded, setLoaded] = useState(false);

  // Load cart from localStorage on mount
  useEffect(() => {
    setItems(loadCart());
    setLoaded(true);
  }, []);

  // Save cart to localStorage whenever it changes
  useEffect(() => {
    if (loaded) {
      saveCart(items);
    }
  }, [items, loaded]);

  const addItem = useCallback((newItem: CartItem) => {
    setItems((prev) => {
      const existing = prev.find(
        (i) =>
          i.productId === newItem.productId &&
          i.variantId === newItem.variantId
      );
      if (existing) {
        return prev.map((i) =>
          i.productId === newItem.productId &&
          i.variantId === newItem.variantId
            ? { ...i, quantity: i.quantity + newItem.quantity }
            : i
        );
      }
      return [...prev, newItem];
    });
  }, []);

  const removeItem = useCallback(
    (productId: string, variantId: string | null) => {
      setItems((prev) =>
        prev.filter(
          (i) => !(i.productId === productId && i.variantId === variantId)
        )
      );
    },
    []
  );

  const updateQuantity = useCallback(
    (productId: string, variantId: string | null, quantity: number) => {
      if (quantity <= 0) {
        removeItem(productId, variantId);
        return;
      }
      setItems((prev) =>
        prev.map((i) =>
          i.productId === productId && i.variantId === variantId
            ? { ...i, quantity }
            : i
        )
      );
    },
    [removeItem]
  );

  const clearCart = useCallback(() => {
    setItems([]);
  }, []);

  const cartCount = items.reduce((sum, i) => sum + i.quantity, 0);
  const cartTotal = items.reduce((sum, i) => sum + i.price * i.quantity, 0);

  return (
    <CartContext.Provider
      value={{
        items,
        addItem,
        removeItem,
        updateQuantity,
        clearCart,
        cartCount,
        cartTotal,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

/**
 * Hook to access the cart context.
 *
 * @returns The cart context value with items, actions, and computed totals.
 * @throws Error if used outside of a CartProvider.
 *
 * @example
 * ```tsx
 * const { items, addItem, cartCount } = useCart();
 * ```
 */
export function useCart(): CartContextValue {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error("useCart must be used within a CartProvider");
  }
  return context;
}
