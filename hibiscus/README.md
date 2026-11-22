# Hibiscus feasibility test — 17 November 2026

Goal: test a free replacement for MoneyMoney against the actual ING accounts and all three depots before changing the working MCP connector. No live compatibility is claimed yet. The agent workspace cannot resolve `www.willuhn.de`, so installation must run in the owner's network-enabled terminal.

## Install Jameica on macOS

```sh
cd ~/code/dankelleher/ing-investment-mcp/hibiscus
./scripts/install-jameica-macos.sh
```

The script downloads the official Jameica 2.12.0 archive for Apple Silicon or Intel, verifies its architecture-specific SHA-256 against Homebrew's published cask, and installs it under `~/Applications/jameica.app`. It does not replace an existing app, change macOS security settings, or connect to the bank. Jameica's macOS package includes Java 21; the system Java installation does not need changing.

Homebrew's Jameica cask is currently disabled because it fails Gatekeeper checks, so `brew install --cask jameica` is not the recommended route. If macOS blocks the downloaded app, use its normal Settings → Privacy & Security → Open Anyway flow after checking the named app is Jameica. If the message says the app is damaged or malicious, stop and investigate the exact message instead of overriding it. Do not disable Gatekeeper globally or strip quarantine recursively.

## First launch and plugins

1. Choose a local profile and create Jameica's master password. This protects the app/profile; it is separate from your ING password.
2. Use **Datei → Plugins online suchen…** to install **Hibiscus** from the bundled official repository. Restart Jameica when requested.
3. Open **Datei → Einstellungen → Updates**. Add `https://www.open4me.de/hibiscus/` if it is absent. Open that repository and install **Depot-Viewer** (`hibiscus.depotviewer`). Review the publisher information displayed by Jameica; do not disable signature checks. Restart when requested.
4. Confirm Jameica is at least 2.10.5, Hibiscus at least 2.10.1, and Java at least 17. The pinned Jameica package is 2.12.0 with bundled Java 21. Use the stable plugin versions offered by their repositories.

## Configure ING locally

In Hibiscus, create a **PIN/TAN** bank access:

| Setting | Value |
|---|---|
| Bank code / BLZ | `50010517` |
| FinTS endpoint | `https://fints.ing.de/fints/` |
| Protocol | FinTS 3.0 |
| Benutzerkennung | Your chosen ING username, as used in online banking |
| Kunden-ID | Blank, per ING's current official instructions |
| PIN/password | Your ING password, entered only into the local banking app |

ING's current instructions supersede the old access-number/PIN guidance in the initial October proposal. Log in to trusted ING online banking first if your last successful two-factor login was over 90 days ago. Never paste a bank password into chat or terminal commands. If the UI refuses an empty customer ID, stop at that validation message so we can check the application-specific instructions; do not experiment with repeated bank logins.

Synchronize once for account discovery and request read operations only (balances, booked transactions, holdings). ING states payments are unavailable through this FinTS interface. The scope of this test does not include payment/order setup.

## Test depots

Open **Depot-Viewer → Einrichtungsassistenten**. The plugin documentation says FinTS depot accounts should have account type **Wertpapierkonto** or **Fonds-Depot** and access method **HBCI**, rather than **Depot Viewer**. Its ING compatibility table claims holdings support and no securities-transaction support, but that ING entry was last updated in 2017 and requires current validation.

Check each depot separately:

- Direkt-Depot: appears; holdings have ISIN, quantity and market value.
- First Smart-Depot: appears and has actual holdings.
- Second Smart-Depot: appears and has actual holdings.
- Cash accounts: balances and at least one booked transaction can be read.

Do not treat a Smart-Depot's settlement/cash account as successful securities coverage. Compare against the current ING view. The previous MoneyMoney capture had 10/13/13 positions, but later purchases can change those counts. ING's official FinTS page lists Girokonto, Extra-Konto and Direkt-Depot; it does not establish Smart-Depot support. If Smart-Depots are absent, report that gap rather than assuming the credentials failed.

## Report and next step

Tell the agent which accounts/depots appear, whether holdings load, and the exact error text for any failure. Credentials remain local. The owner has already authorized financial-data inspection, but bank protocol logs can contain credentials/session details and should not be pasted wholesale.

After account coverage passes, inspect Depot-Viewer's export/report interfaces and implement an adapter for the existing read-only MCP. Installing Hibiscus alone does not reconnect the MCP: the current `ing-moneymoney` server still uses MoneyMoney.

## Sources

- [Jameica project and installation](https://github.com/willuhn/jameica)
- [Homebrew cask: architecture-specific download URLs and SHA-256](https://raw.githubusercontent.com/Homebrew/homebrew-cask/master/Casks/j/jameica.rb)
- [Depot-Viewer installation](https://github.com/littleyoda/hibiscus.depotviewer)
- [Depot-Viewer bank support](https://github.com/littleyoda/hibiscus.depotviewer/blob/master/banken.md)
- [ING current FinTS setup](https://www.ing.de/hilfe/log-in/fints/)
