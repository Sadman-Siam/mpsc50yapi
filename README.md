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

Registration creates an account with `status="pending"`, and `POST /auth/login`
only admits `status="confirmed"` accounts. Approve new registrations through:

```bash
curl -X PATCH "http://localhost:8000/admin/alumnae/<uuid>/status?new_status=confirmed" \
  -H "X-Admin-Secret: $ADMIN_SECRET"
```

Use `status=cancelled` to deactivate an account; both `/auth/login` and
`/auth/verify-token` reject non-confirmed accounts immediately.

## Payment flow

The redirect wiring matters, so it is worth stating explicitly:

1. The frontend calls `POST /payments/initiate`.
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
server and is never accepted from the client.

Re-initiating reuses an existing `unpaid` payment rather than creating a
duplicate; a `failed` payment gets a fresh reference. Once a payment is
`completed`, `/payments/initiate` returns 409.

## Endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/auth/register` | – | Register with optional work profile, address and acquaintances |
| POST | `/auth/login` | – | Authenticate and set the access-token cookie |
| POST | `/auth/logout` | – | Clear the access-token cookie |
| POST | `/auth/refresh-token` | cookie | Reissue a token within the refresh window |
| GET | `/auth/verify-token` | cookie | Confirm the session is still active |
| GET | `/auth/me` | cookie | Current alumna with nested profile |
| PUT | `/auth/update-profile` | cookie | Update name and phone number |
| PUT | `/auth/update-password` | cookie | Change password |
| GET | `/admin/alumnae` | admin | List alumnae, filterable by `status` |
| GET | `/admin/alumnae/counts` | admin | Counts grouped by status |
| PATCH | `/admin/alumnae/{uuid}/status` | admin | Approve, cancel or reactivate |
| POST | `/payments/initiate` | cookie | Create an SSLCommerz session |
| GET | `/payments/me` | cookie | List the alumna's payments |
| GET | `/payments/{uuid}` | cookie | Get one payment (ownership enforced) |
| POST | `/payments/{uuid}/confirm` | cookie | Manually confirm an offline payment |
| POST | `/payments/callback` | – | Browser redirect; validates then forwards to the frontend |
| POST | `/payments/ipn` | – | SSLCommerz server-to-server notification |
| GET | `/public/event` | – | Static event information |
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

- `/admin/*` is protected by one shared secret with no audit trail of who
  approved or cancelled an account. Introduce real admin users before this
  handles live registrations.
- The payment flow is covered by tests that stub the gateway; it has not been
  exercised against the real SSLCommerz sandbox.
- Refunds are represented in the `PaymentStatus` type but not implemented.

Author:  Docufy <info@docufybd.com>

License: See [License](./LICENSE) file.