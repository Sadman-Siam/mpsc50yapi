# MPSC 50 Years Alumni API

Backend for the web based system for the 50 years celebrations event.

The system offers,

1. Authentication & Authorization for Alumni
2. Payment via SSLCommerz
3. Information displayed via public facing pages

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL (production) or SQLite (development)

## Setup

```bash
uv sync
cp .env.example .env   # then edit the values
uv run alembic upgrade head
uv run uvicorn app:app --reload --port 8000
```

For local development use `DATABASE_URI="sqlite:///./mpsc50years.db"` and set
`DEV_MODE="1"`. Without `DEV_MODE` the access cookie is issued with `Secure`
and `SameSite=None`, which browsers drop over plain `http://localhost`, so
login would appear to fail for no visible reason.

Interactive API docs: http://localhost:8000/docs

## Environment variables

All variables are documented in [.env.example](./.env.example). Required:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URI` | SQLAlchemy database URL |
| `JWT_SECRET_KEY` | Signing key (private key when using RS256) |
| `JWT_PUBLIC_KEY` | Verification key (public key when using RS256) |
| `JWT_ALGORITHM` | e.g. `HS256` or `RS256` |
| `ACCESS_TOKEN_NAME` | Name of the httpOnly cookie holding the access token |
| `ADMIN_SECRET` | Shared secret for the `X-Admin-Secret` header on `/admin/*` |

`DEV_MODE`, `API_URL`, `FRONTEND_URL`, `EVENT_FEE_BDT` and the
`SSLCOMMERZ_*` variables have defaults; see `.env.example`.

## Account lifecycle

An alumna registers, pays the participation fee, and is then approved by an
admin. Approval is the last step, not a gate on payment.

Registration creates an account with `status="pending"` and issues the access
cookie, so the client can go straight from `POST /auth/register` to
`POST /payments/initiate` without logging in. A `pending` account may log in,
pay, and view its own record; admin approval is what promotes it to
`confirmed`.

Approve new registrations through:

```bash
curl -X PATCH "http://localhost:8000/admin/alumnae/<uuid>/status?new_status=confirmed" \
  -H "X-Admin-Secret: $ADMIN_SECRET"
```

Use `status=cancelled` to deactivate an account. `cancelled` is the only status
that is refused: `/auth/login`, `/auth/verify-token`, `/auth/refresh-token` and
every `/payments/*` route reject a cancelled alumna immediately.

## Admin panel authentication

`/admin/*` accepts either credential:

- **A session cookie.** `POST /admin/login` with `{"admin_secret": "..."}`
  compares against `ADMIN_SECRET` in constant time and returns a dedicated
  httpOnly cookie (`ADMIN_TOKEN_NAME`, 8 hours). This is what the browser panel
  uses, so the secret is never handed to browser JavaScript or stored in
  `localStorage`.
- **The `X-Admin-Secret` header**, unchanged, for scripted access:

```bash
curl "http://localhost:8000/admin/alumnae" -H "X-Admin-Secret: $ADMIN_SECRET"
```

The two sessions are separate. An admin token carries an `admin` claim and no
`uuid`, and it is read from a different cookie than the alumna session, so
neither credential is accepted by the other's routes. An unset `ADMIN_SECRET`
fails closed: every admin request is rejected rather than allowing an empty
secret.

## Payment visibility for admins

Every row of `GET /admin/alumnae` carries a `payment` summary:

```json
"payment": {
  "has_paid": true,
  "latest_status": "completed",
  "amount": 1500,
  "transaction_reference": "MPSC50-...",
  "paid_at": "2026-10-13T10:00:00Z"
}
```

With the register → pay → approve flow this is what the panel sorts and filters
on. When an alumna has several payments, a `completed` one is reported in
preference to a later failure, because a settled payment takes its timestamp
from the gateway while a failure keeps its creation time — ordering on time
alone would let a failure hide a success.

## Payment flow

The redirect wiring matters, so it is worth stating explicitly:

1. The frontend calls `POST /payments/initiate`, immediately after registering.
   A `pending` alumna is allowed to pay.
2. The API creates a `Payment` row and asks SSLCommerz for a checkout session.
   `success_url` and `ipn_url` point at **the API**, not the frontend.
3. The alumna pays on the gateway.
4. The gateway redirects the browser to `POST /payments/callback`. The API
   re-validates the transaction server-to-server, marks the payment, then
   returns a `303` to `/payment/success` or `/payment/cancelled`.
5. The gateway may also send a server-to-server notification to
   `POST /payments/ipn`, which settles the payment even if the alumna closes
   the browser before step 4.

`/payments/callback` must not point at the frontend: nothing would validate the
transaction, and the payment would appear to fail even though money moved.

A transaction is only accepted when the gateway validation reports `VALID`,
the same `tran_id`, and **the expected amount and currency**. Paying 1 BDT
does not settle a 1500 BDT fee. The amount comes from `EVENT_FEE_BDT` on the
server and is never accepted from the client. `GET /public/event` reports the
same value, so the advertised price cannot drift from the charged one.

Re-initiating reuses an existing `unpaid` payment rather than creating a
duplicate; a `failed` payment gets a fresh reference. Once a payment is
`completed`, `/payments/initiate` returns 409.

## Endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/auth/register` | – | Register, then set the access-token cookie |
| POST | `/auth/login` | – | Authenticate and set the access-token cookie |
| POST | `/auth/logout` | – | Clear the access-token cookie |
| POST | `/auth/refresh-token` | cookie | Reissue a token within the refresh window |
| GET | `/auth/verify-token` | cookie | Confirm the session is still active |
| GET | `/auth/me` | cookie | Current alumna with nested profile |
| PUT | `/auth/update-profile` | cookie | Update name and phone number |
| PUT | `/auth/update-password` | cookie | Change password |
| POST | `/admin/login` | – | Exchange `ADMIN_SECRET` for an admin session cookie |
| POST | `/admin/logout` | – | Clear the admin session cookie |
| GET | `/admin/session` | admin | Confirm the admin session is still valid |
| GET | `/admin/alumnae` | admin | List alumnae with a payment summary, filterable by `status` |
| GET | `/admin/alumnae/counts` | admin | Counts grouped by status |
| PATCH | `/admin/alumnae/{uuid}/status` | admin | Approve, cancel or reactivate |
| POST | `/payments/initiate` | cookie | Create an SSLCommerz session (allowed while `pending`) |
| GET | `/payments/me` | cookie | List the alumna's payments |
| GET | `/payments/{uuid}` | cookie | Get one payment (ownership enforced) |
| POST | `/payments/{uuid}/confirm` | cookie | Manually confirm an offline payment |
| POST | `/payments/callback` | – | Browser redirect; validates then forwards to the frontend |
| POST | `/payments/ipn` | – | SSLCommerz server-to-server notification |
| GET | `/public/event` | – | Static event information, fee from `EVENT_FEE_BDT` |
| GET | `/public/statistics` | – | Aggregate counts, no personal data |

## Migrations

`create_all()` is only used for SQLite in development. Use Alembic for anything else:

```bash
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
uv run alembic downgrade -1
```

## Development

```bash
uv run pytest                       # test suite
uv run pytest --cov=app             # with coverage
uv run ruff check .                 # lint
uv run ruff format .                # format
uv run mypy app                     # type check
```

## Known gaps

- `/admin/*` is protected by one shared secret with no record of who approved an
  account. The panel authenticates with a session cookie, but the credential is
  still a single shared secret, so an approval cannot be attributed to a person.
- The payment flow is covered by tests that stub the gateway; it has not been
  exercised against the real SSLCommerz sandbox.
- Refunds are represented in the `PaymentStatus` type but not implemented.
- `pending` covers both "registered, not paid" and "paid, awaiting approval".
  The `payment` summary on each row distinguishes them, but the status itself
  does not.
- There is no search, pagination beyond `limit`/`offset`, or bulk approval in the
  listing.
- A `pending` alumna may read and edit her own record via `/auth/me` and
  `/auth/update-profile`, since only `cancelled` is refused.

Author:  Docufy <info@docufybd.com>

License: See [License](./LICENSE) file.