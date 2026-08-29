# Live VPS Fleet Architecture & Network Topology 🌐

**Server IP:** `${VPS_HOST}`  
**OS:** Ubuntu 24.04 LTS  
**Primary Agent Container Engine:** Docker (s6-rc supervised)

---

## 1. Container Inventory & Memory Databases

| Agent Name | Role | Container Name | Memory Database | Internal DSN | Vault Path | MCP Tools |
|---|---|---|---|---|---|---|
| **Toy** | Chief Orchestrator & Lead Researcher | `hermes-agent` | `toy_db` (186 notes) | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/toy_db` | `/opt/data/vault` | 9 Tools (v3.5.0) |
| **Old** | Task Manager & Executive Ops | `hermes-assistant` | `old_db` (41 notes) | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/old_db` | `/opt/data/obsidian-vault` | 9 Tools (v3.5.0) |
| **Candy** | Content Pipeline & Marketing AI | `hermes-marketing` | `candy_db` (14 notes) | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/candy_db` | `/opt/data/obsidian-vault` | 9 Tools (v3.5.0) |
| **Pencil** | Security Auditing (154 Hexstrike tools) | `hermes-pentest` | `pencil_db` (29 notes) | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/pencil_db` | `/opt/data/obsidian-vault` | 9 Tools (v3.5.0) |
| **Coin** | Crypto & Market Quantitative Intelligence | `hermes-trader` | `trader_db` (13 notes) | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/trader_db` | `/opt/data/obsidian-vault` | 9 Tools (v3.5.0) |
| **Shared Fleet** | Global Policies & Threat Intel | Cross-Agent Layer | `shared_db` (20 policies) | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/shared_db` | *Shared DB* | Credential Guard |
| **PostgreSQL** | Storage Engine | `mo-graphify-obsidian-memory-postgres-1` | All 6 DBs (303 notes) | `<POSTGRES_INTERNAL_IP>:5432` | `/var/lib/postgresql/data` | HNSW pgvector |

---

## 2. Docker Network Map

```
                     ┌────────────────────────────────────────────────────────┐
                     │     mo-graphify-obsidian-memory_default (Bridge)       │
                     │                 Subnet: <POSTGRES_SUBNET>                  │
                     └──────────────────────────┬─────────────────────────────┘
                                                │
         ┌───────────────────┬──────────────────┼───────────────────┬──────────────────┐
         ▼                   ▼                  ▼                   ▼                  ▼
┌──────────────────┐┌──────────────────┐┌──────────────────┐┌──────────────────┐┌──────────────────┐
│   hermes-agent   ││ hermes-assistant ││ hermes-marketing ││  hermes-pentest  ││  hermes-trader   │
│      (Toy)       ││      (Old)       ││     (Candy)      ││     (Pencil)     ││      (Coin)      │
│   <AGENT_IP>     ││   <AGENT_IP>     ││   <AGENT_IP>     ││   <AGENT_IP>     ││   <AGENT_IP>     │
└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘
         │                   │                  │                   │                  │
         └───────────────────┴──────────────────┼───────────────────┴──────────────────┘
                                                │
                                                ▼
                               ┌───────────────────────────────────┐
                               │   PostgreSQL + pgvector Container │
                               │           (<POSTGRES_INTERNAL_IP>:5432)       │
                               │   Host mapped: 127.0.0.1:15432    │
                               └───────────────────────────────────┘
```

---

## 3. Host Port Allocations & Firewall Rules

| Port | Service | Bound Interface | Purpose / Security |
|---|---|---|---|
| `22` | SSH | `0.0.0.0` (Public) | Secure SSH Admin Access |
| `80` / `443` | Caddy (`sophia-caddy`) | `0.0.0.0` (Public) | Web ingress & reverse proxy |
| `15432` | PostgreSQL (`pgvector`) | `127.0.0.1` (Localhost) | **Blocked by UFW** from external internet; host bridge only |
| `8642` | Toy Web Gateway | `127.0.0.1` (Localhost) | Hermes Gateway UI |
| `8643` | Pencil Web Gateway | `127.0.0.1` (Localhost) | Pentest Hermes Gateway UI |

---

## 4. Automated Nightly Consolidation Cron

* **Schedule:** `0 3 * * *` (Daily at 03:00 AM Europe/Berlin)
* **Action:** Iterates through `toy_db`, `old_db`, `candy_db`, `pencil_db`, `trader_db`, and `shared_db`, applying Ebbinghaus decay ($S_t = S_0 \times 0.95^{\text{days}}$) to active notes while exempting `pinned`, `policy`, and permanent knowledge.
