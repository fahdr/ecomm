/**
 * Categories management page for a store.
 *
 * Displays product categories in a hierarchical tree view with indented
 * sub-categories. Provides forms to create top-level categories and
 * nested sub-categories, and to edit existing category names.
 *
 * **For End Users:**
 *   Organize your products into categories and sub-categories. A clear
 *   taxonomy helps customers browse your storefront and find products
 *   quickly. Categories can be nested up to three levels deep.
 *
 * **For QA Engineers:**
 *   - Categories load from ``GET /api/v1/stores/{store_id}/categories``.
 *   - Creating a category calls ``POST /api/v1/stores/{store_id}/categories``.
 *   - Editing a category calls ``PATCH /api/v1/stores/{store_id}/categories/{id}``.
 *   - Parent categories expand/collapse to show children.
 *   - The tree renders recursively; verify with 3+ nesting levels.
 *
 * **For Developers:**
 *   - The tree is built client-side from a flat list using ``parent_id``.
 *   - ``buildTree()`` produces a nested structure for recursive rendering.
 *   - ``CategoryNode`` is a recursive component for the tree view.
 *   - Uses ``useStore()`` from store context for the store ID.
 *   - Wrapped in ``PageTransition`` for consistent entrance animation.
 *
 * **For Project Managers:**
 *   Implements Feature 9 (Categories) from the backlog. Covers CRUD and
 *   hierarchy visualization; drag-and-drop reordering is a future iteration.
 */

"use client";

import { FormEvent, useEffect, useState, useCallback } from "react";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition } from "@/components/motion-wrappers";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/** Shape of a category returned by the backend API. */
interface Category {
  id: string;
  name: string;
  slug: string;
  parent_id: string | null;
  position: number;
  product_count: number;
  created_at: string;
}

/** Recursive tree node structure for rendering the category hierarchy. */
interface CategoryTreeNode {
  category: Category;
  children: CategoryTreeNode[];
}

/**
 * Build a tree structure from a flat list of categories.
 * @param categories - Flat array of categories from the API.
 * @returns An array of root-level CategoryTreeNode objects.
 */
function buildTree(categories: Category[]): CategoryTreeNode[] {
  const nodeMap = new Map<string, CategoryTreeNode>();
  const roots: CategoryTreeNode[] = [];

  // First pass: create nodes for each category.
  for (const cat of categories) {
    nodeMap.set(cat.id, { category: cat, children: [] });
  }

  // Second pass: wire up parent-child relationships.
  for (const cat of categories) {
    const node = nodeMap.get(cat.id)!;
    if (cat.parent_id && nodeMap.has(cat.parent_id)) {
      nodeMap.get(cat.parent_id)!.children.push(node);
    } else {
      roots.push(node);
    }
  }

  // Sort children by position at each level.
  function sortChildren(nodes: CategoryTreeNode[]) {
    nodes.sort((a, b) => a.category.position - b.category.position);
    for (const n of nodes) sortChildren(n.children);
  }
  sortChildren(roots);

  return roots;
}

/**
 * Recursive component that renders a single category node and its children.
 * @param node - The tree node to render.
 * @param depth - Current nesting depth (for indentation).
 * @param onEdit - Callback to open the edit dialog for a category.
 * @param onAddChild - Callback to open the create dialog pre-set with parent.
 */
