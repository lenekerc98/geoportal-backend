# -*- coding: utf-8 -*-
import os
import re
import json

base_dir = r"c:\LNCZ\proyecto-catastro-2026\movil"

print("--- 1. PATCHING MainActivity.java with physical directory purge ---")
main_act_path = os.path.join(base_dir, "android", "app", "src", "main", "java", "com", "gad", "catastromovil", "MainActivity.java")

clean_main_act = """package com.gad.catastromovil;

import android.content.Context;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.print.PrintAttributes;
import android.print.PrintDocumentAdapter;
import android.print.PrintManager;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.ServiceWorkerController;
import android.webkit.WebSettings;
import android.widget.Toast;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import com.getcapacitor.BridgeActivity;
import java.io.File;

public class MainActivity extends BridgeActivity {
    private long lastBackPressTime = 0;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        // Purgar carpetas físicas de Service Worker y caché HTTP ANTES de iniciar el WebView
        purgeStaleCacheDirectories();

        super.onCreate(savedInstanceState);
        configureSystemBars();

        if (bridge != null && bridge.getWebView() != null) {
            bridge.getWebView().setBackgroundColor(Color.WHITE);
            bridge.getWebView().clearCache(true);
            WebSettings webSettings = bridge.getWebView().getSettings();
            if (webSettings != null) {
                webSettings.setCacheMode(WebSettings.LOAD_NO_CACHE);
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                try {
                    ServiceWorkerController swController = ServiceWorkerController.getInstance();
                    if (swController != null && swController.getServiceWorkerWebSettings() != null) {
                        swController.getServiceWorkerWebSettings().setCacheMode(WebSettings.LOAD_NO_CACHE);
                    }
                } catch (Throwable t) {}
            }
            bridge.getWebView().addJavascriptInterface(new AndroidBridgeInterface(), "AndroidBridge");
        }
    }

    private void purgeStaleCacheDirectories() {
        try {
            File dataDir = new File(getApplicationInfo().dataDir);
            File[] targetsToDelete = new File[] {
                new File(dataDir, "app_webview/Default/Service Worker"),
                new File(dataDir, "app_webview/Service Worker"),
                new File(dataDir, "app_webview/Default/Cache"),
                new File(dataDir, "app_webview/Default/Code Cache"),
                new File(dataDir, "app_webview/Default/GPUCache"),
                new File(getCacheDir(), "org.chromium.android_webview"),
                new File(getCacheDir(), "WebView")
            };

            for (File dir : targetsToDelete) {
                if (dir != null && dir.exists()) {
                    deleteRecursive(dir);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private boolean deleteRecursive(File fileOrDirectory) {
        if (fileOrDirectory != null && fileOrDirectory.isDirectory()) {
            File[] children = fileOrDirectory.listFiles();
            if (children != null) {
                for (File child : children) {
                    deleteRecursive(child);
                }
            }
        }
        return fileOrDirectory != null && fileOrDirectory.delete();
    }

    @Override
    public void onResume() {
        super.onResume();
        configureSystemBars();
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            configureSystemBars();
        }
    }

    private void configureSystemBars() {
        try {
            // Indicar al sistema que ajuste la app dentro de las barras del sistema (no pantalla completa oculta)
            WindowCompat.setDecorFitsSystemWindows(getWindow(), true);
            getWindow().clearFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
            getWindow().clearFlags(WindowManager.LayoutParams.FLAG_TRANSLUCENT_STATUS);
            getWindow().addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
            getWindow().setStatusBarColor(Color.parseColor("#0f172a"));
            getWindow().setNavigationBarColor(Color.parseColor("#ffffff"));

            WindowInsetsControllerCompat insetsController = WindowCompat.getInsetsController(getWindow(), getWindow().getDecorView());
            if (insetsController != null) {
                // Forzar que la barra de notificaciones y navegación SIEMPRE se muestren
                insetsController.show(WindowInsetsCompat.Type.statusBars());
                insetsController.show(WindowInsetsCompat.Type.navigationBars());
                // false = iconos blancos de reloj/batería/notificaciones sobre fondo oscuro #0f172a
                insetsController.setAppearanceLightStatusBars(false);
                // true = iconos oscuros sobre barra de navegación inferior blanca
                insetsController.setAppearanceLightNavigationBars(true);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public class AndroidBridgeInterface {
        @JavascriptInterface
        public void print(String documentName) {
            runOnUiThread(() -> {
                try {
                    if (bridge != null && bridge.getWebView() != null) {
                        PrintManager printManager = (PrintManager) getSystemService(Context.PRINT_SERVICE);
                        if (printManager != null) {
                            String docName = (documentName != null && !documentName.isEmpty()) ? documentName : "Reporte_Planimetrico";
                            PrintDocumentAdapter printAdapter = bridge.getWebView().createPrintDocumentAdapter(docName);
                            PrintAttributes.Builder builder = new PrintAttributes.Builder();
                            builder.setMediaSize(PrintAttributes.MediaSize.ISO_A4.asLandscape());
                            builder.setMinMargins(PrintAttributes.Margins.NO_MARGINS);
                            builder.setColorMode(PrintAttributes.COLOR_MODE_COLOR);
                            printManager.print(docName, printAdapter, builder.build());
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            });
        }
    }

    @Override
    public void onBackPressed() {
        if (bridge != null && bridge.getWebView() != null) {
            // Disparar evento personalizado en JavaScript para manejar regreso sin salir de la app
            bridge.getWebView().evaluateJavascript(
                "(function() { " +
                "  var ev = new CustomEvent('androidHardwareBack', { cancelable: true }); " +
                "  var dispatched = window.dispatchEvent(ev); " +
                "  return ev.defaultPrevented; " +
                "})()",
                value -> {
                    // Si ningún componente en JS capturó el evento (ev.defaultPrevented == false):
                    if (!"true".equals(value)) {
                        long currentTime = System.currentTimeMillis();
                        if (currentTime - lastBackPressTime < 2000) {
                            super.onBackPressed();
                        } else {
                            lastBackPressTime = currentTime;
                            Toast.makeText(this, "Presiona atrás nuevamente para salir", Toast.LENGTH_SHORT).show();
                        }
                    }
                }
            );
        } else {
            super.onBackPressed();
        }
    }
}
"""

