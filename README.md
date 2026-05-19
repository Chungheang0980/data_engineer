# SentinelDB

**Course:** Database\
**Started:** 2026-05-16\
**Status:** Demo complete — final report & presentation remaining

------------------------------------------------------------------------

## Project Overview

**SentinelDB** is a role-based access control (RBAC) server backed by a relational database. It guards every module behind an authentication engine — controlling who can log in, what they can access, and logging every action for audit. The system enforces access across four functional modules: Account, Stock, Sales, and Admin.

Architecture diagram: [`Project overview/user_access_server_architecture.svg`](./Project%20overview/user_access_server_architecture.svg)

------------------------------------------------------------------------

## Complete Process From The Beginning

Follow this section when starting from a fresh computer, a fresh PostgreSQL database, or a clean demo reset. The project has three moving parts:

-   **PostgreSQL database** — stores users, roles, permissions, products, orders, invoices, sessions, and audit logs.
-   **FastAPI backend** — exposes the API on port `8000` and delegates auth/permission checks to PostgreSQL functions.
-   **React/Vite frontend** — serves the customer shop and hidden staff portal on port `5173`.

Open the project root first:

``` bash
cd "/Users/lychungheang/Documents/67 fresh mart .project"
```

### 0. Prerequisites

-   **PostgreSQL** ≥ 14 running locally on `localhost:5432`
-   **Python** ≥ 3.10 with `pip` and `venv`
-   **Node.js** ≥ 18 with `npm`
-   A terminal at the repository root

### 1. Prepare PostgreSQL

``` bash
# 1.1 Create the database
createdb sentineldb

# 1.2 Load base tables, constraints, and relationships
psql -d sentineldb -f schema/schema.sql

# 1.3 Load stored procedures and permission helpers
psql -d sentineldb -f queries/auth.sql
psql -d sentineldb -f queries/permissions.sql

# 1.4 Load demo roles, staff users, products, customers, orders, invoices, config, and audit logs
psql -d sentineldb -f data/seed.sql

# 1.5 Add customer signup/login tables and functions
psql -d sentineldb -f queries/customer_auth.sql

# 1.6 Optional database checks
psql -d sentineldb -f queries/test_login.sql
psql -d sentineldb -f queries/test_permissions.sql
```

If `createdb sentineldb` says the database already exists, either keep it and continue, or reset it:

``` bash
dropdb sentineldb
createdb sentineldb
```

Then run steps `1.2` through `1.5` again.

### 2. Start the Backend

``` bash
cd backend

# 2.1 Create and activate the Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2.2 Install dependencies
pip install -r requirements.txt

# 2.3 Create backend environment config
cp .env.example .env

# 2.4 Edit .env only if your PostgreSQL username/password/host differs:
#   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sentineldb

# 2.5 Run the API server
uvicorn main:app --reload --port 8000
```

Keep this terminal running. Verify the backend:

-   Health check: <http://localhost:8000/health> → expect `{"database":"up"}`
-   API docs: <http://localhost:8000/docs>

### 3. Review Or Sync Staff Accounts

Open a second terminal from the project root:

``` bash
cd backend
source .venv/bin/activate

# Confirm the seeded staff accounts and roles
python manage_staff.py --list

# Optional: sync the STAFF list in manage_staff.py into the users table
python manage_staff.py
```

Seeded staff demo accounts are loaded by `data/seed.sql` and are also used by the quick-login buttons on `/staff/login`:

| Username     | Password     | Role    |
|--------------|--------------|---------|
| `admin_user` | `Admin@1234` | Admin   |
| `sales_mgr`  | `Sales@1234` | Sales   |
| `cashier_01` | `Cash@1234`  | Cashier |
| `user_01`    | `User@1234`  | User    |

Running `python manage_staff.py` also syncs the current manual staff list from `backend/manage_staff.py`:

| Username     | Email                   | Password     | Role    |
|--------------|-------------------------|--------------|---------|
| `Sattha`     | `adminSattha@gmail.com` | `12345`      | Admin   |
| `MengHong`   | `sales@gmail.com`       | `Sales@1234` | Sales   |
| `cashier_01` | `cashier@gmail.com`     | `Cash@1234`  | Cashier |
| `viewer_01`  | `viewer@gmail.com`      | `View@1234`  | Viewer  |

