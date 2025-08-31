from copy import deepcopy
from typing import List, Dict, Literal, Union
import json

SeleniumCookie  = Dict[str, Union[str, int, bool, None]]
EditorCookie    = Dict[str, Union[str, float, bool, None]]

# ────────────────────────────────────────────────
# Table de correspondance
# ────────────────────────────────────────────────
SELENIUM_TO_CHROME_SAMESITE = {
    None:            "unspecified",   # ou laissez None si vous préférez
    "Lax":           "lax",
    "Strict":        "strict",
    "None":          "no_restriction",
}

CHROME_TO_SELENIUM_SAMESITE = {
    None:            None,            # Cookies-Editor peut mettre null
    "unspecified":   None,
    "lax":           "Lax",
    "strict":        "Strict",
    "no_restriction":"None",
}

# ─────────────────────────────────────────────────────────────
# 1) Selenium  ➜  Cookies-Editor
# ─────────────────────────────────────────────────────────────
def selenium_to_editor(cookies: List[SeleniumCookie]) -> List[EditorCookie]:
    """Convertit une liste de cookies au format Selenium vers
       le format « Cookies Editor » (extension navigateur)."""
    out: List[EditorCookie] = []

    for c in cookies:
        dst: EditorCookie = {}

        # Champs communs / renommés
        dst["domain"]           = c.get("domain")
        dst["name"]             = c.get("name")
        dst["path"]             = c.get("path", "/")
        dst["httpOnly"]         = c.get("httpOnly", False)
        dst["secure"]           = c.get("secure", False)
        # dst["sameSite"]         = c.get("sameSite")          # Peut rester None
        same_site_raw = c.get("sameSite")          # ex. "Lax"
        dst["sameSite"] = SELENIUM_TO_CHROME_SAMESITE.get(same_site_raw, "unspecified")
        dst["value"]            = c.get("value", "")

        # hostOnly : « true » si le domaine ne commence PAS par un point
        dst["hostOnly"]         = not str(dst["domain"]).startswith(".")

        # session / expirationDate
        expiry = c.get("expiry")
        if expiry is None:      # Cookie de session
            dst["session"]      = True
            dst["expirationDate"] = None
        else:
            dst["session"]      = False
            dst["expirationDate"] = float(expiry)            # l’extension accepte float

        # Champs sans équivalent direct
        dst["storeId"]          = None

        out.append(dst)
    return out


# ─────────────────────────────────────────────────────────────
# 2) Cookies-Editor  ➜  Selenium
# ─────────────────────────────────────────────────────────────
def editor_to_selenium(cookies: List[EditorCookie]) -> List[SeleniumCookie]:
    """Convertit une liste de cookies au format « Cookies Editor »
       vers le format Selenium/WebDriver."""
    out: List[SeleniumCookie] = []

    for c in cookies:
        dst: SeleniumCookie = {}

        # Champs communs / renommés
        dst["domain"]      = c.get("domain")
        dst["name"]        = c.get("name")
        dst["path"]        = c.get("path", "/")
        dst["httpOnly"]    = c.get("httpOnly", False)
        dst["secure"]      = c.get("secure", False)
        # dst["sameSite"]    = c.get("sameSite")               # Selenium accepte None
        same_site_raw = c.get("sameSite")          # ex. "lax"
        dst["sameSite"]  = CHROME_TO_SELENIUM_SAMESITE.get(same_site_raw)
        dst["value"]       = c.get("value", "")

        # expiry
        if not c.get("session", False):                      # pas un cookie de session
            exp = c.get("expirationDate")
            if exp is not None:
                dst["expiry"] = int(exp)                     # Selenium attend un int

        out.append(dst)
    return out


# ─────────────────────────────────────────────────────────────
# 3) Convertisseur générique pratique
# ─────────────────────────────────────────────────────────────
def convert_cookies(cookies: List[dict],
                    source: Literal["selenium", "editor"]) -> List[dict]:
    """Petit helper qui route vers la bonne fonction."""
    if source == "selenium":
        return selenium_to_editor(cookies)
    elif source == "editor":
        return editor_to_selenium(cookies)
    else:
        raise ValueError("source doit être 'selenium' ou 'editor'")
