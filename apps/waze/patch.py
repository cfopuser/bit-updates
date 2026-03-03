import os
import re
import sys
import glob

def patch_file(file_path, replacements):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        for pattern, replacement in replacements:
            # We use re.DOTALL to match across newlines
            content = re.sub(pattern, replacement, content, flags=re.DOTALL | re.MULTILINE)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[+] Successfully patched {file_path}")
    except Exception as e:
        print(f"[-] Error processing {file_path}: {e}")

def patch(target_dir: str) -> bool:
    print(f"[*] Searching for files to patch in {target_dir}...")

    # Rules mapping file paths (or parts of file paths) to a list of (regex_pattern, replacement)
    rules = [
        # XML resource fixes for compilation errors (AAPT2 strict checking on '0x0' flags)
        (
            "**/res/layout/*.xml",
            [
                (r'android:layout_gravity="0x0"', ""),
                (r'app:layout_gravity="0x0"', ""),
                (r'android:gravity="0x0"', ""),
                (r'app:gravity="0x0"', "")
            ]
        ),
        (
            "**/androidx/browser/customtabs/TrustedWebUtils.smali",
            [
                (
                    r"\.method public static launchAsTrustedWebActivity\(Landroid/content/Context;Landroidx/browser/customtabs/CustomTabsIntent;Landroid/net/Uri;\)V.*?\.end method",
                    """.method public static launchAsTrustedWebActivity(Landroid/content/Context;Landroidx/browser/customtabs/CustomTabsIntent;Landroid/net/Uri;)V
    .registers 3
    # Do nothing, preventing the browser from ever opening
    return-void
.end method"""
                ),
                (
                    r"\.method public static launchBrowserSiteSettings\(Landroid/content/Context;Landroidx/browser/customtabs/CustomTabsSession;Landroid/net/Uri;\)V.*?\.end method",
                    """.method public static launchBrowserSiteSettings(Landroid/content/Context;Landroidx/browser/customtabs/CustomTabsSession;Landroid/net/Uri;)V
    .registers 3
    # Do nothing
    return-void
.end method"""
                )
            ]
        ),
        (
            "**/com/waze/InternalWebBrowser.smali",
            [
                (
                    r"\.method protected onCreate\(Landroid/os/Bundle;\)V.*?\.end method",
                    """.method protected onCreate(Landroid/os/Bundle;)V
    .registers 3

    # Call the parent onCreate
    invoke-super {p0, p1}, Lcom/waze/web/SimpleWebActivity;->onCreate(Landroid/os/Bundle;)V

    # Close the activity immediately before it can load anything
    invoke-virtual {p0}, Landroid/app/Activity;->finish()V

    return-void
.end method"""
                )
            ]
        ),
        (
            "**/com/waze/sharedui/payment/PaymentWebActivity.smali",
            [
                (
                    r"\.method protected onCreate\(Landroid/os/Bundle;\)V.*?\.end method",
                    """.method protected onCreate(Landroid/os/Bundle;)V
    .registers 2

    # Call parent to prevent crashes
    invoke-super {p0, p1}, Lxi/c;->onCreate(Landroid/os/Bundle;)V

    # Close the payment activity immediately
    invoke-virtual {p0}, Landroid/app/Activity;->finish()V

    return-void
.end method"""
                )
            ]
        ),
        (
            "**/com/waze/sharedui/web/WazeWebView.smali",
            [
                (
                    r"\.method private M\(Ljava/lang/String;\)Z.*?\.end method",
                    """.method private M(Ljava/lang/String;)Z
    .registers 3

    # Always return false so the app thinks every URL is invalid/blocked
    const/4 v0, 0x0
    return v0
.end method"""
                ),
                (
                    r"\.method public final F\(Ljava/lang/String;\)V.*?\.end method",
                    """.method public final F(Ljava/lang/String;)V
    .registers 5

    iget-object v0, p0, Lcom/waze/sharedui/web/WazeWebView;->v:Lcom/waze/sharedui/web/a;

    if-nez v0, :cond_0
    return-void

    :cond_0
    # Blocked message HTML
    const-string v1, "<html><body style='background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;'><h1>Access Blocked</h1></body></html>"
    const-string v2, "text/html"
    const-string p1, "UTF-8"

    # Force load the blocked message instead of the URL
    invoke-virtual {v0, v1, v2, p1}, Landroid/webkit/WebView;->loadData(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V

    return-void
.end method"""
                ),
                (
                    r"\.method public final G\(Ljava/lang/String;Ljava/util/Map;\)V.*?\.end method",
                    """.method public final G(Ljava/lang/String;Ljava/util/Map;)V
    .registers 3
    # Redirect to the basic F method we just modified above
    invoke-virtual {p0, p1}, Lcom/waze/sharedui/web/WazeWebView;->F(Ljava/lang/String;)V
    return-void
.end method"""
                )
            ]
        ),
        (
            "**/com/waze/web/SimpleWebActivity.smali",
            [
                (
                    r"\.method protected n1\(Ljava/lang/String;\)V.*?\.end method",
                    """.method protected n1(Ljava/lang/String;)V
    .registers 5

    # Define the blocked message
    const-string v0, "<html><body style='display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;'><h1>Access Blocked</h1></body></html>"
    
    # Get the WebView instance (stored in field U)
    iget-object v1, p0, Lcom/waze/web/SimpleWebActivity;->U:Lcom/waze/sharedui/web/WazeWebView;

    if-eqz v1, :cond_0

    # Load the custom HTML string instead of the actual URL
    const-string v2, "text/html"
    const-string p1, "UTF-8"
    invoke-virtual {v1, v0, v2, p1}, Lcom/waze/sharedui/web/WazeWebView;->loadData(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V

    :cond_0
    return-void
.end method"""
                )
            ]
        )
    ]

    for pattern, replacements in rules:
        # Use glob to find matching files
        search_pattern = os.path.join(target_dir, pattern)
        matched_files = glob.glob(search_pattern, recursive=True)
        
        for file_path in matched_files:
            patch_file(file_path, replacements)
            
    return True

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    patch(target)