Staff accounts are not self-registered. Add, remove, activate, deactivate, or reset staff accounts through `backend/manage_staff.py`, then rerun `python manage_staff.py`.

### 4. Start the Frontend

Open a third terminal from the project root:

``` bash
cd frontend
npm install
npm run dev -- --port 5173
```

Open <http://localhost:5173/>.

Keep the frontend terminal running while you test the app.

### 5. Use the App

| Entry point           | URL                                 | Who           |
|-----------------------|-------------------------------------|---------------|
| Customer shop         | <http://localhost:5173/>            | Public        |
| Customer sign-up      | <http://localhost:5173/signup>      | New customers |
| Customer sign-in      | <http://localhost:5173/login>       | Customers     |
| My orders             | <http://localhost:5173/orders/mine> | Customers     |
| Staff portal (hidden) | <http://localhost:5173/staff/login> | Staff/Admin   |

Customer accounts are created from the public `/signup` page. Staff accounts use the seeded credentials or the synced credentials from step 3.

### 6. Demo Walkthrough (3 min)

1.  Open the shop, add 2 products to the cart, hit **Sign in to order** → sign up a new customer → place the order.
2.  Visit `/orders/mine` → confirm the order and auto-issued unpaid invoice appear.
3.  Open `/staff/login` in a private window → quick-login as `admin_user` → Dashboard activity feed shows the new signup, order, and invoice within 30s.
4.  Switch staff role by quick-logging in as `sales_mgr`, `cashier_01`, and `user_01` → confirm Navbar links and activity feed change per the access matrix.

### 7. Shutdown

Press `Ctrl+C` in the backend and frontend terminals. To wipe and restart with a clean database:

``` bash
dropdb sentineldb
createdb sentineldb
# then repeat steps 1.2 through 1.5, then steps 2 through 4
```

------------------------------------------------------------------------

## Roles & Permissions

Five roles total — four on the staff track, one on the customer track.

| Role | Track | Access Level |
|----|----|----|
| Admin | Staff | Full access — all modules + user management + audit logs + system config |
| Sales | Staff | Manage orders, invoices, customers; view + edit stock; no user/audit access |
| Cashier | Staff | Process orders + invoices at point of sale; view products only; no stock edit |
| User | Staff | Basic staff — read-only across Stock and Sales; cannot edit or access Admin |
| Viewer (Customer) | Customer | Browse shop + view own orders only; never sees staff modules or RBAC terminology |

### Access Matrix

| Module / Action             | Admin | Sales | Cashier | User | Viewer (Customer) |
|-----------------------------|:-----:|:-----:|:-------:|:----:|:-----------------:|
| Shop (browse products)      |   ✓   |   ✓   |    ✓    |  ✓   |         ✓         |
| Place order (self)          |   —   |   —   |    —    |  —   |         ✓         |
| View own orders             |   —   |   —   |    —    |  —   |         ✓         |
| Products — view             |   ✓   |   ✓   |    ✓    |  ✓   |         —         |
| Products — add/edit/restock |   ✓   |   ✓   |    —    |  —   |         —         |
| Orders — view all           |   ✓   |   ✓   |    ✓    |  ✓   |         —         |
| Orders — create/invoice/pay |   ✓   |   ✓   |    ✓    |  —   |         —         |
| Users — manage              |   ✓   |   —   |    —    |  —   |         —         |
| Audit logs                  |   ✓   |   —   |    —    |  —   |         —         |
| System config               |   ✓   |   —   |    —    |  —   |         —         |

------------------------------------------------------------------------

## Authentication — Two Separate Login Flows

The demo web exposes **two completely independent auth entry points** that share the database but never cross.

### 1. Staff & Admin Login — `/staff/login`

-   **Login only.** No sign-up, no self-registration, no password reset from the UI.
-   For roles: `Admin`, `Sales`, `Cashier`, `User`.
-   Accounts are provisioned exclusively by the admin via `backend/manage_staff.py` (config-driven CLI: `--list`, `--reset-password`, `--deactivate`).
-   Backed by `users` + `sessions` tables and `fn_login` / `fn_check_permission`.
-   Issued token: `sentinel_token` → 401 redirects to `/staff/login`.
-   Hidden URL — no link from any customer-facing page.

