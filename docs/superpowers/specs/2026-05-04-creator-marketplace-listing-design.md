# Creator Marketplace Listing — Design Spec
**Date:** 2026-05-04  
**Status:** Approved

---

## Problem

The marketplace currently shows only admin-seeded tools. Users have no way to publish their own templates, playbooks, or services. There is no backend model for user-created listings, no CRUD API, and no frontend entry point.

---

## Architecture

### New DB Model: `CreatorListing`

Separate table from `MarketplaceTool` (which is admin-controlled). User-owned listings live in `creator_listings`.

```
creator_listings
├── id                INTEGER PK
├── user_id           FK → users.id (CASCADE DELETE)
├── title             VARCHAR(255) NOT NULL
├── description       TEXT NOT NULL          -- short blurb for card
├── full_description  TEXT                   -- detail modal body
├── listing_type      VARCHAR(50) NOT NULL   -- Template | Playbook | Service | Tool |
│                                            -- Course | Automation | Consulting | Strategy
├── category          VARCHAR(100) NOT NULL
├── price             FLOAT DEFAULT 0.0
├── tags              JSON                   -- list of strings
├── features          JSON                   -- list of feature strings
├── icon_name         VARCHAR(50)            -- Lucide icon name
├── color_theme       VARCHAR(30)            -- orange | blue | purple | green | pink | yellow
├── purchase_url      VARCHAR(500)           -- external link or null
├── sales_count       INTEGER DEFAULT 0
├── rating            FLOAT DEFAULT 0.0
├── review_count      INTEGER DEFAULT 0
├── is_active         BOOLEAN DEFAULT TRUE
└── created_at        TIMESTAMPTZ server_default now()
```

---

## Backend API

All routes live in `api/routes/marketplace/marketplace.py` under the existing `/api/marketplace` prefix.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/marketplace/listings` | User | Create a listing |
| `GET` | `/api/marketplace/listings` | Public | List all active listings |
| `GET` | `/api/marketplace/listings/{id}` | Public | Get single listing |
| `PUT` | `/api/marketplace/listings/{id}` | Listing owner | Update listing |
| `DELETE` | `/api/marketplace/listings/{id}` | Listing owner | Soft-delete (set `is_active=False`) |

### Request body for POST/PUT

```json
{
  "title": "string",
  "description": "string",
  "full_description": "string | null",
  "listing_type": "Template",
  "category": "string",
  "price": 0.0,
  "tags": ["string"],
  "features": ["string"],
  "icon_name": "Cpu",
  "color_theme": "orange",
  "purchase_url": "string | null"
}
```

### Response shape (GET list item)

```json
{
  "id": 1,
  "title": "...",
  "description": "...",
  "listing_type": "Template",
  "category": "...",
  "price": 0.0,
  "tags": [],
  "features": [],
  "icon_name": "Cpu",
  "color_theme": "orange",
  "purchase_url": null,
  "sales_count": 0,
  "rating": 0.0,
  "review_count": 0,
  "created_at": "...",
  "source": "user_listing"
}
```

The `source` field differentiates listings from admin tools when both are merged on the frontend.

---

## Migration

New Alembic migration: `alembic revision --autogenerate -m "add creator_listings table"` then `alembic upgrade head`.

---

## Frontend Changes

### `market-place/page.tsx`

1. **Parallel fetch**: Replace single tools fetch with `Promise.all([fetchTools(), fetchListings()])`.
2. **Merge grid**: Combine both arrays into one `allItems` list; render same card component with a type badge.
3. **"Create Listing" button**: Added to the controls bar, opens `CreateListingModal`. No chops language anywhere.
4. **`CreateListingModal`**: Form fields matching the POST body above, plus a colour-theme picker (6 colour swatches). Submits to `POST /api/marketplace/listings`.

### Card display

- Admin tools: render as today (no badge change)
- User listings: show a `listing_type` badge (e.g. "Template", "Playbook") in the card corner
- Both share the same grid layout and icon/colour-theme system

---

## Seed

A seed script (`scripts/seed_creator_listings.py`) creates 2 real listings from existing users to verify all fields write and read correctly:

1. Listing 1: type=Template, price=0, tags + features arrays, icon_name, color_theme, purchase_url=null
2. Listing 2: type=Playbook, price=29.00, tags + features arrays, icon_name, color_theme, purchase_url set

Run: `PYTHONPATH=. uv run python scripts/seed_creator_listings.py`

---

## Error Handling

- `POST` validates `listing_type` is one of the 8 allowed values; returns 422 otherwise.
- `PUT`/`DELETE` check `current_user.id == listing.user_id`; return 403 if not owner.
- Frontend shows inline form validation before submit; shows toast on success/error.

---

## Out of Scope

- Review/rating system for listings (future)
- Admin moderation queue (future)
- File/image upload for listing thumbnails (future)
- Listing purchase flow (separate from admin tool purchase) (future)