with open(main_act_path, "w", encoding="utf-8") as f:
    f.write(clean_main_act)
print("Saved MainActivity.java with physical directory cache purge")


print("--- 2. PATCHING index.html with inline SW and Cache purge script ---")
index_html_path = os.path.join(base_dir, "index.html")
clean_index_html = """<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="default" />
    <meta name="color-scheme" content="light" />
    <meta name="theme-color" content="#ffffff" />
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
    <meta http-equiv="Pragma" content="no-cache" />
    <meta http-equiv="Expires" content="0" />
    <script>
      // Purga inmediata de Service Workers y CacheStorage antes de montar la app
      if (typeof window !== 'undefined') {
        if ('serviceWorker' in navigator) {
          navigator.serviceWorker.getRegistrations().then(function(regs) {
            for (var i = 0; i < regs.length; i++) {
              regs[i].unregister();
            }
          });
        }
        if ('caches' in window) {
          caches.keys().then(function(names) {
            for (var i = 0; i < names.length; i++) {
              caches.delete(names[i]);
            }
          });
        }
      }
    </script>
    <link rel="icon" type="image/png" href="/logo_gad.png" />
    <link rel="apple-touch-icon" href="/logo_gad.png" />
    <title>Catastro Móvil 2026 | Campo Offline</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  </head>
  <body style="background-color: #ffffff; color: #0f172a; margin: 0; padding: 0;">
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""

with open(index_html_path, "w", encoding="utf-8") as f:
    f.write(clean_index_html)
print("Saved index.html with inline cache purger")


print("--- 3. BUMPING VERSION TO v4.6.3 (code 39) ---")
pkg_path = os.path.join(base_dir, "package.json")
with open(pkg_path, "r", encoding="utf-8") as f:
    pkg = json.load(f)
pkg["version"] = "4.6.3"
with open(pkg_path, "w", encoding="utf-8") as f:
    json.dump(pkg, f, indent=2)
print("Updated package.json to v4.6.3")

gradle_path = os.path.join(base_dir, "android", "app", "build.gradle")
with open(gradle_path, "r", encoding="utf-8") as f:
    gradle_code = f.read()
gradle_code = re.sub(r'versionCode\s+\d+', 'versionCode 39', gradle_code)
gradle_code = re.sub(r'versionName\s+"[^"]+"', 'versionName "4.6.3"', gradle_code)
with open(gradle_path, "w", encoding="utf-8") as f:
    f.write(gradle_code)
print("Updated build.gradle to versionCode 39, versionName 4.6.3")

print("=== AUTO CACHE PURGE APPLIED SUCCESSFULLY ===")