### 2. Customer Login — `/login` and `/signup`

-   **Sign in** (existing customers) **and Sign up** (new customers) both available.
-   For role: `Viewer (Customer)` only.
-   Backed by `customer_accounts` + `customer_sessions` tables and the four customer PL/pgSQL functions.
-   Issued token: `sentinel_customer_token` → 401 redirects to `/login`.
-   Public entry — linked from the shop navigation.

A customer token can never grant staff access, and a staff token can never act as a customer. Tokens, tables, routes, and React contexts are all separated.

------------------------------------------------------------------------

## System Modules

| Module  | Responsibilities                           |
|---------|--------------------------------------------|
| Account | Users, roles, sessions, permissions        |
| Stock   | Products, categories, inventory, suppliers |
| Sales   | Orders, order items, customers, invoices   |
| Admin   | Audit logs, system config, reports         |

------------------------------------------------------------------------

## Database Tables

### Account Module

-   **users** — `user_id` PK, `username`, `password_hash`, `role_id` FK, `is_active`, `created_at`
-   **roles** — `role_id` PK, `role_name`, `description`, `can_admin`, `can_sales`, ...
-   **sessions** — `session_id` PK, `user_id` FK, `token_hash`, `expires_at`, `ip_address`

### Stock Module

-   **products** — `product_id` PK, `name`, `category_id` FK, `price`, `stock_qty`, `supplier_id` FK

### Sales Module

-   **orders** — `order_id` PK, `customer_id` FK, `user_id` FK, `total_amount`, `status`, `created_at`

### Admin Module

-   **audit_logs** — `log_id` PK, `user_id` FK, `action`, `table_affected`, `timestamp`

------------------------------------------------------------------------

## Authentication Engine

Login → Session token → Role lookup → Permission check

------------------------------------------------------------------------

## Foreign Key Relationships

| Table | Column | References | On Delete |
|----|----|----|----|
| `users` | `role_id` | `roles.role_id` | RESTRICT |
| `sessions` | `user_id` | `users.user_id` | CASCADE |
| `products` | `category_id` | `categories.category_id` | SET NULL |
| `products` | `supplier_id` | `suppliers.supplier_id` | SET NULL |
| `orders` | `customer_id` | `customers.customer_id` | SET NULL |
| `orders` | `user_id` | `users.user_id` | RESTRICT (nullable — NULL for customer self-service orders) |
| `order_items` | `order_id` | `orders.order_id` | CASCADE |
| `order_items` | `product_id` | `products.product_id` | RESTRICT |
| `invoices` | `order_id` | `orders.order_id` | RESTRICT |
| `audit_logs` | `user_id` | `users.user_id` | SET NULL |
| `system_config` | `updated_by` | `users.user_id` | SET NULL |

------------------------------------------------------------------------

## Progress Tracker

### Phase 1 — Design

-   [x] Draw system architecture diagram
-   [x] Define all table schemas with full column types and constraints
-   [x] Draw ER diagram (entities, relationships, cardinality)
-   [x] Identify all foreign key relationships

### Phase 2 — Implementation

-   [x] Write `CREATE TABLE` SQL for all tables
-   [x] Insert seed/test data (roles, users, products, customers)
-   [x] Implement authentication flow (login, session, token)
-   [x] Implement permission check logic per role

### Phase 3 — Queries & Features

-   [x] Write queries for Account module (user lookup, role assignment)
-   [x] Write queries for Stock module (inventory check, product listing)
-   [x] Write queries for Sales module (order creation, invoice generation)
-   [x] Write queries for Admin module (audit log retrieval, reports)

### Phase 4 — Testing & Documentation

-   [x] Test each role's access permissions
-   [ ] Write final project report / documentation
-   [ ] Prepare presentation / demo

### Phase 5 — Demo Stack (Backend)

