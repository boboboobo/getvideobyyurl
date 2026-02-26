import time
import subprocess
import json
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# 👇 ここに対象のSharePoint動画ページのURLを貼る
# ==========================================
TARGET_PAGE_URL = f"************************************" 

# プロファイルのパス（前回作成したものを使用）
PROFILE_PATH = f"C******"

def main_downloader():
    # --- [フェーズ1] 探査機: マニフェストURLとCookieの確保 ---
    print("🚀 [Phase 1] 認証情報とストリームURLを解析中...")
    
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={PROFILE_PATH}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    # options.add_argument("--headless") # 画面を見たい場合はコメントアウト

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    manifest_url = ""
    cookie_header = ""
    file_name = "output_video.mp4"

    try:
        driver.get(TARGET_PAGE_URL)
        time.sleep(40) # 読み込み待機

        # g_fileInfo (動画情報オブジェクト) を取得
        file_info = driver.execute_script("return typeof g_fileInfo !== 'undefined' ? g_fileInfo : null;")

        if not file_info:
            print("❌ エラー: ログインできていないか、ページが間違っています。")
            return

        # ファイル名取得
        if file_info.get('name'):
            file_name = file_info['name']
            if not file_name.endswith(".mp4"): file_name += ".mp4"

        # ベースURLの取得
        base_url = file_info.get(".providerCdnTransformUrl") or file_info.get(".transformUrl")
        
        if base_url:
            # マニフェストURL（設計図）の構築
            parsed = urlparse(base_url)
            new_path = parsed.path.replace("thumbnail", "videomanifest")
            query = parse_qs(parsed.query)
            
            # ストリーミング用パラメータ（ここが重要）
            query.update({
                "action": ["Access"],
                "part": ["index"],
                "format": ["dash"], # 分割配信(DASH)を指定
                "useScf": ["true"],
                "pretranscode": ["0"],
                "transcodeahead": ["0"]
            })

            new_query = urlencode(query, doseq=True)
            manifest_url = urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, new_query, parsed.fragment))
            print(f"✅ 解析成功: {file_name}")
        
        # Cookieの取得（これがないとダウンロードできない）
        cookies = driver.get_cookies()
        cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

    except Exception as e:
        print(f"❌ 解析エラー: {e}")
        driver.quit()
        return
    finally:
        driver.quit()

    if not manifest_url:
        print("❌ マニフェストURLの生成に失敗しました。")
        return

    # --- [フェーズ2] 作業員: 分割ファイルのダウンロードと結合 ---
    print("\n🚀 [Phase 2] 分割ダウンロードと結合を開始します...")
    print("   (ログがたくさん流れますが、分割ファイルを処理している証拠です)")

    # yt-dlpコマンドの構築
    # -N 4 : 4分割並列ダウンロード
    # --verbose : 詳細ログを表示（分割処理が見えるように）
    cmd = [
        "yt-dlp",
        manifest_url,
        "--add-header", f"Cookie: {cookie_header}",
        "-o", file_name,
        "--no-check-certificate",
        "--concurrent-fragments", "4",
        # "--verbose" # ←これを有効にすると、裏で何個ファイルを落としてるか全部見えます
    ]

    try:
        subprocess.run(cmd)
        print(f"\n🎉 完了！ファイルはここにあります: {file_name}")
    except Exception as e:
        print(f"❌ ダウンロードエラー: {e}")

if __name__ == "__main__":
    main_downloader()