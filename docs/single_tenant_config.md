# Single-Tenant Configuration

Set `SINGLE_TENANT_MODE=true` in `.env` to indicate there is only one user/tenant.
- No tenant IDs required.
- All data is stored to shared tables.
- Future: add tenant_id to tables and middleware if you expand.