-   [x] Backend skeleton: `main.py`, `db.py`, `deps.py`, `schemas.py` (Phase A)
-   [x] Auth router: `POST /api/auth/login|logout`, `GET /api/auth/me` (Phase A)
-   [x] Account router: users, roles, sessions CRUD with `admin` permission guard (Phase B)
-   [x] Stock router: products, categories, suppliers with `view`/`stock` guards (Phase B)
-   [x] Sales router: orders, order items, invoices with `view`/`sales` guards (Phase B)
-   [x] Admin router: audit logs, system config, reports with `admin` guard (Phase B)
-   [x] Customer auth router: `POST /api/customer/signup|login|logout`, `GET /api/customer/me` (Phase F)
-   [x] Shop router: `GET /api/shop/products` (public), `GET /api/shop/orders/mine` (customer auth) (Phase F)
-   [x] `manage_staff.py` — config-driven staff provisioning with CLI flags (Phase F)
-   [x] Shop router: `POST /api/shop/orders` — customer-authenticated checkout (stock check → order + items → deduct stock → **auto-issue unpaid invoice, 14-day due**), `user_id` NULL for self-service orders (Phase G)
-   [x] Schema migration: `orders.user_id` dropped NOT NULL so customer self-service orders can persist (Phase G)
-   [x] Dashboard router: `GET /api/dashboard/activity` — last 20 signups/orders/invoices, role-filtered (Admin/Sales: all; Cashier: orders+invoices; User: orders only) (Phase G)

### Phase 6 — Demo Stack (Frontend)

-   [x] `AuthContext`, `ProtectedRoute`, axios client with Bearer injection (Phase C)
-   [x] `StaffLogin` page with quick-login demo buttons (Phase C)
-   [x] Staff `Dashboard` page — role permission cards + system snapshot (Phase C)
-   [x] `Products` page — table with add product / restock / discontinue (Phase D)
-   [x] `Orders` page — orders table + create order modal + invoice workflow (Phase D)
-   [x] `Users` page — user table with role selector + enable/disable (Phase D)
-   [x] `AuditLogs` page — log table with action filter (Phase D)
-   [x] `Navbar` with permission-gated links + logout (Phase D)
-   [x] Customer `Login` / `Signup` pages (Phase F)
-   [x] `Shop` page — public product catalog with customer nav (Phase F)
-   [x] `MyOrders` page — customer order history (Phase F)
-   [x] `CustomerAuthContext` + `CustomerProtectedRoute` (Phase F)
-   [x] Route split: customer at `/`, staff at `/staff/*` (hidden URL) (Phase F)
-   [x] `Shop` checkout flow — cart state as list of `{product_id, name, price, quantity}` local to `Shop.jsx`; per-product "Add to cart" with circular qty badge on each card; slide-over cart drawer with +/− qty (capped at `stock_qty`), remove, line total, grand total; **success toast → redirect to `/orders/mine`**; **drawer swaps "Place order" for "Sign in to order" CTA when logged out** (Phase G)
-   [x] `Dashboard` recent activity panel — fetches `/api/dashboard/activity` on mount, auto-refreshes every 30s, role-filtered server-side, empty-state when no records (Phase G)

------------------------------------------------------------------------

## File Structure

