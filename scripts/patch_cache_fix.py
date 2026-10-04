# -*- coding: utf-8 -*-
import os
import re
import json

base_dir = r"c:\LNCZ\proyecto-catastro-2026\movil"

print("--- 1. PATCHING vite.config.js (Remove VitePWA) ---")
vite_cfg_path = os.path.join(base_dir, "vite.config.js")
clean_vite_config = """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import basicSsl from '@vitejs/plugin-basic-ssl';

export default defineConfig({
  plugins: [
    react(),
    basicSsl()
  ],
  server: {
    host: true,
    port: 5174
  }
});
"""
with open(vite_cfg_path, "w", encoding="utf-8") as f:
    f.write(clean_vite_config)
print("Saved clean vite.config.js without stale PWA precaching")


print("--- 2. PATCHING main.jsx (Add Cache Purger & Remove registerSW) ---")
main_jsx_path = os.path.join(base_dir, "src", "main.jsx")
clean_main_jsx = """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import { MobileProvider } from './context/MobileContext.jsx';

// Importar estilos base y de Leaflet
import 'leaflet/dist/leaflet.css';
import './index.css';

// PURGA TOTAL DE SERVICE WORKERS Y CACHÉ ANTERIOR (Evita que el teléfono muestre versiones viejas)
if (typeof window !== 'undefined') {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(registrations => {
      for (const registration of registrations) {
        registration.unregister().then(() => {
          console.log('[CachePurger] ServiceWorker antiguo desregistrado');
        });
      }
    });
  }

  if ('caches' in window) {
    caches.keys().then(keys => {
      if (keys.length > 0) {
        console.log('[CachePurger] Vaciando cachés antiguas de la app:', keys);
        Promise.all(keys.map(k => caches.delete(k))).then(() => {
          const busterKey = 'catastro_pwa_cache_purged_v461';
          if (!localStorage.getItem(busterKey)) {
            localStorage.setItem(busterKey, 'true');
            window.location.reload();
          }
        });
      }
    });
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <MobileProvider>
      <App />
    </MobileProvider>
  </React.StrictMode>
);
"""
with open(main_jsx_path, "w", encoding="utf-8") as f:
    f.write(clean_main_jsx)
print("Saved clean main.jsx with automatic cache purger")


print("--- 3. PATCHING index.html (Add Anti-Cache Meta Tags) ---")
index_html_path = os.path.join(base_dir, "index.html")
with open(index_html_path, "r", encoding="utf-8") as f:
    index_html = f.read()

anti_cache_meta = """    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
    <meta http-equiv="Pragma" content="no-cache" />
    <meta http-equiv="Expires" content="0" />"""

if "Cache-Control" not in index_html:
    index_html = index_html.replace(
        '<meta name="theme-color" content="#ffffff" />',
        '<meta name="theme-color" content="#ffffff" />\n' + anti_cache_meta
    )
    with open(index_html_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print("Added anti-cache meta tags to index.html")
else:
    print("Anti-cache meta tags already present in index.html")


print("--- 4. PATCHING MainActivity.java (Clear WebView Cache on Startup) ---")
main_act_path = os.path.join(base_dir, "android", "app", "src", "main", "java", "com", "gad", "catastromovil", "MainActivity.java")
with open(main_act_path, "r", encoding="utf-8") as f:
    main_act = f.read()

# Add WebSettings import if missing
if "import android.webkit.WebSettings;" not in main_act:
    main_act = main_act.replace(
        "import android.webkit.JavascriptInterface;",
        "import android.webkit.JavascriptInterface;\nimport android.webkit.WebSettings;"
    )

# Add clearCache and LOAD_NO_CACHE in onCreate
old_create_block = """        if (bridge != null && bridge.getWebView() != null) {
            bridge.getWebView().setBackgroundColor(Color.WHITE);
            bridge.getWebView().addJavascriptInterface(new AndroidBridgeInterface(), "AndroidBridge");
        }"""

new_create_block = """        if (bridge != null && bridge.getWebView() != null) {
            bridge.getWebView().setBackgroundColor(Color.WHITE);
            bridge.getWebView().clearCache(true);
            WebSettings webSettings = bridge.getWebView().getSettings();
            if (webSettings != null) {
                webSettings.setCacheMode(WebSettings.LOAD_NO_CACHE);
            }
            bridge.getWebView().addJavascriptInterface(new AndroidBridgeInterface(), "AndroidBridge");
        }"""

if old_create_block in main_act:
    main_act = main_act.replace(old_create_block, new_create_block, 1)
    with open(main_act_path, "w", encoding="utf-8") as f:
        f.write(main_act)
    print("Configured WebView clearCache and LOAD_NO_CACHE in MainActivity.java")
else:
    print("Warning: old_create_block not matched directly in MainActivity.java")


print("--- 5. BUMPING VERSION TO v4.6.1 (code 37) ---")
pkg_path = os.path.join(base_dir, "package.json")
with open(pkg_path, "r", encoding="utf-8") as f:
    pkg = json.load(f)
pkg["version"] = "4.6.1"
with open(pkg_path, "w", encoding="utf-8") as f:
    json.dump(pkg, f, indent=2)
print("Updated package.json to v4.6.1")

gradle_path = os.path.join(base_dir, "android", "app", "build.gradle")
with open(gradle_path, "r", encoding="utf-8") as f:
    gradle_code = f.read()
gradle_code = re.sub(r'versionCode\s+\d+', 'versionCode 37', gradle_code)
gradle_code = re.sub(r'versionName\s+"[^"]+"', 'versionName "4.6.1"', gradle_code)
with open(gradle_path, "w", encoding="utf-8") as f:
    f.write(gradle_code)
print("Updated build.gradle to versionCode 37, versionName 4.6.1")

print("=== CACHE FIX APPLIED SUCCESSFULLY ===")
