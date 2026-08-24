# Live VPS Fleet Architecture & Network Topology 🌐

**Server IP:** `<YOUR_VPS_IP>`  
**OS:** Ubuntu 24.04 LTS  
**Primary Agent Container Engine:** Docker (s6-rc supervised)

---

## 1. Container Inventory & Memory Databases

| Agent Name | Role | Container Name | Memory Database | Internal DSN | Vault Path |
|---|---|---|---|---|---|
| **Toy** | Core DevOps & Assistant | `hermes-agent` | `toy_db` (58 notes) | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/toy_db` | `/root/.hermes/vault` |
| **Old** | General Assistant | `hermes-assistant` | `old_db` (14 notes) | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/old_db` | `/root/.hermes/vault` |
| **Candy** | Marketing AI Agent | `hermes-marketing` | `candy_db` (3 notes) | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/candy_db` | `/root/.hermes/vault` |
| **Pencil** | Cybersecurity Pentester | `hermes-pentest` | `pencil_db` (5 notes) | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/pencil_db` | `/root/.hermes/vault` |
| **Coin** | Crypto Trader AI | `hermes-trader` | `trader_db` (2 notes) | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/trader_db` | `/root/.hermes/vault` |
| **PostgreSQL Database** | Storage Engine | `mo-graphify-obsidian-memory-postgres-1` | All 5 DBs | `<POSTGRES_INTERNAL_IP>:5432` | `/var/lib/postgresql/data` |

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
| `7440` / `8443` | Pencil FRP Relay | `0.0.0.0` (Public) | Remote campus tunnels |

---

## 4. Automated Nightly Consolidation Cron

* **Host Script:** `/root/.hermes/scripts/run-nightly-consolidation.sh`
* **Python Engine:** `/root/.hermes/scripts/nightly_consolidation.py`
* **Schedule:** `0 3 * * *` (Daily at 03:00 AM Europe/Berlin)
* **Action:** Iterates through `toy_db`, `old_db`, `candy_db`, `pencil_db`, and `trader_db`, applying Ebbinghaus decay ($S_t = S_0 \times 0.95^{\text{days}}$) to active notes while exempting `pinned` and permanent knowledge.