```         
<repository root>/
├── README.md                          ← this file
├── Project overview/
│   └── user_access_server_architecture.svg
├── schema/
│   └── schema.sql                     ← full CREATE TABLE scripts (all modules)
├── data/
│   └── seed.sql                       ← roles, users, products, customers, orders, sessions
├── queries/
│   ├── auth.sql                       ← fn_login, fn_validate_session, fn_logout, fn_cleanup_sessions
│   ├── customer_auth.sql              ← customer_accounts/sessions tables + 4 PL/pgSQL functions
│   ├── permissions.sql                ← fn_check_permission, v_role_permissions, v_active_sessions
│   ├── test_login.sql                 ← runnable DO block: 7 tests covering all roles + failure cases
│   ├── account.sql                    ← user lookup, role assignment, session management (A1–A10)
│   ├── stock.sql                      ← product listing, inventory check, supplier queries (S1–S10)
│   ├── sales.sql                      ← order creation, invoice generation, revenue summary (SL1–SL12)
│   ├── admin.sql                      ← audit log retrieval, system config, reports (AD1–AD12)
│   └── test_permissions.sql           ← 30 assertions across 3 parts: matrix, scenarios, edge cases
├── backend/                           ← FastAPI server
│   ├── .env.example
│   ├── requirements.txt
│   ├── manage_staff.py                ← config-driven staff provisioning CLI
│   ├── main.py                        ← app entry, CORS, pool lifecycle, /health
│   ├── db.py                          ← psycopg3 connection pool
│   ├── deps.py                        ← get_current_user, require(module), get_current_customer
│   ├── schemas.py                     ← Pydantic models (staff + customer + shop)
│   └── routers/
│       ├── auth.py                    ← POST /api/auth/login|logout, GET /api/auth/me
│       ├── customer_auth.py           ← POST /api/customer/signup|login|logout, GET /me
│       ├── shop.py                    ← GET /api/shop/products (public), /orders/mine + POST /orders (customer)
│       ├── account.py                 ← /api/users, /api/roles, /api/sessions
│       ├── stock.py                   ← /api/products, /api/categories, /api/suppliers
│       ├── sales.py                   ← /api/orders, /api/customers, /api/invoices
│       ├── admin.py                   ← /api/audit-logs, /api/system-config, /api/reports
│       └── dashboard.py               ← GET /api/dashboard/activity (staff, role-filtered feed)
├── frontend/                          ← React + Vite + Tailwind
│   └── src/
│       ├── api/
│       │   ├── client.js              ← staff axios instance (Bearer + 401 → /staff/login)
│       │   ├── customerClient.js      ← customer axios instance (Bearer + 401 → /login)
│       │   ├── endpoints.js           ← all staff API call functions
│       │   └── customerEndpoints.js   ← customer signup/login/shop API functions
│       ├── auth/
│       │   ├── AuthContext.jsx        ← staff auth state (sentinel_token)
│       │   ├── CustomerAuthContext.jsx← customer auth state (sentinel_customer_token)
│       │   ├── ProtectedRoute.jsx     ← staff guard → /staff/login
│       │   └── CustomerProtectedRoute.jsx ← customer guard → /login
│       ├── components/
│       │   ├── Navbar.jsx             ← staff navbar with permission-gated links
│       │   ├── DataTable.jsx          ← reusable table component
│       │   └── PermissionGate.jsx     ← conditional render by module permission
│       └── pages/
│           ├── Shop.jsx               ← / public product catalog
│           ├── Login.jsx              ← /login customer sign-in
│           ├── Signup.jsx             ← /signup customer sign-up
│           ├── MyOrders.jsx           ← /orders/mine customer order history
│           ├── StaffLogin.jsx         ← /staff/login staff portal (demo quick-login)
│           ├── Dashboard.jsx          ← /staff/dashboard role permission cards
│           ├── Products.jsx           ← /staff/products inventory management
│           ├── Orders.jsx             ← /staff/orders orders + invoices
│           ├── Users.jsx              ← /staff/users user management (admin)
│           ├── AuditLogs.jsx          ← /staff/audit log viewer with filter
│           └── Forbidden.jsx          ← 403 page
└── docs/
    ├── demo_plan.md                   ← original backend + frontend plan (Phases A–E)
    ├── customer_auth_plan.md          ← customer auth + staff login plan (Phases F1–F6)
    └── er_diagram.md                  ← Mermaid ER diagram + FK + cardinality notes
```

------------------------------------------------------------------------

## Notes & Decisions

