# 小北智慧購物 App｜GitHub Pages 公開示範站

## 部署

1. GitHub Pages workflow 會發布 `site/` 目錄，桌面／響應式入口為 `site/index.html`，手機優先頁面為 `site/mobile.html`。
2. 推送 `site/` 變更到 `main` 後，`Actions` 會自動部署靜態網站。
3. 若 GitHub 權限不允許 workflow 自動啟用，請到 repository 的 **Settings → Pages**，選擇 **GitHub Actions** 作為部署來源，然後重新執行 workflow。

## 公開版範圍

- GitHub Pages 是免費靜態前端；門市篩選使用官方門市資料檔 `stores-tw.js`。
- 會員、商品、價格、庫存、購物車及訂單仍是瀏覽器端示範資料。
- 公開版客服會使用 FAQ 示範回覆。GitHub Pages 不會連到開發者電腦上的 Ollama；本機 Qwen 只在本機 `start-local-ai.bat` 伺服器啟動時可用。
- 正式公開 AI 客服需要可公開連線的後端（例如 Cloud Run），並需設定 HTTPS、存取控制、限流、成本告警及隱私政策。不要把 Ollama 的 11434 埠直接公開。
- 商品分類參考小北官方公司簡介；商品名稱、價格與庫存數量為企劃展示資料，不是正式銷售資料。
- 手機版網址：`https://qian03777.github.io/test/mobile.html`；完整網站仍是 `https://qian03777.github.io/test/`。

## Google 帳號與 Cloud SQL 後端（尚待 GCP 專案）

`backend/` 已準備 Google Identity token 驗證與 Cloud SQL PostgreSQL 訂單 API。尚未建立 GCP project/Cloud SQL，因此公開 Pages 目前只使用示範會員與 FAQ 客服。

部署後端前需：

1. 建立 GCP project、啟用帳單與 Cloud Run / Cloud SQL / Secret Manager APIs。
2. 建立 Cloud SQL PostgreSQL、Google OAuth Web Client ID；將 `https://qian03777.github.io` 加入 OAuth Authorized JavaScript origins。
3. 建立 Cloud Run service account 並授予 Cloud SQL Client；在 Secret Manager 建立 `db-password`、`qr-signing-secret`。
4. 在 GitHub repo 設定 Actions Variables：`GCP_PROJECT_ID`、`GCP_REGION`、`CLOUD_RUN_SERVICE`、`GOOGLE_CLIENT_ID`、`INSTANCE_CONNECTION_NAME`、`DB_NAME`、`DB_USER`、`WEB_ORIGIN`；Secrets：`GCP_WIF_PROVIDER`、`GCP_DEPLOY_SERVICE_ACCOUNT`。
5. 先執行 `python backend/seed_data.py` 初始化門市、示範商品與模擬庫存，再於 Actions 手動執行 Cloud Run workflow。
6. 將 OAuth Client ID 與 Cloud Run API URL 設定到 `site/site-config.js`，推送後 Google 登入與 SQL 下單才會啟用。

Cloud SQL 不是免費服務；目前線上金流未串接，所以 SQL API 只建立取貨付款訂單。不要提交 DB 密碼、Google 私鑰或 QR 簽章密鑰；使用 Secret Manager/GitHub Actions Secrets。
