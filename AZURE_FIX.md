# Azure Deployment Fix - Root Cause Analysis

## Shrnutí problému

Azure deployment selhává s:
```
ModuleNotFoundError: No module named 'uvicorn'
WARNING: Could not find virtual environment directory /home/site/wwwroot/antenv.
Could not find build manifest file at '/home/site/wwwroot/oryx-manifest.toml'
```

## Root Cause Analysis

### Co jsem zjistil:

1. **Poslední 3 commity (1a747c3, 13e57fd, 95bd38c) změnily POUZE testy**
   - Žádná změna v requirements.txt
   - Žádná změna v workflow
   - Žádná změna v app kódu
   - **→ Kód aplikace je v pořádku**

2. **requirements.txt obsahuje uvicorn**
   - Řádek 62: `uvicorn==0.35.0`
   - Řádek 16: `gunicorn==23.0.0`
   - **→ Dependencies jsou správně definované**

3. **GitHub Actions workflow uploaduje artifact správně**
   - Builduje lokálně do `antenv/`
   - Uploaduje vše kromě `antenv/` (řádek 42)
   - Azure má provést Oryx build podle `SCM_DO_BUILD_DURING_DEPLOYMENT=true`
   - **→ Workflow je správně nakonfigurovaný**

4. **PROBLÉM: Azure Oryx build neproběhl**
   - Log ukazuje: `Could not find build manifest file at '/home/site/wwwroot/oryx-manifest.toml'`
   - Oryx manifest se vytváří BĚHEM buildu
   - Pokud manifest neexistuje = build neproběhl
   - **→ Azure build proces selhal**

## Možné příčiny

### 1. Azure App Service Configuration změněna
**Nejpravděpodobnější příčina**: Někdo (nebo automatický proces) změnil nastavení v Azure Portal.

Zkontrolujte:
- Configuration > General settings > Startup Command
- Configuration > Application settings > `SCM_DO_BUILD_DURING_DEPLOYMENT`
- Configuration > Application settings > `ENABLE_ORYX_BUILD`

### 2. Azure Platform Issue
Azure může mít dočasný problém s Oryx build systémem.

### 3. Deployment Slot swap nebo reset
Pokud došlo k slot swap nebo reset konfigurace, nastavení mohlo být ztraceno.

## ŘEŠENÍ - Krok za krokem

### Verze A: Zkontrolujte a opravte Azure Configuration (doporučeno)

```bash
# 1. Přihlaste se do Azure
az login

# 2. Zkontrolujte Application Settings
az webapp config appsettings list \
  --name gallery-twin \
  --resource-group <your-resource-group> \
  --query "[?name=='SCM_DO_BUILD_DURING_DEPLOYMENT' || name=='ENABLE_ORYX_BUILD']"

# 3. Pokud SCM_DO_BUILD_DURING_DEPLOYMENT není true, nastavte ho
az webapp config appsettings set \
  --name gallery-twin \
  --resource-group <your-resource-group> \
  --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true ENABLE_ORYX_BUILD=true

# 4. Zkontrolujte startup command
az webapp config show \
  --name gallery-twin \
  --resource-group <your-resource-group> \
  --query "appCommandLine"

# 5. Pokud startup command obsahuje gunicorn, ODSTRAŇTE HO (nechte Azure Oryx ho nastavit)
az webapp config set \
  --name gallery-twin \
  --resource-group <your-resource-group> \
  --startup-file ""

# 6. Restartujte aplikaci
az webapp restart \
  --name gallery-twin \
  --resource-group <your-resource-group>

# 7. Trigger nový deployment
# Buď pushnete prázdný commit:
git commit --allow-empty -m "trigger Azure deployment"
git push

# Nebo trigger workflow manuálně v GitHub Actions
```

### Verze B: Azure Portal (GUI)

1. Přejděte do Azure Portal → App Services → gallery-twin
2. Configuration → General settings
   - **Startup Command**: SMAZAT (nechte prázdné)
   - Klikněte Save
3. Configuration → Application settings
   - Přidejte/upravte: `SCM_DO_BUILD_DURING_DEPLOYMENT` = `true`
   - Přidejte/upravte: `ENABLE_ORYX_BUILD` = `true`
   - Klikněte Save
4. Overview → Restart
5. Deployment Center → Redeploy latest

### Verze C: Vynuťte kompletní rebuild

```bash
# 1. Smažte deployment cache
az webapp deployment source delete \
  --name gallery-twin \
  --resource-group <your-resource-group>

# 2. Pushnete znovu
git commit --allow-empty -m "force rebuild"
git push
```

## Ověření

Po deployi zkontrolujte logy:

```bash
# Real-time log stream
az webapp log tail \
  --name gallery-twin \
  --resource-group <your-resource-group>
```

Hledejte v logu:
```
✅ SPRÁVNĚ: Oryx build úspěšný
Detected following platforms:
  python: 3.12.12
Running oryx build...
Build succeeded.
```

```
❌ ŠPATNĚ: Oryx build se nespustil
Could not find build manifest file
WARNING: Could not find virtual environment
```

## Prevence do budoucna

### Doporučení 1: Pin Azure configuration as code

Vytvořte `azure-config.json`:
```json
{
  "appSettings": [
    {
      "name": "SCM_DO_BUILD_DURING_DEPLOYMENT",
      "value": "true"
    },
    {
      "name": "ENABLE_ORYX_BUILD",
      "value": "true"
    }
  ],
  "startupCommand": ""
}
```

Aplikujte:
```bash
az webapp config appsettings set \
  --name gallery-twin \
  --resource-group <your-resource-group> \
  --settings @azure-config.json
```

### Doporučení 2: Přidejte health check do workflow

Do `.github/workflows/main_gallery-twin.yml` přidejte po deploy:

```yaml
- name: Health Check
  run: |
    sleep 30
    response=$(curl -s -o /dev/null -w "%{http_code}" https://gallery-twin.azurewebsites.net/)
    if [ $response != "200" ]; then
      echo "❌ Deployment failed - HTTP $response"
      exit 1
    fi
    echo "✅ Deployment successful - HTTP $response"
```

### Doporučení 3: Monitoring & Alerts

Nastavte Azure Monitor alert na application crashes:
```bash
az monitor metrics alert create \
  --name gallery-twin-crash-alert \
  --resource-group <your-resource-group> \
  --scopes /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Web/sites/gallery-twin \
  --condition "count Http5xx > 10" \
  --window-size 5m \
  --evaluation-frequency 1m
```

## FAQ

### Q: Proč to fungovalo předtím a teď ne?
A: Azure konfigurace byla změněna (manuálně nebo automaticky). Kód aplikace je v pořádku.

### Q: Musím něco změnit v kódu?
A: NE. Problém není v kódu. Všechny poslední commity měnily jen testy.

### Q: Můžu to opravit bez Azure CLI?
A: Ano, použijte Azure Portal (Verze B výše).

### Q: Kolik to bude trvat?
A: Po opravě konfigurace + restart + redeploy ~5-10 minut.

### Q: Co když to nepomůže?
A: Kontaktujte Azure Support nebo zkontrolujte Azure Service Health pro známé problémy.
