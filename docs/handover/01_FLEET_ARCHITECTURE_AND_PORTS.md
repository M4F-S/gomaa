# Live VPS Fleet Architecture & Network Topology 🌐

**Server IP:** `` ${VPS_HOST} ``  
**OS:** Ubuntu 24.04 LTS  
**Primary Agent Container Engine:** Docker (s6-rc supervised)

---

## 1. Container Inventory & Memory Databases

| Agent Name | Role | Container Name | Memory Database | Internal DSN | Vault Path |
|---|---|---|---|---|---|
| **Toy** | Core DevOps & Assistant | `hermes-agent` | `toy_db` | `postgresql://mnemosyne:***@${DB_HOST}:5432/toy_db` | `${VAULT_PATH}` |
| **Old** | General Assistant | `hermes-assistant` | `old_db` | `postgresql://mnemosyne:***@${DB_HOST}:5432/old_db` | `${VAULT_PATH}` |
| **Candy** | Marketing AI Agent | `hermes-marketing` | `candy_db` | `postgresql://mnemosyne:***@${DB_HOST}:5432/candy_db` | `${VAULT_PATH}` |
| **Pencil** | Cybersecurity Pentester | `hermes-pentest` | `pencil_db` | `postgresql://mnemosyne:***@${DB_HOST}:5432/pencil_db` | `${VAULT_PATH}` |
| **Coin** | Crypto Trader AI | `hermes-trader` | `trader_db` | `postgresql://mnemosyne:***@${DB_HOST}:5432/trader_db` | `${VAULT_PATH}` |
| **PostgreSQL Database** | Storage Engine | `mo-graphify-obsidian-memory-postgres-1` | All 5 DBs | `${DB_HOST}:5432` | `/var/lib/postgresql/data` |

---

## 2. Docker Network Map

```
                     ┌────────────────────────────────────────────────────────┐
                     │     mo-graphify-obsidian-memory_default (Bridge)       │
                     │                 Subnet: ${DB_NETWORK}                  │
                     └──────────────────────────┬─────────────────────────────┘
                                                │
         ┌───────────────────┬──────────────────┼───────────────────┬──────────────────┐
         ▼                   ▼                  ▼                   ▼                  ▼
┌──────────────────┐┌──────────────────┐┌──────────────────┐┌──────────────────┐┌──────────────────┐
│   hermes-agent   ││ hermes-assistant ││ hermes-marketing ││  hermes-pentest  ││  hermes-trader   │
│      (Toy)       ││      (Old)       ││     (Candy)      ││     (Pencil)     ││      (Coin)      │
│    ${NODE_TOY}    ││    ${NODE_OLD}    ││   ${NODE_CANDY}   ││  ${NODE_PENCIL}  ││   ${NODE_COIN}   │
└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘
         │                   │                  │                   │                  │
         └───────────────────┴──────────────────┼───────────────────┴──────────────────┘
                                                │
                                                ▼
                               ┌───────────────────────────────────┐
                               │   PostgreSQL + pgvector Container │
                               │   (${DB_HOST}:5432)           │
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

* **Host Script:** `${HOST_SCRIPTS_DIR}/run-nightly-consolidation.sh`
* **Python Engine:** `${HOST_SCRIPTS_DIR}/nightly_consolidation.py`
* **Schedule:** `0 3 * * *` (Daily at 03:00 AM Europe/Berlin)
* **Action:** Iterates through `toy_db`, `old_db`, `candy_db`, `pencil_db`, and `trader_db`, applying Ebbinghaus decay ($S_t = S_0 \times 0.95^{\text{days}}$) to active notes while exempting `pinned` and permanent knowledge.