function CategoryNode({
  node,
  depth,
  onEdit,
  onAddChild,
}: {
  node: CategoryTreeNode;
  depth: number;
  onEdit: (category: Category) => void;
  onAddChild: (parentId: string) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children.length > 0;
  const cat = node.category;

  return (
    <div>
      <div
        className="group flex items-center gap-3 rounded-md px-3 py-2.5 transition-colors hover:bg-muted/60"
        style={{ paddingLeft: `${depth * 28 + 12}px` }}
      >
        {/* Expand/collapse toggle */}
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex h-5 w-5 shrink-0 items-center justify-center rounded text-muted-foreground hover:text-foreground"
          aria-label={expanded ? "Collapse" : "Expand"}
        >
          {hasChildren ? (
            <span className="text-xs">{expanded ? "\u25BC" : "\u25B6"}</span>
          ) : (
            <span className="text-xs text-muted-foreground/40">{"\u2022"}</span>
          )}
        </button>

        {/* Category name and info */}
        <div className="flex flex-1 items-center gap-3 min-w-0">
          <span className="font-medium truncate">{cat.name}</span>
          <Badge variant="secondary" className="text-xs shrink-0">
            {cat.product_count} product{cat.product_count !== 1 ? "s" : ""}
          </Badge>
        </div>

        {/* Actions (visible on hover) */}
        <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onAddChild(cat.id)}
            className="h-7 px-2 text-xs"
          >
            + Sub
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEdit(cat)}
            className="h-7 px-2 text-xs"
          >
            Edit
          </Button>
        </div>
      </div>

      {/* Render children recursively */}
      {expanded && hasChildren && (
        <div className="border-l border-border/50" style={{ marginLeft: `${depth * 28 + 22}px` }}>
          {node.children.map((child) => (
            <CategoryNode
              key={child.category.id}
              node={child}
              depth={depth + 1}
              onEdit={onEdit}
              onAddChild={onAddChild}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * CategoriesPage is the main page component for managing store categories.
 *
 * Fetches categories from the API, builds a tree hierarchy, and renders
 * create/edit dialogs for CRUD operations. Uses the store context for
 * the store ID and PageTransition for entrance animation.
 *
 * @returns The rendered categories management page.
 */
export default function CategoriesPage() {
  const { store } = useStore();
  const storeId = store!.id;
  const { user, loading: authLoading } = useAuth();

  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create dialog state.
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [newParentId, setNewParentId] = useState<string>("none");

  // Edit dialog state.
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [editCategory, setEditCategory] = useState<Category | null>(null);
  const [editName, setEditName] = useState("");

  /**
   * Fetch all categories for this store.
   */
  const fetchCategories = useCallback(async () => {
    setLoading(true);
    const result = await api.get<{ items: Category[] }>(
      `/api/v1/stores/${storeId}/categories`
    );
    if (result.data) {
      setCategories(result.data.items);
      setError(null);
    } else {
      setError(result.error?.message || "Failed to load categories");
    }
    setLoading(false);
  }, [storeId]);

  useEffect(() => {
    if (authLoading || !user) return;
    fetchCategories();
  }, [storeId, user, authLoading, fetchCategories]);

  /**
   * Handle creation of a new category.
   * @param e - The form submission event.
   */
  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);

    const payload: { name: string; parent_id?: string } = {
      name: newName.trim(),
    };
    if (newParentId !== "none") {
      payload.parent_id = newParentId;
    }

    const result = await api.post<Category>(
      `/api/v1/stores/${storeId}/categories`,
      payload
    );

    if (result.error) {
      setCreateError(result.error.message);
      setCreating(false);
      return;
    }

    setCreateDialogOpen(false);
    setNewName("");
    setNewParentId("none");
    setCreating(false);
    fetchCategories();
  }

  /**
   * Handle editing an existing category name.
   * @param e - The form submission event.
   */
  async function handleEdit(e: FormEvent) {
    e.preventDefault();
    if (!editCategory) return;
    setEditing(true);
    setEditError(null);

    const result = await api.patch<Category>(
      `/api/v1/stores/${storeId}/categories/${editCategory.id}`,
      { name: editName.trim() }
    );

    if (result.error) {
      setEditError(result.error.message);
      setEditing(false);
      return;
    }

    setEditDialogOpen(false);
    setEditCategory(null);
    setEditName("");
    setEditing(false);
    fetchCategories();
  }

  /**
   * Open the edit dialog pre-populated with a category's current name.
   * @param category - The category to edit.
   */
  function openEditDialog(category: Category) {
    setEditCategory(category);
    setEditName(category.name);
    setEditError(null);
    setEditDialogOpen(true);
  }

  /**
   * Open the create dialog with a pre-selected parent.
   * @param parentId - The ID of the parent category, or "none" for root.
   */
  function openCreateWithParent(parentId: string) {
    setNewParentId(parentId);
    setNewName("");
    setCreateError(null);
    setCreateDialogOpen(true);
  }

  const tree = buildTree(categories);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
          <p className="text-sm text-muted-foreground tracking-wide">Loading categories...</p>
        </div>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Page heading and action */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold font-heading">Categories</h1>
          <Button onClick={() => { setNewParentId("none"); setNewName(""); setCreateError(null); setCreateDialogOpen(true); }}>
            Add Category
          </Button>
        </div>

        {error && (
          <Card className="border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Category tree */}
        {categories.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
              <span className="text-2xl text-muted-foreground">#</span>
            </div>
            <h2 className="text-xl font-semibold font-heading">No categories yet</h2>
            <p className="max-w-sm text-muted-foreground">
              Create categories to organize your products and help customers
              navigate your storefront.
            </p>
            <Button onClick={() => setCreateDialogOpen(true)}>
              Create your first category
            </Button>
          </div>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="font-heading">Category Hierarchy</CardTitle>
              <CardDescription>
                {categories.length} categor{categories.length !== 1 ? "ies" : "y"} across{" "}
                {tree.length} top-level group{tree.length !== 1 ? "s" : ""}
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0 pb-2">
              {tree.map((node) => (
                <CategoryNode
                  key={node.category.id}
                  node={node}
                  depth={0}
                  onEdit={openEditDialog}
                  onAddChild={openCreateWithParent}
                />
              ))}
            </CardContent>
          </Card>
        )}

        {/* Create Category Dialog */}
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>
                {newParentId !== "none" ? "Add Sub-Category" : "Add Category"}
              </DialogTitle>
              <DialogDescription>
                {newParentId !== "none"
                  ? `This category will be nested under "${categories.find((c) => c.id === newParentId)?.name || "parent"}".`
                  : "Create a new top-level category for your products."}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreate}>
              <div className="space-y-4 py-4">
                {createError && (
                  <p className="text-sm text-destructive">{createError}</p>
                )}
                <div className="space-y-2">
                  <Label htmlFor="cat-name">Category Name</Label>
                  <Input
                    id="cat-name"
                    placeholder="e.g. Electronics"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    required
                  />
                </div>
                {newParentId === "none" && categories.length > 0 && (
                  <div className="space-y-2">
                    <Label htmlFor="cat-parent">Parent Category</Label>
                    <Select value={newParentId} onValueChange={setNewParentId}>
                      <SelectTrigger id="cat-parent">
                        <SelectValue placeholder="None (top level)" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">None (top level)</SelectItem>
                        {categories.map((cat) => (
                          <SelectItem key={cat.id} value={cat.id}>
                            {cat.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setCreateDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={creating}>
                  {creating ? "Creating..." : "Create"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Edit Category Dialog */}
        <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Edit Category</DialogTitle>
              <DialogDescription>
                Update the name for &quot;{editCategory?.name}&quot;.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleEdit}>
              <div className="space-y-4 py-4">
                {editError && (
                  <p className="text-sm text-destructive">{editError}</p>
                )}
                <div className="space-y-2">
                  <Label htmlFor="edit-cat-name">Category Name</Label>
                  <Input
                    id="edit-cat-name"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    required
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setEditDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={editing}>
                  {editing ? "Saving..." : "Save Changes"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </main>
    </PageTransition>
  );
}
