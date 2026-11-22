# ING Investment MCP

Local, read-only MCP servers for ING Deutschland cash accounts and securities depots. There are three independent routes to the bank data, each in its own folder with its own package, dependencies, tests and documentation. They share no code.

| Folder | Route | Bank access handled by | Status |
|---|---|---|---|
| [`moneymoney/`](moneymoney/) | MoneyMoney AppleScript exports | MoneyMoney (paid licence) | Working; validated against real exports, including both Smart-Depots |
| [`hibiscus/`](hibiscus/) | Jameica + Hibiscus + Depot-Viewer | Hibiscus (free) | Installed; blocked at ING login |
| [`fints/`](fints/) | Direct FinTS with python-fints | This project (registered FinTS product ID) | Feasibility spike; awaiting product registration |

All three are designed to expose the same read-only tools: accounts, holdings, balances, portfolio summary, sync status and, optionally, booked transactions. None of them offers payments, securities orders, or any bank-login tool. Credentials stay in the banking application or the OS keychain, never in this repository, MCP responses or chat.

ING's FinTS interface officially covers Girokonto, Extra-Konto and Direkt-Depot only. Smart-Depots (Smart Invest) have so far only been reachable through MoneyMoney.

Each folder's README explains setup, launch and tests for that route.
