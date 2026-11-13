# 小北智慧購物 App｜GitHub Pages 公開示範站

## 部署

1. 在 GitHub 建立一個 **Public** repository。
2. 將此資料夾內的所有檔案上傳至 repository 根目錄，主要入口為 `index.html`。
3. 推送到 `main` 分支後，`Actions` 會嘗試啟用 Pages 並自動部署靜態網站。
4. 若 GitHub 權限不允許 workflow 自動啟用，請到 repository 的 **Settings → Pages**，選擇 **GitHub Actions** 作為部署來源，然後重新執行 workflow。

## 公開版範圍

- GitHub Pages 是免費靜態前端；門市篩選使用官方門市資料檔 `stores-tw.js`。
- 會員、商品、價格、庫存、購物車及訂單仍是瀏覽器端示範資料。
- 公開版客服會使用 FAQ 示範回覆。GitHub Pages 不會連到開發者電腦上的 Ollama；本機 Qwen 只在本機 `start-local-ai.bat` 伺服器啟動時可用。
- 正式公開 AI 客服需要可公開連線的後端（例如 Cloud Run），並需設定 HTTPS、存取控制、限流、成本告警及隱私政策。不要把 Ollama 的 11434 埠直接公開。
- 商品分類參考小北官方公司簡介；商品名稱、價格與庫存數量為企劃展示資料，不是正式銷售資料。