| Date | Note |
|----|----|
| 2026-05-16 | Project started. Architecture diagram completed. |
| 2026-05-16 | Project named **SentinelDB** — reflects auth guarding, audit logging, and DB focus. |
| 2026-05-16 | Renamed `Tester` role to `Cashier` to match the ERP/POS business context. |
| 2026-05-16 | Renamed `Viewer` staff role to `User` (basic read-only staff). `viewer_01` → `user_01`. Customer track uses `Viewer (Customer)` label — never mixed with staff RBAC. |
| 2026-05-16 | Mini mart retheme applied: brand name **FreshMart**, emerald color scheme, product category icons, hero banner, search+filter bar on shop, card-style order list. Staff portal retains dark navbar with FreshMart Staff branding. |
| 2026-05-16 | Phase 1 Design complete: full schema (12 tables), ER diagram, and FK map written. |
| 2026-05-16 | Phase 2 Implementation complete: seed data, auth flow (fn_login / fn_validate_session / fn_logout / fn_cleanup_sessions), and permission checks (fn_check_permission + views). |
| 2026-05-16 | Phase 3 Queries complete: account.sql (A1–A10), stock.sql (S1–S10), sales.sql (SL1–SL12), admin.sql (AD1–AD12). |
| 2026-05-16 | Phase 4 (partial) — test_permissions.sql: 30 assertions across matrix test, scenario test, and edge cases. |
| 2026-05-16 | Demo plan written (`docs/demo_plan.md`). Stack chosen: DB-centric auth, FastAPI + psycopg3 backend, React (Vite) + Tailwind frontend, minimal UI. |
| 2026-05-16 | Phase A complete — backend skeleton: db.py, deps.py (require/get_current_user), schemas.py, routers/auth.py (login/logout/me), main.py (CORS + /health). |
| 2026-05-16 | Phase B complete — all four staff module routers implemented: account, stock, sales, admin. |
| 2026-05-16 | Phase C complete — frontend skeleton: AuthContext, ProtectedRoute, axios client, StaffLogin (quick-login buttons), Dashboard. |
| 2026-05-16 | Phase D complete — all staff module pages implemented with real data: Products (add/restock/discontinue), Orders (create/status/invoice/pay), Users (role selector/toggle), AuditLogs (action filter). |
| 2026-05-16 | Phase F complete — two-track auth: customer self-service (signup/login/my orders/shop) runs parallel to staff RBAC. Staff login hidden at /staff/login. customer_accounts + customer_sessions tables + 4 PL/pgSQL functions added. manage_staff.py provisioning script created. All routes reorganized: customer at /, staff at /staff/\*. |
| 2026-05-16 | Both servers verified live: backend :8000, frontend :5173. All API endpoints tested — signup, login, /me, /shop/products, /shop/orders/mine, error cases (401/400). |
| 2026-05-16 | Plan updated: roles expanded to 5 (Admin, Sales, Cashier, User, Viewer/Customer) with explicit access matrix. Two auth flows finalized — `/staff/login` (login only, no signup, provisioned via `manage_staff.py`) for staff/admin, and `/login` + `/signup` for customers. |
| 2026-05-17 | Phase G — customer checkout: `POST /api/shop/orders` (customer-auth, `user_id` NULL) added; Shop page gained cart sidebar with qty controls + Place order; success redirects to `/orders/mine` which refetches on mount. Stock check + deduction kept inside a single DB transaction. |
| 2026-05-17 | Phase G — live dashboard feed: new `backend/routers/dashboard.py` with `GET /api/dashboard/activity` (UNION ALL across customers/orders/invoices, ORDER BY created_at DESC LIMIT 20). Per-role visibility filtered server-side off `out_role`: Admin/Sales see all, Cashier sees orders+invoices, User sees orders only. Dashboard.jsx auto-refreshes every 30s with cancellation flag for safe unmount. |
| 2026-05-17 | Live e2e verified: customer signup → order → invoice all appear in the staff activity feed within one refresh cycle, with correct labels (`Order #16 — Demo User …`, `Invoice #3 — Demo User …`). Role filtering confirmed: Admin/Sales = 3 types, Cashier = order+invoice, User = order only. |
| 2026-05-17 | Schema migration applied: `ALTER TABLE orders ALTER COLUMN user_id DROP NOT NULL` — the original schema declared `orders.user_id NOT NULL`, which blocked customer self-service orders. `schema/schema.sql` updated to match so re-seeds preserve the behavior. Staff-processed orders still set `user_id`; customer self-service orders leave it NULL. |
| 2026-05-17 | Phase G refinement — `POST /api/shop/orders` now also auto-issues an `unpaid` invoice (due in 14 days) inside the same transaction, so every customer order has a payable invoice immediately. Response trimmed to `{order_id, total_amount, status}`. |
| 2026-05-17 | Phase G refinement — `Shop.jsx` cart state refactored from `{id: qty}` map to a list of `{product_id, name, price, quantity}` (price/name snapshotted at add-time). Unauth users can build a cart freely; drawer footer swaps **Place order** for a **Sign in to order** link. Each product card shows a circular qty-in-cart badge. Success toast displays for \~1.2s before redirecting to `/orders/mine`. Customer API helper renamed `shopCreateOrder` → `placeOrder`. |
